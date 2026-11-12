"""RAG sem dependências: chunking + BM25 (+ embeddings opcionais).

Por que BM25 e não só embeddings?
  * A obra do Olavo é argumentativa: quando o usuário pergunta "o que ele diz
    sobre X", o que importa é o *trecho que fala de X*, e termos raros
    ("paralaxe cognitiva", "imbecil coletivo", "graus de certeza") são
    exatamente onde BM25 brilha e embeddings às vezes borram.
  * Roda 100% offline: você pode indexar 30 mil páginas sem gastar 1 token.

O modo "hybrid" soma BM25 normalizado + cosseno de embeddings.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

EXTENSOES = {".txt", ".md", ".markdown", ".text"}

STOPWORDS = set(
    """a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela
    para com sem sob sobre entre que se como e ou mas porem contudo todavia
    ja nao sim mais menos muito pouco todo toda todos todas isto isso aquilo
    este esta esse essa aquele aquela eu tu ele ela nos vos eles elas me te lhe
    nos vos lhes meu minha teu tua seu sua nosso nossa dele dela e ao aos aquela
    foi ser sao era eram ter tem tinha havia ha ainda tambem so quando onde
    qual quais quem cujo cuja porque pois entao assim mesmo cada outro outra
    qualquer algum alguma nenhum nenhuma ora la aqui ali""".split()
)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def tokenizar(texto: str) -> list[str]:
    bruto = re.findall(r"[a-z0-9]+", normalizar(texto))
    saida = []
    for t in bruto:
        if t in STOPWORDS or len(t) < 3:
            continue
        # radicalização leve: plurais e advérbios em -mente
        if t.endswith("mente") and len(t) > 8:
            t = t[:-5]
        elif t.endswith("oes") and len(t) > 6:
            t = t[:-3] + "ao"
        elif t.endswith("s") and len(t) > 4:
            t = t[:-1]
        saida.append(t)
    return saida


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------
@dataclass
class Chunk:
    id: str
    doc_id: str
    titulo: str
    tipo: str  # livro | artigo | transcricao | entrevista | estilo | outro
    caminho: str
    ordem: int
    texto: str


def _paragrafos(texto: str) -> list[str]:
    partes = re.split(r"\n\s*\n", texto)
    return [p.strip() for p in partes if p.strip()]


def chunk_documento(
    texto: str,
    *,
    doc_id: str,
    titulo: str,
    tipo: str,
    caminho: str,
    chunk_chars: int = 1400,
    overlap: int = 200,
) -> list[Chunk]:
    """Chunking por parágrafo, respeitando fronteiras de frase."""
    paragrafos = _paragrafos(texto)
    chunks: list[Chunk] = []
    buffer = ""
    for p in paragrafos:
        if len(buffer) + len(p) + 2 <= chunk_chars:
            buffer = f"{buffer}\n\n{p}" if buffer else p
            continue
        if buffer:
            chunks.append(_mk(buffer, doc_id, titulo, tipo, caminho, len(chunks)))
            cauda = buffer[-overlap:] if overlap else ""
            buffer = f"{cauda}\n\n{p}" if cauda else p
        else:
            # parágrafo maior que o chunk: corta em sentenças
            for pedaco in _cortar_sentencas(p, chunk_chars):
                chunks.append(
                    _mk(pedaco, doc_id, titulo, tipo, caminho, len(chunks))
                )
            buffer = ""
    if buffer.strip():
        chunks.append(_mk(buffer, doc_id, titulo, tipo, caminho, len(chunks)))
    return chunks


def _cortar_sentencas(texto: str, limite: int) -> list[str]:
    sentencas = re.split(r"(?<=[.!?])\s+", texto)
    saida, atual = [], ""
    for s in sentencas:
        if len(atual) + len(s) + 1 <= limite:
            atual = f"{atual} {s}".strip()
        else:
            if atual:
                saida.append(atual)
            atual = s[:limite]
    if atual:
        saida.append(atual)
    return saida


def _mk(texto, doc_id, titulo, tipo, caminho, ordem) -> Chunk:
    h = hashlib.sha1(f"{doc_id}:{ordem}".encode()).hexdigest()[:12]
    return Chunk(
        id=f"{doc_id}-{ordem:04d}-{h}",
        doc_id=doc_id,
        titulo=titulo,
        tipo=tipo,
        caminho=caminho,
        ordem=ordem,
        texto=texto.strip(),
    )


# --------------------------------------------------------------------------
# BM25
# --------------------------------------------------------------------------
class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs: list[list[str]] = []
        self.tfs: list[Counter] = []
        self.df: Counter = Counter()
        self.avgdl = 0.0

    def fit(self, textos: list[str]) -> None:
        self.docs = [tokenizar(t) for t in textos]
        self.tfs = [Counter(d) for d in self.docs]
        self.df = Counter()
        for tf in self.tfs:
            self.df.update(tf.keys())
        self.avgdl = (sum(len(d) for d in self.docs) / len(self.docs)) if self.docs else 0.0

    def scores(self, consulta: str) -> list[float]:
        termos = tokenizar(consulta)
        n = len(self.docs)
        if not n or not termos:
            return [0.0] * n
        saida = [0.0] * n
        for termo in termos:
            df = self.df.get(termo, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, tf in enumerate(self.tfs):
                f = tf.get(termo, 0)
                if not f:
                    continue
                dl = len(self.docs[i]) or 1
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                saida[i] += idf * (f * (self.k1 + 1)) / denom
        return saida

    def to_dict(self) -> dict:
        return {
            "k1": self.k1,
            "b": self.b,
            "tfs": [dict(tf) for tf in self.tfs],
            "avgdl": self.avgdl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BM25":
        obj = cls(d["k1"], d["b"])
        obj.tfs = [Counter(tf) for tf in d["tfs"]]
        obj.docs = []  # só precisamos dos tfs e do tamanho
        obj.docs = [[] for _ in obj.tfs]
        obj.df = Counter()
        for tf in obj.tfs:
            obj.df.update(tf.keys())
        obj.avgdl = d["avgdl"]
        return obj

    def scores_serializado(self, consulta: str) -> list[float]:
        """Igual a scores(), mas usando apenas os tfs salvos (sem tokens)."""
        termos = tokenizar(consulta)
        n = len(self.tfs)
        if not n or not termos:
            return [0.0] * n
        tamanhos = [sum(tf.values()) for tf in self.tfs]
        saida = [0.0] * n
        for termo in termos:
            df = self.df.get(termo, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, tf in enumerate(self.tfs):
                f = tf.get(termo, 0)
                if not f:
                    continue
                dl = tamanhos[i] or 1
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                saida[i] += idf * (f * (self.k1 + 1)) / denom
        return saida


# --------------------------------------------------------------------------
# Índice em disco
# --------------------------------------------------------------------------
@dataclass
class Hit:
    chunk: Chunk
    score: float


TIPO_POR_PASTA = {
    "livros": "livro",
    "articles": "artigo",
    "artigos": "artigo",
    "transcricoes": "transcricao",
    "transcrições": "transcricao",
    "entrevistas": "entrevista",
    "estilo": "estilo",
}


def _classificar(caminho: Path, raiz: Path) -> str:
    try:
        pasta = caminho.relative_to(raiz).parts[0].lower()
    except ValueError:
        return "outro"
    return TIPO_POR_PASTA.get(pasta, "outro")


def ingerir(
    corpus_dir: Path,
    cfg_chunk: int = 1400,
    cfg_overlap: int = 200,
) -> tuple[list[Chunk], dict]:
    chunks: list[Chunk] = []
    docs = []
    for caminho in sorted(corpus_dir.rglob("*")):
        if caminho.suffix.lower() not in EXTENSOES or not caminho.is_file():
            continue
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        if not texto.strip():
            continue
        doc_id = hashlib.sha1(str(caminho).encode()).hexdigest()[:10]
        titulo = texto.lstrip().splitlines()[0].lstrip("# ").strip()[:120] or caminho.stem
        tipo = _classificar(caminho, corpus_dir)
        pedacos = chunk_documento(
            texto,
            doc_id=doc_id,
            titulo=titulo,
            tipo=tipo,
            caminho=str(caminho.relative_to(corpus_dir)),
            chunk_chars=cfg_chunk,
            overlap=cfg_overlap,
        )
        chunks.extend(pedacos)
        docs.append(
            {
                "doc_id": doc_id,
                "titulo": titulo,
                "tipo": tipo,
                "caminho": str(caminho.relative_to(corpus_dir)),
                "chunks": len(pedacos),
                "caracteres": len(texto),
            }
        )
    meta = {"docs": docs, "total_chunks": len(chunks), "corpus": str(corpus_dir)}
    return chunks, meta


class Indice:
    def __init__(self, chunks: list[Chunk], bm25: BM25, meta: dict, vetores=None):
        self.chunks = chunks
        self.bm25 = bm25
        self.meta = meta
        self.vetores = vetores or []

    # -- persistência ------------------------------------------------------
    def salvar(self, pasta: Path) -> None:
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "chunks.json").write_text(
            json.dumps([asdict(c) for c in self.chunks], ensure_ascii=False),
            encoding="utf-8",
        )
        (pasta / "bm25.json").write_text(
            json.dumps(self.bm25.to_dict(), ensure_ascii=False), encoding="utf-8"
        )
        (pasta / "meta.json").write_text(
            json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if self.vetores:
            (pasta / "vetores.json").write_text(
                json.dumps(self.vetores), encoding="utf-8"
            )

    @classmethod
    def carregar(cls, pasta: Path) -> "Indice":
        chunks = [Chunk(**c) for c in json.loads((pasta / "chunks.json").read_text("utf-8"))]
        bm25 = BM25.from_dict(json.loads((pasta / "bm25.json").read_text("utf-8")))
        meta = json.loads((pasta / "meta.json").read_text("utf-8"))
        vetores = []
        pv = pasta / "vetores.json"
        if pv.exists():
            vetores = json.loads(pv.read_text("utf-8"))
        return cls(chunks, bm25, meta, vetores)

    # -- busca -------------------------------------------------------------
    def buscar(self, consulta: str, k: int = 8, modo: str = "keyword") -> list[Hit]:
        if not self.chunks:
            return []
        bm = self.bm25.scores_serializado(consulta)
        bm_max = max(bm) if bm else 0.0
        bm_norm = [s / bm_max for s in bm] if bm_max > 0 else bm

        emb = [0.0] * len(self.chunks)
        if modo in {"embedding", "hybrid"} and self.vetores:
            emb = self._scores_vetoriais(consulta)
            emb_max = max(emb) if emb else 0.0
            if emb_max > 0:
                emb = [s / emb_max for s in emb]

        if modo == "embedding" and self.vetores:
            finais = emb
        elif modo == "hybrid" and self.vetores:
            finais = [0.5 * a + 0.5 * b for a, b in zip(bm_norm, emb)]
        else:
            finais = bm_norm

        ordem = sorted(range(len(finais)), key=lambda i: finais[i], reverse=True)[:k]
        return [Hit(self.chunks[i], round(finais[i], 4)) for i in ordem if finais[i] > 0]

    def _scores_vetoriais(self, consulta: str) -> list[float]:
        # importado aqui para evitar dependência circular
        from .llm import embed  # noqa: PLC0415
        from .config import RetrievalConfig  # noqa: PLC0415

        cfg = RetrievalConfig()
        q = embed(
            [consulta],
            cfg.embedding_base_url,
            cfg.embedding_api_key,
            cfg.embedding_model,
        )[0]
        return [_cosseno(q, v) for v in self.vetores]


def _cosseno(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return num / (da * db) if da and db else 0.0
