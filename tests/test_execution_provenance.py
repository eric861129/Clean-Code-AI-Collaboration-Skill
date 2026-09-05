from __future__ import annotations

import subprocess
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from evals.harness.execution_provenance import (
    build_execution_provenance,
    canonical_tree_sha256,
    verify_staged_tree,
    verify_execution_provenance,
)
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest
from evals.harness.models import CommandResult, HarnessPaths, RunSlot
from evals.harness.process import run_process


class ExecutionProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Provenance Test")
        self.git("config", "user.email", "provenance@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.write(".gitignore", b"ignored/\n")
        self.write("evals/harness/__init__.py", b"")
        self.write("evals/harness/Zebra.py", b"VALUE = 1\n")
        self.write("evals/harness/apple.py", b"VALUE = 2\n")
        self.write("evals/v040_strategy_full_run.py", b"VALUE = 3\n")
        self.write("evals/profile-pilot-result.schema.json", b"{}\n")
        self.write("evals/rubrics/profile-increment.md", "評分\n".encode())
        self.write("evals/manifests/pilot.json", b"{}\n")
        self.write("requirements-dev.txt", b"example==1\n")
        self.git("add", "-A")
        self.git("commit", "-m", "baseline")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.manifest = self.root / "evals/manifests/pilot.json"

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True,
            capture_output=True, text=True, encoding="utf-8",
        ).stdout

    def write(self, relative: str, data: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_freeze_records_committed_inputs_in_case_sensitive_posix_order(self) -> None:
        result = build_execution_provenance(self.root, self.manifest)
        self.assertEqual(self.commit, result["execution_commit"])
        self.assertEqual([
            "evals/harness/Zebra.py", "evals/harness/__init__.py",
            "evals/harness/apple.py", "evals/manifests/pilot.json",
            "evals/profile-pilot-result.schema.json",
            "evals/rubrics/profile-increment.md",
            "evals/v040_strategy_full_run.py", "requirements-dev.txt",
        ], list(result["input_sha256"]))
        self.assertEqual(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            result["input_sha256"]["evals/harness/__init__.py"],
        )

    def test_initial_freeze_refuses_dirty_source_even_outside_execution_inputs(self) -> None:
        self.write("draft.md", b"not committed\n")
        with self.assertRaisesRegex(ValueError, "clean committed"):
            build_execution_provenance(self.root, self.manifest)

    def test_pinned_execution_survives_evidence_commit_but_rejects_helper_drift(self) -> None:
        receipt = build_execution_provenance(self.root, self.manifest)
        self.write("evals/results/new.json", b"{}\n")
        self.git("add", "-A")
        self.git("commit", "-m", "publish evidence")
        verify_execution_provenance(self.root, receipt)
        self.write("evals/harness/apple.py", b"VALUE = 99\n")
        with self.assertRaisesRegex(ValueError, "source input drift.*apple.py"):
            verify_execution_provenance(self.root, receipt)

    def test_checkout_crlf_is_not_equivalent_to_frozen_lf_execution_bytes(self) -> None:
        receipt = build_execution_provenance(self.root, self.manifest)
        self.write("evals/harness/apple.py", b"VALUE = 2\r\n")
        with self.assertRaisesRegex(ValueError, "source input drift"):
            verify_execution_provenance(self.root, receipt)

    def test_initial_freeze_rejects_committed_crlf_source(self) -> None:
        self.write("evals/harness/apple.py", b"VALUE = 2\r\n")
        self.git("add", "-A")
        self.git("commit", "-m", "noncanonical source")
        with self.assertRaisesRegex(ValueError, "UTF-8 LF"):
            build_execution_provenance(self.root, self.manifest)

    def test_added_helper_cannot_be_omitted_from_frozen_input_list(self) -> None:
        receipt = build_execution_provenance(self.root, self.manifest)
        self.write("evals/harness/new_helper.py", b"VALUE = 4\n")
        with self.assertRaisesRegex(ValueError, "source input list drift"):
            verify_execution_provenance(self.root, receipt)

    def test_receipt_rejects_wrong_execution_commit_and_deleted_input_record(self) -> None:
        receipt = build_execution_provenance(self.root, self.manifest)
        changed = deepcopy(receipt)
        changed["execution_commit"] = "main"
        with self.assertRaisesRegex(ValueError, "full commit SHA"):
            verify_execution_provenance(self.root, changed)
        changed = deepcopy(receipt)
        del changed["input_sha256"]["evals/v040_strategy_full_run.py"]
        with self.assertRaisesRegex(ValueError, "pinned Git inputs"):
            verify_execution_provenance(self.root, changed)

    def test_staged_lf_bytes_match_git_tree_and_later_change_is_rejected(self) -> None:
        stage = self.root / "ignored/stage"
        stage.mkdir(parents=True)
        (stage / "Zebra.py").write_bytes(b"VALUE = 1\n")
        (stage / "__init__.py").write_bytes(b"")
        (stage / "apple.py").write_bytes(b"VALUE = 2\n")
        receipt = verify_staged_tree(self.root, self.commit, "evals/harness", stage)
        self.assertEqual(receipt["tree_sha256"], canonical_tree_sha256(stage))
        self.assertEqual(["Zebra.py", "__init__.py", "apple.py"], list(receipt["file_sha256"]))
        (stage / "apple.py").write_bytes(b"VALUE = 2\r\n")
        with self.assertRaisesRegex(ValueError, "staged byte mismatch.*apple.py"):
            verify_staged_tree(self.root, self.commit, "evals/harness", stage)

    def test_nested_fixture_paths_are_read_as_git_blobs_not_local_filenames(self) -> None:
        subtree = "fixture-" + "x" * 55
        relative = ("nested-" + "y" * 55) + "/" + "z" * 55 + ".txt"
        self.write(subtree + "/" + relative, b"nested fixture\n")
        self.git("add", "-A")
        self.git("commit", "-m", "nested fixture")
        commit = self.git("rev-parse", "HEAD").strip()
        receipt = verify_staged_tree(self.root, commit, subtree, self.root / subtree)
        self.assertIn(relative, receipt["file_sha256"])

    def test_staging_rejects_extra_files_and_non_lf_git_blob(self) -> None:
        self.write("fixture/source.txt", b"hello\n")
        self.git("add", "-A")
        self.git("commit", "-m", "fixture")
        commit = self.git("rev-parse", "HEAD").strip()
        stage = self.root / "ignored/stage"
        stage.mkdir(parents=True)
        (stage / "source.txt").write_bytes(b"hello\n")
        (stage / "extra.txt").write_bytes(b"injected\n")
        with self.assertRaisesRegex(ValueError, "staged file list mismatch"):
            verify_staged_tree(self.root, commit, "fixture", stage)
        (stage / "extra.txt").unlink()
        self.write("fixture/source.txt", b"hello\r\n")
        self.git("add", "-A")
        self.git("commit", "-m", "invalid newline")
        commit = self.git("rev-parse", "HEAD").strip()
        (stage / "source.txt").write_bytes(b"hello\r\n")
        with self.assertRaisesRegex(ValueError, "UTF-8 LF"):
            verify_staged_tree(self.root, commit, "fixture", stage)


    def test_v5_workspace_pins_git_newline_policy_and_records_blob_verification(self) -> None:
        self.write("fixture/source.ts", b"export const value = 1;\n")
        self.write("clean-code-ai-collaboration/SKILL.md", b"# Test Skill\n")
        self.git("add", "-A")
        self.git("commit", "-m", "fixture")
        commit = self.git("rev-parse", "HEAD").strip()
        self.git("config", "core.autocrlf", "true")
        manifest = load_manifest(Path(__file__).resolve().parents[1] / "evals/manifests/v0.5.1-profile-pilot.json")
        manifest = replace(
            manifest, fixture_commit=commit, skill_commit=commit, skill_tag=commit,
            subject_executor={"protocol_version": "desktop-subject-v5"},
            scenarios=({"id": "fixture", "fixture_path": "fixture", "language": "typescript"},),
        )
        paths = HarnessPaths(self.root, self.root / "ignored/runs", self.root, self.root)
        slot = RunSlot("fixture--core-only--r01", "fixture", "typescript", "core-only", 1, 0)

        def process(args, cwd, timeout):
            if args[0] == "npm":
                return CommandResult(tuple(args), 0, "", "", 0, False, "success", 1)
            return run_process(args, cwd, timeout)

        with patch("evals.harness.fixture_builder.run_process", side_effect=process):
            workspace = build_workspace(slot, manifest, paths)
        newline_policy = subprocess.run(
            ["git", "config", "--local", "--get", "core.autocrlf"], cwd=workspace.root,
            capture_output=True, text=True,
        )
        self.assertEqual("false", newline_policy.stdout.strip())
        self.assertTrue((workspace.artifact_dir / "staging-provenance.json").is_file())
        self.assertNotIn(b"\r", (workspace.root / ".gitignore").read_bytes())
        self.assertEqual(b"# Test Skill\n", (workspace.root / ".agents/skills/clean-code-ai-collaboration/SKILL.md").read_bytes())
        self.assertEqual("true", self.git("config", "--local", "--get", "core.autocrlf").strip())
        legacy_manifest = replace(manifest, subject_executor={"protocol_version": "desktop-subject-v4"})
        with patch("evals.harness.fixture_builder.run_process", side_effect=process):
            legacy = build_workspace(replace(slot, run_id="fixture--core-only--legacy"), legacy_manifest, paths)
        self.assertEqual(b"export const value = 1;\r\n", (legacy.root / "source.ts").read_bytes())
        self.assertEqual(b"# Test Skill\r\n", (legacy.root / ".agents/skills/clean-code-ai-collaboration/SKILL.md").read_bytes())
        drift_slot = replace(slot, run_id="fixture--core-only--drift")

        def dependency_with_drift(args, cwd, timeout):
            if args[0] == "npm":
                (cwd / "source.ts").write_bytes(b"export const value = 99;\n")
            return process(args, cwd, timeout)

        with patch("evals.harness.fixture_builder.run_process", side_effect=dependency_with_drift):
            with self.assertRaisesRegex(ValueError, "staged byte mismatch"):
                build_workspace(drift_slot, manifest, paths)


if __name__ == "__main__":
    unittest.main()
