"""Test improvement module.

Generates ranked, actionable improvement recommendations based on the
combined output of the analyzer and validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shadow_architect.core.analyzer import StrategyAnalysis
from shadow_architect.core.models import Recommendation, Severity
from shadow_architect.core.validator import ValidationResult


_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass
class ImprovementPlan:
    """A prioritised list of recommendations to improve the test strategy."""

    recommendations: list[Recommendation] = field(default_factory=list)
    quick_wins: list[Recommendation] = field(default_factory=list)
    long_term: list[Recommendation] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(
            1 for r in self.recommendations if r.priority == Severity.CRITICAL
        )

    @property
    def high_count(self) -> int:
        return sum(1 for r in self.recommendations if r.priority == Severity.HIGH)


class TestImprover:
    """Merges findings from analysis and validation into a prioritised improvement plan.

    Usage::

        improver = TestImprover()
        plan = improver.build_plan(analysis, validation_result)
        for rec in plan.recommendations:
            print(rec)
    """

    def build_plan(
        self, analysis: StrategyAnalysis, validation: ValidationResult
    ) -> ImprovementPlan:
        """Produce a ranked :class:`ImprovementPlan`."""
        # Collect recommendations from validation (already mapped from findings)
        recs: list[Recommendation] = list(validation.recommendations)

        # Add Azure-specific recommendations
        recs += self._azure_recommendations(analysis)

        # Deduplicate by id
        seen: set[str] = set()
        unique_recs: list[Recommendation] = []
        for rec in recs:
            if rec.id not in seen:
                seen.add(rec.id)
                unique_recs.append(rec)

        # Sort by severity, then by effort (low effort first within same severity)
        effort_order = {"low": 0, "medium": 1, "high": 2}
        unique_recs.sort(
            key=lambda r: (
                _SEVERITY_ORDER.get(r.priority, 99),
                effort_order.get(r.effort, 99),
            )
        )

        quick_wins = [r for r in unique_recs if r.effort == "low"]
        long_term = [r for r in unique_recs if r.effort == "high"]

        return ImprovementPlan(
            recommendations=unique_recs,
            quick_wins=quick_wins,
            long_term=long_term,
        )

    # ------------------------------------------------------------------
    def _azure_recommendations(
        self, analysis: StrategyAnalysis
    ) -> list[Recommendation]:
        """Generate Azure-specific recommendations."""
        recs: list[Recommendation] = []
        product_lower = (
            analysis.suite.product + " " + analysis.suite.use_case
        ).lower()

        if "azure" not in product_lower and analysis.test_count > 0:
            recs.append(
                Recommendation(
                    id="rec-azure-monitor",
                    title="Integrate test results with Azure Monitor",
                    description=(
                        "Push test metrics and results to Azure Monitor / Application "
                        "Insights so trends can be tracked over time."
                    ),
                    priority=Severity.INFO,
                    category="observability",
                    effort="medium",
                    references=[
                        "https://learn.microsoft.com/en-us/azure/azure-monitor/overview"
                    ],
                )
            )

        recs.append(
            Recommendation(
                id="rec-azure-devops-pipeline",
                title="Run tests in Azure DevOps CI/CD pipeline",
                description=(
                    "Configure an Azure Pipelines YAML pipeline to run the test suite "
                    "on every pull request and publish test results to the Azure DevOps "
                    "Test Plans dashboard."
                ),
                priority=Severity.MEDIUM,
                category="ci_cd",
                effort="medium",
                references=[
                    "https://learn.microsoft.com/en-us/azure/devops/pipelines/ecosystems/python"
                ],
            )
        )

        if any(
            kw in product_lower for kw in ("ai", "ml", "model", "llm", "gpt")
        ):
            recs.append(
                Recommendation(
                    id="rec-azure-ai-eval",
                    title="Use Azure AI Evaluation SDK for model testing",
                    description=(
                        "Leverage the Azure AI Evaluation SDK to measure groundedness, "
                        "coherence, fluency, and safety of AI-generated responses."
                    ),
                    priority=Severity.HIGH,
                    category="ai_quality",
                    effort="medium",
                    references=[
                        "https://learn.microsoft.com/en-us/azure/ai-studio/how-to/evaluate-generative-ai-app"
                    ],
                )
            )
            recs.append(
                Recommendation(
                    id="rec-responsible-ai",
                    title="Apply Microsoft Responsible AI guidelines",
                    description=(
                        "Incorporate fairness, reliability, privacy, security, and "
                        "inclusiveness evaluations as part of the test strategy."
                    ),
                    priority=Severity.HIGH,
                    category="responsible_ai",
                    effort="high",
                    references=[
                        "https://www.microsoft.com/en-us/ai/responsible-ai"
                    ],
                )
            )

        return recs
