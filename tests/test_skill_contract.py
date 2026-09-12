from pathlib import Path
import re
import unittest

from scripts.validate_profiles import load_registry, profile_is_available


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "clean-code-ai-collaboration"
SKILL_PATH = SKILL_ROOT / "SKILL.md"
CORE_REFERENCE_NAMES = {
    "code-readability.md",
    "testing-and-change-safety.md",
    "design-and-dependency-boundaries.md",
    "collaboration-and-estimation.md",
    "clean-code-for-agent-legibility.md",
    "repository-context-template.md",
    "review-output-contract.md",
    "profile-selection.md",
}


def profile_reference_names() -> set[str]:
    return {
        Path(profile["reference"]).name
        for profile in load_registry(REPOSITORY_ROOT)
        if profile_is_available(profile) and profile.get("reference")
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

        for reference_name in CORE_REFERENCE_NAMES:
            with self.subTest(reference_name=reference_name):
                self.assertIn(f"references/{reference_name}", content)

        runtime_index = (
            SKILL_ROOT / "references" / "profile-selection.md"
        ).read_text(encoding="utf-8")
        for reference_name in profile_reference_names():
            with self.subTest(profile_reference_name=reference_name):
                self.assertIn(f"]({reference_name})", runtime_index)

    def test_profile_selection_keeps_runtime_routing_contract(self) -> None:
        content = (
            SKILL_ROOT / "references" / "profile-selection.md"
        ).read_text(encoding="utf-8")
        required_headings = {
            "## Use This Reference When",
            "## Changed Module Discovery",
            "## Candidate Detection",
            "## Availability and Composition",
            "## Explicit Selection",
            "## Stage Evidence",
            "## Output Additions",
            "## Runtime Profile Index",
        }

        for heading in required_headings:
            with self.subTest(heading=heading):
                self.assertIn(heading, content)
        self.assertIn("<!-- runtime-profile-index:generated:start -->", content)
        self.assertIn("<!-- runtime-profile-index:generated:end -->", content)

    def test_all_references_exist_and_scaffold_placeholders_are_removed(self) -> None:
        references = SKILL_ROOT / "references"
        actual_names = {path.name for path in references.glob("*.md")}
        expected_names = CORE_REFERENCE_NAMES | profile_reference_names()

        self.assertEqual(expected_names, actual_names)
        for path in [SKILL_PATH, *references.glob("*.md")]:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("TODO", content)
                self.assertNotIn("WorkItems.Api", content)

    def test_entrypoint_stays_short(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        body = content.split("---", maxsplit=2)[-1]

        self.assertLessEqual(len(body.split()), 525)

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

    def test_full_audit_contract_leads_with_status_and_keeps_blind_spots(self) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )
        full_audit = content.split("## Full Audit Output Contract", maxsplit=1)[1]

        self.assertLess(
            full_audit.index("### Outcome and Status"),
            full_audit.index("### Repository Facts Used"),
        )
        self.assertIn("### Validation Blind Spots", full_audit)
        self.assertIn("### Human Decisions Required", full_audit)

    def test_standard_output_is_concise_and_full_audit_remains_traceable(
        self,
    ) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )
        standard, full_audit = content.split("## Full Audit Output Contract", maxsplit=1)

        self.assertIn("## Standard Output Contract", standard)
        self.assertIn("The first five are required", standard)
        for field in {
            "Outcome and Status",
            "Decision Basis",
            "Selected Approach",
            "Behavior, Diff, and Validation",
            "Stop or Human Decision",
        }:
            with self.subTest(standard_field=field):
                self.assertIn(field, standard)

        self.assertNotIn("`None; Sources checked: ...`", standard)
        self.assertNotIn("`Not investigated`", standard)
        for term in {
            "F1",
            "A1",
            "U1",
            "O1",
            "E1",
            "`None; Sources checked: ...`",
            "`Not investigated`",
            "Validation Blind Spots",
            "Human Decisions Required",
        }:
            with self.subTest(full_audit_term=term):
                self.assertIn(term, full_audit)

    def test_review_contract_distinguishes_all_empty_sections_from_not_investigated(
        self,
    ) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("For every output heading with no item", content)
        self.assertIn("`None; Sources checked: ...`", content)
        self.assertIn("`Not investigated`", content)
        self.assertIn("This rule applies to every output heading", content)

    def test_common_misjudgments_are_traceable_experiment_observations(self) -> None:
        names = {
            "code-readability.md",
            "testing-and-change-safety.md",
            "design-and-dependency-boundaries.md",
            "collaboration-and-estimation.md",
        }
        experiment_permalink = (
            r"https://github\.com/eric861129/AI-CleanCode-API-Demo/blob/"
            r"[0-9a-f]{40}/docs/evidence/"
        )

        for name in names:
            content = (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            common_misjudgments = content.split("## Common Misjudgments", maxsplit=1)[1]
            common_misjudgments = common_misjudgments.split("## Stop Conditions", maxsplit=1)[
                0
            ]
            observation_blocks = common_misjudgments.split("### Observation ID: ")[1:]

            with self.subTest(reference=name):
                self.assertNotIn("observed", common_misjudgments.lower())
                self.assertGreaterEqual(len(observation_blocks), 1)
                for block in observation_blocks:
                    self.assertIn("\n\nSource: [", block)
                    self.assertRegex(block, experiment_permalink)
                    self.assertIn("\n\nSupports: ", block)

    def test_entrypoint_defines_three_risk_paths_and_one_way_escalation(
        self,
    ) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")

        for path_name in {"Lightweight Path", "Standard Path", "Full Audit Path"}:
            with self.subTest(path_name=path_name):
                self.assertIn(path_name, content)

        self.assertIn("public contract", content)
        self.assertIn("external side effect", content)
        self.assertIn("critical unknown", content)
        self.assertIn("upgrade", content.lower())
        self.assertIn("must not downgrade", content.lower())

    def test_entrypoint_excludes_tasks_without_repository_tradeoffs(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        section = content.split("## Do Not Use", maxsplit=1)[1]
        section = section.split("## ", maxsplit=1)[0]

        for term in {
            "syntax",
            "conceptual explanation",
            "standalone example",
            "formatter",
            "fully covered by a more specialized Skill",
            "behavior",
            "boundary",
            "side-effect",
            "Clean Code trade-off",
        }:
            with self.subTest(term=term):
                self.assertIn(term.lower(), section.lower())

    def test_delivery_readiness_does_not_lower_risk_or_authority(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        section = content.split("## Delivery Readiness", maxsplit=1)[1]
        section = section.split("## ", maxsplit=1)[0]

        for term in {"Prototype", "Production-Ready", "Full Audit", "authorization"}:
            with self.subTest(term=term):
                self.assertIn(term, section)

    def test_testing_reference_routes_repository_native_gates(self) -> None:
        content = (
            SKILL_ROOT / "references" / "testing-and-change-safety.md"
        ).read_text(encoding="utf-8")
        gate_section = content.split("## Executable Gate Routing", maxsplit=1)[1]
        gate_section = gate_section.split("## ", maxsplit=1)[0]

        for term in {
            "Formatter",
            "Linter",
            "Static Analysis",
            "Build",
            "Unit",
            "Integration",
            "E2E",
            "Security",
            "Mutation",
            "blind spot",
            "authorization",
        }:
            with self.subTest(term=term):
                self.assertIn(term.lower(), gate_section.lower())

    def test_testing_reference_defines_user_selected_development_rhythm(self) -> None:
        content = (
            SKILL_ROOT / "references" / "testing-and-change-safety.md"
        ).read_text(encoding="utf-8")
        section = content.split("## User-Selected Development Rhythm", maxsplit=1)[1]
        section = section.split("## Executable Gate Routing", maxsplit=1)[0]

        for value in {
            "auto",
            "direct",
            "tdd",
            "tcr",
            "characterization-first",
        }:
            with self.subTest(development_rhythm=value):
                self.assertIn(f"`{value}`", section)

        self.assertIn("current User prompt", section)
        self.assertIn("Repository Policy", section)
        self.assertIn("must not silently substitute", section)
        self.assertIn("explicit version-control authorization", section)

    def test_development_rhythm_is_separate_from_validation_profile(self) -> None:
        content = (
            SKILL_ROOT / "references" / "testing-and-change-safety.md"
        ).read_text(encoding="utf-8")
        section = content.split("## User-Selected Development Rhythm", maxsplit=1)[1]
        section = section.split("## Executable Gate Routing", maxsplit=1)[0]

        self.assertIn("development_rhythm", section)
        self.assertIn("validation_profile", section)
        for value in {
            "focused",
            "repository",
            "acceptance-e2e",
            "mutation-assisted",
        }:
            with self.subTest(validation_profile=value):
                self.assertIn(f"`{value}`", section)

        self.assertIn("TDD and TCR control the development rhythm", section)
        self.assertIn("E2E and mutation testing control validation depth", section)

    def test_explicit_auto_keeps_the_user_prompt_as_request_source(self) -> None:
        testing_reference = (
            SKILL_ROOT / "references" / "testing-and-change-safety.md"
        ).read_text(encoding="utf-8")
        output_contract = (
            SKILL_ROOT / "references" / "review-output-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn("explicit `auto` is sourced from the current User prompt", testing_reference)
        self.assertIn("source identifies where the requested value came from", output_contract)
        self.assertIn("not how the effective value was inferred", output_contract)

    def test_output_contract_reports_requested_and_effective_strategy(self) -> None:
        content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Requested Development Rhythm", content)
        self.assertIn("Effective Development Rhythm", content)
        self.assertIn("Development Rhythm Source", content)
        self.assertIn("Requested Validation Profile", content)
        self.assertIn("Effective Validation Profile", content)
        self.assertIn("Validation Profile Source", content)
        self.assertIn("Feasibility or Escalation", content)

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
        public_plan = (
            REPOSITORY_ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-31-clean-code-ai-collaboration-v0.2.0.md"
        ).read_text(encoding="utf-8")

        self.assertIn("結構契約", readme)
        self.assertIn("Structural Contract", workflow)
        self.assertIn("cache-dependency-path: requirements-dev.txt", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn(
            "agentskills validate clean-code-ai-collaboration",
            workflow,
        )
        self.assertNotIn("skills-ref validate", workflow)
        self.assertNotIn("skills-ref validate", public_plan)
        self.assertNotIn("quick_validate.py", public_plan)
        self.assertGreaterEqual(
            public_plan.count("agentskills validate clean-code-ai-collaboration"),
            7,
        )

    def test_readme_documents_portability_evidence_and_limits(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        required = {
            ".agents\\skills",
            "Codex",
            "GitHub Copilot",
            "Claude Code",
            "Clean Code 如何改善 AI Coding",
            "CLEAN 五原則",
            "Benchmark",
            "不保證",
            "規劃",
            "實作",
            "Review",
            "貢獻",
        }

        for term in required:
            with self.subTest(term=term):
                self.assertIn(term, readme)

        for term in {
            "Lightweight",
            "Standard",
            "Full Audit",
            "Prototype",
            "Production-Ready",
            "allow_implicit_invocation: false",
            "明確指定 `$clean-code-ai-collaboration`",
            "Repository 既有",
        }:
            with self.subTest(v030_readme_term=term):
                self.assertIn(term, readme)

        self.assertNotIn(
            "自動偵測、implicit invocation 與重新啟動行為尚待實機驗證",
            readme,
        )

        ordered_sections = [
            "## 這個 Skill 解決什麼問題",
            "## Clean Code 如何改善 AI Coding",
            "## CLEAN 五原則",
            "## Skill、Repository Policy 與自動化 Gate 的分工",
            "## 如何選擇執行深度與交付成熟度",
            "## 安裝",
            "## 使用方式",
            "## Benchmark",
            "## 已知限制與不保證事項",
            "## Repository 結構",
            "## 貢獻評測情境",
            "## 來源、非官方聲明與授權",
        ]
        positions = [readme.index(section) for section in ordered_sections]

        self.assertEqual(positions, sorted(positions))
        usage_sections = ["### 規劃", "### 實作", "### Review"]
        for index, section in enumerate(usage_sections):
            start = readme.index(section)
            end_marker = (
                usage_sections[index + 1]
                if index + 1 < len(usage_sections)
                else "## Benchmark"
            )
            end = readme.index(end_marker, start + len(section))
            with self.subTest(usage_section=section):
                self.assertIn("$clean-code-ai-collaboration", readme[start:end])

        self.assertIn(
            '$skillSource = (Resolve-Path ".\\clean-code-ai-collaboration").Path',
            readme,
        )
        self.assertIn("cd Clean-Code-AI-Collaboration-Skill", readme)
        self.assertIn('$projectRoot = "C:\\path\\to\\your-project"', readme)
        self.assertIn('project_root="/path/to/your-project"', readme)
        self.assertIn('skill_source="$(pwd)/clean-code-ai-collaboration"', readme)
        self.assertIn(
            '$skillsRoot = Join-Path $projectRoot ".agents\\skills"',
            readme,
        )
        self.assertIn(
            '$skillsRoot = Join-Path $env:USERPROFILE ".agents\\skills"',
            readme,
        )
        self.assertIn("Copy-Item -LiteralPath $skillSource", readme)
        self.assertIn('cp -R "$skill_source" "$target"', readme)
        self.assertIn(
            "安裝完成後，建議先在任務中明確指定 `$clean-code-ai-collaboration`",
            readme,
        )
        self.assertIn("請先確認內容，不要直接覆寫", readme)
        self.assertIn("內容與格式", readme)
        self.assertIn("尚未完成實機驗證", readme)
        self.assertIn("預先宣告的四種 Repository 情境", readme)
        self.assertIn("| 通用 Prompt 基準 | 12 | 2 | 6／12 | 7／12 | 1／12 |", readme)
        self.assertIn("| v0.2.0 Skill | 12 | 0 | 9／12 | 12／12 | 12／12 |", readme)
        self.assertIn("不保證一定節省 Token、時間或費用", readme)
        self.assertIn(
            "不是 Robert C. Martin、原出版商、OpenAI、GitHub 或 Anthropic 的官方作品",
            readme,
        )
        self.assertIn("[LICENSE](LICENSE)", readme)

    def test_validation_workflow_uses_the_same_full_gate_on_both_platforms(
        self,
    ) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "validate.yml"
        ).read_text(encoding="utf-8")

        for term in {
            "fail-fast: false",
            "os: [ubuntu-latest, windows-latest]",
            "runs-on: ${{ matrix.os }}",
            "fetch-depth: 0",
            "python -m unittest discover -s tests -v",
            "python -m compileall -q evals/harness evals/v040_strategy_full_run.py scripts",
        }:
            with self.subTest(term=term):
                self.assertIn(term, workflow)

    def test_ui_prompt_explicitly_names_the_skill(self) -> None:
        content = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("$clean-code-ai-collaboration", content)

    def test_codex_adapter_exposes_open_core_work_types_and_guardrails(self) -> None:
        content = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        required_terms = {
            'display_name: "Clean Code AI Collaboration"',
            'short_description: "Use repository-aware Clean Code judgment for AI coding"',
            "$clean-code-ai-collaboration",
            "plan",
            "implement",
            "review",
            "repository facts",
            "behavior gates",
            "keep the Diff local",
            "report validation blind spots",
            "stop at authorization boundaries",
            "allow_implicit_invocation: false",
        }

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_current_metadata_and_clean_lenses_are_discoverable(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")
        frontmatter = re.match(
            r"---\n(?P<frontmatter>.*?)\n---\n",
            content,
            re.DOTALL,
        ).group("frontmatter")
        required = {
            "license: MIT",
            "compatibility:",
            'version: "0.5.2"',
            "C — Context-Aware Code",
            "L — Localized Change",
            "E — Explicit Intent and Boundaries",
            "A — Auditable by Evidence",
            "N — Non-Surprising Behavior",
            "C — Context-Aware Code（情境感知）",
            "L — Localized Change（局部變更）",
            "E — Explicit Intent and Boundaries（意圖明確）",
            "A — Auditable by Evidence（實據可審）",
            "N — Non-Surprising Behavior（符合預期）",
            "clean-code-for-agent-legibility.md",
        }
        for term in required:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_readme_installation_matches_released_source_version(self) -> None:
        skill = SKILL_PATH.read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        source_version = re.search(
            r'^  version: "([^"]+)"$', skill, re.MULTILINE
        ).group(1)

        self.assertEqual("0.5.2", source_version)
        self.assertIn(f"固定安裝 Tag 為 `v{source_version}`", readme)
        self.assertIn(f"git checkout v{source_version}", readme)
        self.assertIn(f'version: "{source_version}"', readme)
        self.assertNotIn(f"`v{source_version}` Candidate", readme)
        self.assertNotIn("git checkout v0.5.1", readme)

    def test_v040_readme_documents_strategy_configuration(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        for term in {
            "v0.4.0",
            "development_rhythm",
            "validation_profile",
            "characterization-first",
            "acceptance-e2e",
            "mutation-assisted",
            "當次 User Prompt",
            "Repository 根目錄的 `AGENTS.md`",
            "越接近 CWD 的指示會排在後面",
            "不會因為後來修改了 `backend` 內的檔案，就自動補載入",
            "https://learn.chatgpt.com/docs/agent-configuration/agents-md",
            "development_rhythm: tdd",
            "development_rhythm: tcr",
            "`development_rhythm: tcr` 本身不等於 Commit／Revert 授權",
            "明確指定的策略無法執行時",
            "三十秒快速開始",
            "如果沒有填寫兩個設定",
            "常見任務可以怎麼搭配",
            "一定要選 TDD 或 TCR 嗎？",
            "目前沒有另外執行設定檔解析器",
            "v0.4.0 Strategy Decision-Conformance Full Run",
            "v0.3.0 Cross-language Full Run",
            "evals/manifests/v0.4.0-strategy-full-run.json",
            "evals/v040_strategy_full_run.py",
            "python3 -m evals.v040_strategy_full_run verify-result",
            "公開收據無法獨立證明 Subject 是否屬於全新 Context",
        }:
            with self.subTest(v040_readme_term=term):
                self.assertIn(term, readme)

    def test_v040_codex_adapter_preserves_explicit_strategy_preferences(self) -> None:
        adapter = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("development_rhythm", adapter)
        self.assertIn("validation_profile", adapter)
        self.assertIn("Never silently substitute", adapter)

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
