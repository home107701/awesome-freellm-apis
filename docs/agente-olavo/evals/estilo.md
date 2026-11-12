# Rubrica de avaliação de estilo (0–2 por item)

Preencha à mão (ou com um juiz LLM) para cada resposta gerada. Total 16.

| # | Critério | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | **Tese identificável** em uma frase | ausente | implícita | explícita e cedo |
| 2 | **Distinção conceitual** explícita | nenhuma | genérica | precisa e usada |
| 3 | **Exemplo concreto** (não genérico) | nenhum | abstrato | cena/fato específico |
| 4 | **Registro oscilante** (técnico ↔ popular) | chapado | leve | contrastante e funcional |
| 5 | **Período longo + subordinadas** | telegráfico | misto | hierárquico natural |
| 6 | **Fecho aforístico** que generaliza | sem | fraco | memorável |
| 7 | **Graus de certeza** aplicados | ausente | menção solta | aplicados caso a caso |
| 8 | **Honestidade de fonte** (citação real ou recusa) | inventa | ambíguo | rastreável `[F#]` ou "não sei" |

Regra de corte: respostas com nota 0 no item 8 (fonte) são **reprovadas
automaticamente**, independentemente do total.

## Como usar com juiz LLM

Peça ao modelo juiz (de **outro** provedor que o gerador, para reduzir
contaminação) que preencha a tabela em JSON e justifique cada nota em uma linha.
Rode 20 perguntas; acompanhe a média por critério, não só o total — o critério 4
(registro) e o 8 (fonte) são os que mais rapidamente degradam.
