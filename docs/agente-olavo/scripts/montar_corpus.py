#!/usr/bin/env python3
"""Fase 2 — montar o corpus a partir de três fontes:

  1. `midia/`      (áudios/vídeos baixados do YouTube)      -> Whisper -> transcricoes/
  2. `data/*.csv`  (planilhas de artigos: url,titulo,data)   -> scraping -> artigos/
  3. `data/*.pdf|epub|docx` (livros)                         -> extração -> livros/

Uso típico:
    export GROQ_API_KEY=...        # opcional: transcrição via API (rápida)
    python scripts/montar_corpus.py --whisper local
    python scripts/montar_corpus.py --somente sites --limite 50

Pré-requisitos (instale só o que for usar):
    pip install faster-whisper requests beautifulsoup4 trafilatura pypdf
    apt install ffmpeg poppler-utils
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.robotparser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CORPUS = RAIZ / "corpus"
MIDIA = RAIZ / "midia"
DATA = RAIZ / "data"
UA = ("Mozilla/5.0 (compatible; corpus-builder/1.0; "
      "+https://github.com/open-home/awesome-freellm-apis)")


def log(msg: str) -> None:
    print(msg, flush=True)


def slug(texto: str, limite: int = 70) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto[:limite] or "sem-titulo"


# ---------------------------------------------------------------------------
# 1. LIVROS (pdf / epub / docx)
# ---------------------------------------------------------------------------
def extrair_livros() -> None:
    destino = CORPUS / "livros"
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = [p for p in DATA.glob("*") if p.suffix.lower() in
                {".pdf", ".epub", ".docx", ".odt", ".rtf", ".txt", ".md"}]
    if not arquivos:
        log("[livros] nada em data/ (.pdf .epub .docx ...)")
        return
    for arq in arquivos:
        saida = destino / (slug(arq.stem) + ".txt")
        if saida.exists() and saida.stat().st_size > 1000:
            continue
        ext = arq.suffix.lower()
        log(f"[livros] {arq.name}")
        if ext == ".pdf":
            _pdf(arq, saida)
        elif ext in {".epub", ".docx", ".odt", ".rtf"}:
            _pandoc(arq, saida)
        else:
            shutil.copy(arq, saida)
        if saida.exists():
            _limpar(saida)


def _pdf(arq: Path, saida: Path) -> None:
    if shutil.which("pdftotext"):
        subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(arq), str(saida)],
            check=False,
        )
    else:
        try:
            from pypdf import PdfReader  # noqa: PLC0415

            texto = "\n\n".join(
                (p.extract_text() or "") for p in PdfReader(str(arq)).pages
            )
            saida.write_text(texto, "utf-8")
        except Exception as exc:  # noqa: BLE001
            log(f"  ! falha pypdf: {exc}")
            return
    if saida.exists() and saida.stat().st_size < 3000:
        log("  ! pouco texto extraído — PDF provavelmente digitalizado (rode OCR)")
        if shutil.which("ocrmypdf"):
            tmp = Path("/tmp/_ocr.pdf")
            subprocess.run(
                ["ocrmypdf", "-l", "por", "--force-ocr", str(arq), str(tmp)],
                check=False,
                capture_output=True,
            )
            if tmp.exists():
                subprocess.run(
                    ["pdftotext", "-layout", str(tmp), str(saida)], check=False
                )


def _pandoc(arq: Path, saida: Path) -> None:
    if shutil.which("pandoc"):
        subprocess.run(
            ["pandoc", str(arq), "-t", "plain", "--wrap=none", "-o", str(saida)],
            check=False,
        )
    else:
        log("  ! pandoc não instalado")


def _limpar(caminho: Path) -> None:
    """Remove numeração de página, cabeçalhos repetidos e hifenização."""
    linhas = caminho.read_text("utf-8", errors="replace").splitlines()
    vistos: dict[str, int] = {}
    saida = []
    for linha in linhas:
        s = linha.strip()
        if re.fullmatch(r"\d{1,4}", s):
            continue
        if 3 < len(s) < 70:
            vistos[s] = vistos.get(s, 0) + 1
            if vistos[s] > 8:
                continue
        saida.append(linha)
    texto = "\n".join(saida)
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    caminho.write_text(texto, "utf-8")


# ---------------------------------------------------------------------------
# 2. SITES / ARTIGOS (via CSV)
# ---------------------------------------------------------------------------
def _permitido(url: str, cache: dict) -> bool:
    partes = urllib.parse.urlsplit(url)
    base = f"{partes.scheme}://{partes.netloc}"
    if base not in cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base + "/robots.txt")
        try:
            rp.read()
        except Exception:  # noqa: BLE001
            return True  # sem robots acessível: seguir com cautela
        cache[base] = rp
    try:
        return cache[base].can_fetch(UA, url)
    except Exception:  # noqa: BLE001
        return True


def _html_para_texto(html: str) -> str:
    """Extração de texto sem dependências (fallback do trafilatura)."""
    html = re.sub(r"(?is)<(script|style|noscript|nav|footer)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</h[1-6]>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    import html as h  # noqa: PLC0415

    texto = h.unescape(html)
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    texto = re.sub(r"\n\s*\n\s*\n+", "\n\n", texto)
    return "\n".join(l.strip() for l in texto.splitlines()).strip()


def processar_htmls_baixados() -> None:
    """Converte `corpus/_raw/*.html` (baixados à parte, ex.: pelo wget) em texto.

    O Wayback serve a página original em `id_`, então dá para extrair o corpo
    do artigo. Se `trafilatura` estiver instalada, usa; senão cai no parser
    simples — suficiente para páginas .htm dos anos 2000, que são HTML puro.
    """
    origem = CORPUS / "_raw"
    if not origem.exists():
        return
    arquivos = sorted(origem.glob("*.htm*"))
    if not arquivos:
        return
    log(f"[html] {len(arquivos)} arquivos em corpus/_raw")
    destino = CORPUS / "artigos"
    destino.mkdir(parents=True, exist_ok=True)
    try:
        import trafilatura  # noqa: PLC0415

        usar_trafilatura = True
    except ImportError:
        usar_trafilatura = False
    for arq in arquivos:
        saida = destino / (arq.stem + ".txt")
        if saida.exists() and saida.stat().st_size > 800:
            continue
        bruto = arq.read_text("utf-8", errors="replace")
        texto = ""
        if usar_trafilatura:
            texto = trafilatura.extract(bruto, favor_recall=True) or ""
        if len(texto) < 600:
            texto = _html_para_texto(bruto)
        if len(texto) < 600:
            log(f"[html] ! texto curto: {arq.name}")
            continue
        saida.write_text(f"# {arq.stem}\n# fonte: web.archive.org (espelho)\n\n{texto}", "utf-8")
        log(f"[html] ok {saida.name} ({len(texto)} chars)")


def extrair_sites(limite: int = 0, delay: float = 1.5) -> None:
    processar_htmls_baixados()
    try:
        import requests
        import trafilatura
    except ImportError:
        log("[sites] requests/trafilatura ausentes — só processei corpus/_raw")
        return

    destino = CORPUS / "artigos"
    destino.mkdir(parents=True, exist_ok=True)
    manifestos = sorted(DATA.glob("*.csv")) + sorted(DATA.glob("*.jsonl"))
    if not manifestos:
        log("[sites] nada em data/ (*.csv com coluna url, ou *.jsonl)")
        return

    urls: list[dict] = []
    for man in manifestos:
        if man.suffix == ".csv":
            with man.open(encoding="utf-8", newline="") as f:
                urls += list(csv.DictReader(f))
        else:
            urls += [json.loads(l) for l in man.read_text("utf-8").splitlines() if l.strip()]

    if limite:
        urls = urls[:limite]
    cache_robots: dict = {}
    feitos = extraidos = 0
    for item in urls:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        alvo = destino / (slug(item.get("titulo") or url) + ".txt")
        if alvo.exists():
            continue
        if not _permitido(url, cache_robots):
            log(f"[sites] robots.txt proíbe: {url}")
            continue
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            log(f"[sites] ! {url}: {exc}")
            continue
        texto = trafilatura.extract(
            resp.text, include_comments=False, include_tables=False, favor_recall=True
        ) or ""
        feitos += 1
        if len(texto) < 600:
            log(f"[sites] ! texto curto ({len(texto)} chars): {url}")
            continue
        cabecalho = (
            f"# {item.get('titulo') or 'Sem título'}\n"
            f"# fonte: {url}\n"
            f"# data: {item.get('data', 's/d')} | veículo: {item.get('veiculo', 's/i')}\n\n"
        )
        alvo.write_text(cabecalho + texto, "utf-8")
        extraidos += 1
        log(f"[sites] ok ({len(texto)} chars) {url}")
        time.sleep(delay)  # seja educado; respeite o servidor

    log(f"[sites] {extraidos} artigos extraídos de {feitos} tentativas")


# ---------------------------------------------------------------------------
# 3. TRANSCRIÇÃO (áudio/vídeo)
# ---------------------------------------------------------------------------
def transcrever(backend: str, limite: int = 0) -> None:
    destino = CORPUS / "transcricoes"
    destino.mkdir(parents=True, exist_ok=True)
    midias = [p for p in sorted(MIDIA.rglob("*"))
              if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".mp4", ".mkv", ".webm", ".opus"}]
    if limite:
        midias = midias[:limite]
    if not midias:
        log("[audio] nada em midia/ — rode scripts/01_baixar_youtube.sh")
        return
    log(f"[audio] {len(midias)} arquivos, backend={backend}")

    if backend == "local":
        try:
            from faster_whisper import WhisperModel  # noqa: PLC0415
        except ImportError:
            sys.exit("pip install faster-whisper  (ou use --whisper groq)")
        modelo = WhisperModel(
            os.getenv("WHISPER_MODEL", "large-v3"),
            device=os.getenv("WHISPER_DEVICE", "auto"),
            compute_type="int8",
        )
        for arq in midias:
            alvo = destino / (slug(arq.stem) + ".txt")
            if alvo.exists():
                continue
            log(f"[audio] -> {arq.name}")
            segmentos, info = modelo.transcribe(
                str(arq), language="pt", vad_filter=True, beam_size=5,
                condition_on_previous_text=False,
            )
            with alvo.open("w", encoding="utf-8") as f:
                f.write(f"# {arq.stem}\n# idioma: {info.language}\n\n")
                buffer = []
                for s in segmentos:
                    buffer.append(s.text.strip())
                    if len(" ".join(buffer)) > 1200:
                        f.write(" ".join(buffer) + "\n\n")
                        buffer = []
                if buffer:
                    f.write(" ".join(buffer) + "\n")
    else:  # groq
        chave = os.getenv("GROQ_API_KEY", "")
        if not chave:
            sys.exit("defina GROQ_API_KEY ou use --whisper local")
        for arq in midias:
            alvo = destino / (slug(arq.stem) + ".txt")
            if alvo.exists():
                continue
            if arq.stat().st_size > 24_000_000:
                log(f"[audio] ! {arq.name} > 25 MB — divida com ffmpeg antes")
                continue
            log(f"[audio] -> {arq.name} (groq)")
            cmd = [
                "curl", "-sS", "https://api.groq.com/openai/v1/audio/transcriptions",
                "-H", f"Authorization: Bearer {chave}",
                "-F", f"file=@{arq}", "-F", "model=whisper-large-v3",
                "-F", "language=pt", "-F", "response_format=text",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode or len(r.stdout) < 200:
                log(f"  ! falha: {r.stderr[:200]}")
                continue
            alvo.write_text(f"# {arq.stem}\n\n# --- trecho inicial omitido ---\n", "utf-8")
            alvo.write_text(f"# {arq.stem}\n\n{r.stdout}", "utf-8")
            log(f"  ok ({len(r.stdout)} chars)")


# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--somente", choices=["livros", "sites", "audio", "limpeza"])
    p.add_argument("--whisper", choices=["local", "groq"], default="local")
    p.add_argument("--limite", type=int, default=0, help="máx. de itens por fonte")
    p.add_argument("--delay", type=float, default=1.5, help="pausa entre requisições")
    args = p.parse_args()

    CORPUS.mkdir(exist_ok=True)
    if args.somente in (None, "livros"):
        extrair_livros()
    if args.somente in (None, "sites"):
        extrair_sites(args.limite, args.delay)
    if args.somente in (None, "audio"):
        transcrever(args.whisper, args.limite)
    if args.somente in (None, "limpeza"):
        n = 0
        for t in CORPUS.rglob("*.txt"):
            _limpar(t)
            n += 1
        log(f"[limpeza] {n} arquivos normalizados")

    total = sum(1 for _ in CORPUS.rglob("*.txt"))
    log(f"\n[ok] corpus com {total} arquivos .txt em {CORPUS}")
    log("Agora: python -m agente_olavo ingest --embeddings")


if __name__ == "__main__":
    main()
