"""Pydantic output models for LLM chain structured responses."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class TLDRItem(BaseModel):
    """Single TLDR item for an entity topic."""

    entity_id: str = Field(description="Normalized entity identifier")
    tldr: str = Field(description="One-sentence TLDR in target language")


class ClassifyTranslateItem(BaseModel):
    """Single news classification and translation result."""

    id: Annotated[int, Field(ge=1, description="News ID (1-indexed integer)")]
    tags: list[str] = Field(
        description="List of 0-3 tags from candidate tag list, most specific first"
    )
    translation: str = Field(description="Translated news title in target language")


class ClassifyTranslateOutput(BaseModel):
    """Batch classification and translation output."""

    items: list[ClassifyTranslateItem] = Field(
        description="List of classification results, one per news item"
    )
