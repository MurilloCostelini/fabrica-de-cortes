# Núcleo / Core document

**PT.** O núcleo é o único documento que *toda* sessão (humana ou LLM) lê, inteiro, uma vez, antes de qualquer trabalho. Ele existe para que ninguém precise repetir contexto e para que nenhuma sessão leia 50 arquivos "por precaução". Estrutura usada neste método:

**EN.** The core is the one document *every* session (human or LLM) reads, whole, once, before any work. It exists so nobody repeats context and no session reads 50 files "just in case". Structure used by this method:

| # | Seção / Section | Conteúdo / Content |
|---|---|---|
| 1 | Quem manda / Who decides | Aprovação é 100% humana; a IA executa a visão, não decide gosto. Human approval is 100%; the AI executes the vision, it does not decide taste. |
| 2 | Regras inegociáveis / Hard rules | Custo zero, scripts nunca tocam o material bruto nem a biblioteca, nunca sobrescrever (versões `v01`, `v02`). Zero cost, scripts never touch raw footage or the library, never overwrite. |
| 3 | Reflexo local / Local reflex | Antes de dizer "não dá", pedir ajuda ou escrever script do zero: (1) olhar o Mapa; (2) se existe, rodar; (3) se não, procurar na máquina; (4) só então perguntar. Before saying "can't", asking, or writing a script: (1) check the Map, (2) run it if listed, (3) search the machine, (4) only then ask. |
| 4 | Mapa do que temos / Map of what we have | Veja [mapa-do-que-temos.md](mapa-do-que-temos.md). |
| 5 | Onde está o trabalho / Where the work is | Cada tarefa termina com um `passagem.md` curto (≤ 25 linhas): o que está pronto, o que falta e qual linha do Mapa usar a seguir. Every task ends with a short hand-off note. |
| 6 | Manuais: abrir só no gatilho / Manuals: open on trigger | Manual de *uso* na 1ª vez que a ferramenta aparece; manual de *estilo* só na etapa que o pede, com um **portão** (citar a regra lida antes de executar). |
| 7 | Lei de leitura / Reading law | Privilégio mínimo: núcleo + checklist do tipo de tarefa. Se um guia citado não existe com aquele número, ler a **maior versão** do mesmo nome. |

## Recibo de leitura e portão / Reading receipt and gate
- **Recibo:** no primeiro post de uma tarefa, a sessão lista o que leu e as etapas que vai fazer. Sem recibo, não começa. *Receipt: the first post lists what was read and which steps will be done.*
- **Portão:** `GATE <etapa> | módulo lido: <arquivo> | regra citada: <≤20 palavras>`. Cita-se a regra com palavras próprias — prova que leu, não que copiou. *Gate: quote the rule in your own words.*

## Por que funciona / Why it works
Em vez de um "prompt gigante", o conhecimento fica em arquivos versionados, lidos sob demanda, com prova de leitura. Isso reduz tokens, evita regras contraditórias e deixa um rastro auditável. *Instead of a giant prompt, knowledge lives in versioned files, read on demand, with proof of reading.*
