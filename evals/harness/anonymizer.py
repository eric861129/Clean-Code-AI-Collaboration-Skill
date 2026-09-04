from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from evals.harness.models import BenchmarkManifest

RUBRIC_IDS = (
    "context-and-locality",
    "behavior-and-validation",
    "decision-and-escalation",
)


def build_review_packet(
    run_document: dict[str, object],
    candidate_id: str,
    manifest: BenchmarkManifest | None = None,
) -> dict[str, object]:
    packet = {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "task": run_document.get("task", ""),
        "must_preserve": run_document.get("must_preserve", []),
        "diff": run_document.get("diff", ""),
        "oracle_results": run_document.get("oracle_results", []),
        "automatic_failure_reasons": run_document.get(
            "automatic_failure_reasons", []
        ),
        "blind_spots": run_document.get("blind_spots", []),
        "rubrics": {
            rubric_id: {"score": None, "reason": ""} for rubric_id in RUBRIC_IDS
        },
    }
    sensitive_tokens = {
        str(run_document.get("run_id", "")),
        "skill-v0.3.0",
        "generic-clean-code",
        "clean-code-ai-collaboration",
        "codex-desktop-collaboration",
    }
    if manifest is not None:
        scenario_id = str(run_document.get("scenario_id", ""))
        try:
            scenario = next(
                item for item in manifest.scenarios if item["id"] == scenario_id
            )
        except StopIteration as error:
            raise ValueError(f"unknown review scenario: {scenario_id}") from error
        packet.update(
            {
                "language": scenario["language"],
                "profile_under_test": scenario["profile_under_test"],
                "scenario_type": scenario["scenario_type"],
                "incremental_criteria": [
                    {"criterion": criterion, "score": None, "reason": ""}
                    for criterion in scenario["incremental_criteria"]
                ],
            }
        )
        sensitive_tokens.update(arm.id for arm in manifest.arms)
        sensitive_tokens.update(
            arm.skill for arm in manifest.arms if arm.skill is not None
        )
    redacted = _redact_for_review(packet, sensitive_tokens)
    if not isinstance(redacted, dict):  # pragma: no cover - packet is a dictionary
        raise TypeError("review packet must remain a dictionary")
    return redacted


def write_review_packet(
    run_document: dict[str, object],
    runs_root: Path,
    manifest: BenchmarkManifest | None = None,
) -> Path:
    mapping_path = runs_root / "review-key.json"
    mapping = _load_mapping(mapping_path)
    run_id = str(run_document["run_id"])
    evidence_id = str(run_document.get("evidence_id", run_id))
    candidate_id = _candidate_for_run(mapping, evidence_id)
    if candidate_id is None:
        candidate_id = f"candidate-{secrets.token_hex(4)}"
        mapping["candidates"][candidate_id] = {
            "run_id": run_id,
            "evidence_id": evidence_id,
            "arm_id": run_document.get("arm_id", ""),
        }
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_path.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    packet_dir = runs_root / "review-packets"
    packet_dir.mkdir(parents=True, exist_ok=True)
    packet_path = packet_dir / f"{candidate_id}.json"
    serialized = json.dumps(
        build_review_packet(run_document, candidate_id, manifest),
        ensure_ascii=False,
        indent=2,
    )
    if packet_path.is_file():
        if packet_path.read_text(encoding="utf-8") != serialized:
            raise FileExistsError(
                f"refusing to overwrite changed review packet: {packet_path}"
            )
        return packet_path
    packet_path.write_text(serialized, encoding="utf-8")
    return packet_path


def _load_mapping(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    if not path.is_file():
        return {"candidates": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("candidates"), dict):
        raise ValueError("invalid private review mapping")
    return value


def _candidate_for_run(
    mapping: dict[str, dict[str, dict[str, str]]], evidence_id: str
) -> str | None:
    return next(
        (
            candidate_id
            for candidate_id, identity in mapping["candidates"].items()
            if identity.get("evidence_id", identity.get("run_id")) == evidence_id
        ),
        None,
    )


def _redact_for_review(value: object, sensitive_tokens: set[str]) -> object:
    if isinstance(value, dict):
        return {
            str(key): _redact_for_review(item, sensitive_tokens)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_for_review(item, sensitive_tokens) for item in value]
    if not isinstance(value, str):
        return value

    redacted = value
    for sensitive in sorted(sensitive_tokens, key=len, reverse=True):
        if sensitive:
            redacted = re.sub(
                rf"(?<![A-Za-z0-9]){re.escape(sensitive)}(?![A-Za-z0-9])",
                "[redacted]",
                redacted,
                flags=re.IGNORECASE,
            )
    redacted = re.sub(
        r"(?:[A-Za-z]:[/\\]|/)[^\s\"']*?[.]benchmark-runs"
        r"(?:[/\\][^\s\"']*)?",
        "[private-run-path]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"(?<![A-Za-z0-9_.-])(?:[.]{1,2}[/\\])?[.]benchmark-runs"
        r"(?:[/\\][^\s\"']*)?",
        "[private-run-path]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"(?:[A-Za-z]:[/\\](?:Users|Documents and Settings)[/\\]"
        r"[^/\\\r\n\"']+|/(?:Users|home)/[^/\\\r\n\"']+)"
        r"(?:[/\\][^\s\"']*)?",
        "[private-path]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"(?:[A-Za-z]:[/\\][^\s\"']+|/(?:Users|home|tmp|var|private|workspace)(?:/[^\s\"']*)?)",
        "[private-path]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"desktop-dispatch-[A-Za-z0-9_.-]+",
        "[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"run-[0-9a-f]{16}",
        "[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"\bthread[-_][A-Za-z0-9_-]+\b",
        "[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"thread(?:_id|[- ]id)?[=:][^\s\"']+",
        "thread_id=[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
