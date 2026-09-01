import json
from pathlib import Path
import unittest

from evals.harness.manifest import load_manifest, validate_manifest
from evals.harness.planner import build_run_slots, full_slots, pilot_slots


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "evals" / "manifests" / "v0.3.0-cross-language.json"


class CrossLanguageHarnessTests(unittest.TestCase):
    def test_manifest_builds_exactly_36_unique_slots(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slots = build_run_slots(manifest)

        self.assertEqual(36, len(slots))
        self.assertEqual(36, len({slot.run_id for slot in slots}))
        self.assertEqual(12, len(pilot_slots(slots)))
        self.assertEqual(24, len(full_slots(slots)))
        self.assertEqual(set(range(36)), {slot.order_index for slot in slots})

    def test_planner_order_is_reproducible_and_partitions_repetitions(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        first = build_run_slots(manifest)
        second = build_run_slots(manifest)

        self.assertEqual(first, second)
        self.assertEqual({1}, {slot.repetition for slot in pilot_slots(first)})
        self.assertEqual({2, 3}, {slot.repetition for slot in full_slots(first)})

    def test_manifest_rejects_unknown_arm_and_missing_fixture_sha(self) -> None:
        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        raw["arms"][0]["id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown arm"):
            validate_manifest(raw)

        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        raw["fixture_repository"]["commit"] = ""
        with self.assertRaisesRegex(ValueError, "40-character fixture commit"):
            validate_manifest(raw)


if __name__ == "__main__":
    unittest.main()
