from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "clean-code-ai-collaboration"
SKILL_PATH = SKILL_ROOT / "SKILL.md"
REFERENCE_NAMES = {
    "code-readability.md",
    "testing-and-change-safety.md",
    "design-and-dependency-boundaries.md",
    "collaboration-and-estimation.md",
    "clean-code-for-agent-legibility.md",
    "repository-context-template.md",
    "review-output-contract.md",
}


class SkillContractTests(unittest.TestCase):
    def test_skill_frontmatter_is_discoverable(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        match = re.match(r"---\n(?P<frontmatter>.*?)\n---\n", content, re.DOTALL)

        self.assertIsNotNone(match)
        frontmatter = match.group("frontmatter")
        self.assertIn("name: clean-code-ai-collaboration", frontmatter)
        self.assertRegex(frontmatter, r"description:\s+Use when ")

    def test_skill_entrypoint_routes_to_every_reference(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")

        for reference_name in REFERENCE_NAMES:
            with self.subTest(reference_name=reference_name):
                self.assertIn(f"references/{reference_name}", content)

    def test_all_references_exist_and_scaffold_placeholders_are_removed(self) -> None:
        references = SKILL_ROOT / "references"
        actual_names = {path.name for path in references.glob("*.md")}

        self.assertEqual(REFERENCE_NAMES, actual_names)
        for path in [SKILL_PATH, *references.glob("*.md")]:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("TODO", content)
                self.assertNotIn("WorkItems.Api", content)

    def test_entrypoint_stays_short(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        body = content.split("---", maxsplit=2)[-1]

        self.assertLessEqual(len(body.split()), 500)

    def test_review_contract_keeps_options_context_and_human_decisions(self) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )
        required_fields = {
            "Repository Facts Used",
            "Assumptions",
            "Unknowns",
            "Options Considered",
            "When Other Options Fit Better",
            "Behavior That Must Not Change",
            "Validation Plan",
            "Stop or Escalation Conditions",
            "Human Decisions Required",
        }

        for field in required_fields:
            with self.subTest(field=field):
                self.assertIn(field, content)

    def test_decision_references_define_tradeoffs_and_stop_conditions(self) -> None:
        names = {
            "code-readability.md",
            "testing-and-change-safety.md",
            "design-and-dependency-boundaries.md",
            "collaboration-and-estimation.md",
        }
        for name in names:
            content = (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            with self.subTest(reference=name):
                self.assertIn("## Use This Reference When", content)
                self.assertIn("## Selection Rules", content)
                self.assertIn("## When Another Option Fits Better", content)
                self.assertIn("## Common Misjudgments", content)
                self.assertIn("## Stop Conditions", content)

    def test_review_contract_leads_with_status_and_keeps_blind_spots(self) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertLess(
            content.index("## Outcome and Status"),
            content.index("## Repository Facts Used"),
        )
        self.assertIn("## Validation Blind Spots", content)
        self.assertIn("## Human Decisions Required", content)

    def test_entrypoint_has_lightweight_and_full_paths(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("Lightweight Path", content)
        self.assertIn("Full Path", content)
        self.assertIn("public contract", content)
        self.assertIn("side effect", content)

    def test_authorization_gate_is_always_loaded(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        required_terms = {
            "Authorization Gate",
            "dependency",
            "production data",
            "external side effect",
            "deployment",
            "destructive",
            "evidence does not grant authority",
        }

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_full_review_contract_is_traceable(self) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )
        required_terms = {
            "F1",
            "A1",
            "U1",
            "O1",
            "E1",
            "Actual Diff Boundary and Deviations",
            "Sources checked",
            "exit code",
            "blind spot",
        }

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_repository_calls_tests_structural_contract_checks(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("結構契約", readme)
        self.assertIn("Structural Contract", workflow)

    def test_ui_prompt_explicitly_names_the_skill(self) -> None:
        content = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("$clean-code-ai-collaboration", content)

    def test_v020_metadata_and_clean_lenses_are_discoverable(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        frontmatter = re.match(
            r"---\n(?P<frontmatter>.*?)\n---\n",
            content,
            re.DOTALL,
        ).group("frontmatter")
        required = {
            "license: MIT",
            "compatibility:",
            'version: "0.2.0"',
            "C — Context-Aware Code",
            "L — Localized Change",
            "E — Explicit Intent and Boundaries",
            "A — Auditable by Evidence",
            "N — Non-Surprising Behavior",
            "clean-code-for-agent-legibility.md",
        }
        for term in required:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_skill_core_stays_platform_neutral(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        frontmatter = re.match(
            r"---\n(?P<frontmatter>.*?)\n---\n",
            content,
            re.DOTALL,
        ).group("frontmatter")

        self.assertIn(
            "compatibility: Agent Skills-compatible coding agents.",
            frontmatter,
        )
        self.assertNotIn("Codex", content)


if __name__ == "__main__":
    unittest.main()
