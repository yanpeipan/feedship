"""Entity-based report generation pipeline.

Modules:
- filter: SignalFilter (Layer 0)
- ner: NERExtractor (Layer 1)
- entity_cluster: EntityClusterer (Layer 2)
- tldr: TLDRGenerator (Layer 3)
- render: render_entity_report (Layer 4)

For the CLI entry point, see src/application/report.py.
"""

from src.application.report.entity_cluster import EntityClusterer
from src.application.report.filter import SignalFilter
from src.application.report.models import (
    ArticleEnriched,
    EntityTag,
    EntityTopic,
    ReportData,
)
from src.application.report.ner import NERExtractor
from src.application.report.render import (
    dim_zh,
    group_by_dimension,
    group_by_layer,
    render_entity_inline,
    render_entity_report,
)
from src.application.report.tldr import TLDRGenerator

__all__ = [
    "SignalFilter",
    "NERExtractor",
    "EntityClusterer",
    "TLDRGenerator",
    "render_entity_report",
    "render_entity_inline",
    "group_by_layer",
    "group_by_dimension",
    "dim_zh",
    "ArticleEnriched",
    "EntityTag",
    "EntityTopic",
    "ReportData",
]
