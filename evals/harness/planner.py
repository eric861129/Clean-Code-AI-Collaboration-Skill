from __future__ import annotations

import random

from evals.harness.models import BenchmarkManifest, RunSlot


def build_run_slots(manifest: BenchmarkManifest) -> tuple[RunSlot, ...]:
    unordered: list[tuple[str, str, str, str, int]] = []
    for scenario in manifest.scenarios:
        for arm_id in scenario["comparison_arms"]:
            for repetition in range(1, manifest.repetitions + 1):
                scenario_id = str(scenario["id"])
                unordered.append(
                    (
                        f"{scenario_id}--{arm_id}--r{repetition:02d}",
                        scenario_id,
                        str(scenario["language"]),
                        arm_id,
                        repetition,
                    )
                )

    run_ids = [run_id for run_id, *_ in unordered]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("duplicate run ID")
    random.Random(manifest.random_seed).shuffle(unordered)
    return tuple(
        RunSlot(
            run_id=run_id,
            scenario_id=scenario_id,
            language=language,
            arm_id=arm_id,
            repetition=repetition,
            order_index=order_index,
        )
        for order_index, (
            run_id,
            scenario_id,
            language,
            arm_id,
            repetition,
        ) in enumerate(unordered)
    )


def pilot_slots(slots: tuple[RunSlot, ...]) -> tuple[RunSlot, ...]:
    return tuple(slot for slot in slots if slot.repetition == 1)


def full_slots(slots: tuple[RunSlot, ...]) -> tuple[RunSlot, ...]:
    return tuple(slot for slot in slots if slot.repetition in {2, 3})
