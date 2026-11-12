"""Configuração do agente.

Tudo vem de variáveis de ambiente (ou de um arquivo .env carregado à mão),
para que o mesmo código rode com qualquer provedor compatível com a API da
OpenAI -- Groq, Cerebras, Gemini (endpoint compatível), OpenRouter, Ollama
local etc. Ver a lista em ../../README.md (seção "Provider Directory").
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PERSONA_DIR = RAIZ / "persona" / "olavo-de-carvalho"


def _load_dotenv(caminho: Path | None = None) -> None:
    """Carregador mínimo de .env (sem dependência externa)."""
    caminho = caminho or RAIZ / ".env"
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        chave = chave.strip()
        valor = valor.strip().strip("'\"")
        os.environ.setdefault(chave, valor)


_load_dotenv()


@dataclass
class LLMConfig:
    """Qualquer provedor OpenAI-compatible serve."""

    base_url: str = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    )
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "moonshotai/kimi-k2-instruct")
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.75"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "4000"))
    )
    # Nome do cabeçalho de autenticação: "Authorization" (padrão OpenAI) ou
    # "x-goog-api-key" para o endpoint Gemini "OpenAI-compat".
    auth_header: str = field(
        default_factory=lambda: os.getenv("LLM_AUTH_HEADER", "Authorization")
    )

    def headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY não definida. Copie .env.example para .env e preencha."
            )
        if self.auth_header.lower() == "authorization":
            valor = f"Bearer {self.api_key}"
        else:
            valor = self.api_key
        return {"Content-Type": "application/json", self.auth_header: valor}


@dataclass
class RetrievalConfig:
    # "keyword" = busca léxica BM25 pura (zero dependências, roda offline)
    # "embedding" = embeddings via API (melhor recall semântico)
    # "hybrid" = soma normalizada dos dois (recomendado com corpus grande)
    mode: str = field(default_factory=lambda: os.getenv("RETRIEVAL_MODE", "keyword"))
    top_k: int = field(default_factory=lambda: int(os.getenv("RETRIEVAL_TOP_K", "8")))
    chunk_chars: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_CHARS", "1400"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )
    embedding_base_url: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_BASE_URL", "https://api.openai.com/v1"
        )
    )
    embedding_api_key: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY", "")
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )


@dataclass
class AgentConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    persona_dir: Path = field(default_factory=lambda: PERSONA_DIR)
    index_dir: Path = field(default_factory=lambda: RAIZ / ".index")
    # Quando True, o agente anexa uma "ficha de graus de certeza" ao final,
    # separando o que é doutrina documentada do que é extrapolação de estilo.
    mostrar_graus_de_certeza: bool = field(
        default_factory=lambda: os.getenv("MOSTRAR_GRAUS", "1") == "1"
    )
    max_historico: int = field(
        default_factory=lambda: int(os.getenv("MAX_HISTORICO", "8"))
    )
