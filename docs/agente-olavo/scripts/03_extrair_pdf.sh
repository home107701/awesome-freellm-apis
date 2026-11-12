#!/usr/bin/env bash
# Fase 2 — extrair texto de PDFs/EPUBs para a pasta do corpus.
#
#   ./03_extrair_pdf.sh livros/ corpus/livros/
#
# Requer: poppler-utils (pdftotext) e, opcionalmente, ocrmypdf + tesseract
# para PDFs digitalizados (imagem), e pandoc para epub.
set -euo pipefail
ENTRADA="${1:?uso: $0 <pasta-entrada> <pasta-saida>}"
SAIDA="${2:?}"
mkdir -p "$SAIDA"

for f in "$ENTRADA"/*; do
  base="$(basename "${f%.*}")"
  destino="$SAIDA/$base.txt"
  [[ -f "$destino" ]] && continue
  case "${f,,}" in
    *.pdf)
      pdftotext -layout -enc UTF-8 "$f" "$destino"
      # se saiu quase vazio, provavelmente é digitalizado -> OCR
      if [[ $(wc -c < "$destino") -lt 2000 ]]; then
        echo "[ocr] $f"
        ocrmypdf -l por --force-ocr "$f" /tmp/ocr.pdf 2>/dev/null && \
          pdftotext -layout /tmp/ocr.pdf "$destino"
      fi
      ;;
    *.epub)
      pandoc "$f" -t plain -o "$destino"
      ;;
    *.docx|*.odt|*.rtf)
      pandoc "$f" -t plain -o "$destino"
      ;;
    *) continue ;;
  esac
  echo "[ok] $base -> $(wc -c < "$destino") bytes"
done

# higiene: numeração de página órfã, cabeçalhos repetidos, hifenização
find "$SAIDA" -name '*.txt' -print0 | while IFS= read -r -d '' t; do
  python3 - "$t" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
linhas = p.read_text("utf-8", errors="replace").splitlines()
saida, vistos = [], {}
for l in linhas:
    s = l.strip()
    if re.fullmatch(r"\d{1,4}", s):        # página sozinha
        continue
    if 3 < len(s) < 70:                    # cabeçalho repetido
        vistos[s] = vistos.get(s, 0) + 1
        if vistos[s] > 8:
            continue
    saida.append(l)
texto = "\n".join(saida)
texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)   # hifenização quebrada
texto = re.sub(r"\n{3,}", "\n\n", texto)
p.write_text(texto, "utf-8")
PY
done
echo "[ok] corpus limpo em $SAIDA"
