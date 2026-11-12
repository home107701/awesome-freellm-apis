#!/usr/bin/env bash
# Fase 2 — baixar áudios/vídeos de um canal ou playlist do YouTube.
#
#   ./01_baixar_youtube.sh "https://www.youtube.com/@canal" audios/
#
# Requer: yt-dlp (pip install -U yt-dlp), ffmpeg.
# Use apenas conteúdo que você tem direito de baixar. Ver AVISO no README.
set -euo pipefail
URL="${1:?uso: $0 <url-do-canal-ou-playlist> <pasta-saida> [limite]}"
SAIDA="${2:-audios}"
LIMITE="${3:-}"
mkdir -p "$SAIDA"

ARGS=(
  --extract-audio --audio-format mp3 --audio-quality 5
  --output "$SAIDA/%(upload_date)s-%(id)s-%(title).80s.%(ext)s"
  --write-info-json          # metadados: título, data, URL, descrição
  --download-archive "$SAIDA/.baixados.txt"
  --ignore-errors
  --no-overwrites
)
[[ -n "$LIMITE" ]] && ARGS+=(--playlist-end "$LIMITE")

yt-dlp "${ARGS[@]}" "$URL"
echo "[ok] áudios em $SAIDA — total: $(find "$SAIDA" -name '*.mp3' | wc -l)"
