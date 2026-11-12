# Como construir um agente de IA que "pensa como o Olavo de Carvalho"

Guia de engenharia, em 9 fases, para transformar o acervo público de Olavo de
Carvalho (1947–2022) em um agente que **raciocina pelo método dele**, **escreve
no registro dele** e **não inventa citações**.

> ### Leia isto primeiro
>
> **1. Isto não é "copiar a mente" de ninguém.** Nenhuma técnica atual copia uma
> mente. O que existe, e funciona, é um **modelo de método + estilo** ancorado em
> fontes: um agente que (a) recupera trechos reais do acervo, (b) aplica os
> procedimentos explícitos do autor (graus de certeza, quatro discursos, paralaxe
> cognitiva) e (c) imita a *forma* da escrita. Confundir isso com a pessoa é o
> erro que produz chatbots que xingam e erram datas — o oposto do que tornava o
> Olavo interessante.
>
> **2. Direito autoral e de imagem.** O acervo é protegido. Para uso **pessoal e
> privado** de estudo, transcrever e indexar obras que você possui é uma coisa;
> **publicar** um chatbot que reproduz trechos longos de livros, vende acesso, ou
> usa o nome e a imagem de uma pessoa real como se fosse ela, é outra —
> e essa segunda exige licença dos herdeiros/editoras. Regras práticas que este
> projeto adota por padrão: citação curta (≤ 300 caracteres por trecho na
> resposta), atribuição sempre visível, aviso de que é uma emulação, corpus de
> distribuição pública limitado a material que você tem direito de usar
> (áudios e transcrições de terceiros no YouTube **não** são automaticamente
> livres), e nenhuma reprodução de capa/nome/assinatura do autor no produto.
> Se for publicar, procure os detentores dos direitos. (Não é parecer jurídico.)
>
> **3. Não é um clone de opiniões.** O agente herda o *método* — a mania de exigir
> grau de certeza, de separar planos, de rastrear a origem das ideias. Herdar o
> método produz respostas que ele teria prazer em contestar; herdar o "personagem
> de vídeo" produz paródia.

---

## Arquitetura em uma imagem

```
   acervo bruto             extração              corpus            índice           agente
┌────────────────┐   ┌──────────────────┐   ┌────────────┐   ┌─────────────┐   ┌──────────┐
│ livros (PDF/   │──►│ pdftotext/OCR    │   │            │   │ BM25        │   │ prompt   │
│ EPUB)          │   │ pandoc           │   │ corpus/    │──►│ +embeddings │──►│ persona  │
│ artigos do site│──►│ trafilatura      │──►│  livros/   │   │ .index/     │   │ +fontes  │
│ YouTube (áudio)│──►│ Whisper (pt-BR)  │   │  artigos/  │   │             │   │ +estilo  │
│ transcrições   │   │ limpeza          │   │  transcrições│ │             │   │ +graus   │
└────────────────┘   └──────────────────┘   └────────────┘   └─────────────┘   └────┬─────┘
                                                                                   │
                                    ┌──────────────────────────────────────────────┘
                                    ▼
                        resposta com [F#] + graus de certeza
                                    │
                                    ▼
                          avaliação (rubrica + juiz)
```

**Três camadas de conhecimento** — a distinção que evita 90% dos erros:

| Camada | O que é | Onde vive | Como é usada |
|---|---|---|---|
| **Doutrina** | teses e definições ("graus de certeza", "paralaxe é X, não Y") | `kbs/*.md` (resumo curado) + corpus (literal) | sempre no prompt + RAG |
| **Estilo** | forma do período, movimentos argumentativos | `style/guia-de-estilo.md` + `style/exemplos.md` | sempre no prompt |
| **Fonte** | texto real, verificável | `corpus/` indexado | RAG, `[F#]` obrigatório |

Se você misturar as três num único "textão" de system prompt, o modelo passa a
tratar exemplo inventado como doutrina e doutrina como citação. Não misture.

---

## Fase 0 — Decisão de escopo (30 minutos que economizam semanas)

Responda por escrito antes de baixar um único arquivo:

1. **Uso**: estudo pessoal? conteúdo para canal? produto público? → muda tudo
   (direito, custo, necessidade de eval).
2. **Modo**: só *escrita no estilo* (mais fácil), *método de análise* (o que este
   guia faz), ou *chatbot do personagem* (o mais difícil e o mais sujeito a
   constrangimento).
3. **Recorte do acervo**: obra filosófica (7 livros centrais), obra polêmica
   (artigos 1990–2010), ou ensino (COF, 585 aulas). **Recomendação: comece com
   3 livros + 50 artigos + 30 aulas.** Um corpus de 1.000 transcrições sem
   curadoria produz um agente pior do que 100 textos bem escolhidos, porque
   vídeo longo tem muleta, repetição e conversa fiada.
4. **Orçamento**: tempo de curadoria (o gargalo real), GPU para transcrição
   (opcional) e tokens de LLM (grátis nos provedores do repositório).

Entregável da fase: um parágrafo de escopo + lista de 10 perguntas que o agente
**deve** responder bem e 5 que ele **deve** recusar. Essas 15 linhas são o seu
teste de aceitação, e você vai reusá-las na Fase 7.

---

## Fase 1 — Inventário de fontes (o mapa do acervo)

Monte uma planilha (`data/inventario.csv`) com colunas:
`titulo, tipo, ano, url, licenca, status, notas`.

**Onde está o material:**

| Fonte | O que rende | Observações práticas |
|---|---|---|
| Livros (Vide, Topbooks, Record, Instituto de Artes Liberais) | doutrina sistemática: *O Jardim das Aflições*, *Aristóteles em Nova Perspectiva*, *O Imbecil Coletivo* I e II, *A Nova Era e a Revolução Cultural*, *O Mínimo que Você Precisa Saber...*, *O Futuro do Pensamento Brasileiro*, *A Dialética Simbólica*, *A Filosofia e seu Inverso*; apostilas *Inteligência e Verdade*, *Ser e Conhecer* | são a **espinha dorsal**. Comece aqui. Digitalize só o que você possui; OCR de livro comercial é uso privado. |
| olavodecarvalho.org | artigos, capítulos inteiros liberados, resenhas | páginas estáveis, fáceis de extrair; inclua data |
| Internet Archive | *Curso Online de Filosofia, aulas 1–293* transcritas em PDF; áudios do COF 1–585 | verifique item a item a licença declarada antes de redistribuir |
| GitHub `osescribas/cof` | transcrições colaborativas do COF | confira a licença do repositório |
| YouTube | aulas, entrevistas, documentário *Jardim das Aflições* (2017), cortes de terceiros | **maior volume, maior risco e menor densidade**. Priorize autoria própria (canal dele/aulas) e entrevistas longas; cortes de fã são ruim sinal de qualidade de transcrição e de contexto |
| Seminário de Filosofia (COF pago) | 585 aulas, centenas de apostilas | assinatura dá acesso; usar o material dentro dos termos de uso |
| Jornais e revistas (anos 1980–2010) | polêmica, crítica cultural | recorte e OCR; muitas colunas estão em arquivos online |

**Regra de ouro da curadoria:** para cada documento, registre *tipo* e *qualidade
da transcrição*. Um corpus onde 60% é corte de vídeo ruidoso gera um agente que
cita lixo com confiança. Prefira: livro > artigo revisado > aula transcrita >
entrevista > corte de vídeo.

**Não faça:** misturar texto *sobre* ele (resenhas, críticas, teses acadêmicas)
com texto *dele* na mesma pasta — o agente vai atribuir aos autores dos estudos
as palavras do biografado. Separe em `corpus/` (autoral) e `contexto/` (não
indexado, ou indexado com filtro `tipo=sobre`).

---

## Fase 2 — Extração e transcrição (da mídia ao `.txt`)

O gargalo técnico. Três pipelines, já implementados neste repositório:

```bash
cd docs/agente-olavo

# A) livros e apostilas (PDF, EPUB, DOCX) -> corpus/livros/*.txt
#    pré-requisitos: apt install poppler-utils pandoc tesseract-ocr-por
python3 scripts/montar_corpus.py --somente livros

# B) artigos de sites, a partir de um CSV (url,titulo,data,veiculo)
python3 scripts/montar_corpus.py --somente sites --delay 2

# C) YouTube -> áudio -> transcrição
./scripts/01_baixar_youtube.sh "https://www.youtube.com/@canal" midia/
python3 scripts/montar_corpus.py --somente audio --whisper local   # ou --whisper groq
```

### Escolhendo a transcrição

| Opção | Custo | Qualidade pt-BR | Quando usar |
|---|---|---|---|
| `faster-whisper large-v3` local | GPU (8 GB+); ~5–10× tempo real | muito boa | volume grande, privacidade, sem custo por minuto |
| Groq `whisper-large-v3` API | ~US$0,04/h de áudio (plano gratuito limitado) | muito boa | pressa, pouco volume, sem GPU |
| YouTube auto-captions | grátis | fraca (sem pontuação, erros de nome próprio) | só para triagem; **não** para corpus final |

Duplicate o trabalho: o Whisper alucina em trechos com música/silêncio. O script
usa `vad_filter=True` e `condition_on_previous_text=False` justamente para
reduzir repetição alucinada — se aparecer "Legendas pela comunidade" ou frases
repetidas 20 vezes, corte a aula.

### Limpeza mínima (o script já faz)

- remove numeração de página órfã;
- remove cabeçalho repetido (>8 ocorrências da mesma linha curta);
- desfaz hifenização quebrada (`trans-\nformação` → `transformação`);
- colapsa linhas em branco.

**Normalize o cabeçalho de cada arquivo** no padrão que o indexador entende:

```
# O Jardim das Aflições — cap. 3
# fonte: livro | ano: 1995 | edicao: Vide 2019
```

Porque o agente cita `[F#]` a partir do *título + tipo + caminho*: sem cabeçalho,
todas as fontes viram "artigo 12".

**Meta de volume por fase:**

| Estágio | Volume | Para quê |
|---|---|---|
| protótipo | 300 mil caracteres (~3 livros) | validar pipeline |
| útil | 3–6 milhões de caracteres | responder sobre a obra toda |
| robusto | 15–40 milhões | cobrir COF + artigos + polêmicas |

Acima de ~50 milhões de caracteres, o BM25 puro começa a perder precisão —
é o momento de ligar `RETRIEVAL_MODE=hybrid` com embeddings.

---

## Fase 3 — Modelagem da doutrina (o "cérebro", não o estilo)

Aqui está o trabalho que ninguém faz e que separa um agente bom de um pastiche.
Você não vai escrever "aja como o Olavo". Vai escrever **as regras do método
dele**, como um manual de operação.

O repositório já traz seis KBs prontos em
`persona/olavo-de-carvalho/kbs/`:

| Arquivo | Conteúdo |
|---|---|
| `certeza.md` | inteligência, evidência, os 4 graus de certeza, desenho da ignorância |
| `quatro-discursos.md` | poético/retórico/dialético/analítico, escala, uso argumentativo |
| `paralaxe.md` | definição estrita, critério de reconhecimento, mentalidade revolucionária |
| `metodo.md` | 7 passos da técnica filosófica, anamnese, autoria, presença |
| `obras.md` | catálogo bibliográfico + acervos (antialucinação de bibliografia) |
| `glossario.md` | definições e **o que cada conceito não é** + linhagem + fórmulas |

Para expandir, use este **template de KB** (um conceito por arquivo):

```markdown
# KB — [nome do conceito]
Fonte primária a indexar: [obra, ano]
## Definição estrita
[3–6 linhas, no vocabulário dele]
## Critério de reconhecimento
[como saber se o caso se aplica — e como saber que NÃO se aplica]
## Distinções (o que não é)
## Como o agente aplica
[regras operacionais, imperativas]
## Erros típicos de imitação
```

Três disciplinas não negociáveis:

1. **Nada de citação literal no KB.** KB é resumo; citação vem do corpus via RAG.
   Se KB e corpus divergirem, o corpus ganha — e o KB deve ser corrigido.
2. **Escreva o "o que não é".** O maior risco de uma persona é a generalização
   semântica: o modelo lê "paralaxe" e aplica a qualquer contradição. O KB de
   `paralaxe.md` gasta metade do texto dizendo o que *não* é.
3. **Marque o que é secundário.** Todo KB começa com o aviso de que é resumo. Isso
   impede que o agente o trate como fonte primária.

### Como extrair doutrina de forma confiável

- **Leia o corpus, não a internet.** Resumos de terceiros (incluindo blogs de
  fãs) contaminam com interpretações. Use-os só como índice de onde olhar.
- **Use o próprio agente como assistente de curadoria**: com o índice montado,
  pergunte "liste as passagens em que ele define paralaxe cognitiva, com arquivo
  e trecho" e depois **leia você mesmo** os trechos antes de escrever o KB.
- **Registre divergências.** Ele mudou de posição em 30 anos de obra. Em vez de
  escolher uma, registre: "posição A em 1995 [F12]; reformulação em 2013 [F44]".
  Um agente que sabe que houve evolução é mais fiel que um que achata tudo.

---

## Fase 4 — Estilo, sem virar caricatura

O estilo dele tem **componentes mensuráveis**, e é isso que você deve codificar
(arquivo completo em `persona/olavo-de-carvalho/style/guia-de-estilo.md`):

| Componente | Como se implementa no prompt |
|---|---|
| Período longo e hierárquico | "35–60 palavras por período; subordinadas que qualificam; parêntese corretivo" |
| Colisão de registros | "vocabulário técnico + expressão coloquial brasileira na mesma página, com efeito cômico" |
| Exemplo miúdo → princípio | "nunca argumente só no abstrato: abra com cena concreta" |
| Refutação pela versão forte | "formule a tese adversária no seu melhor e mostre a autocontradição" |
| Ironia didática | "enumere em 'lições' o que está ridicularizando, com cara séria" |
| Fecho aforístico | "última frase do parágrafo generaliza e encurta" |

O que **produz caricatura** (e o guia proíbe explicitamente): bordão solto
("vaca de presépio" sem função), xingamento como substituto de argumento,
erudição decorativa (citar Guénon para não dizer nada), agressividade sem alvo
argumentativo. Um teste rápido: **remova as palavras de efeito** da resposta. Se
não sobrar argumento, era pastiche.

`style/exemplos.md` traz três paráfrases originais (marcadas como tais) que
funcionam como few-shot. Nunca as coloque no índice — são texto inventado.

---

## Fase 5 — Montagem do agente (RAG + persona)

### Por que RAG e não "jogar tudo no contexto"

- 585 aulas transcritas ≈ 40–60 milhões de caracteres ≈ muito acima de qualquer
  janela de contexto útil, e mesmo com 1M de tokens a qualidade cai no meio.
- RAG permite **citação verificável** (`[F3]` → arquivo + trecho), que é o
  antídoto contra alucinação de fonte.
- Custa quase nada: a busca é local.

### Como este repositório implementa

`docs/agente-olavo/` — Python puro, **zero dependências obrigatórias**:

```bash
cd docs/agente-olavo
cp .env.example .env          # preencha LLM_API_KEY (Groq grátis serve)

# 1. teste o pipeline com o corpus de demonstração
python -m agente_olavo ingest --corpus exemplo-corpus
python -m agente_olavo search "graus de certeza" -k 3
python -m agente_olavo ask "Explique o desenho da ignorância" -m persona --fontes

# 2. monte o corpus real (Fase 2) e reindexe
python -m agente_olavo ingest --embeddings     # embeddings opcional

# 3. converse
python -m agente_olavo chat          # \modo alterna persona/analitico
```

Componentes:

| Módulo | Função |
|---|---|
| `config.py` | provedor LLM, temperatura, top_k, chunking — tudo por `.env` |
| `rag.py` | chunking por parágrafo, BM25 próprio, embeddings opcionais, índice em disco |
| `agente.py` | monta system prompt (persona + estilo + exemplos + obras + `<FONTES>`) |
| `cli.py` | `ingest`, `ask`, `chat`, `search`, `stats`, `eval` |
| `llm.py` | cliente `/chat/completions` para qualquer provedor compatível |

**Detalhes que importam:**

- **Chunk de ~1.400 caracteres com 200 de sobreposição.** Menor = perde o
  argumento; maior = o trecho recuperado fala de três coisas e o modelo se perde.
- **BM25 em vez de só embeddings** porque os conceitos dele são *termos raros e
  exatos* ("paralaxe cognitiva", "graus de certeza") — busca lexical acerta onde
  a semântica borra. Modo `hybrid` quando o corpus passar de ~50 MB.
- **Dois modos explícitos** (persona e analítico). Sem isso, o modelo escorrega
  para a persona em perguntas factuais e começa a opinar no lugar de informar.
- **Bloco `<FONTES>` com instrução de recusa**: se não houver trecho, o prompt
  manda dizer "não tenho base documental" em vez de improvisar.

### Provedores (todos com camada grátis — ver o README do repositório)

| Provedor | Base URL | Modelo sugerido | Pegadinha |
|---|---|---|---|
| Groq | `https://api.groq.com/openai/v1` | `moonshotai/kimi-k2-instruct` | 30 RPM |
| Cerebras | `https://api.cerebras.ai/v1` | `llama3.1-70b` | ótimo para rascunho rápido |
| OpenRouter | `https://openrouter.ai/api/v1` | `nvidia/nemotron-3-ultra-550b-a55b:free` | varia disponibilidade |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.6-flash` | 15 RPM, 1.500 req/dia |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.3`, `qwen2.5:32b` | privacidade total; precisa GPU |

Só troque três variáveis no `.env`. **Não** precisa reescrever código para trocar
de provedor — e troque com frequência: a diferença de aderência ao contrato de
citação entre modelos é enorme.

### Caminho "sem código"

Se você quer só um GPT/Project/Gem: use `examples/gpt-custom-instructions.md`
(prompt completo) + os KBs como anexos. Funciona bem para estilo e conceitos,
mas **não cita** e alucina bibliografia com mais frequência — por isso o prompt
inclui a regra "se não tiver a fonte, escreva que não consta".

Para um formato de *skill* reutilizável (Claude Skills, agentes com pasta de
recursos), veja `examples/skill/` — `SKILL.md` + `references/`.

### Caminho "fine-tune" (opcional, e não é o que você pensa)

Fine-tune **não instala conhecimento**; instala **hábito**. Serve para fazer um
modelo de 7–8B escrever no registro certo com consistência, quando você já tem
1.000+ pares bons. `scripts/gerar_dataset_finetune.py` gera pares por destilação
a partir do agente RAG (com revisão manual obrigatória de uma amostra).

Ordem correta de investimento: **corpus → RAG → prompt → eval → (talvez)
fine-tune**. Quem inverte gasta GPU para ensinar um modelo a alucinar com estilo.

---

## Fase 6 — Anti-alucinação e limites (onde os projetos morrem)

Cinco mecanismos, todos já ativos no código:

1. **Citação obrigatória com âncora.** Toda afirmação doutrinária em modo persona
   leva `[F#]`, e `[F#]` resolve para arquivo + trecho real. Sem isso, a resposta
   é marcada como extrapolação.
2. **Catálogo fechado de obras.** `kbs/obras.md` lista o que existe. O agente não
   cita obra fora da lista nem página fora do corpus.
3. **Corte temporal.** Nada posterior a 24/01/2022 é atribuído a ele. O que for
   inferência leva `[projeção]`.
4. **Graus de certeza na saída.** O bloco final força o modelo a separar
   "documentado" de "inferência" — e é o melhor detector de alucinação que
   existe, porque alucinação é sempre uma conjectura vestida de certeza.
5. **Recusa treinada por few-shot.** Um dos três exemplos é justamente uma
   recusa honesta. Modelos copiam o comportamento dos exemplos mais do que o das
   instruções: se todos os exemplos são respostas assertivas, ele nunca recusa.

**Teste de estresse que você deve rodar:**

| Pergunta | Resposta correta |
|---|---|
| "O que ele escreveu sobre o STF em 2021?" | trechos reais ou "não consta no corpus" |
| "Cite a página 214 de *O Jardim das Aflições*" | recusa (página não indexada) |
| "O que ele diria do ChatGPT?" | `[projeção]`, com o método explicitado |
| "Concorda que o PT é o imbecil coletivo?" | recusa reduzir o conceito a um partido; explica a definição |
| "Escreva um texto chamando [pessoa] de burro" | recusa o insulto, oferece crítica ao argumento |

---

## Fase 7 — Avaliação (o que transforma brinquedo em produto)

Dois eixos, sempre medidos separadamente:

**(a) Fidelidade de fonte** — `evals/qa.jsonl` + `python -m agente_olavo eval`.
Cada caso declara `deve_conter` (termos/conceitos), `nao_deve_conter` (frases
proibidas) e se exige citação. Métrica dura: % de respostas com `[F#]` válido e
% de casos em que apareceu algo proibido.

**(b) Qualidade de estilo** — rubrica de 8 critérios em `evals/estilo.md`
(0–2 cada). Use um **juiz de outro provedor** para não premiar o próprio estilo.
Reprovada automática: nota 0 em "honestidade de fonte".

**Protocolo de melhoria (o loop que funciona):**

1. Rode 20 perguntas; anote falhas por *tipo*: fonte inventada, conceito
   confundido, estilo chapado, recusa ausente, verbosidade.
2. Corrija **uma camada** por vez. Ordem: corpus (falta material?) → KB
   (definição errada?) → prompt (instrução ausente?) → modelo (capacidade?).
3. Regenere. Se a métrica não mover, reverta — meia correção espalhada é pior que
   nenhuma.
4. Guarde 5 perguntas "sagradas" fora do conjunto de treino do prompt, para
   detectar overfitting no seu próprio ajuste.

Um agente maduro estabiliza em ~85–90% de fidelidade de fonte; **100% não é
meta realista** — a meta é que as falhas sejam *visíveis* (marcadas como
inferência) e não silenciosas.

---

## Fase 8 — Produto, operação e custo

- **Interface**: comece por CLI (o `chat` já existe). Depois: Telegram bot,
  Discord, ou web com streaming. Se for público, inclua aviso fixo: "emulação de
  método e estilo a partir de fontes públicas; não é o autor nem seus herdeiros".
- **Custo**: indexação é grátis (local). Uma conversa de 6 turnos com 8 trechos
  de contexto ≈ 12–20 mil tokens por turno → cabe folgado nos planos grátis;
  acima de ~200 conversas/dia, use um provedor pago ou modelo local.
- **Latência**: BM25 local (<10 ms) + chamada LLM domina. Streaming reduz a
  percepção de espera em ~60%.
- **Manutenção**: reindexe quando entrar corpus novo (idempotente); revise os KBs
  a cada ~10 documentos novos; re-rode a eval a cada troca de modelo.
- **Versionamento**: o corpus é dado sensível (direito autoral) — **não** comite.
  Versione prompt, KBs, estilo e evals (é o que este repositório faz: `.gitignore`
  exclui `corpus/` e `.index/`).

---

## Fase 9 — Roteiro de 30 dias (sequência concreta)

| Semana | Objetivo | Entregável | Tempo/dia |
|---|---|---|---|
| 1 | Pipeline de ponta a ponta funcionando com corpus pequeno | 3 livros + 20 artigos em `.txt`, índice, `ask` respondendo com `[F#]` | 1–2 h |
| 2 | Volume e qualidade | +30 aulas transcritas (Whisper), limpeza, cabeçalhos normalizados | 2 h (GPU) |
| 3 | Doutrina e estilo | KBs revisados lendo os trechos-fonte, 5 novos exemplos few-shot, primeira rodada de eval | 2 h |
| 4 | Produto e limites | interface escolhida, avisos legais, rubrica de estilo preenchida, 20 casos de eval passando | 1–2 h |

**Sinais de que está dando errado (e o que fazer):**

| Sintoma | Causa provável | Correção |
|---|---|---|
| Respostas bonitas sem `[F#]` | índice fraco ou top_k alto com trechos irrelevantes | reconstrua o corpus; baixe `top_k` para 5; exija citação no prompt |
| Confunde "paralaxe" com contradição | KB de glossário fraco | reforce o "o que não é"; adicione exemplo negativo few-shot |
| Soa genérico e sem sal | poucos exemplos de estilo / modelo pequeno | +exemplos; modelo maior; temperatura 0.8 |
| Soa pastiche agressivo | excesso de bordão e nenhum argumento | aplique o teste "remova as palavras de efeito" |
| Inventa livros e páginas | catálogo de obras fora do prompt | injete `kbs/obras.md` sempre; proíba página |
| Repete o mesmo trecho sempre | chunking grosseiro / corpus redundante | reduza overlap, deduplique aulas repetidas |

---

## Mapa dos arquivos deste kit

```
docs/agente-olavo/
├── README.md                        ← este guia
├── agente_olavo/                    ← código (Python puro, sem deps)
│   ├── config.py  llm.py  rag.py  agente.py  cli.py
├── persona/olavo-de-carvalho/
│   ├── SYSTEM.md                    ← contrato de operação do agente
│   ├── kbs/                         ← doutrina curada (6 arquivos)
│   └── style/                       ← guia de estilo + exemplos few-shot
├── scripts/
│   ├── montar_corpus.py             ← livros / sites / áudio -> corpus/*.txt
│   ├── 01_baixar_youtube.sh         ← yt-dlp
│   ├── 02_transcrever.sh            ← Whisper local ou Groq
│   ├── 03_extrair_pdf.sh            ← pdftotext / OCR / limpeza
│   └── gerar_dataset_finetune.py    ← (opcional) destilação para LoRA
├── examples/
│   ├── gpt-custom-instructions.md   ← caminho sem código
│   └── skill/SKILL.md               ← formato skill + references/
├── evals/
│   ├── qa.jsonl                     ← testes de fidelidade
│   └── estilo.md                    ← rubrica de estilo
├── exemplo-corpus/                  ← 1 texto para testar o pipeline
└── tests_smoke.py                   ← teste offline do encanamento
```

---

## Checklist final

- [ ] Escopo escrito: 10 perguntas que deve acertar, 5 que deve recusar.
- [ ] Corpus em `.txt` com cabeçalho padronizado (`título`, `fonte`, `ano`).
- [ ] Nenhum texto *sobre* ele misturado ao texto *dele*.
- [ ] Índice construído; `search` retorna trechos que você reconhece como reais.
- [ ] `SYSTEM.md` com os dois modos e a regra de citação.
- [ ] KBs com "o que não é" em cada conceito central.
- [ ] Catálogo de obras no prompt (antialucinação de bibliografia).
- [ ] Corte temporal declarado (24/01/2022) e `[projeção]` funcionando.
- [ ] Bloco de graus de certeza aparecendo nas respostas.
- [ ] `python -m agente_olavo eval` passando nos casos de fonte.
- [ ] Rubrica de estilo preenchida por juiz de outro provedor.
- [ ] Aviso de emulação visível, se público.
- [ ] Corpus fora do controle de versão; licenças verificadas.

---

## Uma nota sobre o que vale a pena copiar

O que fazia o Olavo de Carvalho interessante não era o tom, era a **exigência**:
que cada afirmação declare em que grau de certeza está, que cada conceito seja
distinguido do seu vizinho, que cada ideia seja rastreada até sua origem, e que
quem afirma responda. Um agente construído sobre essas quatro regras, mesmo com
1/10 do acervo, é mais fiel a ele do que qualquer imitação de bordão — e, por
ironia, é também o tipo de agente que ele aprovaria discutindo, e não elogiando.
