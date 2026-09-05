from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from scripts import build_skill_package as packager
from scripts.validate_profiles import load_registry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "profile-packaging" / "csharp"
FIXED_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def read_committed_bytes(path: Path) -> bytes:
    relative_path = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return result.stdout


class ProfilePackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_root = Path(self.temporary_directory.name)
        self.output = self.temporary_root / "clean-code-ai-csharp"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def build_worktree_package(self, *profile_ids: str) -> dict:
        return packager.build_package(
            ROOT,
            self.output,
            "worktree",
            profile_ids,
        )

    def create_git_source(self) -> Path:
        source = self.temporary_root / "source"
        (source / "scripts").mkdir(parents=True)
        shutil.copytree(ROOT / "profiles", source / "profiles")
        shutil.copytree(
            ROOT / "clean-code-ai-collaboration",
            source / "clean-code-ai-collaboration",
        )
        shutil.copy2(ROOT / "LICENSE", source / "LICENSE")
        shutil.copy2(ROOT / ".gitattributes", source / ".gitattributes")
        shutil.copy2(
            ROOT / "scripts" / "package-manifest.schema.json",
            source / "scripts" / "package-manifest.schema.json",
        )
        for relative_path in (
            Path("evals/profile-pilot-result.schema.json"),
            Path("evals/profile-pilot-result-v2.schema.json"),
            Path("evals/manifests/v0.5.1-profile-pilot.json"),
            Path("evals/results/v0.5.1-profile-pilot.json"),
            Path("evals/manifests/v0.5.2-profile-pilot.json"),
            Path("evals/results/v0.5.2-profile-pilot.json"),
        ):
            target = source / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative_path, target)
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(
            ["git", "-C", str(source), "config", "user.email", "fixture@example.test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(source), "config", "user.name", "Fixture"],
            check=True,
        )
        subprocess.run(["git", "-C", str(source), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(source), "commit", "-q", "-m", "fixture"],
            check=True,
        )
        return source

    def test_csharp_package_contains_only_core_and_selected_profile(self) -> None:
        manifest = self.build_worktree_package("csharp")
        paths = {entry["path"] for entry in manifest["files"]}

        self.assertIn("SKILL.md", paths)
        self.assertIn("references/language-csharp.md", paths)
        self.assertNotIn("references/language-python.md", paths)

    def test_react_does_not_implicitly_package_typescript(self) -> None:
        manifest = self.build_worktree_package("react")

        self.assertEqual(["react"], manifest["profile_ids"])

    def test_selected_profiles_render_in_load_order(self) -> None:
        self.build_worktree_package("react", "typescript")
        selection = (
            self.output / "references" / "profile-selection.md"
        ).read_text(encoding="utf-8")

        self.assertLess(
            selection.index("- ID: `typescript`"),
            selection.index("- ID: `react`"),
        )

    def test_generated_skill_keeps_bundled_profiles_conditional(self) -> None:
        self.build_worktree_package("csharp")
        skill = (self.output / "SKILL.md").read_text(encoding="utf-8")
        adapter = (self.output / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        selection = (
            self.output / "references" / "profile-selection.md"
        ).read_text(encoding="utf-8")

        self.assertIn("profile-selection.md", skill)
        self.assertIn(
            "Bundled means available, not automatically applied",
            selection,
        )
        self.assertIn("allow_implicit_invocation: false", adapter)
        self.assertIn("$clean-code-ai-csharp", adapter)
        self.assertEqual(1, selection.count("- ID: `csharp`"))
        self.assertNotIn("- ID: `python`", selection)

    def test_generated_package_passes_open_standard_validation(self) -> None:
        self.build_worktree_package("csharp")
        executable = shutil.which("agentskills")

        self.assertIsNotNone(executable, "agentskills must be available on PATH")

        result = subprocess.run(
            [executable, "validate", str(self.output)],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_existing_output_directory_fails_without_mutation(self) -> None:
        output = self.temporary_root / "existing"
        output.mkdir()
        sentinel = output / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")

        with self.assertRaisesRegex(
            FileExistsError,
            "output directory already exists",
        ):
            packager.build_package(ROOT, output, "worktree", ["csharp"])

        self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_output_directory_race_fails_without_mutating_competing_content(
        self,
    ) -> None:
        real_validate = packager._validate_manifest

        def create_competing_output(*args, **kwargs) -> None:
            real_validate(*args, **kwargs)
            self.output.mkdir()
            (self.output / "sentinel.txt").write_text(
                "keep",
                encoding="utf-8",
            )

        with patch.object(
            packager,
            "_validate_manifest",
            side_effect=create_competing_output,
        ):
            with self.assertRaisesRegex(
                FileExistsError,
                "output directory already exists",
            ):
                self.build_worktree_package("csharp")

        self.assertEqual(
            "keep",
            (self.output / "sentinel.txt").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            ["sentinel.txt"],
            [path.name for path in self.output.iterdir()],
        )

    def test_missing_output_parent_is_created_for_dist_layout(self) -> None:
        output = (
            self.temporary_root
            / "dist"
            / "clean-code-ai-csharp"
        )

        packager.build_package(ROOT, output, "worktree", ["csharp"])

        self.assertTrue((output / "PACKAGE-MANIFEST.json").is_file())

    def test_planned_target_and_missing_requirement_fail_before_output(self) -> None:
        with self.assertRaisesRegex(ValueError, "planned"):
            self.build_worktree_package("go")
        self.assertFalse(self.output.exists())

        profiles = {profile["id"]: profile for profile in load_registry(ROOT)}
        modified = deepcopy(profiles)
        modified["csharp"]["composition"]["requires"] = ["go"]

        with self.assertRaisesRegex(ValueError, "requires unavailable"):
            packager.compose_profiles(modified, ["csharp"])

    def test_recommendation_is_not_automatically_composed(self) -> None:
        profiles = {profile["id"]: profile for profile in load_registry(ROOT)}

        self.assertEqual(
            ["react"],
            list(packager.compose_profiles(profiles, ["react"])),
        )

    def test_manifest_schema_hashes_and_overall_digest_are_recomputable(self) -> None:
        manifest = self.build_worktree_package("csharp")
        schema = json.loads(
            (ROOT / "scripts" / "package-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(manifest)))
        self.assertEqual(
            sorted(manifest["profile_ids"]),
            manifest["profile_ids"],
        )
        for entry in manifest["inputs"]:
            with self.subTest(input=entry["path"]):
                self.assertEqual(
                    entry["sha256"],
                    hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest(),
                )
        for entry in manifest["files"]:
            with self.subTest(file=entry["path"]):
                self.assertEqual(
                    entry["sha256"],
                    hashlib.sha256((self.output / entry["path"]).read_bytes()).hexdigest(),
                )
        without_digest = dict(manifest)
        without_digest.pop("overall_digest")
        self.assertEqual(
            manifest["overall_digest"],
            hashlib.sha256(packager.canonical_json_bytes(without_digest)).hexdigest(),
        )
        self.assertEqual(
            {
                "schema_version",
                "source_commit",
                "source_mode",
                "suite_version",
                "packager_version",
                "profile_ids",
                "inputs",
                "files",
                "overall_digest",
            },
            set(manifest),
        )
        self.assertNotIn(str(ROOT), json.dumps(manifest))

    def test_identical_worktree_inputs_produce_identical_packages(self) -> None:
        first_manifest = self.build_worktree_package("csharp")
        second_output = self.temporary_root / "second-package"
        second_manifest = packager.build_package(
            ROOT,
            second_output,
            "worktree",
            ["csharp"],
        )

        self.assertEqual(first_manifest, second_manifest)
        first_files = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second_output).as_posix(): path.read_bytes()
            for path in second_output.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_files, second_files)

    def test_release_mode_rejects_a_dirty_worktree(self) -> None:
        source = self.create_git_source()
        (source / "LICENSE").write_text("dirty\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "clean worktree"):
            packager.build_package(
                source,
                self.output,
                "release",
                ["csharp"],
            )

        self.assertFalse(self.output.exists())

    def test_release_mode_builds_from_a_clean_commit(self) -> None:
        source = self.create_git_source()

        manifest = packager.build_package(
            source,
            self.output,
            "release",
            ["csharp"],
        )

        expected_commit = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        self.assertEqual("release", manifest["source_mode"])
        self.assertEqual(expected_commit, manifest["source_commit"])

    def test_release_mode_uses_git_blobs_for_validation_and_inputs(self) -> None:
        source = self.create_git_source()
        profile_path = source / "profiles" / "csharp.yaml"
        subprocess.run(
            [
                "git",
                "-C",
                str(source),
                "update-index",
                "--assume-unchanged",
                "profiles/csharp.yaml",
            ],
            check=True,
        )
        profile_path.write_text("invalid: checkout-only\n", encoding="utf-8")
        output = self.temporary_root / "release-from-blobs"

        manifest = packager.build_package(
            source,
            output,
            "release",
            ["csharp"],
        )

        committed = subprocess.run(
            ["git", "-C", str(source), "show", "HEAD:profiles/csharp.yaml"],
            capture_output=True,
            check=True,
        ).stdout
        input_hashes = {
            entry["path"]: entry["sha256"] for entry in manifest["inputs"]
        }
        self.assertEqual(
            hashlib.sha256(committed).hexdigest(),
            input_hashes["profiles/csharp.yaml"],
        )

    def test_release_evidence_schema_uses_and_records_committed_bytes(self) -> None:
        source = self.create_git_source()
        schema_path = "evals/profile-pilot-result.schema.json"
        committed = (source / schema_path).read_bytes()
        subprocess.run(
            ["git", "-C", str(source), "update-index", "--assume-unchanged", schema_path],
            check=True,
        )
        (source / schema_path).write_text("false\n", encoding="utf-8")

        manifest = packager.build_package(
            source, self.output, "release", ["csharp"]
        )

        input_hashes = {
            entry["path"]: entry["sha256"] for entry in manifest["inputs"]
        }
        self.assertEqual(
            hashlib.sha256(committed).hexdigest(), input_hashes.get(schema_path)
        )

    def test_same_release_commit_produces_byte_identical_packages(self) -> None:
        source = self.create_git_source()
        first = self.temporary_root / "first" / "clean-code-ai-csharp"
        second = self.temporary_root / "second" / "clean-code-ai-csharp"

        first_manifest = packager.build_package(
            source,
            first,
            "release",
            ["csharp"],
        )
        second_manifest = packager.build_package(
            source,
            second,
            "release",
            ["csharp"],
        )

        first_files = {
            path.relative_to(first).as_posix(): path.read_bytes()
            for path in first.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second).as_posix(): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_files, second_files)

    def test_external_source_symlink_fails_before_output_creation(self) -> None:
        source = self.create_git_source()
        outside = self.temporary_root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        linked = (
            source
            / "clean-code-ai-collaboration"
            / "references"
            / "code-readability.md"
        )
        linked.unlink()
        try:
            linked.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"symlink unavailable: {error}")

        with self.assertRaisesRegex(ValueError, "symlink|escapes"):
            packager.build_package(
                source,
                self.output,
                "worktree",
                ["csharp"],
            )

        self.assertFalse(self.output.exists())

    def test_write_failure_removes_only_files_created_by_this_run(self) -> None:
        real_write = packager._write_exclusive
        calls = 0

        def fail_second_write(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected write failure")
            real_write(path, content)

        with patch.object(packager, "_write_exclusive", side_effect=fail_second_write):
            with self.assertRaisesRegex(OSError, "injected write failure"):
                self.build_worktree_package("csharp")

        self.assertFalse(self.output.exists())
        source = (ROOT / "scripts" / "build_skill_package.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("rm" + "tree", source)

    def test_canonical_fixture_has_one_cross_platform_digest(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

        self.assertIn("LICENSE text eol=lf", attributes.splitlines())

        inputs = {
            path.relative_to(FIXTURE_ROOT / "input").as_posix(): read_committed_bytes(
                path
            )
            for path in (FIXTURE_ROOT / "input").rglob("*")
            if path.is_file()
        }
        files = {
            path: content
            for path, content in inputs.items()
            if path in {"LICENSE", "SKILL.md", "references/language-csharp.md"}
        }

        manifest = packager.build_manifest(
            source_commit=FIXED_COMMIT,
            source_mode="worktree",
            suite_version="0.5.0",
            profile_ids=["csharp"],
            inputs=inputs,
            files=files,
        )
        expected = json.loads(
            (FIXTURE_ROOT / "expected-manifest.json").read_text(encoding="utf-8")
        )
        expected_digest = (FIXTURE_ROOT / "expected-digest.txt").read_text(
            encoding="utf-8"
        ).strip()

        self.assertEqual(expected, manifest)
        self.assertEqual(expected_digest, manifest["overall_digest"])

    def test_cli_returns_one_without_traceback_for_a_known_contract_failure(
        self,
    ) -> None:
        with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
            exit_code = packager.main(
                [
                    "--source-root",
                    str(ROOT),
                    "--output",
                    str(self.output),
                    "--source-mode",
                    "worktree",
                    "--profile",
                    "go",
                ]
            )

        self.assertEqual(1, exit_code)
        self.assertIn("profile-unavailable", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_ci_runs_packaging_contract_on_ubuntu_and_windows(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate.yml"
        ).read_text(encoding="utf-8")

        for term in {
            "ubuntu-latest",
            "windows-latest",
            'python-version: "3.12"',
            "scripts/validate_profiles.py --source-root .",
            "scripts/generate_profile_matrix.py --source-root . --check",
            "scripts/build_skill_package.py",
            "agentskills validate clean-code-ai-collaboration",
            "agentskills validate dist/clean-code-ai-csharp",
        }:
            with self.subTest(term=term):
                self.assertIn(term, workflow)


if __name__ == "__main__":
    unittest.main()
