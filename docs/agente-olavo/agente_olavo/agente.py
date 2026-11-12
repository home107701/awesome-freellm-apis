"""O agente: monta o prompt (persona + estilo + RAG) e chama o LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import llm
from .config import AgentConfig
from .rag import Indice


@dataclass
class Resposta:
    texto: str
    fontes: list[dict] = field(default_factory=list)
    modo: str = "persona"


class AgenteOlavo:
    def __init__(self, cfg: AgentConfig | None = None):
        self.cfg = cfg or AgentConfig()
        self.system = self._ler("SYSTEM.md")
        self.estilo = self._ler("style/guia-de-estilo.md")
        self.exemplos = self._ler("style/exemplos.md")
        self.obras = self._ler("kbs/obras.md")
        self.indice: Indice | None = None

    # ------------------------------------------------------------------
    def _ler(self, rel: str) -> str:
        p = self.cfg.persona_dir / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def carregar_indice(self, pasta: Path | None = None) -> None:
        pasta = pasta or self.cfg.index_dir
        if not (pasta / "chunks.json").exists():
            raise FileNotFoundError(
                f"Índice não encontrado em {pasta}. Rode: python -m agente_olavo.cli ingest"
            )
        self.indice = Indice.carregar(pasta)

    # ------------------------------------------------------------------
    def _bloco_fontes(self, consulta: str) -> tuple[str, list[dict]]:
        if not self.indice:
            return "", []
        hits = self.indice.buscar(
            consulta, k=self.cfg.retrieval.top_k, modo=self.cfg.retrieval.mode
        )
        if not hits:
            return "", []
        linhas, meta = [], []
        for i, h in enumerate(hits, 1):
            c = h.chunk
            linhas.append(
                f"[F{i}] {c.titulo} ({c.tipo}, {c.caminho}, trecho {c.ordem})\n{c.texto}"
            )
            meta.append(
                {
                    "id": f"F{i}",
                    "titulo": c.titulo,
                    "tipo": c.tipo,
                    "caminho": c.caminho,
                    "ordem": c.ordem,
                    "score": h.score,
                }
            )
        return "\n\n---\n\n".join(linhas), meta

    # ------------------------------------------------------------------
    def perguntar(
        self,
        pergunta: str,
        *,
        modo: str = "persona",
        historico: list[dict] | None = None,
        mostrar_graus: bool | None = None,
    ) -> Resposta:
        fontes_txt, fontes_meta = self._bloco_fontes(pergunta)

        partes = [self.system]
        if self.estilo:
            partes.append("# GUIA DE ESTILO OPERACIONAL\n\n" + self.estilo)
        if self.exemplos:
            partes.append("# EXEMPLOS DE REFERÊNCIA (forma, não conteúdo)\n\n" + self.exemplos)
        if self.obras:
            partes.append("# CATÁLOGO DE OBRAS CONFIRMADAS\n\n" + self.obras)

        mostrar = (
            self.cfg.mostrar_graus_de_certeza if mostrar_graus is None else mostrar_graus
        )
        partes.append(
            "# INSTRUÇÕES DA TAREFA\n\n"
            f"- Modo: **{modo.upper()}**\n"
            "- Se houver `<FONTES>`, ancore-se nelas e cite como [F#].\n"
            "- Se as fontes não sustentarem a resposta, diga o que falta.\n"
            + (
                "- Anexe o bloco [graus de certeza] ao final.\n"
                if mostrar
                else "- Sem bloco de graus de certeza.\n"
            )
        )
        if fontes_txt:
            partes.append("# <FONTES>\n\n" + fontes_txt + "\n\n# </FONTES>")
        else:
            partes.append(
                "# <FONTES>\n\n(nenhum trecho recuperado — responda apenas como "
                "extrapolação declarada ou peça recorte do corpus)\n\n# </FONTES>"
            )

        mensagens = [{"role": "system", "content": "\n\n".join(partes)}]
        for m in (historico or [])[-self.cfg.max_historico :]:
            mensagens.append(m)
        mensagens.append({"role": "user", "content": pergunta})

        texto = llm.chat(mensagens, self.cfg.llm)
        return Resposta(texto=texto, fontes=fontes_meta, modo=modo)
