# Inventário dos comentários do professor e respostas às revisões

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
- **Resposta:** Foi criada a Seção 1, “Objetivo”, com o objetivo geral, os objetivos específicos e os limites da avaliação. As demais seções foram renumeradas.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:192`

### CM02. Linha 24

- **Trecho associado:** “com a viagem rodoviária completa. Os portos escolhidos, as distâncias de acesso, a carga e as operações de”
- **Comentário:** “falta gastos dentro do terminal”
- **Resposta:** As operações nos dois terminais foram incluídas como componente próprio da alternativa multimodal. A Seção 4.3.3 calcula o consumo de Diesel S10 dos RTGs e caminhões internos e utiliza esse resultado nas emissões e no custo modelado do combustível.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:236-237`

## Página 6

### CM03. Linha 1

- **Trecho associado:** “destino e a massa da carga, e o sistema constrói as duas alternativas de transporte.”
- **Comentário:** “tenho duvidas nessa coisa de entrar com a massa. o custo rodoviário é calculado por carga total ou contêiner. Deveriamos padronizar isso. Ao final fazer uma multiplicação e sempre fornecer comparações /conteiner”
- **Resposta:** A comparação foi padronizada pela mesma remessa, definida por origem, destino e massa. A massa determina o veículo e o número de viagens na rodovia, entra diretamente no trabalho de transporte marítimo e é convertida em TEU apenas para calcular as movimentações portuárias. Os resultados permanecem por remessa, pois contêineres de mesmo tamanho podem transportar massas diferentes.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:241-242`

## Página 11

### CM04. Linha 30

- **Trecho associado:** “0,494671 L por movimento. Aplicando diretamente a fórmula:”
- **Contexto imediato:** o parágrafo informa quatro movimentos de RTG por contêiner, com consumo de 0,355148 L por movimento, e dois movimentos de caminhão interno, com consumo de 0,494671 L por movimento.
- **Comentário:** “qual a referencia para o numero de movimentos e consumos? eu esperava 10l/box”
- **Resposta:** O texto passou a identificar separadamente as referências conceituais e a origem dos valores numéricos. Os movimentos e consumos foram extraídos das abas `RTG Base C1`, `RTG C2`, `TT Base C1` e `TT C2` da planilha técnica não publicada *Dados Relatório 2*, elaborada por Gustavo Adolfo Alves da Costa em 2023. Também foi explicitado que os fatores representam um cenário de referência construído com dados de Santos, e não valores universais para qualquer terminal. Um valor expresso em L/box usa como denominador o contêiner físico, que pode ter tamanho diferente de 1 TEU. Quando *box* designa um contêiner de 40 pés, equivalente a 2 TEU, o resultado do modelo passa a ser $2\times4{,}820=9{,}640$ L/box nos dois terminais, valor próximo de 10 L/box. Essa equivalência é apenas uma conversão do denominador, e não a adoção de um novo fator de consumo. Comparações com outros valores em L/box ainda exigem confirmar os equipamentos incluídos, os consumos auxiliares considerados e se o valor abrange um ou os dois terminais.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:759-762`

## Página 12

### CM05. Linha 4

- **Trecho associado:** “combustível de baixíssimo teor de enxofre) associado a esse deslocamento.”
- **Comentário:** “colocar os links dos sites”
- **Resposta:** Foram adicionados hiperlinks diretamente aos nomes das fontes e ferramentas consultadas, incluindo ANTAQ, EU MRV, ANP, Ship & Bunker e CurrencyConverter.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:781-784`

### CM06. Linha 16

- **Trecho associado:** “viagem pronta, como ‘Santos–Manaus’. Cada linha registra apenas um evento: uma escala em um porto e”
- **Comentário:** “cada linha do quê?”
- **Resposta:** O texto agora identifica os dois arquivos brutos utilizados. Cada linha de `2025Atracacao.txt` representa uma escala de um navio, enquanto cada linha de `2025Carga.txt` representa uma parcela de carga movimentada durante uma atracação. A relação entre as tabelas pelo campo `IDAtracacao` também foi explicada.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:805-808`

### CM07. Linha 16

- **Trecho associado:** “Cada linha registra apenas um evento: uma escala em um porto e”
- **Comentário:** “foto do arquivo”
- **Resposta:** Foram incluídas capturas de partes dos arquivos `2025Carga.txt` e `2025Atracacao.txt`, acompanhadas de legendas, identificação dos registros exibidos e fonte.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:806-808`

## Página 14

### CM08. Linha 45

- **Trecho associado:** `Carga a bordo: 16.718,333 t`
- **Contexto imediato:** valor mostrado no trecho Suape–Pecém da Figura 2, relativo à reconstrução da viagem `voyage_9612791_00011`.
- **Comentário:** “como se determina a carga a bordo?”
- **Resposta:** Foi criada uma subseção específica para a carga a bordo. Ela apresenta o balanço entre embarques e desembarques em cada escala, explica por que a carga inicial não pode ser fixada sempre em zero e resolve numericamente a viagem Santos–Suape–Pecém–Manaus.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1043-1045`

### CM09. Linhas 54-58

- **Tipo de anotação:** destaque sem comentário textual.
- **Trecho destacado:** “Após reconstruir o percurso e a carga a bordo, é preciso estimar quanto combustível foi necessário para realizar esse transporte. Para isso, o sistema usa a intensidade de combustível, isto é, a quantidade de combustível associada ao transporte de uma tonelada por uma milha náutica. A unidade é grama por tonelada-milha náutica, ou g/(t · nm). Esse indicador é uma razão”
- **Resposta:** A fundamentação foi ampliada em dois pontos. A Seção 3.1 explica que o objetivo é comparar os modais a partir de desempenhos médios, e não reproduzir uma viagem específica. Já a Seção 4.3.4.2 apresenta a metodologia do EU MRV, a verificação dos dados, a construção da intensidade anual e sua aplicação às viagens observadas.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1061-1068`

### CM10. Linha 57

- **Trecho associado:** “tonelada-milha náutica, ou g/(t · nm).”
- **Comentário:** “mas isso depende do tipo de navio e do seu calado??...”
- **Resposta:** O texto passou a distinguir uma simulação localizada de uma avaliação comparativa. Calado, velocidade, condições ambientais e estado do navio influenciam uma viagem específica, mas não são usados diretamente porque o estudo busca uma comparação média entre os modais. A intensidade anual verificada pelo EU MRV reúne o desempenho observado do navio ao longo do período, e o tipo ou a classe são usados apenas quando não há um valor individual utilizável.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1064-1066`

## Página 15

### CM11. Linha 6

- **Trecho associado:** “mesmo navio nessa base.”
- **Contexto imediato:** o número IMO registrado na ANTAQ é usado para procurar a mesma embarcação na base EU MRV.
- **Comentário:** “mostrar arquivo”
- **Resposta:** Foi incluída uma captura de parte de uma planilha anual do EU MRV. A figura é acompanhada de uma tabela que identifica o arquivo, o número IMO, o tipo do navio, o campo de intensidade utilizado e a regra de seleção do valor.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1081-1086`

### CM12. Linha 53

- **Trecho associado:** “navios do mesmo tipo.”
- **Comentário:** “como se identifica navios do mesmo tipo?”
- **Resposta:** Foi esclarecido que o tipo é lido diretamente do campo `Ship type` do EU MRV. O sistema normaliza apenas maiúsculas, minúsculas e espaços e reúne os navios com o mesmo rótulo, como `container ship`; não infere o tipo pelo nome, pela rota, pelo armador ou pelas dimensões.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1162-1166`

## Página 16

### CM13. Linha 14

- **Trecho associado:** “a classe do navio, que é o grupo mais específico disponível.”
- **Comentário:** “?”
- **Resposta:** A classe foi definida como uma faixa de porte criada pelo CabotageLens dentro do tipo `container ship`: abaixo de 20.000 t, de 20.000 t a menos de 40.000 t e a partir de 40.000 t. O porte usa prioritariamente informações relacionadas ao DWT e, na ausência delas, à massa transportada. Também foi esclarecido que essas faixas são regras do modelo, não classes publicadas pelo EU MRV ou por uma sociedade classificadora.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1205-1212`

### CM14. Linhas 43-45

- **Trecho destacado:** “Um recorte só entra nessa consolidação quando a origem e o destino são portos distintos da mesma viagem, aparecem na ordem do cenário e todos os subtrechos entre eles têm distância disponível. Se o navio repete a mesma ligação, o sistema usa o recorte direto;”
- **Comentário:** “nao entendi”
- **Resposta:** A explicação foi reescrita como quatro condições objetivas para aceitar um recorte: pertencer à mesma viagem, ligar portos distintos, apresentar a origem antes do destino e possuir distância em todos os subtrechos. Quando a mesma viagem produz mais de uma opção, mantém-se o recorte direto ou, se ele não existir, o recorte completo de menor distância; viagens diferentes continuam sendo consideradas.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1259-1263`

## Página 17

### CM15. Linha 3

- **Trecho associado:** “uma viagem reconstruída, o trabalho entre a origem o e o destino d é:”
- **Contexto imediato:** introdução da equação de trabalho de transporte aplicada a cada recorte válido.
- **Comentário:** “fazer figura que sintetize e torne clara toda a explicação”
- **Resposta:** Foi criada a Seção 4.3.4.5, com um diagrama de cinco recortes observados entre Santos e Manaus. A figura mostra navios, portos intermediários, carga e distância em cada subtrecho; em seguida, são resolvidos os cálculos de trabalho de transporte, consumo, intensidade e distância média. O texto esclarece que o procedimento é repetido para todos os demais recortes elegíveis.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1270-1277`

## Página 20

### CM16. Linhas 58-60

- **Trecho associado:** cabeçalho da coluna `Emissões operacionais TTW` da Tabela 9, que consolida os resultados da alternativa multimodal para uma remessa de 14 t.
- **Comentário:** “onde entra o peso da carga?”
- **Resposta:** A massa da remessa foi explicitada nas fórmulas anteriores à tabela de resultados. Na navegação, ela aparece diretamente em $M_{\mathrm{VLSFO}}=I\,m\,D/1000$; nos acessos rodoviários, define o veículo e o número de viagens; e, nas operações portuárias, determina a quantidade de TEUs. Também foram resolvidas numericamente as contas de consumo, emissões e custo de cada etapa.
- **Referência no fonte editável:** `docs/tf_technical_article.tex:1658-1679`
