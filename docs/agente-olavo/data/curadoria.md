# Curadoria: o que é mais popular e o que é mais relevante

> Levantamento feito em nov/2025 a partir de: catálogo do site oficial,
> espelho Wayback (arquivo por ano, 1998–2016), Internet Archive (metadados dos
> itens do COF), GitHub (`osescribas/cof`), YouTube (canal oficial + buscas por
> termo) e cobertura de imprensa (Folha, BBC, Jacobin).
>
> **Populares ≠ relevantes.** Um corte de 49 segundos tem 300 mil views e ensina
> quase nada; uma aula de 2h58 sobre os quatro conceitos da lógica tem 18 mil
> views e ensina o sistema inteiro. As duas listas estão separadas por isso.

---

## 1. O acervo, em números (verificado)

| Acervo | Volume | Estado | Onde |
|---|---|---|---|
| Canal oficial no YouTube | 1,2 mi de inscritos · ~1,3 mil vídeos · ~97 mi de views | ativo (póstumo, "in memoriam") | `@opropriolavodecarvalho` |
| COF — Curso Online de Filosofia | 585 aulas + 4 de introdução (07/03/2009 → 01/01/2022) | áudio no Archive; transcrições parciais | `archive.org/details/COFemAudio` |
| Transcrições do COF (revisadas) | 257 aulas revisadas + ~330 pendentes | CC0-1.0 | GitHub `osescribas/cof` |
| Transcrições 1–293 em PDF | 6 GB | item do Archive | `curso-online-de-filosofia-aulas-1-293-...` |
| Site oficial | artigos semanais 1998–2016 (~900 textos) | **domínio comprometido** | usar Wayback Machine |
| Livros publicados | 23 de autoria + 32 vols. de coleção | comércio | Vide, Topbooks, Record |

### Três avisos operacionais descobertos na investigação

1. **`olavodecarvalho.org` está servindo spam de loja** (`mall.carlisgrove.com`).
   Artigos, apostilas e arquivos anuais **só existem hoje no Wayback** ou em
   espelhos. Todos os `url_arquivo` do `artigos.csv` já apontam para lá.
2. **O caminho `/apostilas/*.htm` morreu na migração para WordPress.** A versão
   antiga (`.htm`, capturada até ~2016) tem o texto; a nova (slug limpo,
   `/inteligencia-e-verdade/`) devolve 404 ou página de loja. Use captura antiga.
3. **O GitHub `osescribas/cof` é o melhor corpus textual disponível**: 257 aulas
   revisadas, licença **CC0-1.0** (domínio público), ~110 KB de texto por aula.
   Isso é ~28 MB de texto limpo — mais denso e mais confiável que qualquer
   transcrição de vídeo que você faria com Whisper.

---

## 2. Mais populares (alcance medido)

### Vídeos

| # | Item | Alcance | Por que importa |
|---|---|---|---|
| 1 | Entrevista a **Leandro Ruschel** (2014, Richmond) | 1,8 mi views · 2h10 | a entrevista longa mais vista; política + biografia intelectual |
| 2 | Entrevista à **BBC Brasil** (2019) | 2,0 mi views · 1h24 | cobertura jornalística; use como contexto, não doutrina |
| 3 | **Palestra do livro O Jardim das Aflições** (canal oficial) | 338 mil · 1h35 | a obra central explicada por ele, 1 única fonte |
| 4 | **Cortes virais** ("Em 1998 previu tudo", "O ponto fraco do cristianismo", 341 mil) | 300–730 mil cada | alcance massivo, densidade baixa |
| 5 | Boris Casoy / *Passando a Limpo* (1998) | 226 mil · 33 min | retórica televisiva dos anos 90 |
| 6 | "Olavo deixa alunos perplexos sobre Marx" (aula 20) | 421 mil | Marx como caso de exame dialético |

### Livros por circulação

*O Mínimo que Você Precisa Saber para Não Ser um Idiota* (2013, org. Felipe
Moura Brasil) e *O Imbecil Coletivo* (1996) somam **mais de 400 mil exemplares
entre 2013 e 2019** — são os dois mais lidos, e por isso os mais citados de
segunda mão (muita gente cita sem ter lido; ver o short "90% da direita que cita
Olavo nunca leu O Jardim das Aflições").

**Conclusão prática:** o material *popular* é ótimo para **estilo oral e
retórica de palco** (frases curtas, anedota, golpe de ironia) e péssimo para
**doutrina**. Indexe os populares na pasta `transcricoes/` com prioridade baixa;
não os use como fonte de conceito.

---

## 3. Mais relevantes para o agente (ordenado por densidade doutrinária)

### Núcleo duro — indexar primeiro (P0)

| Fonte | O que dá | Por quê |
|---|---|---|
| **Apostila *Inteligência e Verdade*** | os 4 graus de certeza, evidência, dúvida | é o eixo antialucinação do agente |
| ***Ser e Conhecer*** (5 partes) + *Conhecimento e presença* | consciência reflexiva, conhecimento por presença | fundamento de toda a epistemologia |
| ***Aristóteles em Nova Perspectiva*** (livro) + trecho oficial "os quatro discursos" | teoria dos quatro discursos | doutrina mais citada e mais mal-entendida |
| **Série "Pensamento e atualidade de Aristóteles"** (8 partes) | leitura guiada de Aristóteles | a versão *didática* da doutrina |
| ***A Nova Era e a Revolução Cultural*** (texto integral no site) | Capra + Gramsci, genealogia | único livro completo de graça |
| **Prólogo de *O Imbecil Coletivo*** | definição de "imbecil coletivo" | impede o uso vulgar do termo |
| ***O Jardim das Aflições*** (livro + palestra 2015) | materialismo, religião civil, diagnóstico | a obra sistemática |
| **Aula 219 do COF** | paralaxe cognitiva em operação, linguagem e chavões | melhor peça única para **estilo** e para o KB de paralaxe |

### Segundo anel (P1)

- **Artigos 2012–2015 do Diário do Comércio** — o corpo ensaístico maduro:
  ~900 textos curtos, cada um uma tese. Deles, os 10 mais úteis ao agente:
  *O reino do subjetivismo* (genealogia subjetivismo → paralaxe), *Foucault sem
  Foucault* (leitura cerrada), *Pensando como os revolucionários*, *O novo
  imbecil coletivo*, *O método para não entender nada* (falácias ao contrário),
  *A educação grega e nós* (paideia), *Autoridades* (argumentum ad ignorantiam),
  *Modernidade real e imaginária*, *Estudar antes de falar*, *A arte de escrever
  — Lição 1* (o autor sobre estilo).
- **Apostilas de método**: *Fato concreto e depuração abstrativa*, *Debates e
  provas*, *Identidade e Univocidade*, *Poesia e filosofia*, *O Anti-Gramsci*.
- **Entrevista a Jennifer Thalis** e **Boris Casoy** — voz coloquial e
  argumentação ao vivo.

### Terceiro anel (P2) — só depois da eval estabilizar

- *O Mínimo...* e *O Imbecil Coletivo* (completos): são os mais populares e os
  mais propensos a produzir pastiche; entram por último, com peso menor.
- Cursos avulsos (24), *True Outspeak*, entrevistas pós-2018.

### **Não indexar** (marcar como `contexto/`)

Comentário de terceiros, resumos de canal de fã, cortes com título sensacionalista
(ex.: "Use o Método dos 4 Discursos", "The 4 speeches that explain the current
world"), teses acadêmicas sobre ele, cobertura jornalística. Motivo: o agente
passa a atribuir a ele as palavras do comentarista — o erro nº 1 de personas.

---

## 4. Roteiro de ingestão por prioridade

```bash
cd docs/agente-olavo

# Etapa 1 (~20 min, sem GPU): o núcleo duro a partir do GitHub e do Wayback
python3 scripts/baixar_acervo.py --prioridade P0 --fonte cof-github
python3 scripts/baixar_acervo.py --prioridade P0 --fonte wayback
python3 -m agente_olavo ingest
python -m agente_olavo eval          # deve acertar os casos de fonte

# Etapa 2 (~2 h): o segundo anel
python3 scripts/baixar_acervo.py --prioridade P1 --fonte wayback
python3 -m agente_olavo ingest

# Etapa 3 (opcional, com GPU): áudio de aulas específicas
python3 scripts/baixar_acervo.py --prioridade P0 --fonte cof-audio --limite 5
python3 scripts/montar_corpus.py --somente audio --whisper local
python3 -m agente_olavo ingest --embeddings
```

**Meta de volume:** P0 ≈ 800 mil caracteres (dá um agente já útil); P0+P1 ≈ 4–6
milhões (cobre a obra ensaística madura); + COF completo ≈ 30–40 milhões (exige
`RETRIEVAL_MODE=hybrid`).

---

## 5. Direitos: o que cada fonte permite

| Fonte | Distribuir o corpus? | Uso privado de estudo? |
|---|---|---|
| GitHub `osescribas/cof` (CC0) | **sim** | sim |
| Wayback/olavodecarvalho.org (artigos) | não — citação curta | sim |
| Livros comprados | não | sim (indexação privada) |
| Áudios do Archive (`COFemAudio`) | verificar item | sim |
| YouTube | não (ToS + autoral) | transcrição privada, citação curta |

Ou seja: você pode versionar no Git **apenas** o corpus CC0 do COF e o seu
próprio material de curadoria (KB, estilo, evals). O resto fica fora do
repositório — é o que o `.gitignore` já faz.
