"""Teste offline do encanamento (não chama API).

    cd docs/agente-olavo
    python -m agente_olavo ingest --corpus exemplo-corpus
    python tests_smoke.py
"""

import sys

from agente_olavo import llm
from agente_olavo.agente import AgenteOlavo
from agente_olavo.config import AgentConfig

capturado = {}


def fake_chat(messages, cfg, **kw):
    capturado["messages"] = messages
    return "resposta de teste [F1]"


llm.chat = fake_chat

try:
    ag = AgenteOlavo(AgentConfig())
    ag.carregar_indice()
except FileNotFoundError as exc:
    sys.exit(f"{exc}\nRode primeiro: python -m agente_olavo ingest --corpus exemplo-corpus")

r = ag.perguntar("o que é o desenho da ignorância?")
sys_prompt = capturado["messages"][0]["content"]

assert "# <FONTES>" in sys_prompt, "bloco de fontes ausente"
assert "[F1]" in sys_prompt, "nenhuma fonte injetada"
assert "graus de certeza" in sys_prompt.lower(), "KB de certeza ausente"
assert "GUIA DE ESTILO" in sys_prompt, "guia de estilo ausente"
assert "CATÁLOGO DE OBRAS" in sys_prompt, "catálogo de obras ausente"
assert len(r.fontes) >= 1, "nenhuma fonte recuperada"

print("OK — fontes recuperadas:", len(r.fontes))
print("OK — persona, estilo, obras e <FONTES> injetados corretamente.")
