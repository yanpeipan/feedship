"""Layer 4: ReportTemplate — Jinja2 template environment encapsulation."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from .models import ReportData


class ReportTemplate:
    """Encapsulates Jinja2 template environment for report rendering."""

    def __init__(self, template_dirs: list[Path] | None = None):
        """Initialize with optional custom template directories."""
        self._custom_dirs = template_dirs

    @property
    def _template_dirs(self) -> list[Path]:
        """Return list of template directories to search."""
        if self._custom_dirs is not None:
            return self._custom_dirs
        return [
            Path.home() / ".local" / "share" / "feedship" / "templates",
            Path(__file__).parent.parent.parent.parent / "templates",
        ]

    @cached_property
    def environment(self) -> Environment:
        """The underlying Jinja2 Environment (lazy init, cached)."""
        return Environment(
            loader=FileSystemLoader([str(d) for d in self._template_dirs]),
            autoescape=select_autoescape(),
        )

    def get_template(self, template_name: str) -> Template:
        """Get template by name from the environment."""
        return self.environment.get_template(f"{template_name}.md")

    async def render(
        self, report_data: ReportData, template_name: str = "entity"
    ) -> str:
        """Render report using specified template. Async for consistency."""
        template = self.get_template(template_name)
        return template.render(report_data=report_data)
