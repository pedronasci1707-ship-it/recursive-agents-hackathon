"""Thin wrapper around Crusoe Managed Inference (OpenAI-compatible endpoint).

Every agent should call the models through `chat()` so retries, model routing
and token accounting live in one place.
"""

import os
import random
import time
from collections import defaultdict
from functools import lru_cache

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

load_dotenv()

BASE_URL = "https://api.inference.crusoecloud.com/v1"
PLACEHOLDER_KEY = "paste-your-key-here"

# Agent role -> model ID. IDs are case-sensitive; confirm with scripts/check_crusoe.py.
MODELS = {
    "planner": os.getenv("MODEL_PLANNER", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B"),
    "worker": os.getenv("MODEL_WORKER", "nvidia/Nemotron-3.5-Lightning-30B-A3B"),
    "fast": os.getenv("MODEL_FAST", "deepseek-ai/Deepseek-V4-Flash"),
    "tools": os.getenv("MODEL_TOOLS", "openai/gpt-oss-120b"),
    "vision": os.getenv("MODEL_VISION", "google/gemma-4-31b-it"),
}

# Running totals per model: prompt / completion / cached tokens and request count.
USAGE = defaultdict(lambda: {"requests": 0, "prompt": 0, "completion": 0, "cached": 0})

RETRYABLE = (RateLimitError, InternalServerError, APIConnectionError, APITimeoutError)


def api_key():
    key = os.getenv("CRUSOE_API_KEY", "").strip()
    if not key or key == PLACEHOLDER_KEY:
        raise RuntimeError(
            "CRUSOE_API_KEY is missing. Paste your Intelligence API key into .env "
            "(see .env.example)."
        )
    return key


@lru_cache(maxsize=1)
def get_client():
    return OpenAI(base_url=BASE_URL, api_key=api_key(), timeout=120.0, max_retries=0)


def resolve_model(model_or_role):
    return MODELS.get(model_or_role, model_or_role)


def chat(model_or_role, messages, max_tokens=4096, max_tries=6, **kwargs):
    """Chat completion with jittered exponential backoff on 429/503/network errors.

    `model_or_role` is either a role from MODELS ("planner", "worker", ...) or a
    raw model ID. Extra kwargs (tools, temperature, extra_body, ...) pass through.
    """
    model = resolve_model(model_or_role)
    client = get_client()
    for attempt in range(max_tries):
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens, **kwargs
            )
            _record_usage(model, resp)
            return resp
        except RETRYABLE:
            if attempt == max_tries - 1:
                raise
            time.sleep(min(60.0, 2**attempt) + random.uniform(0, 0.5))


def text(resp):
    """Answer text of a response, falling back to the reasoning trace if empty."""
    msg = resp.choices[0].message
    if msg.content:
        return msg.content
    extra = msg.model_dump()
    return extra.get("reasoning_content") or extra.get("reasoning") or ""


def usage_summary():
    """Per-model totals plus prefix-cache hit rate, handy for the demo."""
    summary = {}
    for model, u in USAGE.items():
        hit = u["cached"] / u["prompt"] if u["prompt"] else 0.0
        summary[model] = {**u, "cache_hit_rate": round(hit, 3)}
    return summary


def _record_usage(model, resp):
    u = USAGE[model]
    u["requests"] += 1
    if resp.usage:
        u["prompt"] += resp.usage.prompt_tokens or 0
        u["completion"] += resp.usage.completion_tokens or 0
        details = resp.usage.prompt_tokens_details
        u["cached"] += (details.cached_tokens or 0) if details else 0
