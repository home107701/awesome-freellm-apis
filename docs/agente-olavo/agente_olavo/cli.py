"""CLI do agente.

Uso:
    python -m agente_olavo ingest                 # indexa ./corpus
    python -m agente_olavo ask "pergunta" -m persona
    python -m agente_olavo chat                   # REPL
    python -m agente_olavo stats                  # tamanho do índice
    python -m agente_olavo eval                   # roda evals/qa.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import llm
from .agente import AgenteOlavo
from .config import AgentConfig, RAIZ
from .rag import BM25, Chunk, Indice, chunk_documento, ingerir

CORPUS_PADRAO = RAIZ / "corpus"


# --------------------------------------------------------------------------
def cmd_ingest(args, cfg: AgentConfig) -> int:
    corpus = Path(args.corpus or CORPUS_PADRAO)
    if not corpus.exists():
        print(f"[erro] corpus não encontrado: {corpus}", file=sys.stderr)
        print(
            "Crie a pasta e ponha .txt/.md (ver docs/COMO-MONTAR-O-CORPUS.md).",
            file=sys.stderr,
        )
        return 1
    chunks, meta = ingerir(
        corpus, args.chunk_chars or cfg.retrieval.chunk_chars,
        args.overlap or cfg.retrieval.chunk_overlap,
    )
    if not chunks:
        print(f"[erro] nenhum .txt/.md em {corpus}", file=sys.stderr)
        return 1
    bm25 = BM25()
    bm25.fit([c.texto for c in chunks])

    vetores = None
    if args.embeddings:
        if not cfg.retrieval.embedding_api_key:
            print("[erro] EMBEDDING_API_KEY não definida", file=sys.stderr)
            return 1
        print("[info] gerando embeddings (pode demorar)...")
        vetores = []
        lote = 32
        for i in range(0, len(chunks), lote):
            parte = [c.texto for c in chunks[i : i + lote]]
            vetores.extend(
                llm.embed(
                    parte,
                    cfg.retrieval.embedding_base_url,
                    cfg.retrieval.embedding_api_key,
                    cfg.retrieval.embedding_model,
                )
            )
            print(f"  {min(i + lote, len(chunks))}/{len(chunks)}", end="\r")
        print()

    idx = Indice(chunks, bm25, meta, vetores)
    idx.salvar(cfg.index_dir)
    print(
        f"[ok] {len(meta['docs'])} documentos, {len(chunks)} chunks, "
        f"índice em {cfg.index_dir}"
    )
    return 0


def cmd_stats(args, cfg: AgentConfig) -> int:
    idx = Indice.carregar(cfg.index_dir)
    print(f"documentos: {len(idx.meta['docs'])}")
    print(f"chunks:     {len(idx.chunks)}")
    print(f"embeddings: {len(idx.vetores)}")
    por_tipo: dict[str, int] = {}
    for c in idx.chunks:
        por_tipo[c.tipo] = por_tipo.get(c.tipo, 0) + 1
    for tipo, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
        print(f"  {tipo:12s} {n:6d}")
    return 0


def cmd_search(args, cfg: AgentConfig) -> int:
    idx = Indice.carregar(cfg.index_dir)
    for h in idx.buscar(args.consulta, k=args.k, modo=cfg.retrieval.mode):
        print(f"\n=== {h.score:.3f} | {h.chunk.titulo} ({h.chunk.tipo}) ===")
        print(h.chunk.texto[:600])
    return 0


def cmd_ask(args, cfg: AgentConfig) -> int:
    ag = AgenteOlavo(cfg)
    ag.carregar_indice()
    r = ag.perguntar(args.pergunta, modo=args.modo)
    print(r.texto)
    if args.fontes and r.fontes:
        print("\n--- fontes ---")
        for f in r.fontes:
            print(f"[{f['id']}] {f['titulo']} ({f['caminho']}#{f['ordem']}) score={f['score']}")
    return 0


def cmd_chat(args, cfg: AgentConfig) -> int:
    ag = AgenteOlavo(cfg)
    ag.carregar_indice()
    historico: list[dict] = []
    modo = args.modo
    print(f"Agente Olavo de Carvalho — modo {modo}. '\\modo' alterna, '\\sair' encerra.")
    while True:
        try:
            q = input("\nvocê> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in {"\\sair", "\\quit", "\\exit"}:
            break
        if q == "\\modo":
            modo = "analitico" if modo == "persona" else "persona"
            print(f"[modo {modo}]")
            continue
        try:
            r = ag.perguntar(q, modo=modo, historico=historico)
        except llm.LLMError as exc:
            print(f"[erro] {exc}")
            continue
        print("\n" + r.texto)
        historico += [
            {"role": "user", "content": q},
            {"role": "assistant", "content": r.texto},
        ]
    return 0


def cmd_eval(args, cfg: AgentConfig) -> int:
    """Roda um jsonl de {pergunta, deve_conter: [...], nao_deve_conter: [...]}."""
    caminho = Path(args.arquivo or RAIZ / "evals" / "qa.jsonl")
    ag = AgenteOlavo(cfg)
    ag.carregar_indice()
    casos = [json.loads(l) for l in caminho.read_text("utf-8").splitlines() if l.strip()]
    ok = 0
    for caso in casos:
        r = ag.perguntar(caso["pergunta"], modo=caso.get("modo", "persona"))
        t = r.texto.lower()
        falhas = [s for s in caso.get("deve_conter", []) if s.lower() not in t]
        probs = [s for s in caso.get("nao_deve_conter", []) if s.lower() in t]
        if caso.get("exige_fonte", True) and caso.get("modo", "persona") == "persona":
            if "[f" not in t:
                falhas.append("<sem citação [F#]>")
        if falhas or probs:
            print(f"✗ {caso['pergunta'][:70]}")
            if falhas:
                print(f"   faltou: {falhas}")
            if probs:
                print(f"   proibido apareceu: {probs}")
        else:
            ok += 1
            print(f"✓ {caso['pergunta'][:70]}")
    print(f"\n{ok}/{len(casos)} aprovados")
    return 0 if ok == len(casos) else 2


# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agente_olavo", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest", help="indexar o corpus")
    i.add_argument("--corpus", help="pasta com .txt/.md (padrão: ./corpus)")
    i.add_argument("--chunk-chars", type=int)
    i.add_argument("--overlap", type=int)
    i.add_argument("--embeddings", action="store_true", help="também gerar embeddings")
    i.set_defaults(fn=cmd_ingest)

    a = sub.add_parser("ask", help="uma pergunta")
    a.add_argument("pergunta")
    a.add_argument("-m", "--modo", choices=["persona", "analitico"], default="persona")
    a.add_argument("--fontes", action="store_true", help="imprimir a lista de fontes")
    a.set_defaults(fn=cmd_ask)

    c = sub.add_parser("chat", help="conversa contínua")
    c.add_argument("-m", "--modo", choices=["persona", "analitico"], default="persona")
    c.set_defaults(fn=cmd_chat)

    s = sub.add_parser("search", help="buscar trechos no índice")
    s.add_argument("consulta")
    s.add_argument("-k", type=int, default=5)
    s.set_defaults(fn=cmd_search)

    st = sub.add_parser("stats", help="estatísticas do índice")
    st.set_defaults(fn=cmd_stats)

    e = sub.add_parser("eval", help="rodar avaliação")
    e.add_argument("--arquivo")
    e.set_defaults(fn=cmd_eval)

    args = p.parse_args(argv)
    cfg = AgentConfig()
    try:
        return args.fn(args, cfg)
    except FileNotFoundError as exc:
        print(f"[erro] {exc}", file=sys.stderr)
        return 1
    except llm.LLMError as exc:
        print(f"[erro] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
