from dataclasses import dataclass


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
