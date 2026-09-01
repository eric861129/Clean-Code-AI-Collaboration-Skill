import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals.harness.anonymizer import build_review_packet
from evals.harness.cli import (
    _build_parser,
    _run_document_path,
    _sanitize_persisted_text,
    _validate_terminal_document,
)
from evals.harness.diff_boundary import classify_paths
from evals.harness.evidence_recorder import record_subject_evidence
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest, validate_manifest
from evals.harness.models import (
    CommandResult,
    HarnessPaths,
    Rename,
    RunSlot,
    Workspace,
)
from evals.harness.oracle_runner import baseline_acceptance_is_expected
from evals.harness.planner import build_run_slots, full_slots, pilot_slots
from evals.harness.process import run_process
from evals.harness.result_builder import build_public_result, can_retry
from evals.harness.subject_runner import build_prompt, run_subject

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "evals" / "manifests" / "v0.3.0-cross-language.json"


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

    def test_rename_requires_source_and_destination_to_be_allowed(self) -> None:
        evidence = classify_paths(
            changed=["src/allowed.ts"],
            renamed=[Rename("src/allowed.ts", "scripts/escape.ts")],
            allowed_exact={"src/allowed.ts"},
            allowed_patterns=(),
        )

        self.assertEqual(("scripts/escape.ts",), evidence.outside_boundary)

    def test_result_requires_all_36_terminal_states(self) -> None:
        slots = build_run_slots(load_manifest(MANIFEST_PATH))

        with self.assertRaisesRegex(ValueError, "36 terminal states"):
            build_public_result(slots, run_documents=[])

    def test_result_rejects_invalidated_pilot_as_final_evidence(self) -> None:
        slots = build_run_slots(load_manifest(MANIFEST_PATH))
        documents = [
            {
                "run_id": slot.run_id,
                "terminal_state": "passed",
            }
            for slot in slots
        ]
        documents[0]["terminal_state"] = "invalidated_pilot"

        with self.assertRaisesRegex(ValueError, "invalid terminal state"):
            build_public_result(slots, documents)

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

    def test_cli_exposes_all_contract_commands(self) -> None:
        parser = _build_parser()
        help_text = parser.format_help()

        for command in (
            "prepare",
            "pilot",
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
