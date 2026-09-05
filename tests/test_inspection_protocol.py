"""透過 staged dispatch 與 report 公開介面鎖定查閱契約。"""

import hashlib
import json
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

from evals.harness.desktop_subject import (
    DesktopSubjectValidationError,
    stage_desktop_subject,
    load_desktop_dispatch,
    validate_desktop_report,
)
from evals.harness.manifest import load_manifest
from evals.harness.models import RunSlot, Workspace
from evals.harness.cli import main as harness_main
from evals.harness.skill_inspection import materialize_inspection_paths

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ".agents/skills/clean-code-ai-collaboration"
CORE_EXTRA = f"{SKILL_ROOT}/references/testing-and-change-safety.md"
PYTHON_PROFILE = f"{SKILL_ROOT}/references/language-python.md"


class InspectionProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.workspace = Workspace(root / "workspace", root / "artifacts", "a" * 40)
        self.workspace.artifact_dir.mkdir()
        old = load_manifest(ROOT / "evals/manifests/v0.5.1-profile-pilot.json")
        self.arm = replace(next(arm for arm in old.arms if arm.id == "core-only"),
            inspection_policy="required-subset/v1", applied_profiles=(),
            allowed_skill_inspection_paths=tuple(sorted([
                f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/references/profile-selection.md", CORE_EXTRA])))
        manifest = replace(old, arms=(self.arm,), subject_executor={**old.subject_executor, "protocol_version": "desktop-subject-v5"})
        for relative in (*self.arm.allowed_skill_inspection_paths, PYTHON_PROFILE):
            path = self.workspace.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes("查閱內容\n".encode("utf-8"))
        slot = RunSlot("new-core", "fastapi-provider-boundary", "python-fastapi", "core-only", 1, 0)
        self.dispatch = stage_desktop_subject(slot, manifest, self.workspace, 1, 1, "run-new", "b" * 64, "c" * 64, root / "controller")

    def report(self, paths=None):
        if paths is None:
            paths = list(self.arm.allowed_skill_inspection_paths)
        report = json.loads(self.dispatch.report_template_path.read_text(encoding="utf-8"))
        report.update(applied_profiles=[], files_inspected=paths, skill_inspection_claims=[
            {"path": path, "sha256": hashlib.sha256((self.workspace.root / path).read_bytes()).hexdigest()}
            for path in paths])
        return report

    def collect(self, report):
        self.dispatch.report_path.write_text(json.dumps(report), encoding="utf-8")
        return validate_desktop_report(load_desktop_dispatch(self.dispatch.dispatch_path))

    def test_v5_accepts_complete_honest_extra_core_reads(self):
        result = self.collect(self.report())
        self.assertEqual("desktop-subject-report/v3", result["schema_version"])
        self.assertTrue(result["skill_inspection_verified"])
        self.assertEqual([], result["inspection_diagnostics"])
        self.assertEqual([], result["applied_profiles"])

    def test_inspect_skill_reads_only_requested_allowed_content_without_writes(self):
        before = {p: p.read_bytes() for p in self.workspace.root.rglob("*") if p.is_file()}
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, harness_main(["inspect-skill", "--dispatch", str(self.dispatch.dispatch_path), "--path", CORE_EXTRA]))
        result = json.loads(output.getvalue())
        self.assertEqual([CORE_EXTRA], [item["path"] for item in result["files"]])
        self.assertEqual("查閱內容\n", result["files"][0]["content"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.workspace.root.rglob("*") if p.is_file()})
        self.assertFalse(self.dispatch.report_path.exists())
        with self.assertRaises(ValueError):
            harness_main(["inspect-skill", "--dispatch", str(self.dispatch.dispatch_path), "--path", PYTHON_PROFILE])

    def test_v5_reports_all_violations_deterministically(self):
        report = self.report([CORE_EXTRA, PYTHON_PROFILE])
        report["skill_inspection_claims"][0]["sha256"] = "0" * 64
        report["skill_inspection_claims"].append(dict(report["skill_inspection_claims"][0]))
        report["applied_profiles"] = ["python"]
        report["files_inspected"] = [PYTHON_PROFILE]
        with self.assertRaises(DesktopSubjectValidationError) as rejected:
            self.collect(report)
        self.assertEqual("invalid_claim", rejected.exception.reason)
        codes = {item["code"] for item in rejected.exception.diagnostics}
        self.assertEqual({"profile_contamination", "missing_required_skill_file", "skill_hash_mismatch", "duplicate_skill_claim", "applied_profiles_mismatch", "inspection_record_mismatch"}, codes)

    def test_v5_detects_unreported_profile_in_files_inspected(self):
        report = self.report()
        report["files_inspected"].append(PYTHON_PROFILE)
        with self.assertRaises(DesktopSubjectValidationError) as rejected:
            self.collect(report)
        self.assertIn("profile_contamination", {d["code"] for d in rejected.exception.diagnostics})

    def test_v5_catches_profile_aliases_and_keeps_diagnostics_when_fields_missing(self):
        for alias in (f"./{PYTHON_PROFILE}", PYTHON_PROFILE.replace(".agents/", ".agents//"), PYTHON_PROFILE.replace(".agents/", ".agents/./")):
            for omit_profiles in (False, True):
                with self.subTest(alias=alias, missing=omit_profiles):
                    report = self.report()
                    report["files_inspected"].append(alias)
                    if omit_profiles:
                        del report["applied_profiles"]
                    with self.assertRaises(DesktopSubjectValidationError) as rejected:
                        self.collect(report)
                    codes = {d["code"] for d in rejected.exception.diagnostics}
                    self.assertIn("profile_contamination", codes)
                    self.assertIn("invalid_skill_path", codes)
                    if omit_profiles:
                        self.assertIn("applied_profiles_mismatch", codes)

    def test_v5_rejects_case_aliases_even_on_case_insensitive_hosts(self):
        report = self.report()
        report["files_inspected"].append(PYTHON_PROFILE.replace(".agents", ".Agents"))
        with self.assertRaises(DesktopSubjectValidationError) as rejected:
            self.collect(report)
        self.assertIn("invalid_skill_path", {d["code"] for d in rejected.exception.diagnostics})

    def test_v5_rejects_noncanonical_and_escaping_claim_paths(self):
        for invalid in ("../outside.md", "C:/secret.md", f"{SKILL_ROOT}/references/../SKILL.md", f"{SKILL_ROOT}//SKILL.md", ".agents/skills/other/SKILL.md"):
            with self.subTest(path=invalid):
                report = self.report()
                report["skill_inspection_claims"].append({"path": invalid, "sha256": "0" * 64})
                with self.assertRaises(DesktopSubjectValidationError) as rejected:
                    self.collect(report)
                self.assertIn("invalid_skill_path", {d["code"] for d in rejected.exception.diagnostics})

    def test_v5_does_not_accept_v1_result_or_missing_policy(self):
        report = self.report()
        report["schema_version"] = "desktop-subject-result/v1"
        with self.assertRaises(DesktopSubjectValidationError):
            self.collect(report)

    def test_rehashed_v5_dispatch_cannot_weaken_arm_policy(self):
        original = self.dispatch.dispatch_path.read_text(encoding="utf-8")
        mutations = [
            lambda p: p.pop("inspection_policy"),
            lambda p: p.update(applied_profiles=["python"]),
            lambda p: p.update(required_skill_inspection_paths=[]),
            lambda p: p["allowed_skill_inspection_paths"].append(PYTHON_PROFILE),
        ]
        for mutate in mutations:
            payload = json.loads(original)
            mutate(payload)
            payload.pop("dispatch_sha256")
            payload["dispatch_sha256"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            self.dispatch.dispatch_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_desktop_dispatch(self.dispatch.dispatch_path)

    def test_v5_prompt_pins_empty_profiles_and_lists_allowed_not_mandatory(self):
        prompt = self.dispatch.prompt_path.read_text(encoding="utf-8")
        self.assertIn("Applied Profiles: []", prompt)
        self.assertIn("不執行自動 Profile 套用", prompt)
        self.assertIn(CORE_EXTRA, prompt)
        self.assertIn("不代表必須全部讀取", prompt)


class LegacyInspectionBoundaryTests(unittest.TestCase):
    def test_allowed_materialization_uses_pinned_metadata_and_keeps_profiles_separate(self):
        revision = "4ce3a697eb7eea36ecddd937ffa915f931e9524a"
        core = materialize_inspection_paths(ROOT, revision, "clean-code-ai-collaboration", [])
        python = materialize_inspection_paths(ROOT, revision, "clean-code-ai-collaboration", ["python"])
        self.assertIn(CORE_EXTRA, core)
        self.assertNotIn(PYTHON_PROFILE, core)
        self.assertEqual(set(core) | {PYTHON_PROFILE}, set(python))
        self.assertEqual(core, sorted(set(core)))
        with self.assertRaises(ValueError):
            materialize_inspection_paths(ROOT, revision, "clean-code-ai-collaboration", ["go"])

    def test_v4_rejects_both_honest_core_extra_and_profile_contamination(self):
        manifest = load_manifest(ROOT / "evals/manifests/v0.5.1-profile-pilot.json")
        arm = next(arm for arm in manifest.arms if arm.id == "core-only")
        for extra in (CORE_EXTRA, PYTHON_PROFILE):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workspace = Workspace(root / "workspace", root / "artifacts", "a" * 40)
                workspace.artifact_dir.mkdir()
                inspected = [*arm.required_skill_inspection_paths, extra]
                claims = []
                for relative in inspected:
                    path = workspace.root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes("誠實查閱證據\n".encode("utf-8"))
                    claims.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                slot = RunSlot("legacy-core", "fastapi-provider-boundary", "python-fastapi", "core-only", 1, 0)
                dispatch = stage_desktop_subject(slot, manifest, workspace, 1, 1, "run-legacy", "b" * 64, "c" * 64, root / "controller")
                report = json.loads(dispatch.report_template_path.read_text(encoding="utf-8"))
                report.update(files_inspected=inspected, skill_inspection_claims=claims)
                dispatch.report_path.write_text(json.dumps(report), encoding="utf-8")
                with self.assertRaises(DesktopSubjectValidationError) as rejected:
                    validate_desktop_report(dispatch)
                self.assertEqual("invalid_claim", rejected.exception.reason)
                self.assertIn("claims undeclared Skill files", str(rejected.exception))


if __name__ == "__main__":
    unittest.main()
