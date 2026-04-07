"""Quality evaluation and improvement loop for report generation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

IMPROVEMENT_LOG_DIR = Path("~/.config/feedship/improvement_logs").expanduser()


@dataclass
class QualityScore:
    overall: float  # 0.0-1.0
    coherence: float
    relevance: float
    depth: float
    structure: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ImprovementRecord:
    iteration: int
    date_range: str
    quality_score: QualityScore
    issues: list[str]
    prompt_adjustments: list[str]
    report_sample: str  # First 500 chars


async def evaluate_report(report_text: str) -> QualityScore:
    """Use LLM to evaluate report quality.

    Returns QualityScore with subscores for coherence, relevance, depth, structure.
    """
    from src.llm.chains import get_evaluate_chain

    chain = get_evaluate_chain()

    try:
        result = await chain.ainvoke({"report": report_text[:2000]})
        # Try to parse as JSON
        scores = json.loads(result)
        return QualityScore(
            overall=sum(scores.values()) / (4 * 100),
            coherence=scores.get("coherence", 0) / 100,
            relevance=scores.get("relevance", 0) / 100,
            depth=scores.get("depth", 0) / 100,
            structure=scores.get("structure", 0) / 100,
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning(
            "Quality evaluation failed to parse result: %s. Raw result: %s",
            e,
            result[:500] if result else "empty",
        )
        # Fallback: try simple 0-1 score parsing from existing chain
        try:
            score_val = float(result.strip())
            return QualityScore(
                overall=score_val,
                coherence=score_val,
                relevance=score_val,
                depth=score_val,
                structure=score_val,
            )
        except ValueError:
            logger.warning(
                "Quality evaluation completely failed, returning default 0.5"
            )
            return QualityScore(
                overall=0.5, coherence=0.5, relevance=0.5, depth=0.5, structure=0.5
            )


def suggest_improvements(quality_score: QualityScore) -> list[str]:
    """Generate prompt adjustment suggestions based on quality subscores."""
    suggestions = []
    if quality_score.depth < 0.6:
        suggestions.append("Increase prompt weight for analysis and insights")
    if quality_score.relevance < 0.6:
        suggestions.append("Adjust relevance filtering threshold")
    if quality_score.structure < 0.6:
        suggestions.append("Improve template structure directives")
    if quality_score.coherence < 0.6:
        suggestions.append("Strengthen transition guidance in layer summaries")
    return suggestions


def log_improvement(record: ImprovementRecord) -> None:
    """Log improvement record to file (file-based approach from decision checkpoint)."""
    IMPROVEMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = IMPROVEMENT_LOG_DIR / f"iteration_{record.iteration:04d}.json"
    with open(log_file, "w") as f:
        json.dump(
            {
                "iteration": record.iteration,
                "date_range": record.date_range,
                "quality_score": {
                    "overall": record.quality_score.overall,
                    "coherence": record.quality_score.coherence,
                    "relevance": record.quality_score.relevance,
                    "depth": record.quality_score.depth,
                    "structure": record.quality_score.structure,
                    "timestamp": record.quality_score.timestamp,
                },
                "issues": record.issues,
                "prompt_adjustments": record.prompt_adjustments,
                "report_sample": record.report_sample,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info("Logged improvement iteration %d to %s", record.iteration, log_file)


def run_improvement_loop(
    since: str,
    until: str,
    iterations: int = 100,
    auto_summarize: bool = True,
) -> dict[str, Any]:
    """Run N automated improvement iterations on report quality.

    Each iteration:
    1. Generate report
    2. Evaluate quality
    3. Log results
    4. Apply incremental improvements for next iteration

    Returns summary dict with all iteration scores.
    """
    import asyncio

    from src.application.report import cluster_articles_for_report, render_report

    results = []
    for i in range(1, iterations + 1):
        # Generate report
        data = cluster_articles_for_report(
            since=since, until=until, limit=100, auto_summarize=auto_summarize
        )
        report_text = render_report(data)

        # Evaluate quality
        score = asyncio.run(evaluate_report(report_text))

        # Generate issues and adjustments
        issues = [
            f"{dim}={getattr(score, dim):.2f}"
            for dim in ["coherence", "relevance", "depth", "structure"]
            if getattr(score, dim) < 0.6
        ]
        adjustments = suggest_improvements(score)

        # Log
        record = ImprovementRecord(
            iteration=i,
            date_range=f"{since}~{until}",
            quality_score=score,
            issues=issues,
            prompt_adjustments=adjustments,
            report_sample=report_text[:500],
        )
        log_improvement(record)
        results.append({"iteration": i, "score": score.overall, "issues": issues})

        if i % 10 == 0:
            logger.info("Completed %d/%d iterations", i, iterations)

    return {
        "iterations": iterations,
        "results": results,
        "avg_quality": sum(r["score"] for r in results) / len(results)
        if results
        else 0,
    }
