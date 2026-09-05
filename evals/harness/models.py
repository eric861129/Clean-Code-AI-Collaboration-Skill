from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArmDefinition(Mapping[str, object]):
    """Manifest 宣告的一個可重用評測 Arm。"""

    id: str
    instruction: str
    skill: str | None = None
    version: str | None = None
    required_skill_inspection_paths: tuple[str, ...] = ()
    inspection_policy: str | None = None
    allowed_skill_inspection_paths: tuple[str, ...] = ()
    applied_profiles: tuple[str, ...] = ()

    def __getitem__(self, key: str) -> object:
        values: dict[str, object] = {
            "id": self.id,
            "instruction": self.instruction,
        }
        if self.skill is not None:
            values["skill"] = self.skill
        if self.version is not None:
            values["version"] = self.version
        if self.required_skill_inspection_paths or self.inspection_policy is not None:
            values["required_skill_inspection_paths"] = list(
                self.required_skill_inspection_paths
            )
        if self.inspection_policy is not None:
            values["inspection_policy"] = self.inspection_policy
            values["allowed_skill_inspection_paths"] = list(
                self.allowed_skill_inspection_paths
            )
            values["applied_profiles"] = list(self.applied_profiles)
        return values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys())

    def __len__(self) -> int:
        return len(self._keys())

    def _keys(self) -> tuple[str, ...]:
        keys = ["id", "instruction"]
        if self.skill is not None:
            keys.append("skill")
        if self.version is not None:
            keys.append("version")
        if self.required_skill_inspection_paths or self.inspection_policy is not None:
            keys.append("required_skill_inspection_paths")
        if self.inspection_policy is not None:
            keys.extend(("inspection_policy", "allowed_skill_inspection_paths", "applied_profiles"))
        return tuple(keys)


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
    subject_executor: dict[str, object]
    subject_timeout_seconds: int
    fixture_timeout_seconds: int
    oracle_timeout_seconds: int
    repetitions: int
    random_seed: int
    freeze_policy: str
    scenarios: tuple[dict[str, object], ...]
    arms: tuple[ArmDefinition, ...]


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
class SubjectDispatch:
    """Desktop Subject 的不可變派發契約。"""

    dispatch_id: str
    logical_run_id: str
    physical_run_id: str
    scenario_id: str
    arm_id: str
    generation: int
    attempt: int
    workspace: Workspace
    prompt_path: Path
    report_template_path: Path
    report_path: Path
    report_relative_path: str
    dispatch_path: Path
    prompt_sha256: str
    contract_sha256: str
    scenario_contract_sha256: str
    required_skill_inspection_paths: tuple[str, ...]
    dispatch_sha256: str
    schema_version: str = "desktop-subject-dispatch/v4"
    inspection_policy: str | None = None
    allowed_skill_inspection_paths: tuple[str, ...] = ()
    applied_profiles: tuple[str, ...] = ()
    skill_root: str | None = None


@dataclass(frozen=True)
class HarnessPaths:
    """單一 Benchmark Campaign 的所有受管私有路徑。"""

    repository_root: Path
    runs_root: Path
    fixture_clone: Path
    skill_repository: Path
    manifest_path: Path | None = None

    @property
    def workspaces_root(self) -> Path:
        return self.runs_root / "workspaces"

    @property
    def artifacts_root(self) -> Path:
        return self.runs_root / "artifacts"

    @property
    def run_documents_root(self) -> Path:
        return self.runs_root / "run-documents"

    @property
    def preflights_root(self) -> Path:
        return self.runs_root / "preflights"

    @property
    def contract_freezes_root(self) -> Path:
        return self.runs_root / "contract-freezes"

    @property
    def campaign_state_path(self) -> Path:
        return self.runs_root / "campaign-state.json"

    @property
    def invalidations_root(self) -> Path:
        return self.runs_root / "invalidations"

    @property
    def timeout_adjudications_root(self) -> Path:
        return self.runs_root / "timeout-adjudications"

    @property
    def desktop_dispatch_root(self) -> Path:
        return self.runs_root / "desktop-dispatches"

    @property
    def controller_dispatch_root(self) -> Path:
        return self.runs_root / "desktop-controller-dispatches"

    @property
    def attempt_receipts_root(self) -> Path:
        return self.runs_root / "desktop-attempt-receipts"

    @property
    def review_key_path(self) -> Path:
        return self.runs_root / "review-key.json"

    @property
    def review_packets_root(self) -> Path:
        return self.runs_root / "review-packets"

    @property
    def reviews_root(self) -> Path:
        return self.runs_root / "reviews"


@dataclass(frozen=True)
class SubjectObservation:
    run_id: str
    command: CommandResult | None
    prompt_sha256: str
    raw_jsonl_path: Path | None
    last_message_path: Path | None
    executor: str = "codex-cli"
    completion_outcome: str = "completed"
    elapsed_seconds: float | None = None
    dispatch_path: Path | None = None
    dispatch_sha256: str = "not_available"
    report_path: Path | None = None
    report_sha256: str = "not_available"
    subject_thread_id: str | None = None
    telemetry: object = "not_available"


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
