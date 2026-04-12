"""AI report generation - entity clustering pipeline.

Exports:
    SignalFilter: Layer 0 - exact dedup + quality/feed_weight gate.
    NERExtractor: Layer 1 - batch LLM NER extraction + entity normalization.
    TLDRGenerator: Layer 2 - top-10 TLDR summary via single LLM call.
    ReportData: Dataclass models for the report pipeline.
"""

from .filter import SignalFilter
from .models import (
    EntityTag,
    EntityTopic,
    ReportArticle,
    ReportData,
)
from .ner import NERExtractor
from .tldr import TLDRGenerator

__all__ = [
    "ReportArticle",
    "EntityTag",
    "EntityTopic",
    "ReportData",
    "SignalFilter",
    "NERExtractor",
    "TLDRGenerator",
]
