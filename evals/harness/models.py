from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunSlot:
    run_id: str
    scenario_id: str
    language: str
    arm_id: str
    repetition: int
    order_index: int


@dataclass(frozen=True)
class BenchmarkManifest:
    schema_version: str
    benchmark_version: str
    fixture_url: str
    fixture_tag: str
    fixture_commit: str
    skill_tag: str
    skill_commit: str
    model: str
    reasoning_effort: str
    client: str
    subject_timeout_seconds: int
    fixture_timeout_seconds: int
    oracle_timeout_seconds: int
    repetitions: int
    random_seed: int
    scenarios: tuple[dict[str, object], ...]
    arms: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    elapsed_seconds: float
    timed_out: bool
    classification: str
    attempt: int


@dataclass(frozen=True)
class Workspace:
    root: Path
    artifact_dir: Path
    baseline_commit: str


@dataclass(frozen=True)
class HarnessPaths:
    repository_root: Path
    runs_root: Path
    fixture_clone: Path
    skill_repository: Path


@dataclass(frozen=True)
class SubjectObservation:
    run_id: str
    command: CommandResult
    prompt_sha256: str
    raw_jsonl_path: Path
    last_message_path: Path


@dataclass(frozen=True)
class Rename:
    source: str
    destination: str


@dataclass(frozen=True)
class DiffEvidence:
    diff: str
    diff_sha256: str
    changed_paths: tuple[str, ...]
    renamed_paths: tuple[Rename, ...]
    outside_boundary: tuple[str, ...]


@dataclass(frozen=True)
class OracleEvidence:
    public: tuple[CommandResult, ...]
    preservation: tuple[CommandResult, ...]
    acceptance: tuple[CommandResult, ...]
    automatic_failure_reasons: tuple[str, ...]
