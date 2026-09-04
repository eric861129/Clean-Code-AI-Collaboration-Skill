from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest

import yaml

from scripts.generate_profile_matrix import (
    README_MARKERS,
    RUNTIME_MARKERS,
    main as generator_main,
    render_profile_matrix,
    render_runtime_index,
    replace_generated_region,
    synchronize_generated_regions,
)
from scripts.validate_profiles import load_registry, main, validate_repository


ROOT = Path(__file__).resolve().parents[1]
PROFILE_IDS = [
    "csharp",
    "python",
    "typescript",
    "react",
    "go",
    "rust",
    "java",
    "vue",
]
REQUIRED_PROFILE_HEADINGS = (
    "## Use This Profile When",
    "## Repository Facts to Inspect",
    "## Version-Sensitive Facts",
    "## Language or Framework Semantic Risks",
    "## Clean Code Misapplications",
    "## Behavior and Boundary Contracts",
    "## Repository-Native Gate Discovery",
    "## When Another Option Fits Better",
    "## Common Agent Failure Modes",
    "## Stop and Escalation Conditions",
    "## Output Additions",
    "## Evidence Status",
)


class ProfileContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.temporary_directory.name)
        shutil.copytree(ROOT / "profiles", self.fixture_root / "profiles")
        shutil.copytree(
            ROOT / "clean-code-ai-collaboration" / "references",
            self.fixture_root / "clean-code-ai-collaboration" / "references",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def profile_path(self, profile_id: str) -> Path:
        return self.fixture_root / "profiles" / f"{profile_id}.yaml"

    def update_profile(self, profile_id: str, update) -> None:
        path = self.profile_path(profile_id)
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
        update(profile)
        path.write_text(
            yaml.safe_dump(profile, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
            newline="\n",
        )

    def diagnostic_codes(self) -> list[str]:
        return [
            diagnostic.code
            for diagnostic in validate_repository(self.fixture_root)
        ]

    def write_generated_documents(self, body: str = "stale") -> None:
        readme = (
            "# Before\n\n"
            f"{README_MARKERS[0]}\n{body}\n{README_MARKERS[1]}\n\n"
            "After README\n"
        )
        runtime = (
            "# Profile Selection\n\n"
            f"{RUNTIME_MARKERS[0]}\n{body}\n{RUNTIME_MARKERS[1]}\n\n"
            "After Runtime Index\n"
        )
        (self.fixture_root / "README.md").write_text(
            readme,
            encoding="utf-8",
            newline="\n",
        )
        runtime_path = (
            self.fixture_root
            / "clean-code-ai-collaboration"
            / "references"
            / "profile-selection.md"
        )
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(runtime, encoding="utf-8", newline="\n")

    def test_catalog_has_the_fixed_v050_order(self) -> None:
        profiles = load_registry(ROOT)

        self.assertEqual(PROFILE_IDS, [profile["id"] for profile in profiles])

    def test_registry_has_four_experimental_profiles(self) -> None:
        self.assertEqual([], list(validate_repository(ROOT)))
        expected_references = {
            "csharp": "language-csharp.md",
            "python": "language-python.md",
            "typescript": "language-typescript.md",
            "react": "framework-react.md",
        }
        for profile in load_registry(ROOT):
            with self.subTest(profile=profile["id"]):
                expected_status = (
                    "experimental"
                    if profile["id"] in expected_references
                    else "planned"
                )
                self.assertEqual(expected_status, profile["status"])
                if profile["id"] in expected_references:
                    self.assertEqual(
                        "clean-code-ai-collaboration/references/"
                        + expected_references[profile["id"]],
                        profile["reference"],
                    )
                else:
                    self.assertNotIn("reference", profile)
                self.assertEqual(
                    ["eric861129"],
                    profile["ownership"]["maintainers"],
                )
                self.assertEqual(
                    "not_started",
                    profile["evidence"]["benchmark_status"],
                )

    def test_csharp_profile_has_complete_semantic_contract(self) -> None:
        content = (
            ROOT
            / "clean-code-ai-collaboration"
            / "references"
            / "language-csharp.md"
        ).read_text(encoding="utf-8")

        for heading in REQUIRED_PROFILE_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, content)
        for term in {
            "Nullable",
            "CancellationToken",
            "IDisposable",
            "IAsyncDisposable",
            "deferred execution",
            "multiple enumeration",
            "equality",
            "DI lifetime",
            "TargetFramework",
            "LangVersion",
        }:
            with self.subTest(term=term):
                self.assertIn(term.lower(), content.lower())
        self.assertNotIn("ASP.NET Core is required", content)

    def test_python_profile_has_complete_semantic_contract(self) -> None:
        content = (
            ROOT
            / "clean-code-ai-collaboration"
            / "references"
            / "language-python.md"
        ).read_text(encoding="utf-8")

        for heading in REQUIRED_PROFILE_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, content)
        for term in {
            "pyproject.toml",
            "Python version",
            "dynamic typing",
            "mutable default",
            "aliasing",
            "asyncio",
            "cancellation",
            "context manager",
            "exception boundary",
            "type checker",
        }:
            with self.subTest(term=term):
                self.assertIn(term.lower(), content.lower())
        for statement in {
            "FastAPI is required",
            "Django is required",
            "Pydantic is required",
            "mypy is required",
            "pyright is required",
        }:
            with self.subTest(statement=statement):
                self.assertNotIn(statement, content)

    def test_typescript_profile_has_complete_semantic_contract(self) -> None:
        content = (
            ROOT
            / "clean-code-ai-collaboration"
            / "references"
            / "language-typescript.md"
        ).read_text(encoding="utf-8")

        for heading in REQUIRED_PROFILE_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, content)
        for term in {
            "strict",
            "exactOptionalPropertyTypes",
            "noUncheckedIndexedAccess",
            "structural typing",
            "union",
            "narrowing",
            "Promise",
            "moduleResolution",
            "target",
            "runtime validation",
        }:
            with self.subTest(term=term):
                self.assertIn(term.lower(), content.lower())
        for statement in {
            "React is required",
            "Vue is required",
            "Zod is required",
            "ESLint is required",
            "Vite is required",
        }:
            with self.subTest(statement=statement):
                self.assertNotIn(statement, content)

    def test_react_profile_has_complete_renderer_neutral_contract(self) -> None:
        content = (
            ROOT
            / "clean-code-ai-collaboration"
            / "references"
            / "framework-react.md"
        ).read_text(encoding="utf-8")

        for heading in REQUIRED_PROFILE_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, content)
        for term in {
            "Hooks",
            "stale closure",
            "Effect cleanup",
            "state identity",
            "controlled",
            "key",
            "error",
            "loading",
            "react-dom",
            "renderer",
        }:
            with self.subTest(term=term):
                self.assertIn(term.lower(), content.lower())
        self.assertIn("react-native", content.lower())
        self.assertIn("platform APIs are out of scope", content)
        self.assertIn("renderer-neutral", content.lower())

    def test_generated_region_rejects_missing_duplicate_and_reordered_markers(
        self,
    ) -> None:
        start, end = README_MARKERS
        invalid_documents = (
            "no markers",
            f"{start}\ncontent",
            f"{start}\n{start}\n{end}",
            f"{end}\n{start}",
        )

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    replace_generated_region(document, README_MARKERS, "new")

    def test_generator_only_replaces_the_two_generated_regions(self) -> None:
        self.write_generated_documents()

        diagnostics = synchronize_generated_regions(self.fixture_root, check=False)

        self.assertEqual([], list(diagnostics))
        readme = (self.fixture_root / "README.md").read_text(encoding="utf-8")
        runtime = (
            self.fixture_root
            / "clean-code-ai-collaboration"
            / "references"
            / "profile-selection.md"
        ).read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# Before\n\n"))
        self.assertTrue(readme.endswith("\n\nAfter README\n"))
        self.assertTrue(runtime.startswith("# Profile Selection\n\n"))
        self.assertTrue(runtime.endswith("\n\nAfter Runtime Index\n"))
        self.assertNotIn("stale", readme)
        self.assertNotIn("stale", runtime)

    def test_generator_check_reports_drift_without_writing(self) -> None:
        self.write_generated_documents()
        tracked_paths = (
            self.fixture_root / "README.md",
            self.fixture_root
            / "clean-code-ai-collaboration"
            / "references"
            / "profile-selection.md",
        )
        before = {path: path.read_bytes() for path in tracked_paths}

        diagnostics = synchronize_generated_regions(self.fixture_root, check=True)
        with redirect_stdout(io.StringIO()) as output:
            exit_code = generator_main(
                ["--source-root", str(self.fixture_root), "--check"]
            )

        self.assertEqual(1, exit_code)
        self.assertEqual(
            ["generated-drift", "generated-drift"],
            [diagnostic.code for diagnostic in diagnostics],
        )
        self.assertEqual(before, {path: path.read_bytes() for path in tracked_paths})
        self.assertNotIn("Traceback", output.getvalue())

    def test_generator_reports_invalid_yaml_without_a_traceback(self) -> None:
        self.write_generated_documents()
        (self.fixture_root / "profiles" / "catalog.yaml").write_text(
            "schema_version: [\n",
            encoding="utf-8",
            newline="\n",
        )

        with redirect_stdout(io.StringIO()) as output:
            exit_code = generator_main(["--source-root", str(self.fixture_root)])

        self.assertEqual(1, exit_code)
        self.assertIn("catalog-invalid", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_profile_matrix_and_runtime_index_preserve_catalog_order_and_roles(
        self,
    ) -> None:
        profiles = load_registry(ROOT)

        matrix = render_profile_matrix(profiles)
        runtime = render_runtime_index(profiles)

        self.assertIn("| Profile | Kind | Status | Reference | Benchmark |", matrix)
        self.assertLess(matrix.index("C#"), matrix.index("Python"))
        self.assertIn("Not available", matrix)
        self.assertLess(runtime.index("`csharp`"), runtime.index("`python`"))
        for term in {
            "Owning Manifests",
            "Supporting Files",
            "Candidate Dependencies",
            "Supporting Dependencies",
        }:
            with self.subTest(term=term):
                self.assertIn(term, runtime)

    def test_validator_cli_is_read_only_and_returns_zero(self) -> None:
        before = {
            path.relative_to(ROOT).as_posix(): path.read_bytes()
            for path in (ROOT / "profiles").rglob("*")
            if path.is_file()
        }

        exit_code = main(["--source-root", str(ROOT)])

        after = {
            path.relative_to(ROOT).as_posix(): path.read_bytes()
            for path in (ROOT / "profiles").rglob("*")
            if path.is_file()
        }
        self.assertEqual(0, exit_code)
        self.assertEqual(before, after)

    def test_schema_failures_are_sorted_and_cli_returns_one(self) -> None:
        self.update_profile(
            "csharp",
            lambda profile: profile.update({"unknown_field": True}),
        )
        self.update_profile(
            "python",
            lambda profile: profile["ownership"].update({"maintainers": []}),
        )
        diagnostics = validate_repository(self.fixture_root)

        with redirect_stdout(io.StringIO()) as output:
            exit_code = main(["--source-root", str(self.fixture_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual(list(diagnostics), sorted(diagnostics))
        self.assertEqual(
            ["schema-invalid", "schema-invalid"],
            [diagnostic.code for diagnostic in diagnostics],
        )
        self.assertNotIn("Traceback", output.getvalue())

    def test_composition_rejects_unknown_self_cycle_and_asymmetric_conflict(self) -> None:
        cases = {
            "composition-unknown": lambda: self.update_profile(
                "csharp",
                lambda profile: profile["composition"]["requires"].append("ghost"),
            ),
            "composition-self": lambda: self.update_profile(
                "csharp",
                lambda profile: profile["composition"]["requires"].append("csharp"),
            ),
            "composition-cycle": self._create_requires_cycle,
            "conflict-asymmetric": lambda: self.update_profile(
                "csharp",
                lambda profile: profile["composition"]["conflicts"].append("python"),
            ),
        }

        for expected_code, mutate in cases.items():
            with self.subTest(code=expected_code):
                shutil.copytree(
                    ROOT / "profiles",
                    self.fixture_root / "profiles",
                    dirs_exist_ok=True,
                )
                mutate()

                self.assertIn(expected_code, self.diagnostic_codes())

    def _create_requires_cycle(self) -> None:
        self.update_profile(
            "csharp",
            lambda profile: profile["composition"]["requires"].append("python"),
        )
        self.update_profile(
            "python",
            lambda profile: profile["composition"]["requires"].append("csharp"),
        )

    def test_dependency_candidate_and_supporting_roles_cannot_overlap(self) -> None:
        self.update_profile(
            "react",
            lambda profile: profile["detection"]["supporting_dependencies"].append(
                "react"
            ),
        )

        self.assertIn("dependency-role-overlap", self.diagnostic_codes())

    def test_registry_rejects_case_insensitive_ids_and_references(self) -> None:
        self.update_profile(
            "python",
            lambda profile: profile.update({"id": "csharp"}),
        )

        self.assertIn("profile-id-duplicate", self.diagnostic_codes())

        shutil.copytree(
            ROOT / "profiles",
            self.fixture_root / "profiles",
            dirs_exist_ok=True,
        )
        reference = self.fixture_root / "evidence" / "profile.md"
        reference.parent.mkdir(exist_ok=True)
        reference.write_text("# Profile\n", encoding="utf-8")
        for profile_id in ("csharp", "python"):
            self.update_profile(
                profile_id,
                lambda profile: profile.update(
                    {
                        "status": "experimental",
                        "reference": "evidence/profile.md",
                    }
                ),
            )

        self.assertIn("reference-duplicate", self.diagnostic_codes())

    def test_catalog_rejects_duplicate_and_escaped_metadata_paths(self) -> None:
        catalog_path = self.fixture_root / "profiles" / "catalog.yaml"
        invalid_entries = (
            ["csharp.yaml", "CSHARP.yaml"],
            ["../outside.yaml"],
        )
        for entries in invalid_entries:
            with self.subTest(entries=entries):
                catalog_path.write_text(
                    yaml.safe_dump(
                        {"schema_version": "1.0", "profiles": entries},
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                    newline="\n",
                )

                diagnostics = validate_repository(self.fixture_root)

                self.assertEqual("catalog-invalid", diagnostics[0].code)

    def test_missing_reference_and_unknown_deprecation_replacement_fail(self) -> None:
        self.update_profile(
            "csharp",
            lambda profile: profile.update(
                {
                    "status": "deprecated",
                    "reference": "missing/profile.md",
                    "deprecation": {
                        "reason": "Superseded",
                        "replacement": "ghost",
                    },
                }
            ),
        )

        codes = self.diagnostic_codes()

        self.assertIn("reference-invalid", codes)
        self.assertIn("replacement-unknown", codes)

    def test_benchmark_status_cannot_claim_an_unrecorded_stage(self) -> None:
        self.update_profile(
            "csharp",
            lambda profile: profile["evidence"].update(
                {"benchmark_status": "pilot_recorded"}
            ),
        )

        self.assertIn("evidence-status-mismatch", self.diagnostic_codes())

    def test_full_run_result_requires_full_run_recorded_status(self) -> None:
        evidence_path = self.fixture_root / "evidence" / "result.json"
        evidence_path.parent.mkdir()
        evidence_path.write_text('{"status":"passed"}\n', encoding="utf-8")
        digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        reference = self.fixture_root / "evidence" / "profile.md"
        reference.write_text("# Profile\n", encoding="utf-8")
        self._set_evidence_profile(
            status="stable",
            benchmark_status="pilot_recorded",
            stage="full_run",
            outcome="passed",
            digest=digest,
            public=True,
        )
        self.update_profile(
            "csharp",
            lambda profile: profile["evidence"]["results"].append(
                {
                    "stage": "pilot",
                    "outcome": "passed",
                    "path": "evidence/result.json",
                    "sha256": digest,
                    "public": True,
                }
            ),
        )

        self.assertIn("evidence-status-mismatch", self.diagnostic_codes())

    def test_invalid_profile_schema_fails_closed(self) -> None:
        schema_path = self.fixture_root / "profiles" / "profile.schema.json"
        schema_path.write_text('{"type": 123}\n', encoding="utf-8")

        diagnostics = validate_repository(self.fixture_root)

        self.assertEqual("schema-invalid", diagnostics[0].code)

    def test_validator_main_returns_two_for_usage_errors(self) -> None:
        with redirect_stderr(io.StringIO()) as error_output:
            exit_code = main([])

        self.assertEqual(2, exit_code)
        self.assertIn("--source-root", error_output.getvalue())

    def test_evidence_hash_and_benchmark_status_are_recomputed(self) -> None:
        evidence_path = self.fixture_root / "evidence" / "pilot.json"
        evidence_path.parent.mkdir()
        evidence_path.write_text('{"status":"passed"}\n', encoding="utf-8")
        self.update_profile(
            "csharp",
            lambda profile: profile.update(
                {
                    "status": "beta",
                    "reference": "evidence/pilot.json.md",
                    "evidence": {
                        "benchmark_status": "pilot_recorded",
                        "manifests": [],
                        "results": [
                            {
                                "stage": "pilot",
                                "outcome": "passed",
                                "path": "evidence/pilot.json",
                                "sha256": "0" * 64,
                                "public": True,
                            }
                        ],
                    },
                }
            ),
        )
        reference = self.fixture_root / "evidence" / "pilot.json.md"
        reference.write_text("# Evidence\n", encoding="utf-8")

        self.assertIn("evidence-hash-mismatch", self.diagnostic_codes())

    def test_beta_and_stable_require_public_passed_stage_evidence(self) -> None:
        evidence_path = self.fixture_root / "evidence" / "result.json"
        evidence_path.parent.mkdir()
        evidence_path.write_text('{"status":"passed"}\n', encoding="utf-8")
        digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        reference = self.fixture_root / "evidence" / "profile.md"
        reference.write_text("# Profile\n", encoding="utf-8")

        valid_cases = (
            ("beta", "pilot_recorded", "pilot"),
            ("stable", "full_run_recorded", "full_run"),
        )
        for status, benchmark_status, stage in valid_cases:
            with self.subTest(status=status):
                shutil.copytree(
                    ROOT / "profiles",
                    self.fixture_root / "profiles",
                    dirs_exist_ok=True,
                )
                self._set_evidence_profile(
                    status=status,
                    benchmark_status=benchmark_status,
                    stage=stage,
                    outcome="passed",
                    digest=digest,
                    public=True,
                )

                self.assertEqual([], self.diagnostic_codes())

        for outcome in ("failed", "no_difference", "inconclusive"):
            with self.subTest(outcome=outcome):
                shutil.copytree(
                    ROOT / "profiles",
                    self.fixture_root / "profiles",
                    dirs_exist_ok=True,
                )
                self._set_evidence_profile(
                    status="beta",
                    benchmark_status="pilot_recorded",
                    stage="pilot",
                    outcome=outcome,
                    digest=digest,
                    public=True,
                )

                self.assertIn("maturity-evidence-missing", self.diagnostic_codes())

    def _set_evidence_profile(
        self,
        *,
        status: str,
        benchmark_status: str,
        stage: str,
        outcome: str,
        digest: str,
        public: bool,
    ) -> None:
        def update(profile) -> None:
            profile["status"] = status
            profile["reference"] = "evidence/profile.md"
            profile["evidence"] = {
                "benchmark_status": benchmark_status,
                "manifests": [],
                "results": [
                    {
                        "stage": stage,
                        "outcome": outcome,
                        "path": "evidence/result.json",
                        "sha256": digest,
                        "public": public,
                    }
                ],
            }

        self.update_profile("csharp", update)


if __name__ == "__main__":
    unittest.main()
