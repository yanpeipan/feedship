"""Pydantic output models for LLM chain structured responses."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class EntityItem(BaseModel):
    """Single named entity extracted from an article."""

    name: str = Field(description="Raw entity name, e.g. 'Google Gemma 4'")
    type: Annotated[
        str, Field(description="Entity type: ORG, PRODUCT, MODEL, PERSON, or EVENT")
    ]
    normalized: str = Field(
        description="Canonical lowercase slug, e.g. 'google_gemma_4'"
    )


class NERArticle(BaseModel):
    """NER result for a single article."""

    id: str = Field(description="Article ID")
    entities: list[EntityItem] = Field(
        description="List of entities extracted from this article"
    )


class EvaluateScore(BaseModel):
    """Report quality evaluation scores."""

    coherence: Annotated[
        float, Field(ge=0.0, le=1.0, description="Coherence score 0.0-1.0")
    ]
    relevance: Annotated[
        float, Field(ge=0.0, le=1.0, description="Relevance score 0.0-1.0")
    ]
    depth: Annotated[float, Field(ge=0.0, le=1.0, description="Depth score 0.0-1.0")]
    structure: Annotated[
        float, Field(ge=0.0, le=1.0, description="Structure score 0.0-1.0")
    ]


class EntityTopicOutput(BaseModel):
    """Entity topic analysis output from get_entity_topic_chain."""

    headline: Annotated[
        str, Field(max_length=30, description="Topic headline, max 30 characters")
    ]
    layer: str = Field(
        description="AI layer: AI应用, AI模型, AI基础设施, 芯片, or 能源"
    )
    signals: list[str] = Field(description="List of signal keywords")
    insight: str = Field(description="One-sentence insight about the entity")


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
