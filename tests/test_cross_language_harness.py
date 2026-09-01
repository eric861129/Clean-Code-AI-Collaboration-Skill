import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import evals.harness.cli as harness_cli
from evals.harness.anonymizer import build_review_packet
from evals.harness.cli import (
    _build_parser,
    _console_json,
    _desktop_dispatch_id,
    _invalidate_pilot,
    _next_desktop_attempt,
    _physical_run_id,
    _require_no_inflight_desktop_attempts,
    _run_document_path,
    _sanitize_persisted_text,
    _subject_client_contract,
    _validate_terminal_document,
)
from evals.harness.cli import (
    main as harness_main,
)
from evals.harness.desktop_subject import (
    DesktopSubjectValidationError,
    build_desktop_observation,
    desktop_subject_instruction,
    inspect_legacy_pending_newline_defect,
    load_desktop_dispatch,
    stage_desktop_subject,
    validate_desktop_report,
    write_attempt_receipt,
)
from evals.harness.diff_boundary import capture_diff, classify_paths
from evals.harness.evidence_recorder import record_subject_evidence
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest, validate_manifest
from evals.harness.models import (
    CommandResult,
    HarnessPaths,
    Rename,
    RunSlot,
    SubjectDispatch,
    Workspace,
)
from evals.harness.oracle_runner import baseline_acceptance_is_expected
from evals.harness.planner import build_run_slots, full_slots, pilot_slots
from evals.harness.process import run_process
from evals.harness.result_builder import build_public_result, can_retry
from evals.harness.subject_runner import build_prompt, run_subject

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "evals" / "manifests" / "v0.3.0-cross-language.json"


def _canonical_json_sha256(value: dict[str, object]) -> str:
    canonical_json = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def _downgrade_to_legacy_newline_defect(
    dispatch: SubjectDispatch,
    *,
    files_inspected: list[str],
    files_modified_claimed: list[str],
) -> dict[str, object]:
    prompt_path = dispatch.prompt_path
    logical_prompt = prompt_path.read_text(encoding="utf-8")
    prompt_path.write_bytes(logical_prompt.replace("\n", "\r\n").encode("utf-8"))
    payload = json.loads(dispatch.dispatch_path.read_text(encoding="utf-8"))
    payload.pop("prompt_encoding")
    payload.pop("prompt_line_endings")
    payload["schema_version"] = "desktop-subject-dispatch/v1"
    payload["prompt_sha256"] = hashlib.sha256(
        logical_prompt.encode("utf-8")
    ).hexdigest()
    payload.pop("dispatch_sha256")
    payload["dispatch_sha256"] = _canonical_json_sha256(payload)
    dispatch.dispatch_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = json.loads(dispatch.report_template_path.read_text(encoding="utf-8"))
    report.update(
        {
            "dispatch_sha256": payload["dispatch_sha256"],
            "prompt_sha256": payload["prompt_sha256"],
            "summary": "完成最小變更。",
            "files_inspected": files_inspected,
            "files_modified_claimed": files_modified_claimed,
            "commands_claimed": [],
        }
    )
    dispatch.report_path.write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )
    return payload


class CrossLanguageHarnessTests(unittest.TestCase):
    def test_manifest_builds_exactly_36_unique_slots(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slots = build_run_slots(manifest)

        self.assertEqual(36, len(slots))
        self.assertEqual(36, len({slot.run_id for slot in slots}))
        self.assertEqual(12, len(pilot_slots(slots)))
        self.assertEqual(24, len(full_slots(slots)))
        self.assertEqual(set(range(36)), {slot.order_index for slot in slots})

    def test_planner_order_is_reproducible_and_partitions_repetitions(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        first = build_run_slots(manifest)
        second = build_run_slots(manifest)

        self.assertEqual(first, second)
        self.assertEqual({1}, {slot.repetition for slot in pilot_slots(first)})
        self.assertEqual({2, 3}, {slot.repetition for slot in full_slots(first)})

    def test_manifest_rejects_unknown_arm_and_missing_fixture_sha(self) -> None:
        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        raw["arms"][0]["id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown arm"):
            validate_manifest(raw)

        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        raw["fixture_repository"]["commit"] = ""
        with self.assertRaisesRegex(ValueError, "40-character fixture commit"):
            validate_manifest(raw)

    def test_process_timeout_is_terminal_and_not_automatically_retried(self) -> None:
        result = run_process(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            cwd=ROOT,
            timeout_seconds=1,
        )

        self.assertTrue(result.timed_out)
        self.assertEqual("timeout", result.classification)
        self.assertEqual(1, result.attempt)

    def test_arm_prompts_only_contain_the_declared_difference(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        scenario = manifest.scenarios[0]
        control = build_prompt(scenario, "control")
        generic = build_prompt(scenario, "generic-clean-code")
        skill = build_prompt(scenario, "skill-v0.3.0")

        self.assertEqual(control + "\n\n請遵守 Clean Code 完成任務。", generic)
        self.assertIn("$clean-code-ai-collaboration", skill)
        self.assertNotIn("$clean-code-ai-collaboration", control)
        self.assertNotIn("$clean-code-ai-collaboration", generic)
        self.assertIn("已獲授權", control)

    def test_stage_desktop_subject_writes_immutable_dispatch_and_ignores_report(
        self,
    ) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = RunSlot(
            run_id="react-overdue-rule--control--r01",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            controller_dispatch_root = root / "controller-dispatches"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            (workspace_root / ".gitignore").write_text(
                ".benchmark-subject-report.json\n", encoding="utf-8"
            )
            (workspace_root / "subject.txt").write_text(
                "baseline\n", encoding="utf-8"
            )
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            baseline_commit = self._git(workspace_root, "rev-parse", "HEAD").strip()
            workspace = Workspace(workspace_root, artifact_dir, baseline_commit)

            dispatch = stage_desktop_subject(
                slot,
                manifest,
                workspace,
                generation=3,
                attempt=1,
                physical_run_id="run-aabbccddeeff0011",
                contract_sha256="b" * 64,
                scenario_contract_sha256="a" * 64,
                controller_dispatch_root=controller_dispatch_root,
            )

            self.assertTrue(dispatch.dispatch_path.is_file())
            self.assertTrue(dispatch.prompt_path.is_file())
            self.assertTrue(dispatch.report_template_path.is_file())
            dispatch_payload = json.loads(
                dispatch.dispatch_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                "desktop-subject-dispatch/v3",
                dispatch_payload["schema_version"],
            )
            self.assertEqual(controller_dispatch_root, dispatch.dispatch_path.parent)
            self.assertFalse((artifact_dir / "desktop-dispatch.json").exists())
            self.assertEqual(
                {"prompt.md", "subject-report.template.json"},
                {path.name for path in artifact_dir.iterdir()},
            )
            self.assertEqual("utf-8", dispatch_payload["prompt_encoding"])
            self.assertEqual("lf", dispatch_payload["prompt_line_endings"])
            prompt_bytes = dispatch.prompt_path.read_bytes()
            self.assertNotIn(b"\r", prompt_bytes)
            self.assertEqual(
                hashlib.sha256(prompt_bytes).hexdigest(),
                dispatch.prompt_sha256,
            )
            self.assertEqual(
                ".benchmark-subject-report.json",
                dispatch.report_relative_path,
            )
            template = json.loads(
                dispatch.report_template_path.read_text(encoding="utf-8")
            )
            self.assertEqual("desktop-subject-report/v1", template["schema_version"])
            self.assertEqual(dispatch.dispatch_sha256, template["dispatch_sha256"])
            self.assertEqual(workspace.baseline_commit, template["baseline_commit"])
            self.assertEqual(dispatch.prompt_sha256, template["prompt_sha256"])
            self.assertEqual(dispatch.contract_sha256, template["contract_sha256"])
            self.assertEqual(
                dispatch.scenario_contract_sha256,
                template["scenario_contract_sha256"],
            )
            self.assertEqual(dispatch.generation, template["generation"])
            self.assertEqual(dispatch.attempt, template["attempt"])
            reloaded = load_desktop_dispatch(dispatch.dispatch_path)
            self.assertEqual(dispatch.prompt_sha256, reloaded.prompt_sha256)
            instruction = desktop_subject_instruction(dispatch)
            self.assertIn(str(dispatch.prompt_path), instruction)
            self.assertIn(str(dispatch.report_template_path), instruction)
            self.assertNotIn(str(dispatch.dispatch_path), instruction)
            self.assertNotIn("$clean-code-ai-collaboration", instruction)
            self.assertNotIn(slot.arm_id, instruction)
            self.assertIn("若 Prompt 明確指定某個 Skill", instruction)
            self.assertIn("staged", instruction)
            self.assertIn("Workspace", instruction)
            self.assertIn(
                "files_inspected 與 files_modified_claimed 僅接受 Workspace "
                "repository-relative POSIX path",
                instruction,
            )
            self.assertIn("Workspace 外 staged Prompt 或 Report Template", instruction)
            self.assertIn(
                'commands_claimed=[{"command":"...","outcome":',
                instruction,
            )
            with self.assertRaises(FileExistsError):
                stage_desktop_subject(
                    slot,
                    manifest,
                    workspace,
                    generation=3,
                    attempt=1,
                    physical_run_id="run-aabbccddeeff0011",
                    contract_sha256="b" * 64,
                    scenario_contract_sha256="a" * 64,
                    controller_dispatch_root=controller_dispatch_root,
                )

            dispatch.report_path.write_text("{}", encoding="utf-8")
            self.assertEqual("", self._git(workspace_root, "status", "--short"))
            diff = capture_diff(workspace, manifest.scenarios[0])
            self.assertNotIn(
                ".benchmark-subject-report.json", diff.changed_paths
            )
            self.assertNotIn(".benchmark-subject-report.json", diff.diff)

            instruction = desktop_subject_instruction(dispatch)
            self.assertIn("references", instruction)
            self.assertIn("不得讀取其他 Skill", instruction)

            dispatch.prompt_path.write_text("tampered prompt", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prompt hash"):
                load_desktop_dispatch(dispatch.dispatch_path)

    def test_normal_loader_rejects_legacy_v1_dispatch_even_if_text_hash_matches(
        self,
    ) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = RunSlot(
            run_id="react-overdue-rule--control--r01",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            controller_dispatch_root = root / "controller-dispatches"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            (workspace_root / ".gitignore").write_text(
                ".benchmark-subject-report.json\n", encoding="utf-8"
            )
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            workspace = Workspace(
                workspace_root,
                artifact_dir,
                self._git(workspace_root, "rev-parse", "HEAD").strip(),
            )
            dispatch = stage_desktop_subject(
                slot,
                manifest,
                workspace,
                generation=3,
                attempt=1,
                physical_run_id="run-aabbccddeeff0011",
                contract_sha256="b" * 64,
                scenario_contract_sha256="a" * 64,
                controller_dispatch_root=controller_dispatch_root,
            )
            legacy_prompt = dispatch.prompt_path.read_text(encoding="utf-8")
            windows_prompt_bytes = legacy_prompt.replace("\n", "\r\n").encode(
                "utf-8"
            )
            dispatch.prompt_path.write_bytes(windows_prompt_bytes)
            v2_payload = json.loads(
                dispatch.dispatch_path.read_text(encoding="utf-8")
            )
            v2_payload["prompt_sha256"] = hashlib.sha256(
                windows_prompt_bytes
            ).hexdigest()
            v2_payload.pop("dispatch_sha256")
            v2_payload["dispatch_sha256"] = _canonical_json_sha256(v2_payload)
            v2_path = artifact_dir / "v2-crlf-desktop-dispatch.json"
            v2_path.write_text(
                json.dumps(v2_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "prompt hash"):
                load_desktop_dispatch(v2_path)

            legacy_payload = dict(v2_payload)
            legacy_payload.pop("prompt_encoding")
            legacy_payload.pop("prompt_line_endings")
            legacy_payload["schema_version"] = "desktop-subject-dispatch/v1"
            legacy_payload["prompt_sha256"] = hashlib.sha256(
                legacy_prompt.encode("utf-8")
            ).hexdigest()
            legacy_payload.pop("dispatch_sha256")
            legacy_payload["dispatch_sha256"] = _canonical_json_sha256(
                legacy_payload
            )
            legacy_path = artifact_dir / "legacy-desktop-dispatch.json"
            legacy_path.write_text(
                json.dumps(legacy_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "v3"):
                load_desktop_dispatch(legacy_path)

    def test_private_dispatch_index_loads_only_controller_dispatch(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = RunSlot(
            run_id="react-overdue-rule--control--r01",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs_root = root / ".benchmark-runs"
            physical_run_id = "run-aabbccddeeff0011"
            workspace_root = runs_root / "workspaces" / physical_run_id
            artifact_dir = runs_root / "artifacts" / physical_run_id
            controller_dispatch_root = runs_root / "desktop-controller-dispatches"
            dispatch_index_root = runs_root / "desktop-dispatches"
            workspace_root.mkdir(parents=True)
            artifact_dir.mkdir(parents=True)
            (workspace_root / ".gitignore").write_text(
                ".benchmark-subject-report.json\n", encoding="utf-8"
            )
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            workspace = Workspace(
                workspace_root,
                artifact_dir,
                self._git(workspace_root, "rev-parse", "HEAD").strip(),
            )
            dispatch = stage_desktop_subject(
                slot,
                manifest,
                workspace,
                generation=3,
                attempt=1,
                physical_run_id=physical_run_id,
                contract_sha256="b" * 64,
                scenario_contract_sha256="a" * 64,
                controller_dispatch_root=controller_dispatch_root,
            )

            with (
                patch.object(harness_cli, "RUNS_ROOT", runs_root),
                patch.object(harness_cli, "DISPATCH_ROOT", dispatch_index_root),
                patch.object(
                    harness_cli,
                    "CONTROLLER_DISPATCH_ROOT",
                    controller_dispatch_root,
                ),
            ):
                index_path = harness_cli._write_dispatch_index(dispatch)
                index = json.loads(index_path.read_text(encoding="utf-8"))
                self.assertEqual("desktop-dispatch-index/v2", index["schema_version"])
                self.assertEqual(
                    (
                        "desktop-controller-dispatches/"
                        f"{dispatch.dispatch_id}.json"
                    ),
                    index["dispatch_path"],
                )
                self.assertEqual(
                    dispatch,
                    harness_cli._load_dispatch_by_id(dispatch.dispatch_id),
                )

                index["schema_version"] = "desktop-dispatch-index/v1"
                index_path.write_text(
                    json.dumps(index, ensure_ascii=False), encoding="utf-8"
                )
                with self.assertRaisesRegex(ValueError, "v2"):
                    harness_cli._load_dispatch_by_id(dispatch.dispatch_id)
                index["schema_version"] = "desktop-dispatch-index/v2"

                staged_dispatch_path = artifact_dir / "desktop-dispatch.json"
                staged_dispatch_path.write_text(
                    dispatch.dispatch_path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                index["dispatch_path"] = (
                    f"artifacts/{physical_run_id}/desktop-dispatch.json"
                )
                index_path.write_text(
                    json.dumps(index, ensure_ascii=False), encoding="utf-8"
                )
                with self.assertRaisesRegex(ValueError, "private controller"):
                    harness_cli._load_dispatch_by_id(dispatch.dispatch_id)

    def test_legacy_inspector_accepts_only_the_known_windows_newline_defect(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            prompt_path = artifact_dir / "prompt.md"
            prompt_path.write_bytes(b"line one\r\nline two\r\n")
            baseline = "a" * 40
            logical_prompt_sha256 = hashlib.sha256(
                b"line one\nline two\n"
            ).hexdigest()
            payload: dict[str, object] = {
                "schema_version": "desktop-subject-dispatch/v1",
                "dispatch_id": (
                    "desktop-dispatch-react-overdue-rule--control--r01--g03--a01"
                ),
                "logical_run_id": "react-overdue-rule--control--r01",
                "physical_run_id": "run-aabbccddeeff0011",
                "scenario_id": "react-overdue-rule",
                "generation": 3,
                "attempt": 1,
                "workspace_root": str(workspace_root),
                "artifact_directory": str(artifact_dir),
                "baseline_commit": baseline,
                "prompt_sha256": logical_prompt_sha256,
                "contract_sha256": "b" * 64,
                "scenario_contract_sha256": "c" * 64,
                "fixture_commit": "d" * 40,
                "skill_commit": "e" * 40,
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "executor": {
                    "kind": "codex-desktop-collaboration",
                    "dispatch_mode": "external-collaboration-subagent",
                    "network_enforcement": "not_available",
                    "telemetry": "not_available",
                },
                "report_relative_path": ".benchmark-subject-report.json",
                "report_template_relative_path": "subject-report.template.json",
            }
            payload["dispatch_sha256"] = _canonical_json_sha256(payload)
            dispatch_path = artifact_dir / "desktop-dispatch.json"
            dispatch_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            report = {
                "schema_version": "desktop-subject-report/v1",
                "dispatch_sha256": payload["dispatch_sha256"],
                "baseline_commit": baseline,
                "prompt_sha256": logical_prompt_sha256,
                "contract_sha256": "b" * 64,
                "scenario_contract_sha256": "c" * 64,
                "generation": 3,
                "attempt": 1,
                "completion": "completed",
                "summary": "完成。",
                "files_inspected": [],
                "files_modified_claimed": [],
                "commands_claimed": [
                    ".venv\\Scripts\\python.exe -m pytest -q tests (passed)"
                ],
                "telemetry": "not_available",
            }
            (workspace_root / ".benchmark-subject-report.json").write_text(
                json.dumps(report, ensure_ascii=False), encoding="utf-8"
            )

            defect = inspect_legacy_pending_newline_defect(dispatch_path)
            self.assertEqual(logical_prompt_sha256, defect.prompt_sha256)
            self.assertNotEqual(
                logical_prompt_sha256,
                hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
            )

            prompt_path.write_bytes(b"line one\nline two\n")
            with self.assertRaisesRegex(ValueError, "newline defect"):
                inspect_legacy_pending_newline_defect(dispatch_path)

    def test_legacy_pending_newline_defect_creates_precollection_invalidation(
        self,
    ) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        scenario_id = "fastapi-provider-boundary"
        slot = next(
            candidate
            for candidate in pilot_slots(build_run_slots(manifest))
            if candidate.scenario_id == scenario_id and candidate.arm_id == "control"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs_root = root / ".benchmark-runs"
            physical_run_id = "run-494c594491bdbf9e"
            workspace_root = runs_root / "workspaces" / physical_run_id
            artifact_dir = runs_root / "artifacts" / physical_run_id
            workspace_root.mkdir(parents=True)
            artifact_dir.mkdir(parents=True)
            (workspace_root / ".gitignore").write_text(
                ".benchmark-subject-report.json\n", encoding="utf-8"
            )
            (workspace_root / "app.py").write_text("baseline\n", encoding="utf-8")
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            baseline_commit = self._git(
                workspace_root, "rev-parse", "HEAD"
            ).strip()
            prompt_path = artifact_dir / "prompt.md"
            prompt_path.write_bytes(b"first line\r\nsecond line\r\n")
            logical_prompt_sha256 = hashlib.sha256(
                b"first line\nsecond line\n"
            ).hexdigest()
            dispatch_id = _desktop_dispatch_id(slot, 3, 1)
            legacy_payload: dict[str, object] = {
                "schema_version": "desktop-subject-dispatch/v1",
                "dispatch_id": dispatch_id,
                "logical_run_id": slot.run_id,
                "physical_run_id": physical_run_id,
                "scenario_id": scenario_id,
                "generation": 3,
                "attempt": 1,
                "workspace_root": str(workspace_root),
                "artifact_directory": str(artifact_dir),
                "baseline_commit": baseline_commit,
                "prompt_sha256": logical_prompt_sha256,
                "contract_sha256": "b" * 64,
                "scenario_contract_sha256": "c" * 64,
                "fixture_commit": manifest.fixture_commit,
                "skill_commit": manifest.skill_commit,
                "model": manifest.model,
                "reasoning_effort": manifest.reasoning_effort,
                "executor": dict(manifest.subject_executor),
                "report_relative_path": ".benchmark-subject-report.json",
                "report_template_relative_path": "subject-report.template.json",
            }
            legacy_payload["dispatch_sha256"] = _canonical_json_sha256(
                legacy_payload
            )
            dispatch_path = artifact_dir / "desktop-dispatch.json"
            dispatch_path.write_text(
                json.dumps(legacy_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report = {
                "schema_version": "desktop-subject-report/v1",
                "dispatch_sha256": legacy_payload["dispatch_sha256"],
                "baseline_commit": baseline_commit,
                "prompt_sha256": logical_prompt_sha256,
                "contract_sha256": "b" * 64,
                "scenario_contract_sha256": "c" * 64,
                "generation": 3,
                "attempt": 1,
                "completion": "completed",
                "summary": "完成最小變更。",
                "files_inspected": ["app.py"],
                "files_modified_claimed": ["app.py"],
                "commands_claimed": [],
                "telemetry": "not_available",
            }
            report_path = workspace_root / ".benchmark-subject-report.json"
            report_path.write_text(
                json.dumps(report, ensure_ascii=False), encoding="utf-8"
            )
            dispatch_index = (
                runs_root / "desktop-dispatches" / f"{dispatch_id}.json"
            )
            dispatch_index.parent.mkdir(parents=True)
            dispatch_index.write_text(
                json.dumps(
                    {
                        "schema_version": "desktop-dispatch-index/v1",
                        "dispatch_id": dispatch_id,
                        "dispatch_sha256": legacy_payload["dispatch_sha256"],
                        "dispatch_path": (
                            f"artifacts/{physical_run_id}/desktop-dispatch.json"
                        ),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            campaign_state = runs_root / "campaign-state.json"
            campaign_state.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "scenarios": {scenario_id: {"generation": 3}},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            original_dispatch = dispatch_path.read_bytes()
            original_report = report_path.read_bytes()
            paths = HarnessPaths(
                repository_root=root,
                runs_root=runs_root,
                fixture_clone=root / "fixture",
                skill_repository=root,
            )
            current_contract = {"schema_version": "test-contract"}

            with (
                patch.object(harness_cli, "RUNS_ROOT", runs_root),
                patch.object(
                    harness_cli,
                    "DISPATCH_ROOT",
                    runs_root / "desktop-dispatches",
                ),
                patch.object(
                    harness_cli,
                    "ATTEMPT_RECEIPTS_ROOT",
                    runs_root / "desktop-attempt-receipts",
                ),
                patch.object(
                    harness_cli,
                    "RUN_DOCUMENTS",
                    runs_root / "run-documents",
                ),
                patch.object(
                    harness_cli,
                    "INVALIDATIONS_ROOT",
                    runs_root / "invalidations",
                ),
                patch.object(
                    harness_cli,
                    "CAMPAIGN_STATE_PATH",
                    campaign_state,
                ),
                patch.object(
                    harness_cli,
                    "FREEZE_ROOT",
                    runs_root / "contract-freezes",
                ),
                patch.object(
                    harness_cli,
                    "_freeze_document",
                    return_value=current_contract,
                ),
                patch.object(
                    harness_cli,
                    "_scenario_contract_sha256",
                    return_value="f" * 64,
                ),
            ):
                def invalidate() -> None:
                    _invalidate_pilot(
                        manifest,
                        paths,
                        scenario_id,
                        "prompt_hash_newline_defect",
                        legacy_pending_dispatch=dispatch_id,
                    )

                receipt_path = (
                    runs_root
                    / "desktop-attempt-receipts"
                    / slot.run_id
                    / "g03--a01.json"
                )
                receipt_path.parent.mkdir(parents=True)
                receipt_path.write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "receipt invariant"):
                    invalidate()
                receipt_path.unlink()

                terminal_path = (
                    runs_root
                    / "run-documents"
                    / scenario_id
                    / f"{slot.run_id}--g03.json"
                )
                terminal_path.parent.mkdir(parents=True)
                terminal_path.write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "terminal run document"):
                    invalidate()
                terminal_path.unlink()

                other_slot = next(
                    candidate
                    for candidate in pilot_slots(build_run_slots(manifest))
                    if candidate.scenario_id == scenario_id
                    and candidate.run_id != slot.run_id
                )
                other_terminal_path = (
                    runs_root
                    / "run-documents"
                    / scenario_id
                    / f"{other_slot.run_id}--g03.json"
                )
                other_terminal_path.write_text("{}", encoding="utf-8")
                state_before_rejection = campaign_state.read_bytes()
                with self.assertRaisesRegex(RuntimeError, "other pilot slot"):
                    invalidate()
                self.assertEqual(
                    state_before_rejection,
                    campaign_state.read_bytes(),
                )
                self.assertEqual(original_dispatch, dispatch_path.read_bytes())
                self.assertEqual(original_report, report_path.read_bytes())
                other_terminal_path.unlink()

                invalidate()

            state = json.loads(campaign_state.read_text(encoding="utf-8"))
            recovered = state["scenarios"][scenario_id]
            self.assertEqual(4, recovered["generation"])
            self.assertEqual("c" * 64, recovered["must_change_from"])
            invalidation_path = runs_root / recovered["invalidation"]
            invalidation = json.loads(invalidation_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "desktop-pre-collection-invalidation/v1",
                invalidation["schema_version"],
            )
            self.assertEqual("not_run", invalidation["candidate_evaluation"])
            self.assertEqual(dispatch_id, invalidation["dispatch_id"])
            self.assertEqual(baseline_commit, invalidation["workspace_head"])
            self.assertEqual("c" * 64, invalidation["must_change_from"])
            self.assertEqual(
                "f" * 64,
                invalidation["replacement_scenario_contract_sha256"],
            )
            self.assertFalse(
                (
                    runs_root
                    / "run-documents"
                    / scenario_id
                    / f"{slot.run_id}--g03.json"
                ).exists()
            )
            self.assertFalse(
                (
                    runs_root
                    / "desktop-attempt-receipts"
                    / slot.run_id
                    / "g03--a01.json"
                ).exists()
            )
            self.assertEqual(original_dispatch, dispatch_path.read_bytes())
            self.assertEqual(original_report, report_path.read_bytes())

    def test_diff_boundary_excludes_subject_report_without_gitignore(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            (workspace_root / "subject.txt").write_text("baseline\n", encoding="utf-8")
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            workspace = Workspace(
                workspace_root,
                artifact_dir,
                self._git(workspace_root, "rev-parse", "HEAD").strip(),
            )

            (workspace_root / ".benchmark-subject-report.json").write_text(
                '{"unignored": true}', encoding="utf-8"
            )
            (workspace_root / "subject.txt").write_text("candidate\n", encoding="utf-8")
            diff = capture_diff(workspace, manifest.scenarios[0])

            self.assertIn("subject.txt", diff.changed_paths)
            self.assertNotIn(".benchmark-subject-report.json", diff.changed_paths)
            self.assertNotIn(".benchmark-subject-report.json", diff.diff)

    def test_desktop_report_requires_dispatch_baseline_and_prompt_hash(
        self,
    ) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = RunSlot(
            run_id="react-overdue-rule--control--r01",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            controller_dispatch_root = root / "controller-dispatches"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            (workspace_root / ".gitignore").write_text(
                ".benchmark-subject-report.json\n", encoding="utf-8"
            )
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            workspace = Workspace(
                workspace_root,
                artifact_dir,
                self._git(workspace_root, "rev-parse", "HEAD").strip(),
            )
            dispatch = stage_desktop_subject(
                slot,
                manifest,
                workspace,
                generation=3,
                attempt=1,
                physical_run_id="run-aabbccddeeff0011",
                contract_sha256="b" * 64,
                scenario_contract_sha256="a" * 64,
                controller_dispatch_root=controller_dispatch_root,
            )
            with self.assertRaises(DesktopSubjectValidationError) as missing_report:
                validate_desktop_report(dispatch)
            self.assertEqual(
                "candidate_incomplete", missing_report.exception.reason
            )
            self.assertFalse(can_retry(missing_report.exception.reason, 1))
            report = {
                "schema_version": "desktop-subject-report/v1",
                "dispatch_sha256": "wrong",
                "baseline_commit": workspace.baseline_commit,
                "prompt_sha256": dispatch.prompt_sha256,
                "contract_sha256": dispatch.contract_sha256,
                "scenario_contract_sha256": dispatch.scenario_contract_sha256,
                "generation": dispatch.generation,
                "attempt": dispatch.attempt,
                "completion": "completed",
                "summary": "完成最小修改。",
                "files_inspected": ["subject.txt"],
                "files_modified_claimed": [],
                "commands_claimed": [],
                "telemetry": "not_available",
            }
            dispatch.report_path.write_text(
                json.dumps(report, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaises(DesktopSubjectValidationError) as invalid_report:
                validate_desktop_report(dispatch)
            self.assertEqual("invalid_claim", invalid_report.exception.reason)
            self.assertFalse(can_retry(invalid_report.exception.reason, 1))

            report["dispatch_sha256"] = dispatch.dispatch_sha256
            report["files_inspected"] = [str(dispatch.prompt_path)]
            report["files_modified_claimed"] = [
                str(dispatch.report_template_path)
            ]
            dispatch.report_path.write_text(
                json.dumps(report, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                DesktopSubjectValidationError, "non-relative path"
            ):
                validate_desktop_report(dispatch)

            report["files_inspected"] = ["subject.txt"]
            report["files_modified_claimed"] = []
            dispatch.report_path.write_text(
                json.dumps(report, ensure_ascii=False), encoding="utf-8"
            )
            observation = build_desktop_observation(
                dispatch,
                outcome="completed",
                elapsed_seconds=None,
                subject_thread_id="thread-private",
            )
            self.assertEqual("not_available", observation.telemetry)
            self.assertEqual("codex-desktop-collaboration", observation.executor)
            self._git(workspace_root, "commit", "--allow-empty", "-m", "drift")
            for outcome in ("timeout", "infrastructure_failure"):
                with self.assertRaises(DesktopSubjectValidationError) as drift:
                    build_desktop_observation(
                        dispatch,
                        outcome=outcome,
                        elapsed_seconds=None,
                        subject_thread_id="thread-private",
                    )
                self.assertEqual("invalid_claim", drift.exception.reason)
                self.assertFalse(can_retry(drift.exception.reason, 1))

    def test_desktop_attempt_receipt_is_immutable_and_retry_ready(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = RunSlot(
            run_id="react-overdue-rule--control--r01",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            controller_dispatch_root = root / "controller-dispatches"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            (workspace_root / ".gitignore").write_text(
                ".benchmark-subject-report.json\n", encoding="utf-8"
            )
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "-A")
            self._git(workspace_root, "commit", "-m", "baseline")
            workspace = Workspace(
                workspace_root,
                artifact_dir,
                self._git(workspace_root, "rev-parse", "HEAD").strip(),
            )
            dispatch = stage_desktop_subject(
                slot,
                manifest,
                workspace,
                generation=3,
                attempt=1,
                physical_run_id="run-aabbccddeeff0011",
                contract_sha256="b" * 64,
                scenario_contract_sha256="a" * 64,
                controller_dispatch_root=controller_dispatch_root,
            )
            receipt_root = root / "attempts"
            receipt = write_attempt_receipt(
                dispatch,
                receipt_root,
                outcome="infrastructure_failure",
                reason="environment_error",
                elapsed_seconds=None,
                subject_thread_id="thread-private",
            )

            self.assertTrue(receipt.is_file())
            self.assertEqual(2, _next_desktop_attempt(slot, 3, receipt_root))
            with self.assertRaises(FileExistsError):
                write_attempt_receipt(
                    dispatch,
                    receipt_root,
                    outcome="infrastructure_failure",
                    reason="environment_error",
                    elapsed_seconds=None,
                    subject_thread_id="thread-private",
                )

    def test_invalidation_rejects_pending_or_retry_required_desktop_attempt(
        self,
    ) -> None:
        slot = RunSlot(
            run_id="react-overdue-rule--control--r01",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dispatch_root = root / "dispatches"
            receipts_root = root / "receipts"
            run_documents_root = root / "run-documents"
            dispatch_root.mkdir()
            pending = dispatch_root / (
                "desktop-dispatch-react-overdue-rule--control--r01"
                "--g03--a01.json"
            )
            pending.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "pending Desktop dispatch"):
                _require_no_inflight_desktop_attempts(
                    slot,
                    3,
                    dispatch_root,
                    receipts_root,
                    run_documents_root,
                )

            receipt = receipts_root / slot.run_id / "g03--a01.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps(
                    {
                        "attempt": 1,
                        "outcome": "infrastructure_failure",
                        "reason": "environment_error",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "retry-required"):
                _require_no_inflight_desktop_attempts(
                    slot,
                    3,
                    dispatch_root,
                    receipts_root,
                    run_documents_root,
                )

    def test_stub_subject_records_jsonl_last_message_diff_and_terminal_state(
        self,
    ) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            (workspace_root / "allowed.txt").write_text(
                "baseline\n", encoding="utf-8"
            )
            self._git(workspace_root, "init", "--initial-branch=main")
            self._git(workspace_root, "config", "user.name", "Benchmark Runner")
            self._git(
                workspace_root,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            self._git(workspace_root, "add", "allowed.txt")
            self._git(workspace_root, "commit", "-m", "baseline")
            baseline_commit = self._git(workspace_root, "rev-parse", "HEAD").strip()

            workspace = Workspace(workspace_root, artifact_dir, baseline_commit)
            slot = RunSlot(
                run_id="stub-run",
                scenario_id="react-overdue-rule",
                language="typescript-react",
                arm_id="control",
                repetition=1,
                order_index=0,
            )
            stub = (
                "import json, pathlib, sys; "
                "pathlib.Path('allowed.txt').write_text('candidate\\n'); "
                "pathlib.Path(sys.argv[1]).write_text('done', encoding='utf-8'); "
                "print(json.dumps({'type': 'turn.completed', "
                "'usage': {'input_tokens': 5, 'output_tokens': 3}})); "
                "print(json.dumps({'type': 'tool_call'}))"
            )
            observation = run_subject(
                slot,
                manifest,
                workspace,
                command_override=[
                    sys.executable,
                    "-c",
                    stub,
                    str(artifact_dir / "last-message.md"),
                ],
                attempt=2,
            )
            evidence_path = record_subject_evidence(observation, workspace)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

            self.assertEqual("completed", evidence["terminal_state"])
            self.assertIn("allowed.txt", evidence["diff"])
            self.assertTrue(observation.raw_jsonl_path.is_file())
            self.assertEqual("done", observation.last_message_path.read_text())
            self.assertEqual(1, evidence["telemetry"]["tool_call_count"])
            self.assertEqual(2, evidence["command"]["attempt"])
            self.assertEqual(
                {"input_tokens": 5, "output_tokens": 3},
                evidence["telemetry"]["token_usage"],
            )
            self.assertEqual(
                evidence_path,
                record_subject_evidence(observation, workspace),
            )
            (workspace_root / "allowed.txt").write_text(
                "changed again\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(FileExistsError, "immutable"):
                record_subject_evidence(observation, workspace)

    def test_workspace_builder_refuses_to_overwrite_existing_run(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = build_run_slots(manifest)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs_root = root / "runs"
            (runs_root / "workspaces" / slot.run_id).mkdir(parents=True)
            paths = HarnessPaths(
                repository_root=ROOT,
                runs_root=runs_root,
                fixture_clone=root / "fixtures",
                skill_repository=ROOT,
            )

            with self.assertRaisesRegex(FileExistsError, "already exists"):
                build_workspace(slot, manifest, paths)

    def test_existing_fixture_clone_fetches_new_pinned_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture-origin"
            fixture_clone = root / "fixture-cache"
            source.mkdir()
            self._git(source, "init", "--initial-branch=main")
            self._git(source, "config", "user.name", "Benchmark Runner")
            self._git(
                source,
                "config",
                "user.email",
                "benchmark@example.invalid",
            )
            (source / "fixture.txt").write_text("v1\n", encoding="utf-8")
            self._git(source, "add", "fixture.txt")
            self._git(source, "commit", "-m", "fixture v1")
            self._git(source, "tag", "-a", "cross-language-v1", "-m", "v1")
            self._git(root, "clone", "--no-checkout", str(source), str(fixture_clone))

            (source / "fixture.txt").write_text("v2\n", encoding="utf-8")
            self._git(source, "add", "fixture.txt")
            self._git(source, "commit", "-m", "fixture v2")
            self._git(source, "tag", "-a", "cross-language-v2", "-m", "v2")
            fixture_commit = self._git(source, "rev-parse", "HEAD").strip()

            manifest = replace(
                load_manifest(MANIFEST_PATH),
                fixture_url=str(source),
                fixture_tag="cross-language-v2",
                fixture_commit=fixture_commit,
            )
            paths = HarnessPaths(
                repository_root=root,
                runs_root=root / ".benchmark-runs",
                fixture_clone=fixture_clone,
                skill_repository=ROOT,
            )

            harness_cli._ensure_fixture_clone(manifest, paths)

            self.assertEqual(
                fixture_commit,
                self._git(fixture_clone, "rev-parse", "HEAD").strip(),
            )
            self.assertEqual(
                fixture_commit,
                self._git(
                    fixture_clone,
                    "rev-parse",
                    "cross-language-v2^{}",
                ).strip(),
            )

    def test_rename_requires_source_and_destination_to_be_allowed(self) -> None:
        evidence = classify_paths(
            changed=["src/allowed.ts"],
            renamed=[Rename("src/allowed.ts", "scripts/escape.ts")],
            allowed_exact={"src/allowed.ts"},
            allowed_patterns=(),
        )

        self.assertEqual(("scripts/escape.ts",), evidence.outside_boundary)

    def test_result_requires_all_36_terminal_states(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slots = build_run_slots(manifest)

        with self.assertRaisesRegex(ValueError, "36 terminal states"):
            build_public_result(
                slots,
                run_documents=[],
                benchmark_version=manifest.benchmark_version,
            )

    def test_result_rejects_invalidated_pilot_as_final_evidence(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slots = build_run_slots(manifest)
        documents = [
            {
                "run_id": slot.run_id,
                "terminal_state": "passed",
            }
            for slot in slots
        ]
        documents[0]["terminal_state"] = "invalidated_pilot"

        with self.assertRaisesRegex(ValueError, "invalid terminal state"):
            build_public_result(
                slots,
                documents,
                benchmark_version=manifest.benchmark_version,
            )

    def test_result_uses_manifest_benchmark_version(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slots = build_run_slots(manifest)
        documents = [
            {
                "run_id": slot.run_id,
                "terminal_state": "passed",
            }
            for slot in slots
        ]

        result = build_public_result(
            slots,
            documents,
            benchmark_version=manifest.benchmark_version,
        )

        self.assertEqual(manifest.benchmark_version, result["benchmark_version"])

    def test_run_document_generation_preserves_invalidated_evidence(self) -> None:
        slot = RunSlot(
            run_id="sample",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )

        self.assertNotEqual(
            _run_document_path(slot, 1),
            _run_document_path(slot, 2),
        )

    def test_physical_run_id_is_short_and_attempt_specific(self) -> None:
        first = _physical_run_id("logical-run", 1, "a" * 64, 1)
        second = _physical_run_id("logical-run", 1, "a" * 64, 2)

        self.assertLessEqual(len(first), 20)
        self.assertNotEqual(first, second)

    def test_review_packet_does_not_reveal_arm_or_run_order(self) -> None:
        sample_run = {
            "run_id": "react-overdue-rule--skill-v0.3.0--r01",
            "arm_id": "skill-v0.3.0",
            "repetition": 1,
            "task": "Change the High Priority overdue boundary.",
            "must_preserve": ["Completed stays excluded"],
            "diff": "diff --git a/src/overdue.ts b/src/overdue.ts",
            "oracle_results": [],
            "automatic_failure_reasons": [],
            "blind_spots": ["Small fixture"],
        }

        packet = build_review_packet(sample_run, candidate_id="candidate-7f2a")
        serialized = json.dumps(packet, ensure_ascii=False)

        self.assertNotIn("skill-v0.3.0", serialized)
        self.assertNotIn("generic-clean-code", serialized)
        self.assertNotIn("repetition", serialized)
        self.assertEqual("candidate-7f2a", packet["candidate_id"])

    def test_review_packet_redacts_arm_from_paths_and_oracle_commands(self) -> None:
        sample_run = {
            "run_id": "react-overdue-rule--skill-v0.3.0--r01",
            "arm_id": "skill-v0.3.0",
            "task": "Change the overdue boundary.",
            "diff": (
                "diff --git "
                "a/.agents/skills/clean-code-ai-collaboration/SKILL.md "
                "b/.agents/skills/clean-code-ai-collaboration/SKILL.md"
            ),
            "oracle_results": [
                {
                    "args": [
                        "D:/repo/.benchmark-runs/workspaces/"
                        "react-overdue-rule--SKILL-V0.3.0--r01/.venv/python",
                        "/Users/reviewer/repo/.benchmark-runs/workspaces/"
                        "react-overdue-rule--generic-clean-code--r01/python",
                    ]
                }
            ],
        }

        packet = build_review_packet(sample_run, candidate_id="candidate-7f2a")
        serialized = json.dumps(packet, ensure_ascii=False)

        self.assertNotIn("skill-v0.3.0", serialized)
        self.assertNotIn("clean-code-ai-collaboration", serialized)
        self.assertNotIn(".benchmark-runs", serialized)
        self.assertNotIn("D:/repo", serialized)
        self.assertNotIn("/Users/reviewer", serialized)

    def test_review_packet_redacts_desktop_dispatch_and_thread_details(self) -> None:
        sample_run = {
            "run_id": "react-overdue-rule--skill-v0.3.0--r01",
            "arm_id": "skill-v0.3.0",
            "task": "Change the overdue boundary.",
            "diff": (
                "dispatch_id=desktop-dispatch-run-aabbccddeeff0011 "
                "thread_id=thread-private run-aabbccddeeff0011 "
                "C:/Users/private/workspace /tmp/private-workspace"
            ),
            "oracle_results": [],
        }

        packet = build_review_packet(sample_run, candidate_id="candidate-7f2a")
        serialized = json.dumps(packet, ensure_ascii=False)

        self.assertNotIn("desktop-dispatch", serialized)
        self.assertNotIn("thread-private", serialized)
        self.assertNotIn("run-aabbccddeeff0011", serialized)
        self.assertNotIn("C:/Users/private", serialized)
        self.assertNotIn("/tmp/private-workspace", serialized)

    def test_cli_exposes_all_contract_commands(self) -> None:
        parser = _build_parser()
        help_text = parser.format_help()

        for command in (
            "prepare",
            "pilot",
            "stage",
            "collect",
            "freeze",
            "invalidate-pilot",
            "adjudicate-timeout",
            "full",
            "review-packets",
            "build-result",
            "verify",
            "verify-freeze",
            "verify-reviews",
        ):
            self.assertIn(command, help_text)

        invalidation = parser.parse_args(
            [
                "invalidate-pilot",
                "--scenario",
                "fastapi-provider-boundary",
                "--reason",
                "prompt_hash_newline_defect",
                "--legacy-pending-dispatch",
                "desktop-dispatch-fastapi-provider-boundary--control--r01--g03--a01",
            ]
        )
        self.assertEqual(
            "desktop-dispatch-fastapi-provider-boundary--control--r01--g03--a01",
            invalidation.legacy_pending_dispatch,
        )

    def test_desktop_pilot_and_full_fail_closed_without_nested_cli(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "stage --phase pilot"):
            harness_main(["pilot"])
        with self.assertRaisesRegex(RuntimeError, "stage --phase full"):
            harness_main(["full"])

    def test_desktop_contract_does_not_depend_on_unrelated_cli_version(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)

        client = _subject_client_contract(manifest)

        self.assertEqual("codex-desktop-collaboration", client["client"])
        self.assertEqual("not_available", client["client_version"])
        self.assertEqual(manifest.subject_executor, client["subject_executor"])
        self.assertEqual(
            "desktop-subject-v3",
            manifest.subject_executor["protocol_version"],
        )
        self.assertNotIn("codex_version", client)

    def test_baseline_red_rejects_unrelated_extra_failure(self) -> None:
        result = CommandResult(
            args=("pytest",),
            exit_code=1,
            stdout=(
                "test_expected_boundary FAILED\n"
                "test_unrelated_behavior FAILED\n"
                "2 failed in 0.10s\n"
            ),
            stderr="",
            elapsed_seconds=0.1,
            timed_out=False,
            classification="nonzero_exit",
            attempt=1,
        )

        self.assertFalse(
            baseline_acceptance_is_expected(
                (result,),
                markers=("test_expected_boundary",),
                expected_failure_count=1,
            )
        )

    def test_persisted_command_replaces_windows_workspace_path(self) -> None:
        workspace = Path("D:/repo/.benchmark-runs/workspaces/candidate")
        value = "D:/repo/.benchmark-runs/workspaces/candidate/.venv/python.exe"

        sanitized = _sanitize_persisted_text(value, workspace)

        self.assertEqual("{workspace}/.venv/python.exe", sanitized)

    def test_console_json_is_safe_for_windows_cp950(self) -> None:
        serialized = _console_json({"output": "✓ 完成"})

        serialized.encode("cp950")
        self.assertIn(r"\u2713", serialized)

    def test_terminal_document_must_match_current_contract(self) -> None:
        slot = RunSlot(
            run_id="sample",
            scenario_id="react-overdue-rule",
            language="typescript-react",
            arm_id="control",
            repetition=1,
            order_index=0,
        )
        document = {
            "run_id": "sample",
            "terminal_state": "passed",
            "scenario_contract_sha256": "old-contract",
        }

        with self.assertRaisesRegex(ValueError, "another contract"):
            _validate_terminal_document(slot, document, "new-contract")

    def test_retry_is_limited_to_first_infrastructure_attempt(self) -> None:
        self.assertTrue(can_retry("harness_error", attempt=1))
        self.assertFalse(can_retry("harness_error", attempt=2))
        self.assertFalse(can_retry("timeout", attempt=1))
        self.assertFalse(can_retry("candidate_test_failure", attempt=1))

    @staticmethod
    def _git(cwd: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=True,
        )
        return completed.stdout


if __name__ == "__main__":
    unittest.main()
