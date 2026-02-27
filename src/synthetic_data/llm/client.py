"""LLM API client wrapper.

Uses IBM Watson Orchestrate with IAM token authentication by default.
Falls back to OpenAI when ``LLM_PROVIDER=openai``.

Required environment variables (watsonx, default):
    IBM_API_KEY      — IBM Cloud API key
    LLM_ENDPOINT     — Watson Orchestrate chat completions URL
    Optional: LLM_MODEL (default: groq/openai/gpt-oss-120b)

Required environment variables (openai):
    OPENAI_API_KEY
    Optional: OPENAI_MODEL (default: gpt-4o)
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests


def _load_env() -> None:
    """Load variables from .env file if it exists (no external dependency)."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


# ---------------------------------------------------------------------------
# IAM token cache (tokens are valid for ~1 hour, refresh after 50 min)
# ---------------------------------------------------------------------------

_TOKEN_LIFETIME = 50 * 60  # refresh after 50 minutes

_iam_lock = threading.Lock()
_iam_token: str | None = None
_iam_token_expiry: float = 0.0


def _get_iam_token(api_key: str) -> str:
    """Return a cached IAM token, refreshing only when expired."""
    global _iam_token, _iam_token_expiry

    with _iam_lock:
        if _iam_token and time.monotonic() < _iam_token_expiry:
            return _iam_token

        resp = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={api_key}",
        )
        resp.raise_for_status()
        _iam_token = resp.json()["access_token"]
        _iam_token_expiry = time.monotonic() + _TOKEN_LIFETIME
        return _iam_token


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_llm(prompt: str, system: str = "") -> str:
    """Call the LLM and return the raw text response."""
    provider = os.environ.get("LLM_PROVIDER", "watsonx").lower()

    if provider == "watsonx":
        return _call_watsonx(prompt, system)
    elif provider == "openai":
        return _call_openai(prompt, system)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}")


def call_llm_json(prompt: str, system: str = "") -> Any:
    """Call the LLM and parse the response as JSON.

    Extracts the first JSON object or array found in the response text,
    handling cases where the LLM wraps JSON in markdown code fences.
    """
    raw = call_llm(prompt, system)
    return _extract_json(raw)


def call_llm_batch(
    prompts: list[tuple[str, str]],
    *,
    max_workers: int = 8,
) -> list[str]:
    """Call the LLM for multiple (prompt, system) pairs concurrently.

    Returns results in the same order as the input list.
    """
    results: list[str | None] = [None] * len(prompts)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(call_llm, prompt, system): idx
            for idx, (prompt, system) in enumerate(prompts)
        }
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    return results  # type: ignore[return-value]


def call_llm_json_batch(
    prompts: list[tuple[str, str]],
    *,
    max_workers: int = 8,
) -> list[Any]:
    """Call the LLM for multiple (prompt, system) pairs and parse each as JSON.

    Returns results in the same order as the input list.
    """
    raw_results = call_llm_batch(prompts, max_workers=max_workers)
    return [_extract_json(r) for r in raw_results]


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


def _call_watsonx(prompt: str, system: str) -> str:
    api_key = os.environ["IBM_API_KEY"]
    endpoint = os.environ["LLM_ENDPOINT"]
    model = os.environ.get("LLM_MODEL", "groq/openai/gpt-oss-120b")

    token = _get_iam_token(api_key)

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_openai(prompt: str, system: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "openai is required for the openai provider. "
            "Install it with: pip install openai"
        ) from exc

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> Any:
    """Extract JSON from LLM response text.

    Handles plain JSON, markdown-fenced JSON (```json ... ```), and
    responses with surrounding prose.
    """
    # Strip markdown code fences
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    # Try direct parse first
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Find first [ or { and parse from there
    for i, ch in enumerate(stripped):
        if ch in ("{", "["):
            try:
                return json.loads(stripped[i:])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract JSON from LLM response:\n{text[:500]}")
