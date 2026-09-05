import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from evals.harness.manifest import validate_manifest
from evals.harness.anonymizer import build_review_packet
from evals.harness.planner import build_run_slots
from evals.harness.result_builder import build_public_result, validate_profile_pilot_result
from jsonschema import Draft202012Validator
from tests.test_arm_inspection_policy import policy_manifest
from scripts.validate_profiles import load_registry, validate_loaded_profiles
from scripts.build_skill_package import build_package
import yaml


ROOT = Path(__file__).resolve().parents[1]


def public_v2_inputs():
    result = json.loads((ROOT / "evals/results/v0.5.1-profile-pilot.json").read_text("utf-8"))
    manifest = validate_manifest(policy_manifest())
    result["execution"]["subject_executor"] = manifest.subject_executor
    result["source_revisions"].update(
        execution_commit="a" * 40,
        execution_inputs={"evals/harness/manifest.py": "b" * 64},
    )
    for run in result["runs"]:
        run["inspection_diagnostics"] = []
        run["oracle_skipped_reason"] = (
            "not_run_due_to_evidence_gate" if "invalid_claim" in run["automatic_failure_reasons"]
            else "not_applicable"
        )
    return manifest, result


def build_v2(manifest, source):
    return build_public_result(
        build_run_slots(manifest), source["runs"], benchmark_version=manifest.benchmark_version,
        source_revisions=source["source_revisions"], execution=source["execution"],
        review_metadata=source["review_metadata"], profile_outcomes=source["profile_outcomes"],
    )


class PublicResultV2Tests(unittest.TestCase):
    def test_package_hashes_both_actual_schema_inputs_when_results_coexist(self):
        manifest, original = public_v2_inputs()
        result = build_v2(manifest, original)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            for folder in ("profiles", "clean-code-ai-collaboration"):
                shutil.copytree(ROOT / folder, source / folder)
            for relative in (
                "LICENSE", ".gitattributes", "scripts/package-manifest.schema.json",
                "evals/profile-pilot-result.schema.json", "evals/profile-pilot-result-v2.schema.json",
                "evals/results/v0.5.1-profile-pilot.json", "evals/manifests/v0.5.1-profile-pilot.json",
            ):
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            result_bytes = json.dumps(result).encode("utf-8")
            (source / "evals/results/v0.5.2-profile-pilot.json").write_bytes(result_bytes)
            profile_path = source / "profiles/csharp.yaml"
            profile = yaml.safe_load(profile_path.read_text("utf-8"))
            profile["evidence"]["results"].append({
                "stage": "pilot", "outcome": "inconclusive", "public": True,
                "path": "evals/results/v0.5.2-profile-pilot.json",
                "sha256": hashlib.sha256(result_bytes).hexdigest(),
            })
            profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True), "utf-8")
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "fixture"], check=True)
            package = build_package(source, base / "package", "worktree", ["csharp"])
            inputs = {entry["path"]: entry["sha256"] for entry in package["inputs"]}
            for relative in ("evals/profile-pilot-result.schema.json", "evals/profile-pilot-result-v2.schema.json"):
                self.assertEqual(inputs.get(relative), hashlib.sha256((source / relative).read_bytes()).hexdigest())

    def test_registry_selects_only_known_schema_and_rechecks_modified_bytes(self):
        manifest, source = public_v2_inputs()
        result = build_v2(manifest, source)
        profiles = load_registry(ROOT)
        result_path = "evals/results/v0.5.2-profile-pilot.json"
        def diagnostics(candidate, schema_override=None):
            content = json.dumps(candidate).encode("utf-8")
            profiles[0]["evidence"]["results"] = [{
                "stage": "pilot", "outcome": "inconclusive", "path": result_path,
                "sha256": hashlib.sha256(content).hexdigest(), "public": True,
            }]
            def read(path):
                if path == result_path:
                    return content
                if path == "evals/profile-pilot-result-v2.schema.json" and schema_override is not None:
                    return json.dumps(schema_override).encode("utf-8")
                return (ROOT / path).read_bytes()
            return validate_loaded_profiles([(f"profiles/{profile['id']}.yaml", profile) for profile in profiles], read)
        self.assertEqual(diagnostics(result), ())
        self.assertTrue(diagnostics(result, {}))
        for mutate in (
            lambda result: result.update(schema_version="https://untrusted.example/schema"),
            lambda result: result["runs"][0].pop("inspection_diagnostics"),
        ):
            changed = copy.deepcopy(result)
            mutate(changed)
            self.assertIn("evidence-result-schema-invalid", [item.code for item in diagnostics(changed)])

    def test_v5_anonymous_review_hides_inspection_fingerprints_not_objective_criteria(self):
        manifest, source = public_v2_inputs()
        run = next(run for run in source["runs"] if run["scenario_id"] == "fastapi-provider-boundary")
        run.update(
            automatic_failure_reasons=["invalid_claim"],
            inspection_diagnostics=[{"code": "profile_contamination", "path": ".agents/skills/clean-code-ai-collaboration/references/language-python.md"}],
            applied_profiles=["python"],
            blind_spots=["profile_contamination: read language-python.md in core-only"],
            diff="diff --git a/app/main.py b/app/main.py\n+def send(): pass\n",
        )
        packet = build_review_packet(run, "candidate-example", manifest)
        self.assertNotIn("profile_under_test", packet)
        self.assertNotIn("inspection_diagnostics", packet)
        self.assertEqual(packet["automatic_failure_reasons"], ["evidence_gate_failed"])
        self.assertEqual(packet["language"], "python-fastapi")
        self.assertEqual(packet["diff"], run["diff"])
        text = json.dumps(packet)
        for fingerprint in ("profile_contamination", "language-python.md", "core-only", "applied_profiles"):
            self.assertNotIn(fingerprint, text)
        self.assertEqual(len(packet["incremental_criteria"]), 3)

    def test_validator_pins_schema_version_source_slots_and_recomputed_outcome(self):
        manifest, source = public_v2_inputs()
        result = build_v2(manifest, source)
        schema = json.loads((ROOT / "evals/profile-pilot-result-v2.schema.json").read_text("utf-8"))
        def validate(candidate, selected_schema=schema):
            validate_profile_pilot_result(
                candidate, manifest, selected_schema,
                expected_source_revisions=result["source_revisions"],
                expected_scenario_contracts={run["scenario_id"]: run["scenario_contract_sha256"] for run in result["runs"]},
            )
        validate(result)
        with self.assertRaises(ValueError):
            validate(result, {})
        for mutate in (
            lambda result: result.update(schema_version="https://untrusted.example/schema"),
            lambda result: result["runs"].pop(),
            lambda result: result["profile_outcomes"][0].update(outcome="passed"),
            lambda result: result["source_revisions"].update(execution_commit="f" * 40),
        ):
            changed = copy.deepcopy(result)
            mutate(changed)
            with self.assertRaises(ValueError):
                validate(changed)

    def test_builder_rejects_missing_unsafe_or_inconsistent_v2_evidence(self):
        mutations = [
            lambda source: source["runs"][0].pop("inspection_diagnostics"),
            lambda source: source["runs"][0].update(inspection_diagnostics=[{"code": "invalid_skill_path", "path": "D:/private"}]),
            lambda source: source["runs"][0].update(inspection_diagnostics=[{"code": "unknown"}]),
            lambda source: source["runs"][0].update(oracle_skipped_reason="private-detail"),
            lambda source: source["source_revisions"].pop("execution_commit"),
            lambda source: source["source_revisions"].update(execution_inputs={"../private": "a" * 64}),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                manifest, source = public_v2_inputs()
                mutate(source)
                with self.assertRaises(ValueError):
                    build_v2(manifest, source)
        manifest, source = public_v2_inputs()
        run = next(run for run in source["runs"] if "invalid_claim" in run["automatic_failure_reasons"])
        run["oracle_skipped_reason"] = "not_applicable"
        with self.assertRaises(ValueError):
            build_v2(manifest, source)
        for executor in ({"protocol_version": "desktop-subject-v6"}, [], None):
            with self.subTest(executor=executor):
                manifest, source = public_v2_inputs()
                source["execution"]["subject_executor"] = executor
                with self.assertRaises(ValueError):
                    build_v2(manifest, source)

    def test_v2_schema_requires_safe_provenance_and_diagnostics(self):
        schema_path = ROOT / "evals/profile-pilot-result-v2.schema.json"
        self.assertTrue(schema_path.is_file())
        schema = json.loads(schema_path.read_text("utf-8"))
        manifest, source = public_v2_inputs()
        result = build_v2(manifest, source)
        Draft202012Validator(schema).validate(result)
        mutations = [
            ("missing-source", lambda result: result["source_revisions"].pop("execution_commit")),
            ("unsafe-source", lambda result: result["source_revisions"].update(execution_inputs={"C:/private/file.py": "a" * 64})),
            ("missing-diagnostics", lambda result: result["runs"][0].pop("inspection_diagnostics")),
            ("unsafe-diagnostic", lambda result: result["runs"][0].update(inspection_diagnostics=[{"code": "invalid_skill_path", "path": "../secret"}])),
            ("unknown-code", lambda result: result["runs"][0].update(inspection_diagnostics=[{"code": "private-thread"}])),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                changed = copy.deepcopy(result)
                mutate(changed)
                self.assertTrue(list(Draft202012Validator(schema).iter_errors(changed)))

    def test_v5_builder_publishes_required_v2_evidence_without_private_report(self):
        manifest, source = public_v2_inputs()
        run = next(run for run in source["runs"] if "invalid_claim" in run["automatic_failure_reasons"])
        run["inspection_diagnostics"] = [{"code": "invalid_skill_path"}]
        run["raw_report"] = {"subject_thread_id": "private-thread"}
        result = build_v2(manifest, source)
        self.assertEqual(result["schema_version"], "profile-pilot-result/v2")
        published = next(item for item in result["runs"] if item["run_id"] == run["run_id"])
        self.assertEqual(published["inspection_diagnostics"], [{"code": "invalid_skill_path"}])
        self.assertEqual(published["oracle_skipped_reason"], "not_run_due_to_evidence_gate")
        self.assertNotIn("raw_report", published)


if __name__ == "__main__":
    unittest.main()
