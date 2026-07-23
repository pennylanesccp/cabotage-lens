# Inventário dos comentários do professor

Documento comentado: `docs/tf_technical_article_v1_COMENTARIOS.pdf`

Autor das anotações: Marcos Pinto

Total identificado: 15 comentários textuais e 1 destaque sem comentário textual.

## Critério de localização

- A página indicada é a página impressa no próprio artigo, coincidente com a página física do PDF.
- Como o artigo não possui numeração impressa de linhas, a linha foi contada de cima para baixo em cada página, com base na posição visual do texto extraído do PDF.
- Em tabelas, figuras e trechos destacados em mais de uma linha, também é apresentado o contexto necessário para localizar a anotação sem ambiguidade.
- As linhas do arquivo `docs/tf_technical_article.tex` são fornecidas como referência adicional para o trabalho de revisão.
- Os comentários foram transcritos literalmente, sem correção de grafia, acentuação ou pontuação.

## Página 5

### CM01. Linha 1

- **Trecho associado:** `1. Introdução`
- **Comentário:** “falta o objetivo do trabalho como um capitulo”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:192`

### CM02. Linha 24

- **Trecho associado:** “com a viagem rodoviária completa. Os portos escolhidos, as distâncias de acesso, a carga e as operações de”
- **Comentário:** “falta gastos dentro do terminal”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:236-237`

## Página 6

### CM03. Linha 1

- **Trecho associado:** “destino e a massa da carga, e o sistema constrói as duas alternativas de transporte.”
- **Comentário:** “tenho duvidas nessa coisa de entrar com a massa. o custo rodoviário é calculado por carga total ou contêiner. Deveriamos padronizar isso. Ao final fazer uma multiplicação e sempre fornecer comparações /conteiner”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:241-242`

## Página 11

### CM04. Linha 30

- **Trecho associado:** “0,494671 L por movimento. Aplicando diretamente a fórmula:”
- **Contexto imediato:** o parágrafo informa quatro movimentos de RTG por contêiner, com consumo de 0,355148 L por movimento, e dois movimentos de caminhão interno, com consumo de 0,494671 L por movimento.
- **Comentário:** “qual a referencia para o numero de movimentos e consumos? eu esperava 10l/box”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:759-762`

## Página 12

### CM05. Linha 4

- **Trecho associado:** “combustível de baixíssimo teor de enxofre) associado a esse deslocamento.”
- **Comentário:** “colocar os links dos sites”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:781-784`

### CM06. Linha 16

- **Trecho associado:** “viagem pronta, como ‘Santos–Manaus’. Cada linha registra apenas um evento: uma escala em um porto e”
- **Comentário:** “cada linha do quê?”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:805-808`

### CM07. Linha 16

- **Trecho associado:** “Cada linha registra apenas um evento: uma escala em um porto e”
- **Comentário:** “foto do arquivo”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:806-808`

## Página 14

### CM08. Linha 45

- **Trecho associado:** `Carga a bordo: 16.718,333 t`
- **Contexto imediato:** valor mostrado no trecho Suape–Pecém da Figura 2, relativo à reconstrução da viagem `voyage_9612791_00011`.
- **Comentário:** “como se determina a carga a bordo?”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1043-1045`

### CM09. Linhas 54-58

- **Tipo de anotação:** destaque sem comentário textual.
- **Trecho destacado:** “Após reconstruir o percurso e a carga a bordo, é preciso estimar quanto combustível foi necessário para realizar esse transporte. Para isso, o sistema usa a intensidade de combustível, isto é, a quantidade de combustível associada ao transporte de uma tonelada por uma milha náutica. A unidade é grama por tonelada-milha náutica, ou g/(t · nm). Esse indicador é uma razão”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1061-1068`

### CM10. Linha 57

- **Trecho associado:** “tonelada-milha náutica, ou g/(t · nm).”
- **Comentário:** “mas isso depende do tipo de navio e do seu calado??...”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1064-1066`

## Página 15

### CM11. Linha 6

- **Trecho associado:** “mesmo navio nessa base.”
- **Contexto imediato:** o número IMO registrado na ANTAQ é usado para procurar a mesma embarcação na base EU MRV.
- **Comentário:** “mostrar arquivo”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1081-1086`

### CM12. Linha 53

- **Trecho associado:** “navios do mesmo tipo.”
- **Comentário:** “como se identifica navios do mesmo tipo?”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1162-1166`

## Página 16

### CM13. Linha 14

- **Trecho associado:** “a classe do navio, que é o grupo mais específico disponível.”
- **Comentário:** “o que é a classe do navio?”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1205-1212`

### CM14. Linhas 43-45

- **Trecho destacado:** “Um recorte só entra nessa consolidação quando a origem e o destino são portos distintos da mesma viagem, aparecem na ordem do cenário e todos os subtrechos entre eles têm distância disponível. Se o navio repete a mesma ligação, o sistema usa o recorte direto;”
- **Comentário:** “nao entendi”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1259-1263`

## Página 17

### CM15. Linha 3

- **Trecho associado:** “uma viagem reconstruída, o trabalho entre a origem o e o destino d é:”
- **Contexto imediato:** introdução da equação de trabalho de transporte aplicada a cada recorte válido.
- **Comentário:** “fazer figura que sintetize e torne clara toda a explicação”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1270-1277`

## Página 20

### CM16. Linhas 58-60

- **Trecho associado:** cabeçalho da coluna `Emissões operacionais TTW` da Tabela 9, que consolida os resultados da alternativa multimodal para uma remessa de 14 t.
- **Comentário:** “onde entra o peso da carga?”
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1658-1679`
