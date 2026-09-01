import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals.harness.evidence_recorder import record_subject_evidence
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest, validate_manifest
from evals.harness.models import HarnessPaths, RunSlot, Workspace
from evals.harness.planner import build_run_slots, full_slots, pilot_slots
from evals.harness.process import run_process
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
            )
            evidence_path = record_subject_evidence(observation, workspace)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

            self.assertEqual("completed", evidence["terminal_state"])
            self.assertIn("allowed.txt", evidence["diff"])
            self.assertTrue(observation.raw_jsonl_path.is_file())
            self.assertEqual("done", observation.last_message_path.read_text())
            self.assertEqual(1, evidence["telemetry"]["tool_call_count"])
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
