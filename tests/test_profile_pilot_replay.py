from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import unittest
import urllib.request
import zipfile

from evals.harness.manifest import validate_manifest
from evals.harness.planner import build_run_slots
from evals.harness.result_builder import (
    build_public_result,
    validate_profile_pilot_result,
)
from evals.v040_strategy_full_run import git_blob_bytes, git_tree_sha256


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "evals/manifests/v0.5.1-profile-pilot.json"
RESULT_PATH = "evals/results/v0.5.1-profile-pilot.json"
EXECUTION_COMMIT = "c7c49df0b5a9b9a1bc49d6e36030c50f0fea372f"
PUBLICATION_COMMIT = "983ca2f7804103209d8e5430d4090b4e55e69928"
SKILL_COMMIT = "bd895776a80566381003182bfdb24f0f02784731"
SKILL_TREE_SHA256 = "118b96e17477c9ecd415b1d995a15a25961d3e070ccaae09fe792a802c13acb5"
FIXTURE_COMMIT = "6ed8712f2b3d4eaf902dbe1470a8740f92700878"
FIXTURE_REPOSITORY = "Clean-Code-AI-Collaboration-Benchmark-Fixtures"


def _git_paths(revision: str, prefix: str) -> list[str]:
    return subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision, "--", prefix],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        timeout=30,
    ).splitlines()


def _tree_digest(files: dict[str, bytes], *, windows_order: bool = False) -> str:
    digest = hashlib.sha256()
    paths = sorted(files, key=PureWindowsPath if windows_order else str)
    for path in paths:
        content = files[path]
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _historical_namespace(
    path: str, revision: str = EXECUTION_COMMIT
) -> dict[str, object]:
    # 只載入本專案已固定 Commit 的 Harness；Fixture 內容不會執行。
    namespace: dict[str, object] = {
        "__name__": "_profile_pilot_historical_replay",
        "__file__": str(ROOT / path),
    }
    source = git_blob_bytes(ROOT, revision, path)
    exec(compile(source, f"{revision}:{path}", "exec"), namespace)
    return namespace


def _fixture_archive_files() -> dict[str, bytes]:
    url = (
        f"https://codeload.github.com/eric861129/{FIXTURE_REPOSITORY}"
        f"/zip/{FIXTURE_COMMIT}"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "profile-pilot-replay"})
    maximum_bytes = 10 * 1024 * 1024
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise ValueError("pinned fixture archive exceeds replay size limit")
    prefix = f"{FIXTURE_REPOSITORY}-{FIXTURE_COMMIT}/"
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for entry in archive.infolist():
            if not entry.filename.startswith(prefix):
                raise ValueError("fixture archive root does not match the pinned commit")
            path = entry.filename.removeprefix(prefix)
            if entry.is_dir():
                continue
            normalized = PurePosixPath(path)
            if (
                normalized.is_absolute()
                or ".." in normalized.parts
                or "\\" in path
                or path in files
            ):
                raise ValueError("fixture archive contains an unsafe or duplicate path")
            # 只讀取八組 Evaluator、Subject Tree 與根契約，不解壓縮到磁碟。
            if path.startswith(("evaluators/", "fixtures/")) or path == "fixture-contract.json":
                files[path] = archive.read(entry)
    return files


class ProfilePilotReplayTests(unittest.TestCase):
    """CI 需完整 Git 歷史與 GitHub 網路；只下載一次固定 Fixture，不重跑 Subjects。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_bytes = git_blob_bytes(ROOT, EXECUTION_COMMIT, MANIFEST_PATH)
        cls.manifest = validate_manifest(json.loads(cls.manifest_bytes))
        cls.result = json.loads((ROOT / RESULT_PATH).read_text(encoding="utf-8"))
        cls.fixture_files = _fixture_archive_files()
        cls.historical_cli = _historical_namespace("evals/harness/cli.py")
        subject = _historical_namespace("evals/harness/subject_runner.py")
        prompts = {
            f"{scenario['id']}/{arm_id}": hashlib.sha256(
                subject["canonical_prompt_bytes"](
                    subject["build_prompt"](scenario, arm_id, cls.manifest)
                )
            ).hexdigest()
            for scenario in cls.manifest.scenarios
            for arm_id in scenario["comparison_arms"]
        }
        evaluators = {}
        for scenario in cls.manifest.scenarios:
            prefix = str(scenario["evaluator_path"]) + "/"
            files = {
                path.removeprefix(prefix): content
                for path, content in cls.fixture_files.items()
                if path.startswith(prefix)
            }
            if not files:
                raise ValueError(f"pinned evaluator tree is missing: {prefix}")
            # 此 Pilot 的 Windows Clone 使用 core.autocrlf=true，且 Fixture
            # 未設定 .gitattributes。凍結值使用 CRLF Bytes 與 Windows 路徑排序；
            # 這是歷史執行條件，Ubuntu CI 也必須重建同一組 Bytes。
            if any(b"\r" in content or b"\0" in content for content in files.values()):
                raise ValueError("pinned evaluators must be LF text before checkout replay")
            windows_files = {
                path: content.replace(b"\n", b"\r\n")
                for path, content in files.items()
            }
            evaluators[str(scenario["id"])] = _tree_digest(
                windows_files, windows_order=True
            )
        harness_files = {
            path.removeprefix("evals/harness/"): git_blob_bytes(ROOT, EXECUTION_COMMIT, path)
            for path in _git_paths(EXECUTION_COMMIT, "evals/harness")
            if path.endswith(".py")
        }
        cls.contract = {
            "schema_version": "1.0",
            "manifest_sha256": hashlib.sha256(cls.manifest_bytes).hexdigest(),
            "harness_sha256": _tree_digest(harness_files),
            **cls.historical_cli["_subject_client_contract"](cls.manifest),
            "fixture_commit": cls.manifest.fixture_commit,
            "skill_commit": cls.manifest.skill_commit,
            "prompts": prompts,
            "evaluators": evaluators,
            "rubrics": {
                path: hashlib.sha256(git_blob_bytes(ROOT, EXECUTION_COMMIT, path)).hexdigest()
                for path in _git_paths(EXECUTION_COMMIT, "evals/rubrics")
                if path.endswith(".md")
            },
        }
        # 公開資料保留執行時的 Contract。983ca2f 只處理完成後的輸出去識別。
        cls.historical_cli["_freeze_document"] = lambda manifest, paths: cls.contract

    def test_published_result_has_a_reproducible_execution_source(self) -> None:
        self.assertEqual(self.manifest_bytes, (ROOT / MANIFEST_PATH).read_bytes())
        self.assertEqual(FIXTURE_COMMIT, self.manifest.fixture_commit)
        self.assertEqual(SKILL_COMMIT, self.manifest.skill_commit)
        self.assertEqual(
            SKILL_COMMIT,
            subprocess.check_output(
                ["git", "rev-parse", "v0.5.0^{}"], cwd=ROOT, text=True, timeout=30
            ).strip(),
        )
        self.assertEqual(
            SKILL_TREE_SHA256,
            git_tree_sha256(ROOT, SKILL_COMMIT, "clean-code-ai-collaboration"),
        )
        for arm in self.manifest.arms:
            for inspection_path in arm.required_skill_inspection_paths:
                self.assertTrue(
                    git_blob_bytes(
                        ROOT, SKILL_COMMIT, inspection_path.removeprefix(".agents/skills/")
                    )
                )
        source_revisions = {
            "fixture_tag": self.manifest.fixture_tag,
            "fixture_commit": FIXTURE_COMMIT,
            "skill_tag": self.manifest.skill_tag,
            "skill_commit": SKILL_COMMIT,
            "manifest_path": MANIFEST_PATH,
            "contract_sha256": self.historical_cli["_canonical_sha256"](self.contract),
            **{
                key: self.contract[key]
                for key in ("manifest_sha256", "harness_sha256", "prompts", "evaluators", "rubrics")
            },
        }
        self.assertEqual(source_revisions, self.result["source_revisions"])
        expected_scenario_contracts = {
            str(scenario["id"]): self.historical_cli["_scenario_contract_sha256"](
                self.manifest, None, str(scenario["id"])
            )
            for scenario in self.manifest.scenarios
        }
        schema = json.loads(
            (ROOT / "evals/profile-pilot-result.schema.json").read_text(encoding="utf-8")
        )
        validate_profile_pilot_result(
            self.result,
            self.manifest,
            schema,
            expected_source_revisions=source_revisions,
            expected_scenario_contracts=expected_scenario_contracts,
        )

    def test_publication_redaction_preserves_the_frozen_execution_contract(self) -> None:
        changed_harness = subprocess.check_output(
            [
                "git", "diff", "--name-only", EXECUTION_COMMIT, PUBLICATION_COMMIT,
                "--", "evals/harness",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            timeout=30,
        ).splitlines()
        self.assertEqual(["evals/harness/result_builder.py"], changed_harness)
        publication = _historical_namespace(
            "evals/harness/result_builder.py", PUBLICATION_COMMIT
        )
        # 分別驗證歷史與目前 Builder 的輸出，允許後續 Harness 相容演進。
        for builder in (publication["build_public_result"], build_public_result):
            with self.subTest(builder=builder.__module__):
                rebuilt = builder(
                    build_run_slots(self.manifest),
                    self.result["runs"],
                    benchmark_version=self.manifest.benchmark_version,
                    source_revisions=self.result["source_revisions"],
                    execution=self.result["execution"],
                    review_metadata=self.result["review_metadata"],
                    profile_outcomes=self.result["profile_outcomes"],
                )
                self.assertEqual(self.result, rebuilt)
