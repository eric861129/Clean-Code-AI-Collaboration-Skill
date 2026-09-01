from __future__ import annotations

import random

from evals.harness.models import BenchmarkManifest, RunSlot


def build_run_slots(manifest: BenchmarkManifest) -> tuple[RunSlot, ...]:
    unordered: list[tuple[str, str, str, str, int]] = []
    for scenario in manifest.scenarios:
        for arm in manifest.arms:
            for repetition in range(1, manifest.repetitions + 1):
                scenario_id = str(scenario["id"])
                arm_id = str(arm["id"])
                unordered.append(
                    (
                        f"{scenario_id}--{arm_id}--r{repetition:02d}",
                        scenario_id,
                        str(scenario["language"]),
                        arm_id,
                        repetition,
                    )
                )

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
