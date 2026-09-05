"""透過 staged dispatch 與 report 公開介面鎖定查閱契約。"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evals.harness.desktop_subject import (
    DesktopSubjectValidationError,
    stage_desktop_subject,
    validate_desktop_report,
)
from evals.harness.manifest import load_manifest
from evals.harness.models import RunSlot, Workspace

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ".agents/skills/clean-code-ai-collaboration"
CORE_EXTRA = f"{SKILL_ROOT}/references/testing-and-change-safety.md"
PYTHON_PROFILE = f"{SKILL_ROOT}/references/language-python.md"


class LegacyInspectionBoundaryTests(unittest.TestCase):
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
