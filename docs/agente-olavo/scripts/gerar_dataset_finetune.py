#!/usr/bin/env python3
"""Fase 5 (opcional) — gerar dataset de fine-tune por destilação.

Estratégia: usa o próprio agente (RAG + persona) como "professor" para escrever
respostas ancoradas em trechos reais do corpus, e grava pares no formato
chat (JSONL) para fine-tune de um modelo menor.

⚠️ Leia antes de usar:
  * Isto NÃO transmite conhecimento novo ao modelo — transmite *estilo* e
    *procedimento*. Conhecimento continua vindo do RAG.
  * Revise 5–10% das amostras à mão. Destilação sem revisão copia alucinação
    em escala industrial.
  * Para 1.500 amostras boas, um LoRA em 7–8B treina em 1 GPU de 16 GB.

Uso:
    python scripts/gerar_dataset_finetune.py --n 300 --saida data/finetune.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agente_olavo import llm  # noqa: E402
from agente_olavo.agente import AgenteOlavo  # noqa: E402
from agente_olavo.config import AgentConfig  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

TIPOS_PERGUNTA = [
    "Explique, em termos precisos, a tese central deste trecho.",
    "Que erro de raciocínio este trecho está denunciando? Dê nome ao vício.",
    "Reescreva o argumento deste trecho como um ensaio curto, mantendo o rigor.",
    "Em que grau de certeza está a afirmação principal deste trecho? Justifique.",
    "Responda a uma objeção séria a este argumento, e depois refute a objeção.",
    "Aplique a distinção feita neste trecho a um exemplo atual do debate público.",
    "Qual pressuposto não examinado sustenta este trecho? Exponha-o.",
    "Resuma este trecho em uma única frase aforística.",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=200, help="número de amostras")
    p.add_argument("--saida", default="data/finetune.jsonl")
    p.add_argument("--min-score", type=float, default=0.8)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    random.seed(args.seed)
    cfg = AgentConfig()
    agente = AgenteOlavo(cfg)
    agente.carregar_indice()

    # só chunks com contexto substancial viram semente
    sementes = [c for c in agente.indice.chunks if len(c.texto) > 600]
    random.shuffle(sementes)
    if not sementes:
        sys.exit("índice vazio ou sem chunks longos — rode o ingest primeiro")

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    escritas = 0
    with saida.open("w", encoding="utf-8") as f:
        for i, chunk in enumerate(sementes):
            if escritas >= args.n:
                break
            pergunta = random.choice(TIPOS_PERGUNTA)
            entrada = (
                f"{pergunta}\n\nTrecho de {chunk.titulo} ({chunk.tipo}):\n"
                f'"""\n{chunk.texto[:2500]}\n"""'
            )
            try:
                resposta = llm.chat(
                    [
                        {"role": "system", "content": agente.system},
                        {"role": "user", "content": entrada},
                    ],
                    cfg.llm,
                    temperature=0.8,
                )
            except llm.LLMError as exc:
                print(f"[!] {exc}")
                continue
            # filtro de qualidade mínimo
            if len(resposta) < 400 or "[F" in resposta and "[F1]" not in resposta:
                continue
            amostra = {
                "messages": [
                    {"role": "system", "content": agente.system},
                    {"role": "user", "content": entrada},
                    {"role": "assistant", "content": resposta},
                ],
                "meta": {
                    "doc": chunk.caminho,
                    "titulo": chunk.titulo,
                    "tipo": chunk.tipo,
                },
            }
            f.write(json.dumps(amostra, ensure_ascii=False) + "\n")
            escritas += 1
            if escritas % 25 == 0:
                print(f"  {escritas} amostras...", flush=True)

    print(f"[ok] {escritas} amostras em {saida}")
    print("Revise uma amostragem manual antes de treinar.")


if __name__ == "__main__":
    main()
