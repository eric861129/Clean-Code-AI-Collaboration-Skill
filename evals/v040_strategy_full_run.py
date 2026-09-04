from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "evals" / "manifests" / "v0.4.0-strategy-full-run.json"
DEFAULT_RUNS_ROOT = ROOT / ".benchmark-runs" / "v0.4.0-strategy-g04"
DEFAULT_RESULT_PATH = ROOT / "evals" / "results" / "v0.4.0-strategy-full-run.json"
SKILL_SOURCE = ROOT / "clean-code-ai-collaboration"
REQUIRED_INSPECTION_SUFFIXES = {
    "skill/clean-code-ai-collaboration/SKILL.md",
    "skill/clean-code-ai-collaboration/references/testing-and-change-safety.md",
}
EXPECTED_RESULT_KEYS = {
    "status",
    "requested_development_rhythm",
    "effective_development_rhythm",
    "development_rhythm_source",
    "requested_validation_profile",
    "effective_validation_profile",
    "validation_profile_source",
    "mandatory_gates_preserved",
    "missing_prerequisites",
    "recommended_alternative",
}
MANIFEST_KEYS = {
    "schema_version",
    "benchmark_version",
    "skill_version",
    "full_run_generation",
    "model",
    "reasoning_effort",
    "repetitions",
    "claim_boundary",
    "scenarios",
}
SCENARIO_KEYS = {"id", "input", "expected"}
DEVELOPMENT_RHYTHMS = {
    "auto",
    "direct",
    "tdd",
    "tcr",
    "characterization-first",
}
VALIDATION_PROFILES = {
    "auto",
    "focused",
    "repository",
    "acceptance-e2e",
    "mutation-assisted",
}
PREFERENCE_SOURCES = {"user-prompt", "repository-policy", "default-auto"}
ALLOWED_PREREQUISITES = {
    "fast-test-feedback",
    "reliable-test-oracle",
    "isolated-working-tree",
    "version-control-authorization",
    "mutation-tool-and-install-authorization",
}
ALLOWED_RESULT_KEYS = EXPECTED_RESULT_KEYS | {
    "schema_version",
    "run_id",
    "files_inspected",
    "skill_sha256",
    "rationale",
}


def validate_expected_contract(expected: Any) -> None:
    if not isinstance(expected, dict) or set(expected) != EXPECTED_RESULT_KEYS:
        raise ValueError("scenario expected contract must contain every fixed field")
    if expected["status"] not in {"ready", "blocked"}:
        raise ValueError("scenario expected contract has an invalid status")
    if expected["requested_development_rhythm"] not in DEVELOPMENT_RHYTHMS:
        raise ValueError("scenario expected contract has an invalid requested rhythm")
    if expected["effective_development_rhythm"] not in DEVELOPMENT_RHYTHMS | {None}:
        raise ValueError("scenario expected contract has an invalid effective rhythm")
    if expected["development_rhythm_source"] not in PREFERENCE_SOURCES:
        raise ValueError("scenario expected contract has an invalid rhythm source")
    if expected["requested_validation_profile"] not in VALIDATION_PROFILES:
        raise ValueError("scenario expected contract has an invalid requested profile")
    if expected["effective_validation_profile"] not in VALIDATION_PROFILES | {None}:
        raise ValueError("scenario expected contract has an invalid effective profile")
    if expected["validation_profile_source"] not in PREFERENCE_SOURCES:
        raise ValueError("scenario expected contract has an invalid profile source")
    if expected["mandatory_gates_preserved"] is not True:
        raise ValueError("scenario expected contract must preserve mandatory gates")
    prerequisites = expected["missing_prerequisites"]
    if (
        not isinstance(prerequisites, list)
        or len(prerequisites) != len(set(prerequisites))
        or not set(prerequisites).issubset(ALLOWED_PREREQUISITES)
    ):
        raise ValueError("scenario expected contract has invalid missing prerequisites")
    if expected["recommended_alternative"] not in (
        DEVELOPMENT_RHYTHMS | VALIDATION_PROFILES | {None}
    ):
        raise ValueError("scenario expected contract has an invalid alternative")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if set(manifest) != MANIFEST_KEYS:
        raise ValueError("manifest fields do not match the fixed schema")
    if manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported strategy benchmark schema")
    if manifest.get("benchmark_version") != "0.4.0-strategy-full-run-v2":
        raise ValueError("unexpected strategy benchmark version")
    if manifest.get("skill_version") != "0.4.0":
        raise ValueError("unexpected Skill version")
    if not isinstance(manifest.get("full_run_generation"), int):
        raise ValueError("full_run_generation must be an integer")
    if manifest.get("repetitions") != 2:
        raise ValueError("v0.4.0 strategy Full Run requires two repetitions")
    if not isinstance(manifest.get("scenarios"), list) or not manifest["scenarios"]:
        raise ValueError("manifest scenarios must be a non-empty list")
    for scenario in manifest["scenarios"]:
        if set(scenario) != SCENARIO_KEYS:
            raise ValueError("scenario fields do not match the fixed schema")
        if not isinstance(scenario.get("input"), dict):
            raise ValueError("scenario input must be an object")
        validate_expected_contract(scenario.get("expected"))
    scenario_ids = [scenario["id"] for scenario in manifest["scenarios"]]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("scenario ids must be unique")
    return manifest


def build_slots(manifest: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    generation = manifest["full_run_generation"]
    slots = [
        {
            "run_id": (
                f"{scenario['id']}--skill-v0.4.0--g{generation:02d}--r{repetition:02d}"
            ),
            "scenario_id": scenario["id"],
            "repetition": repetition,
            "arm": "skill-v0.4.0",
        }
        for scenario in manifest["scenarios"]
        for repetition in range(1, manifest["repetitions"] + 1)
    ]
    random.Random(560400).shuffle(slots)
    return tuple(slots)


def build_baseline_slots(manifest: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    generation = manifest["full_run_generation"]
    slots = [
        {
            "run_id": f"{scenario['id']}--baseline--g{generation:02d}--r01",
            "scenario_id": scenario["id"],
            "repetition": 1,
            "arm": "baseline",
        }
        for scenario in manifest["scenarios"]
    ]
    random.Random(560399).shuffle(slots)
    return tuple(slots)


def build_prompt(
    *,
    run_id: str,
    scenario: dict[str, Any],
    skill_relative_path: str | None,
    result_relative_path: str,
) -> str:
    scenario_input = json.dumps(scenario["input"], ensure_ascii=False)
    if skill_relative_path is None:
        reading_steps = """1. 不得讀取或使用本次未提供的 Skill，也不要搜尋 Workspace 外的評測資料。
2. 只依目前 Prompt、Repository Policy 與已知事實，判斷要求的開發節奏與驗證範圍是否可行。
3. 將 UTF-8 JSON 寫入指定結果檔。不要 Commit、Push、安裝工具或修改其他檔案。"""
        skill_sha_example = "null"
    else:
        reading_steps = f"""1. 完整讀取 `{skill_relative_path}`。
2. 依 Skill 路由完整讀取 `skill/clean-code-ai-collaboration/references/testing-and-change-safety.md`。
3. 依目前 Prompt、Repository Policy 與已知事實，判斷要求的開發節奏與驗證範圍是否可行。
4. 明確選擇不得略過 Repository 必要 Gate，也不得在前置條件不足時偷偷換成另一種節奏。
5. 計算 staged `SKILL.md` 的 SHA-256。
6. 將 UTF-8 JSON 寫入指定結果檔。不要 Commit、Push、安裝工具或修改其他檔案。"""
        skill_sha_example = '"64 lowercase hexadecimal characters"'
    return f"""# v0.4.0 Strategy Full Run Subject

你是全新 Context 的評測 Subject。只根據下列輸入做一次策略判斷，不修改任何產品程式碼。

{reading_steps}

結果路徑：`{result_relative_path}`

Run ID：`{run_id}`

輸入：

```json
{scenario_input}
```

輸出必須包含以下欄位：

```json
{{
  "schema_version": "1.0",
  "run_id": "{run_id}",
  "status": "ready or blocked",
  "requested_development_rhythm": "string",
  "effective_development_rhythm": "string or null",
  "development_rhythm_source": "user-prompt, repository-policy, or default-auto",
  "requested_validation_profile": "string",
  "effective_validation_profile": "string or null",
  "validation_profile_source": "user-prompt, repository-policy, or default-auto",
  "mandatory_gates_preserved": true,
  "missing_prerequisites": ["stable-machine-readable-id"],
  "recommended_alternative": "string or null",
  "files_inspected": ["Workspace-relative POSIX path"],
  "skill_sha256": {skill_sha_example},
  "rationale": "brief evidence-based reason"
}}
```

`missing_prerequisites` 只使用 `fast-test-feedback`、`reliable-test-oracle`、`isolated-working-tree`、`version-control-authorization` 或 `mutation-tool-and-install-authorization`；沒有缺件時使用空陣列。`recommended_alternative` 只使用正式 rhythm／profile ID。若明確設定不可行，`status` 必須是 `blocked`，不可自行替換。
"""


def evaluate_subject_result(
    scenario: dict[str, Any],
    result: dict[str, Any],
    *,
    require_skill_inspection: bool = True,
) -> list[str]:
    failures: list[str] = []
    unknown_fields = sorted(set(result) - ALLOWED_RESULT_KEYS)
    if unknown_fields:
        failures.append(f"unknown fields: {', '.join(unknown_fields)}")
    for key, expected_value in scenario["expected"].items():
        if result.get(key) != expected_value:
            failures.append(
                f"{key}: expected {expected_value!r}, observed {result.get(key)!r}"
            )

    prerequisites = result.get("missing_prerequisites")
    if (
        not isinstance(prerequisites, list)
        or len(prerequisites) != len(set(prerequisites))
        or not set(prerequisites).issubset(ALLOWED_PREREQUISITES)
    ):
        failures.append("missing_prerequisites: expected known unique stable IDs")

    if require_skill_inspection:
        inspected = result.get("files_inspected")
        if not isinstance(inspected, list) or not REQUIRED_INSPECTION_SUFFIXES.issubset(
            set(inspected)
        ):
            failures.append("files_inspected: required Skill files were not reported")

        skill_sha256 = result.get("skill_sha256")
        if not isinstance(skill_sha256, str) or re.fullmatch(
            r"[0-9a-f]{64}", skill_sha256
        ) is None:
            failures.append(
                "skill_sha256: expected 64 lowercase hexadecimal characters"
            )

    rationale = result.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("rationale: expected a non-empty evidence-based reason")
    return failures


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_expected_dispatch(
    *,
    manifest: dict[str, Any],
    slot: dict[str, Any],
    scenario: dict[str, Any],
    prompt: str,
    skill_file_sha256: str | None,
    skill_tree_sha256: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "benchmark_version": manifest["benchmark_version"],
        "run_id": slot["run_id"],
        "scenario_id": scenario["id"],
        "repetition": slot["repetition"],
        "arm": slot["arm"],
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "manifest_sha256": file_sha256(MANIFEST_PATH),
        "skill_file_sha256": skill_file_sha256,
        "skill_tree_sha256": skill_tree_sha256,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }


def validate_workspace_provenance(
    *,
    manifest: dict[str, Any],
    slot: dict[str, Any],
    scenario: dict[str, Any],
    workspace: Path,
) -> dict[str, Any]:
    staged_skill = workspace / "skill" / "clean-code-ai-collaboration"
    skill_relative_path: str | None = None
    skill_file_hash: str | None = None
    skill_tree_hash: str | None = None
    failures: list[str] = []

    if slot["arm"] == "skill-v0.4.0":
        if not staged_skill.is_dir():
            failures.append("staged Skill is missing")
        else:
            skill_relative_path = "skill/clean-code-ai-collaboration/SKILL.md"
            skill_file_hash = file_sha256(staged_skill / "SKILL.md")
            skill_tree_hash = tree_sha256(staged_skill)
            if skill_file_hash != file_sha256(SKILL_SOURCE / "SKILL.md"):
                failures.append("staged SKILL.md differs from the evaluated source")
            if skill_tree_hash != tree_sha256(SKILL_SOURCE):
                failures.append("staged Skill tree differs from the evaluated source")
    elif staged_skill.exists():
        failures.append("baseline workspace unexpectedly contains the Skill")

    expected_prompt = build_prompt(
        run_id=slot["run_id"],
        scenario=scenario,
        skill_relative_path=skill_relative_path,
        result_relative_path="subject-result.json",
    )
    prompt_path = workspace / "prompt.md"
    if not prompt_path.is_file() or prompt_path.read_text(encoding="utf-8") != expected_prompt:
        failures.append("subject prompt differs from the fixed manifest")

    expected_dispatch = build_expected_dispatch(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        prompt=expected_prompt,
        skill_file_sha256=skill_file_hash,
        skill_tree_sha256=skill_tree_hash,
    )
    dispatch_path = workspace / "dispatch.json"
    if not dispatch_path.is_file():
        failures.append("dispatch is missing")
    else:
        observed_dispatch = json.loads(dispatch_path.read_text(encoding="utf-8"))
        if observed_dispatch != expected_dispatch:
            failures.append("dispatch differs from controller-owned values")

    if failures:
        raise ValueError("provenance validation failed: " + "; ".join(failures))
    return expected_dispatch


def build_terminal_payload(
    *,
    manifest: dict[str, Any],
    slot: dict[str, Any],
    scenario: dict[str, Any],
    dispatch: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    failures = []
    if result.get("schema_version") != "1.0":
        failures.append("schema_version: expected '1.0'")
    if result.get("run_id") != slot["run_id"]:
        failures.append(f"run_id: expected {slot['run_id']!r}")
    require_skill_inspection = slot["arm"] == "skill-v0.4.0"
    failures.extend(
        evaluate_subject_result(
            scenario,
            result,
            require_skill_inspection=require_skill_inspection,
        )
    )
    if require_skill_inspection and result.get("skill_sha256") != dispatch["skill_file_sha256"]:
        failures.append("skill_sha256: staged Skill content hash does not match")
    return {
        "schema_version": "1.0",
        "benchmark_version": manifest["benchmark_version"],
        "run_id": slot["run_id"],
        "scenario_id": scenario["id"],
        "repetition": slot["repetition"],
        "arm": slot["arm"],
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "manifest_sha256": dispatch["manifest_sha256"],
        "terminal_state": (
            "passed"
            if not failures
            else "baseline-diverged"
            if slot["arm"] == "baseline"
            else "failed"
        ),
        "failures": failures,
        "decision": {key: result.get(key) for key in EXPECTED_RESULT_KEYS},
        "files_inspected": result.get("files_inspected", []),
        "skill_file_sha256": dispatch["skill_file_sha256"],
        "skill_tree_sha256": dispatch["skill_tree_sha256"],
        "prompt_sha256": dispatch["prompt_sha256"],
        "rationale": result.get("rationale", ""),
    }


def build_terminal_from_subject(
    *,
    manifest: dict[str, Any],
    slot: dict[str, Any],
    scenario: dict[str, Any],
    workspace: Path,
    dispatch: dict[str, Any],
) -> dict[str, Any]:
    result_path = workspace / "subject-result.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"subject result is missing: {slot['run_id']}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    return build_terminal_payload(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        dispatch=dispatch,
        result=result,
    )


def stage_run(run_id: str, runs_root: Path = DEFAULT_RUNS_ROOT) -> dict[str, Any]:
    manifest = load_manifest()
    all_slots = (*build_baseline_slots(manifest), *build_slots(manifest))
    slot = next((item for item in all_slots if item["run_id"] == run_id), None)
    if slot is None:
        raise ValueError(f"unknown run id: {run_id}")
    scenario = next(
        item for item in manifest["scenarios"] if item["id"] == slot["scenario_id"]
    )
    workspace = runs_root / "workspaces" / run_id
    if workspace.exists():
        raise FileExistsError(f"workspace already exists: {run_id}")
    staged_skill = workspace / "skill" / "clean-code-ai-collaboration"
    skill_relative_path: str | None = None
    skill_file_sha256: str | None = None
    skill_tree_sha256: str | None = None
    if slot["arm"] == "skill-v0.4.0":
        shutil.copytree(SKILL_SOURCE, staged_skill)
        skill_relative_path = "skill/clean-code-ai-collaboration/SKILL.md"
        skill_file_sha256 = file_sha256(staged_skill / "SKILL.md")
        skill_tree_sha256 = tree_sha256(staged_skill)
    else:
        workspace.mkdir(parents=True)
    result_relative_path = "subject-result.json"
    prompt = build_prompt(
        run_id=run_id,
        scenario=scenario,
        skill_relative_path=skill_relative_path,
        result_relative_path=result_relative_path,
    )
    (workspace / "prompt.md").write_text(prompt, encoding="utf-8")
    (workspace / "scenario-input.json").write_text(
        json.dumps(scenario["input"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    dispatch = build_expected_dispatch(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        prompt=prompt,
        skill_file_sha256=skill_file_sha256,
        skill_tree_sha256=skill_tree_sha256,
    )
    (workspace / "dispatch.json").write_text(
        json.dumps(dispatch, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "run_id": run_id,
        "workspace": str(workspace.resolve()),
        "prompt": str((workspace / "prompt.md").resolve()),
        "instruction": (
            f"請完整遵守 {str((workspace / 'prompt.md').resolve())} 的評測指示，"
            f"並只在 {str(workspace.resolve())} 內工作。完成後確認 subject-result.json 已寫入。"
        ),
    }


def collect_run(run_id: str, runs_root: Path = DEFAULT_RUNS_ROOT) -> dict[str, Any]:
    manifest = load_manifest()
    all_slots = (*build_baseline_slots(manifest), *build_slots(manifest))
    slot = next((item for item in all_slots if item["run_id"] == run_id), None)
    if slot is None:
        raise ValueError(f"unknown run id: {run_id}")
    scenario = next(
        item for item in manifest["scenarios"] if item["id"] == slot["scenario_id"]
    )
    workspace = runs_root / "workspaces" / run_id
    dispatch = validate_workspace_provenance(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        workspace=workspace,
    )
    terminal = build_terminal_from_subject(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        workspace=workspace,
        dispatch=dispatch,
    )
    terminal_path = runs_root / "terminals" / f"{run_id}.json"
    terminal_path.parent.mkdir(parents=True, exist_ok=True)
    if terminal_path.exists():
        raise FileExistsError(f"terminal result already exists: {run_id}")
    terminal_path.write_text(
        json.dumps(terminal, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return terminal


def verify_runs(runs_root: Path = DEFAULT_RUNS_ROOT) -> dict[str, Any]:
    manifest = load_manifest()
    baseline_ids = {slot["run_id"] for slot in build_baseline_slots(manifest)}
    full_ids = {slot["run_id"] for slot in build_slots(manifest)}
    expected_ids = baseline_ids | full_ids
    terminal_paths = list((runs_root / "terminals").glob("*.json"))
    observed = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in terminal_paths
    }
    missing = sorted(expected_ids - set(observed))
    unexpected = sorted(set(observed) - expected_ids)
    failed_full = sorted(
        run_id
        for run_id, terminal in observed.items()
        if run_id in full_ids and terminal.get("terminal_state") != "passed"
    )
    provenance_failures: list[str] = []
    replay_failures: list[str] = []
    slots_by_id = {
        slot["run_id"]: slot
        for slot in (*build_baseline_slots(manifest), *build_slots(manifest))
    }
    scenarios_by_id = {
        scenario["id"]: scenario for scenario in manifest["scenarios"]
    }
    for run_id in sorted(expected_ids & set(observed)):
        slot = slots_by_id[run_id]
        scenario = scenarios_by_id[slot["scenario_id"]]
        try:
            dispatch = validate_workspace_provenance(
                manifest=manifest,
                slot=slot,
                scenario=scenario,
                workspace=runs_root / "workspaces" / run_id,
            )
        except (FileNotFoundError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            provenance_failures.append(f"{run_id}: {error}")
            continue
        terminal = observed[run_id]
        try:
            replayed_terminal = build_terminal_from_subject(
                manifest=manifest,
                slot=slot,
                scenario=scenario,
                workspace=runs_root / "workspaces" / run_id,
                dispatch=dispatch,
            )
        except (FileNotFoundError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            replay_failures.append(f"{run_id}: {error}")
            continue
        if terminal != replayed_terminal:
            replay_failures.append(
                f"{run_id}: terminal differs from replayed Subject oracle"
            )
    full_tree_hashes = {
        observed[run_id].get("skill_tree_sha256")
        for run_id in full_ids
        if run_id in observed
    }
    inconsistent_skill_snapshot = len(full_tree_hashes) > 1
    status = (
        "passed"
        if not missing
        and not unexpected
        and not failed_full
        and not provenance_failures
        and not replay_failures
        and not inconsistent_skill_snapshot
        else "failed"
    )
    return {
        "benchmark_version": manifest["benchmark_version"],
        "status": status,
        "expected_baseline_runs": len(baseline_ids),
        "collected_baseline_runs": sum(run_id in observed for run_id in baseline_ids),
        "expected_full_runs": len(full_ids),
        "passed_full_runs": sum(
            run_id in observed and observed[run_id].get("terminal_state") == "passed"
            for run_id in full_ids
        ),
        "missing_runs": missing,
        "unexpected_runs": unexpected,
        "failed_full_runs": failed_full,
        "provenance_failures": provenance_failures,
        "replay_failures": replay_failures,
        "inconsistent_skill_snapshot": inconsistent_skill_snapshot,
    }


def build_public_receipt(
    *,
    manifest: dict[str, Any],
    slot: dict[str, Any],
    runs_root: Path,
) -> dict[str, Any]:
    scenario = next(
        item for item in manifest["scenarios"] if item["id"] == slot["scenario_id"]
    )
    workspace = runs_root / "workspaces" / slot["run_id"]
    dispatch = validate_workspace_provenance(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        workspace=workspace,
    )
    subject_result = json.loads(
        (workspace / "subject-result.json").read_text(encoding="utf-8")
    )
    terminal = json.loads(
        (runs_root / "terminals" / f"{slot['run_id']}.json").read_text(
            encoding="utf-8"
        )
    )
    replayed_terminal = build_terminal_payload(
        manifest=manifest,
        slot=slot,
        scenario=scenario,
        dispatch=dispatch,
        result=subject_result,
    )
    if terminal != replayed_terminal:
        raise RuntimeError(
            f"terminal differs from replayed Subject oracle: {slot['run_id']}"
        )
    return {
        "run_id": slot["run_id"],
        "prompt": (workspace / "prompt.md").read_text(encoding="utf-8"),
        "dispatch": dispatch,
        "subject_result": subject_result,
        "terminal": terminal,
    }


def verify_public_result(
    result_path: Path = DEFAULT_RESULT_PATH,
) -> dict[str, Any]:
    manifest = load_manifest()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        return {"status": "failed", "failures": ["published result must be an object"]}
    failures: list[str] = []
    expected_root_metadata = {
        "schema_version": "1.0",
        "benchmark_version": manifest["benchmark_version"],
        "skill_version": manifest["skill_version"],
        "status": "complete",
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "skill_tree_sha256": tree_sha256(SKILL_SOURCE),
        "claim_boundary": manifest["claim_boundary"],
        "scenario_count": len(manifest["scenarios"]),
        "repetitions": manifest["repetitions"],
    }
    for field, expected in expected_root_metadata.items():
        if result.get(field) != expected:
            failures.append(f"{field} does not match the fixed benchmark contract")
    if result.get("manifest_sha256") != file_sha256(MANIFEST_PATH):
        failures.append("manifest hash does not match the published result")
    if result.get("harness_sha256") != file_sha256(Path(__file__)):
        failures.append("harness hash does not match the published result")

    slots = (*build_baseline_slots(manifest), *build_slots(manifest))
    receipts = result.get("receipts")
    if not isinstance(receipts, list):
        return {"status": "failed", "failures": [*failures, "receipts are missing"]}
    receipt_by_id = {
        receipt.get("run_id"): receipt
        for receipt in receipts
        if isinstance(receipt, dict)
    }
    if len(receipt_by_id) != len(receipts):
        failures.append("receipt run ids must be unique objects")
    expected_ids = {slot["run_id"] for slot in slots}
    if set(receipt_by_id) != expected_ids:
        failures.append("receipt run ids do not match the fixed plan")

    replayed_baseline: list[dict[str, Any]] = []
    replayed_full: list[dict[str, Any]] = []
    scenarios_by_id = {
        scenario["id"]: scenario for scenario in manifest["scenarios"]
    }
    for slot in slots:
        receipt = receipt_by_id.get(slot["run_id"])
        if not isinstance(receipt, dict):
            continue
        scenario = scenarios_by_id[slot["scenario_id"]]
        skill_relative_path = (
            "skill/clean-code-ai-collaboration/SKILL.md"
            if slot["arm"] == "skill-v0.4.0"
            else None
        )
        expected_prompt = build_prompt(
            run_id=slot["run_id"],
            scenario=scenario,
            skill_relative_path=skill_relative_path,
            result_relative_path="subject-result.json",
        )
        if receipt.get("prompt") != expected_prompt:
            failures.append(f"{slot['run_id']}: prompt does not match the manifest")
        expected_dispatch = build_expected_dispatch(
            manifest=manifest,
            slot=slot,
            scenario=scenario,
            prompt=expected_prompt,
            skill_file_sha256=(
                file_sha256(SKILL_SOURCE / "SKILL.md")
                if slot["arm"] == "skill-v0.4.0"
                else None
            ),
            skill_tree_sha256=(
                tree_sha256(SKILL_SOURCE)
                if slot["arm"] == "skill-v0.4.0"
                else None
            ),
        )
        if receipt.get("dispatch") != expected_dispatch:
            failures.append(f"{slot['run_id']}: dispatch does not match provenance")
        subject_result = receipt.get("subject_result")
        if not isinstance(subject_result, dict):
            failures.append(f"{slot['run_id']}: subject result is missing")
            continue
        replayed = build_terminal_payload(
            manifest=manifest,
            slot=slot,
            scenario=scenario,
            dispatch=expected_dispatch,
            result=subject_result,
        )
        if receipt.get("terminal") != replayed:
            failures.append(f"{slot['run_id']}: terminal does not replay")
        if slot["arm"] == "baseline":
            replayed_baseline.append(replayed)
        else:
            replayed_full.append(replayed)

    if result.get("baseline_runs") != replayed_baseline:
        failures.append("published baseline runs do not match replayed receipts")
    if result.get("full_runs") != replayed_full:
        failures.append("published Full Runs do not match replayed receipts")
    if result.get("baseline_run_count") != len(replayed_baseline):
        failures.append("baseline run count does not match receipts")
    if result.get("baseline_conforming_count") != sum(
        terminal["terminal_state"] == "passed" for terminal in replayed_baseline
    ):
        failures.append("conforming baseline count does not match replayed receipts")
    if result.get("full_run_count") != len(replayed_full):
        failures.append("Full Run count does not match receipts")
    if result.get("passed_full_run_count") != sum(
        terminal["terminal_state"] == "passed" for terminal in replayed_full
    ):
        failures.append("passed Full Run count does not match replayed receipts")
    return {"status": "passed" if not failures else "failed", "failures": failures}


def build_public_result(
    runs_root: Path = DEFAULT_RUNS_ROOT,
    output: Path = DEFAULT_RESULT_PATH,
) -> dict[str, Any]:
    verification = verify_runs(runs_root)
    if verification["status"] != "passed":
        raise RuntimeError("cannot build public result before all Full Run slots pass")
    manifest = load_manifest()
    baseline_receipts = [
        build_public_receipt(manifest=manifest, slot=slot, runs_root=runs_root)
        for slot in build_baseline_slots(manifest)
    ]
    full_receipts = [
        build_public_receipt(manifest=manifest, slot=slot, runs_root=runs_root)
        for slot in build_slots(manifest)
    ]
    baseline_terminals = [receipt["terminal"] for receipt in baseline_receipts]
    full_terminals = [receipt["terminal"] for receipt in full_receipts]
    result = {
        "schema_version": "1.0",
        "benchmark_version": manifest["benchmark_version"],
        "skill_version": manifest["skill_version"],
        "status": "complete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "manifest_sha256": file_sha256(MANIFEST_PATH),
        "harness_sha256": file_sha256(Path(__file__)),
        "skill_tree_sha256": full_terminals[0]["skill_tree_sha256"],
        "claim_boundary": manifest["claim_boundary"],
        "baseline_run_count": len(baseline_terminals),
        "baseline_conforming_count": sum(
            terminal["terminal_state"] == "passed"
            for terminal in baseline_terminals
        ),
        "full_run_count": len(full_terminals),
        "passed_full_run_count": sum(
            terminal["terminal_state"] == "passed" for terminal in full_terminals
        ),
        "scenario_count": len(manifest["scenarios"]),
        "repetitions": manifest["repetitions"],
        "observations": [
            "All planned strategy-contract slots completed without silent substitution.",
            "Explicit Prompt values, Repository Policy fallback, default auto selection, mandatory gates, and selected blocked prerequisites were represented; reliable-test-oracle did not have a dedicated scenario.",
            "Baseline receipts were retained because their manifest, prompts, and no-Skill execution contract were unchanged by the final Skill-reference correction.",
            "This result tests decision-contract interpretation; it does not measure code quality, Token savings, or general effectiveness across repositories and clients.",
        ],
        "execution_attestation": {
            "controller": "Codex desktop collaboration.spawn_agent",
            "requested_model": manifest["model"],
            "requested_reasoning_effort": manifest["reasoning_effort"],
            "independent_runtime_identity_verified": False,
            "limitation": "The public receipt proves controller inputs and replayable outputs; it does not independently attest a fresh Context or the provider-side model identity.",
        },
        "receipts": [*baseline_receipts, *full_receipts],
        "baseline_runs": baseline_terminals,
        "full_runs": full_terminals,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.4.0 strategy Full Run harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    stage = subparsers.add_parser("stage")
    stage.add_argument("--run-id", required=True)
    collect = subparsers.add_parser("collect")
    collect.add_argument("--run-id", required=True)
    subparsers.add_parser("verify")
    result = subparsers.add_parser("build-result")
    result.add_argument("--output", type=Path, default=DEFAULT_RESULT_PATH)
    verify_result = subparsers.add_parser("verify-result")
    verify_result.add_argument("--input", type=Path, default=DEFAULT_RESULT_PATH)
    subparsers.add_parser("list")
    args = parser.parse_args()

    if args.command == "stage":
        payload = stage_run(args.run_id)
    elif args.command == "collect":
        payload = collect_run(args.run_id)
    elif args.command == "verify":
        payload = verify_runs()
    elif args.command == "build-result":
        payload = build_public_result(output=args.output)
    elif args.command == "verify-result":
        payload = verify_public_result(result_path=args.input)
    else:
        manifest = load_manifest()
        payload = {"slots": build_slots(manifest)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
