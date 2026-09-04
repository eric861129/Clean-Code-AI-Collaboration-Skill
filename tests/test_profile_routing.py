from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import unittest

from scripts.validate_profiles import load_registry, route_changed_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "profile-routing"
CATALOG_ROOT = FIXTURES / "catalog"


class ProfileRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = load_registry(CATALOG_ROOT)

    def route_case(self, case_name: str) -> dict:
        case_root = FIXTURES / case_name
        expected = json.loads(
            (case_root / "expected.json").read_text(encoding="utf-8")
        )

        actual = route_changed_files(
            case_root,
            self.profiles,
            expected["changed_files"],
            expected["explicit_profiles"],
        )

        self.assertEqual(expected["outcome"], actual["outcome"])
        self.assertEqual(expected["modules"], actual["modules"])
        return actual

    def test_csharp_and_python_use_their_nearest_project_manifest(self) -> None:
        csharp = self.route_case("csharp")
        python = self.route_case("python")

        self.assertEqual(["csharp"], csharp["modules"][0]["profiles"])
        self.assertEqual(["python"], python["modules"][0]["profiles"])

    def test_real_registry_selects_the_experimental_csharp_profile(self) -> None:
        result = route_changed_files(
            FIXTURES / "csharp",
            load_registry(ROOT),
            ["backend/App.cs"],
        )

        self.assertEqual("selected", result["outcome"])
        self.assertEqual(["csharp"], result["modules"][0]["profiles"])

    def test_real_registry_selects_only_the_experimental_python_profile(self) -> None:
        result = route_changed_files(
            FIXTURES / "python",
            load_registry(ROOT),
            ["automation/job.py"],
        )

        self.assertEqual("selected", result["outcome"])
        self.assertEqual(["python"], result["modules"][0]["profiles"])

    def test_typescript_react_selects_language_then_framework(self) -> None:
        result = self.route_case("typescript-react")

        self.assertEqual("selected", result["outcome"])
        self.assertEqual(
            ["typescript", "react"],
            result["modules"][0]["profiles"],
        )

    def test_javascript_react_does_not_invent_typescript(self) -> None:
        result = self.route_case("javascript-react")

        self.assertEqual(["react"], result["modules"][0]["profiles"])

    def test_planned_vue_is_reported_but_not_selected(self) -> None:
        result = self.route_case("typescript-vue-planned")

        self.assertEqual(["typescript"], result["modules"][0]["profiles"])
        self.assertEqual(["vue"], result["modules"][0]["unavailable_profiles"])

    def test_polyglot_repository_routes_each_changed_module_separately(self) -> None:
        result = self.route_case("polyglot")

        self.assertEqual(
            ["backend", "frontend", "automation"],
            [module["root"] for module in result["modules"]],
        )
        self.assertEqual(
            [["csharp"], ["typescript", "react"], ["python"]],
            [module["profiles"] for module in result["modules"]],
        )

    def test_root_solution_does_not_pollute_frontend_module(self) -> None:
        result = self.route_case("root-sln-frontend")

        self.assertNotIn("csharp", result["modules"][0]["profiles"])

    def test_core_only_is_valid_automatically_or_explicitly(self) -> None:
        automatic = self.route_case("core-only")
        explicit = self.route_case("explicit-core-only")

        self.assertEqual("core_only", automatic["outcome"])
        self.assertEqual("core_only", explicit["outcome"])

    def test_conflict_with_critical_behavior_is_blocked(self) -> None:
        result = self.route_case("conflict-blocked")

        self.assertEqual("blocked", result["outcome"])
        self.assertIn("profile-conflict", result["modules"][0]["reason_codes"])

    def test_profile_with_an_unavailable_requirement_is_not_selected(self) -> None:
        profiles = deepcopy(self.profiles)
        next(profile for profile in profiles if profile["id"] == "csharp")[
            "composition"
        ]["requires"] = ["vue"]
        case_root = FIXTURES / "csharp"

        result = route_changed_files(
            case_root,
            profiles,
            ["backend/App.cs"],
        )

        self.assertEqual("core_only", result["outcome"])
        self.assertEqual([], result["modules"][0]["profiles"])
        self.assertIn(
            "profile-requires-unavailable",
            result["modules"][0]["reason_codes"],
        )


if __name__ == "__main__":
    unittest.main()
