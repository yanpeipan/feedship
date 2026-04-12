"""LLM client module — unified interface via litellm Router.

Simplified after Router migration: all provider routing, retries, and
fallback handled by litellm Router. This module provides concurrency
control and daily call capping.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import litellm
from langchain_core.runnables import Runnable
from litellm import Router

from src.application.config import _get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    """LLM configuration loaded from app settings."""

    model: str = "gpt-4o-mini"
    api_key: str | None = None
    max_concurrency: int = 1
    timeout_seconds: int = 60
    daily_cap: int = 1000

    @classmethod
    def from_settings(cls) -> LLMConfig:
        """Load LLM config from app settings."""
        settings = _get_settings()
        llm_data = getattr(settings, "llm", {}) or {}
        api_key = llm_data.get("api_key", "")
        if (
            isinstance(api_key, str)
            and api_key.startswith("${")
            and api_key.endswith("}")
        ):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var)
        return cls(
            model=llm_data.get("model", "gpt-4o-mini"),
            api_key=api_key,
            max_concurrency=llm_data.get("max_concurrency", 5),
            timeout_seconds=llm_data.get("timeout_seconds", 60),
            daily_cap=llm_data.get("daily_cap", 1000),
        )




# ---------------------------------------------------------------------------
# LiteLLM Router singleton — configured from settings
# ---------------------------------------------------------------------------

_llm_settings = _get_settings()
_llm_config = _llm_settings.llm or {}
_model_list: list[dict] = _llm_config.get("model_list", [])
_routing_strategy = _llm_config.get("routing_strategy", "usage-based-routing")
_timeout_seconds: int = _llm_config.get("timeout_seconds", 60)

# Drop unsupported params per-model (e.g. thinking not supported by MiniMax-M2.7)
litellm.drop_params = True

llm_router: Router = Router(
    model_list=_model_list,
    routing_strategy=_routing_strategy,
    num_retries=0,
    timeout=_timeout_seconds,
)


# ---------------------------------------------------------------------------
# LLM wrapper for LCEL chains
# ---------------------------------------------------------------------------


def _get_llm_wrapper(
    max_tokens: int | None = None,
    response_format: dict | None = None,
    thinking: dict | None = None,
) -> Runnable:
    """Get a ChatLiteLLMRouter wrapper with optional configuration.

    Uses the module-level llm_router which handles all provider routing,
    retries, and fallback via litellm.
    """
    from langchain_litellm import ChatLiteLLMRouter

    # Get model_name from router's first model (could be extended to support multiple)
    model_name = _model_list[0]["model_name"] if _model_list else "gpt-4o-mini"

    wrapper = ChatLiteLLMRouter(
        router=llm_router,
        model_name=model_name,
        max_tokens=max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS,
    )
    if response_format:
        wrapper = wrapper.bind(response_format=response_format)
    if thinking:
        wrapper = wrapper.bind(thinking=thinking)
    return wrapper


# Default max tokens for LLM calls
DEFAULT_MAX_TOKENS = 300
