"""Cliente mínimo para qualquer endpoint compatível com /chat/completions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import LLMConfig


class LLMError(RuntimeError):
    pass


def chat(
    messages: list[dict[str, str]],
    cfg: LLMConfig,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_mode: bool = False,
    timeout: int = 180,
) -> str:
    payload: dict = {
        "model": cfg.model,
        "messages": messages,
        "temperature": cfg.temperature if temperature is None else temperature,
        "max_tokens": cfg.max_tokens if max_tokens is None else max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url=f"{cfg.base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=cfg.headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        corpo = exc.read().decode("utf-8", "replace")[:800]
        raise LLMError(f"HTTP {exc.code} em {cfg.base_url}: {corpo}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"Falha de rede em {cfg.base_url}: {exc.reason}") from exc

    try:
        return dados["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Resposta inesperada: {json.dumps(dados)[:800]}") from exc


def embed(textos: list[str], base_url: str, api_key: str, model: str) -> list[list[float]]:
    """Embeddings via endpoint OpenAI-compatible."""
    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/embeddings",
        data=json.dumps({"model": model, "input": textos}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        dados = json.loads(resp.read().decode("utf-8"))
    return [item["embedding"] for item in dados["data"]]
