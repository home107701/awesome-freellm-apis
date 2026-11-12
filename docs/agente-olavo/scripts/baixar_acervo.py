#!/usr/bin/env python3
"""Baixa o acervo curado para `corpus/`, respeitando prioridade e licença.

Fontes suportadas:

  cof-github   transcrições do COF revisadas — GitHub osescribas/cof (CC0-1.0)
               → corpus/transcricoes/  [redistribuível]
  wayback      artigos, apostilas e trechos de livro do site oficial, via
               Wayback Machine (o domínio original está comprometido)
               → corpus/artigos/ e corpus/apostilas/  [uso privado]
  cof-audio    áudios das aulas do Internet Archive, para transcrição própria
               → midia/   [verificar licença do item]

Uso:
    python3 scripts/baixar_acervo.py --fonte cof-github
    python3 scripts/baixar_acervo.py --fonte wayback --prioridade P0
    python3 scripts/baixar_acervo.py --fonte cof-audio --aulas 1 147 219

Sem dependências além da biblioteca padrão.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
CORPUS = RAIZ / "corpus"
MIDIA = RAIZ / "midia"
UA = "Mozilla/5.0 (compatible; corpus-builder/1.0; estudo privado)"

REPO_COF = "osescribas/cof"
API = "https://api.github.com"


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def slug(texto: str, limite: int = 80) -> str:
    texto = re.sub(r"[^\w\s-]", "", texto, flags=re.UNICODE)
    texto = re.sub(r"[\s_]+", "-", texto).strip("-").lower()
    return texto[:limite] or "sem-titulo"


def get(url: str, *, timeout: int = 60, tentativas: int = 3, headers=None) -> bytes:
    h = {"User-Agent": UA}
    h.update(headers or {})
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            erro = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 404):
                break
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"falhou {url}: {erro}")


def texto_de_html(bruto: bytes) -> str:
    """Extração simples: remove scripts/estilos e tags (sem bs4)."""
    html = bruto.decode("utf-8", "replace")
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</h[1-6]>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    import html as h  # noqa: PLC0415

    txt = h.unescape(html)
    txt = re.sub(r"[ \t\xa0]+", " ", txt)
    txt = re.sub(r"\n\s*\n\s*\n+", "\n\n", txt)
    linhas = [l.strip() for l in txt.splitlines()]
    return "\n".join(linhas).strip()


def escrever(caminho: Path, cabecalho: list[str], corpo: str) -> bool:
    if len(corpo) < 600:
        log(f"  ! texto curto ({len(corpo)} chars) — ignorado: {caminho.name}")
        return False
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(f"# {c}" for c in cabecalho) + "\n\n" + corpo, "utf-8")
    log(f"  ok {caminho.relative_to(RAIZ)} ({len(corpo):,} chars)")
    return True


# ---------------------------------------------------------------------------
# fonte 1: COF no GitHub (CC0)
# ---------------------------------------------------------------------------
def baixar_cof_github(aulas: list[int] | None = None, todas: bool = False) -> None:
    destino = CORPUS / "transcricoes"
    log(f"[cof-github] listando {REPO_COF}...")
    arquivos: list[str] = []
    for pasta in ("revisadas", "revisao_pendente"):
        url = f"{API}/repos/{REPO_COF}/contents/{pasta}"
        try:
            itens = json.loads(get(url))
        except RuntimeError as exc:
            log(f"  ! {exc}")
            continue
        arquivos += [f"{pasta}/{i['name']}" for i in itens if i["name"].endswith(".md")]
    log(f"[cof-github] {len(arquivos)} arquivos .md encontrados")

    if aulas:
        alvo = {f"COF{n:03d}.md" for n in aulas}
        arquivos = [a for a in arquivos if Path(a).name in alvo]
    if not todas:
        # preferir as revisadas quando a mesma aula aparece nos dois lugares
        revisadas = {Path(a).name for a in arquivos if a.startswith("revisadas/")}
        arquivos = [
            a for a in arquivos
            if a.startswith("revisadas/") or Path(a).name not in revisadas
        ]

    baixados = 0
    for i, caminho in enumerate(sorted(arquivos), 1):
        nome = Path(caminho).name
        aula = nome.replace(".md", "")
        saida = destino / f"{aula}.txt"
        if saida.exists() and saida.stat().st_size > 2000:
            continue
        url = f"{API}/repos/{REPO_COF}/contents/{caminho}"
        try:
            corpo = get(url, headers={"Accept": "application/vnd.github.raw"})
        except RuntimeError as exc:
            log(f"  ! {aula}: {exc}")
            continue
        texto = corpo.decode("utf-8", "replace")
        # cabeçalho interno do .md já traz aula e data; normaliza para o indexador
        data = ""
        m = re.search(r"(\d{1,2} de \w+ de \d{4})", texto[:400])
        if m:
            data = m.group(1)
        escrever(
            saida,
            [f"COF — {aula}", "fonte: osescribas/cof (CC0-1.0)", f"data: {data or 's/d'}"],
            texto,
        )
        baixados += 1
        if i % 25 == 0:
            log(f"  ... {i}/{len(arquivos)}")
        time.sleep(0.15)  # cortesia com a API (60 req/h sem token)
    log(f"[cof-github] {baixados} aulas novas em {destino.relative_to(RAIZ)}")


# ---------------------------------------------------------------------------
# fonte 2: Wayback (artigos, apostilas, trechos)
# ---------------------------------------------------------------------------
def _carregar_csv(nome: str) -> list[dict]:
    caminho = DATA / nome
    if not caminho.exists():
        log(f"  ! {caminho} não encontrado")
        return []
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def gerar_lista_wget(prioridades: set[str]) -> Path:
    """Escreve um script wget para quem está em rede que bloqueia o Python.

    Alguns ambientes (proxies, sandboxes) fecham a conexão TLS com
    web.archive.org para clientes não-navegador. Nestes casos, rode o script
    gerado na sua máquina — o wget com User-Agent de navegador costuma passar.
    """
    linhas = _carregar_csv("artigos.csv")
    alvo = [
        l for l in linhas
        if (l.get("prioridade") or "P2").upper() in prioridades and l.get("url_arquivo")
    ]
    destino = DATA / "baixar-wayback.sh"
    with destino.open("w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("# Gerado por baixar_acervo.py — baixa o acervo do Wayback.\n")
        f.write("set -u\nmkdir -p corpus/_raw\n")
        for item in alvo:
            nome = slug(item["titulo"]) + ".html"
            f.write(
                'curl -sSL --compressed -A "Mozilla/5.0 (X11; Linux x86_64)" '
                f'--retry 3 --max-time 120 "{item["url_arquivo"]}" '
                f'-o "corpus/_raw/{nome}"\nsleep 2\n'
            )
        f.write('\necho "[ok] baixado. Agora:"\n')
        f.write("python3 scripts/montar_corpus.py --somente sites\n")
    destino.chmod(0o755)
    log(f"[wayback] lista gerada: {destino.relative_to(RAIZ)} ({len(alvo)} URLs)")
    return destino


def baixar_wayback(prioridades: set[str]) -> None:
    linhas = _carregar_csv("artigos.csv")
    if not linhas:
        return
    alvo = [
        l for l in linhas
        if (l.get("prioridade") or "P2").upper() in prioridades
        and l.get("url_arquivo")
    ]
    log(f"[wayback] {len(alvo)} documentos em {sorted(prioridades)}")
    baixados = 0
    falhas_tls = 0
    for item in alvo:
        tipo = (item.get("tipo") or "artigo").strip()
        subpasta = {
            "apostila": "apostilas",
            "trecho_livro": "livros",
            "livro": "livros",
            "entrevista": "entrevistas",
            "discurso": "artigos",
        }.get(tipo, "artigos")
        saida = CORPUS / subpasta / (slug(item["titulo"]) + ".txt")
        if saida.exists() and saida.stat().st_size > 800:
            continue
        url = item["url_arquivo"]
        log(f"[wayback] {item['titulo'][:60]}")
        try:
            bruto = get(url, timeout=90, tentativas=2)
        except RuntimeError as exc:
            if "SSL" in str(exc) or "TLS" in str(exc):
                falhas_tls += 1
            log(f"  ! {exc}")
            continue
        # o Wayback devolve HTML de erro com 200 às vezes
        if b"Page Not Found" in bruto[:4000] or b"P\xc3\xa1gina N\xc3\xa3o Encontrada" in bruto[:4000]:
            log("  ! página não encontrada no snapshot")
            continue
        corpo = texto_de_html(bruto)
        cabeçalho = [
            item["titulo"],
            f"fonte: {item.get('fonte', 'olavodecarvalho.org')}",
            f"ano: {item.get('ano', 's/d')}",
            f"url: {item.get('url_original', '')}",
        ]
        if escrever(saida, cabeçalho, corpo):
            baixados += 1
        time.sleep(1.2)  # Wayback pede ritmo baixo
    log(f"[wayback] {baixados} documentos novos")
    if falhas_tls:
        log(
            f"[wayback] atenção: {falhas_tls} URLs falharam por TLS/rede fechada "
            "neste ambiente."
        )
        gerar_lista_wget(prioridades)
        log("  Rode o script gerado na sua máquina e depois: montar_corpus.py --somente sites")


# ---------------------------------------------------------------------------
# fonte 3: áudio do COF no Internet Archive
# ---------------------------------------------------------------------------
def baixar_cof_audio(aulas: list[int], formato: str = "mp3") -> None:
    MIDIA.mkdir(parents=True, exist_ok=True)
    log("[cof-audio] consultando metadados de COFemAudio...")
    try:
        meta = json.loads(get("https://archive.org/metadata/COFemAudio", timeout=120))
    except RuntimeError as exc:
        log(f"  ! {exc}")
        return
    arquivos = {f["name"]: f for f in meta.get("files", [])}
    for n in aulas:
        nome = f"COF{n:03d}.{formato}"
        if nome not in arquivos:
            log(f"  ! {nome} não existe no item")
            continue
        saida = MIDIA / nome
        if saida.exists() and saida.stat().st_size > 1_000_000:
            continue
        url = f"https://archive.org/download/COFemAudio/{urllib.parse.quote(nome)}"
        log(f"[cof-audio] {nome} (~{int(arquivos[nome]['size']) // 1_000_000} MB)")
        try:
            dados = get(url, timeout=900, tentativas=2)
        except RuntimeError as exc:
            log(f"  ! {exc}")
            continue
        saida.write_bytes(dados)
        log(f"  ok {saida.relative_to(RAIZ)}")
    log(f"[cof-audio] áudios em {MIDIA.relative_to(RAIZ)} — agora:")
    log("  python3 scripts/montar_corpus.py --somente audio --whisper local")


# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--fonte", choices=["cof-github", "wayback", "cof-audio"], required=True)
    p.add_argument("--prioridade", default="P0", help="P0, P1, P2 (lista separada por vírgula)")
    p.add_argument("--aulas", nargs="*", type=int, help="números de aula do COF")
    p.add_argument("--todas", action="store_true", help="cof-github: incluir pendentes também")
    p.add_argument("--limite", type=int, default=0)
    args = p.parse_args()

    if args.fonte == "cof-github":
        baixar_cof_github(args.aulas, args.todas)
    elif args.fonte == "wayback":
        prios = {x.strip().upper() for x in args.prioridade.split(",")}
        baixar_wayback(prios)
    else:
        aulas = args.aulas or [1, 147, 219]
        if args.limite:
            aulas = aulas[: args.limite]
        baixar_cof_audio(aulas)

    total = sum(1 for _ in CORPUS.rglob("*.txt")) if CORPUS.exists() else 0
    log(f"\n[ok] corpus: {total} arquivos .txt")
    if total:
        log("Agora: python -m agente_olavo ingest")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
