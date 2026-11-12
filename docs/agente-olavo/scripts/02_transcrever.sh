#!/usr/bin/env bash
# Fase 2 — transcrever os áudios com Whisper local (faster-whisper) ou API.
#
#   ./02_transcrever.sh audios/ transcricoes/
#
# Local (privado, sem custo): pip install faster-whisper
#   modelo "large-v3" em pt-BR; RTX 3060 faz ~10x tempo real.
# API (mais rápido, pago): Groq whisper-large-v3 (~US$0,04/h de áudio).
set -euo pipefail
ENTRADA="${1:-audios}"
SAIDA="${2:-transcricoes}"
mkdir -p "$SAIDA"

transcrever_local() {
  python3 - "$@" <<'PY'
import sys, pathlib
from faster_whisper import WhisperModel
entrada, saida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
modelo = WhisperModel("large-v3", device="auto", compute_type="int8")
for audio in sorted(entrada.glob("*.mp3")):
    destino = saida / (audio.stem + ".txt")
    if destino.exists():
        continue
    print("->", audio.name, flush=True)
    segmentos, info = modelo.transcribe(
        str(audio), language="pt", vad_filter=True,
        beam_size=5, condition_on_previous_text=False,
    )
    with destino.open("w", encoding="utf-8") as f:
        f.write(f"# {audio.stem}\n# idioma={info.language}\n\n")
        for s in segmentos:
            f.write(s.text.strip() + "\n")
PY
}

transcrever_groq() {
  # Requer GROQ_API_KEY. Limite de 25 MB por arquivo: divide antes se preciso.
  python3 - "$@" <<'PY'
import os, pathlib, subprocess, sys, json, urllib.request
entrada, saida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
chave = os.environ.get("GROQ_API_KEY")
if not chave:
    sys.exit("defina GROQ_API_KEY ou use --local")
for audio in sorted(entrada.glob("*.mp3")):
    destino = saida / (audio.stem + ".txt")
    if destino.exists():
        continue
    print("->", audio.name, flush=True)
    comando = [
        "curl", "-sS", "https://api.groq.com/openai/v1/audio/transcriptions",
        "-H", f"Authorization: Bearer {chave}",
        "-F", f"file=@{audio}",
        "-F", "model=whisper-large-v3",
        "-F", "language=pt",
        "-F", "response_format=text",
    ]
    texto = subprocess.run(comando, capture_output=True, text=True, check=True).stdout
    destino.write_text(f"# {audio.stem}\n\n{texto}", encoding="utf-8")
PY
}

if [[ "${TRANSCRICAO:-local}" == "groq" ]]; then
  transcrever_groq "$ENTRADA" "$SAIDA"
else
  transcrever_local "$ENTRADA" "$SAIDA"
fi
echo "[ok] transcrições em $SAIDA"
