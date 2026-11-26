# Descobrir um estilo de edição com ferramentas locais / Discovering an editing style with local tools

**PT.** O método não pergunta "qual estilo é bom?"; ele **mede** o que já existe e deixa o humano escolher.

1. **Reunir referências** (só links que *você* escolheu; uso privado de estudo): `estilo/baixar_refs.py URL TEMA` baixa numa pasta nova e isolada e marca duplicatas por hash.
2. **Medir cada vídeo**, quadro a quadro, sem economizar (é local): `estilo/analisa_ref.py` gera `metricas.csv` (luminosidade, saturação, contraste, bordas, fluxo óptico: pan, zoom, rotação, energia de áudio), `resumo.json` (cortes, duração média de plano, paleta, aceleração por terços) e duas folhas de quadros. `estilo/quadros_chave.py` guarda um quadro sempre que o conteúdo muda (texto novo, objeto novo, corte).
3. **Descrever o que o OpenCV não vê** (texto na tela, objetos, cenário): `cacador/florence_quadros.py` ou um modelo de visão local.
4. **Comparar criadores:** rode a análise em vários vídeos de cada criador e `estilo/comparar_criadores.py A=pasta_a B=pasta_b` imprime uma tabela (cortes por minuto, plano médio, movimento, cor, tendência de ritmo).
5. **Escrever um guia de estilo** só com o que o humano aprovar. Padrões medidos são hipóteses, não regras.

**Limites conhecidos:** OpenCV não lê texto; cortes por histograma erram em fades e em vídeos de câmera muito instável; fluxo óptico a 160 px basta para câmera global, não para objetos pequenos. Números comparam *forma*, não qualidade.

**EN.** The method does not ask "which style is good?"; it **measures** what exists and lets a human choose.

1. **Collect references** (only links *you* picked; private study): `baixar_refs.py URL TOPIC` downloads into a fresh isolated folder and flags exact duplicates.
2. **Measure each video** frame by frame: `analisa_ref.py` writes per-frame metrics, a summary (cuts, average shot length, palette, pace by thirds) and contact sheets; `quadros_chave.py` keeps a frame whenever content changes.
3. **Describe what OpenCV cannot see** (on-screen text, objects, setting) with Florence-2 or a local vision model.
4. **Compare creators:** run the analysis on several videos per creator, then `comparar_criadores.py A=dir_a B=dir_b` prints one table.
5. **Write a style guide** only from what a human approves. Measured patterns are hypotheses.

**Known limits:** OpenCV cannot read text; histogram cut detection misses fades and very shaky footage; 160 px optical flow only captures global camera motion. The numbers compare *form*, not quality.

Exemplo / Example: `exemplos/saidas/estilo_clip_a/` (saída real do script no clipe sintético / real output on the synthetic clip).
