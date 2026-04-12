"""LLM module — core client and quality evaluation."""

from src.llm.core import (
    LLMConfig,
    _get_llm_wrapper,
)
from src.llm.evaluator import (
    ImprovementRecord,
    QualityScore,
    evaluate_report,
    log_improvement,
    suggest_improvements,
)

__all__ = [
    # core
    "LLMConfig",
    "_get_llm_wrapper",
    # evaluator
    "QualityScore",
    "ImprovementRecord",
    "evaluate_report",
    "suggest_improvements",
    "log_improvement",
]
