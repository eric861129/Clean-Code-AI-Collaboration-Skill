"""從公開 Git 來源重建 v0.5.2 契約；不讀私有 Receipt 或重跑 Subject。"""
from __future__ import annotations

import hashlib
import json
import unittest

from evals.harness.manifest import validate_manifest
from evals.harness.planner import build_run_slots
from evals.harness.result_builder import build_public_result, validate_profile_pilot_result
from evals.v040_strategy_full_run import git_blob_bytes
from tests.test_profile_pilot_replay import (
    ROOT, _fixture_archive_files, _git_paths, _historical_namespace, _tree_digest,
)


EXECUTION_COMMIT = "bbdfb0618dc65b0a56ead0e79d0929c1acc305f8"
FIXTURE_COMMIT = "133e2f739e5d943e853f4c9106d8965ecfac3018"
SKILL_COMMIT = "4ce3a697eb7eea36ecddd937ffa915f931e9524a"
MANIFEST_PATH = "evals/manifests/v0.5.2-profile-pilot.json"
RESULT_PATH = "evals/results/v0.5.2-profile-pilot.json"


class ProfilePilotV052ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads((ROOT / RESULT_PATH).read_text(encoding="utf-8"))
        manifest_bytes = git_blob_bytes(ROOT, EXECUTION_COMMIT, MANIFEST_PATH)
        cls.manifest = validate_manifest(json.loads(manifest_bytes))
        fixture = _fixture_archive_files(FIXTURE_COMMIT)
        cli = _historical_namespace("evals/harness/cli.py", EXECUTION_COMMIT)
        subject = _historical_namespace("evals/harness/subject_runner.py", EXECUTION_COMMIT)
        input_paths = sorted({
            path for path in _git_paths(EXECUTION_COMMIT, ".")
            if (path.startswith("evals/harness/") and path.endswith(".py"))
            or (path.startswith("evals/rubrics/") and path.endswith(".md"))
            or (path.startswith("evals/") and path.endswith(".schema.json"))
            or path in {MANIFEST_PATH, "evals/v040_strategy_full_run.py",
                        "requirements-dev.txt", ".gitattributes"}
        })
        inputs = {
            path: hashlib.sha256(git_blob_bytes(ROOT, EXECUTION_COMMIT, path)).hexdigest()
            for path in input_paths
        }
        provenance = {
            "schema_version": "execution-provenance/v1",
            "execution_commit": EXECUTION_COMMIT,
            "manifest_path": MANIFEST_PATH,
            "input_sha256": inputs,
            "inputs_sha256": cli["_canonical_sha256"](inputs),
        }
        evaluators = {}
        for scenario in cls.manifest.scenarios:
            prefix = str(scenario["evaluator_path"]) + "/"
            files = {
                path.removeprefix(prefix): content
                for path, content in fixture.items() if path.startswith(prefix)
            }
            if not files or any(b"\r" in content or b"\0" in content for content in files.values()):
                raise ValueError("v2 evaluator must contain pinned LF text")
            evaluators[str(scenario["id"])] = _tree_digest(files)
        cls.contract = {
            "schema_version": "1.0",
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "harness_sha256": provenance["inputs_sha256"],
            **cli["_subject_client_contract"](cls.manifest),
            "fixture_commit": FIXTURE_COMMIT,
            "skill_commit": SKILL_COMMIT,
            "prompts": {
                f"{scenario['id']}/{arm_id}": hashlib.sha256(
                    subject["canonical_prompt_bytes"](
                        subject["build_prompt"](scenario, arm_id, cls.manifest)
                    )
                ).hexdigest()
                for scenario in cls.manifest.scenarios
                for arm_id in scenario["comparison_arms"]
            },
            "evaluators": evaluators,
            "rubrics": {
                path: inputs[path] for path in inputs if path.startswith("evals/rubrics/")
            },
            "execution_provenance": provenance,
            "execution_commit": EXECUTION_COMMIT,
            "execution_inputs": inputs,
        }
        cls.source = {
            "fixture_tag": "profile-pilot-v2",
            "fixture_commit": FIXTURE_COMMIT,
            "skill_tag": "v0.5.1",
            "skill_commit": SKILL_COMMIT,
            "manifest_path": MANIFEST_PATH,
            "contract_sha256": cli["_canonical_sha256"](cls.contract),
            **{
                key: cls.contract[key]
                for key in ("manifest_sha256", "harness_sha256", "prompts",
                            "evaluators", "rubrics", "execution_commit", "execution_inputs")
            },
        }
        cli["_freeze_document"] = lambda manifest, paths: cls.contract
        cls.scenario_contracts = {
            str(scenario["id"]): cli["_scenario_contract_sha256"](
                cls.manifest, None, str(scenario["id"])
            )
            for scenario in cls.manifest.scenarios
        }

    def test_public_result_replays_from_pinned_lf_git_sources(self) -> None:
        self.assertEqual(28, len(self.source["execution_inputs"]))
        self.assertEqual(
            "3b55784dad43d89d6a9ae9f029865b54a5a92718056a4b754844698fee57f651",
            self.source["contract_sha256"],
        )
        schema = json.loads(
            (ROOT / "evals/profile-pilot-result-v2.schema.json").read_text(encoding="utf-8")
        )
        validate_profile_pilot_result(
            self.result, self.manifest, schema,
            expected_source_revisions=self.source,
            expected_scenario_contracts=self.scenario_contracts,
        )
        self.assertEqual(34, len(self.result["runs"]))
        self.assertTrue(all(isinstance(run["review"], dict) for run in self.result["runs"]))

    def test_public_builder_reproduces_result_without_private_evidence(self) -> None:
        rebuilt = build_public_result(
            build_run_slots(self.manifest), self.result["runs"],
            benchmark_version=self.manifest.benchmark_version,
            source_revisions=self.source,
            execution=self.result["execution"],
            review_metadata=self.result["review_metadata"],
            profile_outcomes=self.result["profile_outcomes"],
        )
        self.assertEqual(self.result, rebuilt)
        canonical_bytes = (json.dumps(self.result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.assertEqual(canonical_bytes, (ROOT / RESULT_PATH).read_bytes())
