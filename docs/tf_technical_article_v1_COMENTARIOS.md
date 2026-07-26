# Inventário dos comentários do professor e respostas às revisões

## Comentário 1

- **Localização no relatório anterior:** Página 5, Linha 1

- **Trecho associado:** `1. Introdução`
- **Comentário:** “falta o objetivo do trabalho como um capitulo”
- **Resposta:** Criei a Seção 1, “Objetivo”, com o objetivo geral, cinco objetivos específicos e os limites do estudo. As demais seções foram renumeradas.
- **Localização no relatório revisado:** Seção 1, p. 5.

## Comentário 2

- **Localização no relatório anterior:** Página 5, Linha 24

- **Trecho associado:** “com a viagem rodoviária completa. Os portos escolhidos, as distâncias de acesso, a carga e as operações de”
- **Comentário:** “falta gastos dentro do terminal”
- **Resposta:** Deixei explícito na introdução que a alternativa multimodal também considera as operações nos terminais de embarque e desembarque. O consumo de Diesel S10 do RTG e do caminhão interno já entra no cálculo das emissões e do custo do combustível.
- **Localização no relatório revisado:** Seção 4.3.3, p. 15–16; consolidação nas Seções 4.3.5 a 4.3.7, p. 33–36.

## Comentário 3

- **Localização no relatório anterior:** Página 6, Linha 1

- **Trecho associado:** “destino e a massa da carga, e o sistema constrói as duas alternativas de transporte.”
- **Comentário:** “tenho duvidas nessa coisa de entrar com a massa. o custo rodoviário é calculado por carga total ou contêiner. Deveriamos padronizar isso. Ao final fazer uma multiplicação e sempre fornecer comparações /conteiner”
- **Resposta:** Deixei explícito que a comparação usa a mesma remessa: mesma origem, destino e massa. A massa define o veículo e o número de viagens na rodovia, o trabalho de transporte no navio e a quantidade de TEUs nos portos. Os resultados são apresentados por remessa.
- **Localização no relatório revisado:** Seções 4.1 e 4.2.1, p. 10–11; Seção 4.3.3, p. 15–16; Seção 4.3.4.6, p. 33.

## Comentário 4

- **Localização no relatório anterior:** Página 11, Linha 30

- **Trecho associado:** “0,494671 L por movimento. Aplicando diretamente a fórmula:”
- **Contexto imediato:** o parágrafo informa quatro movimentos de RTG por contêiner, com consumo de 0,355148 L por movimento, e dois movimentos de caminhão interno, com consumo de 0,494671 L por movimento.
- **Comentário:** “qual a referencia para o numero de movimentos e consumos? eu esperava 10l/box”
- **Resposta:** Indiquei que os valores de movimentos e consumos vêm da planilha técnica *Dados Relatório 2*, elaborada por Gustavo Adolfo Alves da Costa. O cálculo resulta em 2,410 L/TEU por terminal, ou 4,820 L/TEU nos dois terminais. Para um contêiner de 40 pés, equivalente a 2 TEU, isso corresponde a $2\times4{,}820=9{,}640$ L/box, valor próximo de 10 L/box.
- **Localização no relatório revisado:** Seções 4.3.3.1 e 4.3.3.2, p. 15–16.

## Comentário 5

- **Localização no relatório anterior:** Página 12, Linha 4

- **Trecho associado:** “combustível de baixíssimo teor de enxofre) associado a esse deslocamento.”
- **Comentário:** “colocar os links dos sites”
- **Resposta:** Adicionei os links diretamente aos nomes das fontes e ferramentas citadas no texto.
- **Localização no relatório revisado:** Seções 3, 4.2.1, 4.3.4 e 4.3.6, especialmente p. 7, 11, 16–17 e 34–35.

## Comentário 6

- **Localização no relatório anterior:** Página 12, Linha 16

- **Trecho associado:** “viagem pronta, como ‘Santos–Manaus’. Cada linha registra apenas um evento: uma escala em um porto e”
- **Comentário:** “cada linha do quê?”
- **Resposta:** Especifiquei que cada linha de `2025Atracacao.txt` representa uma escala do navio e cada linha de `2025Carga.txt` representa uma parcela de carga movimentada. As duas tabelas são relacionadas pelo campo `IDAtracacao`.
- **Localização no relatório revisado:** Seções 4.3.4.1 a 4.3.4.1.2, p. 17–20.

## Comentário 7

- **Localização no relatório anterior:** Página 12, Linha 16

- **Trecho associado:** “Cada linha registra apenas um evento: uma escala em um porto e”
- **Comentário:** “foto do arquivo”
- **Resposta:** Incluí capturas de partes dos arquivos `2025Carga.txt` e `2025Atracacao.txt`, com legendas e identificação da fonte.
- **Localização no relatório revisado:** Figuras 2 e 3, p. 18 e 20.

## Comentário 8

- **Localização no relatório anterior:** Página 14, Linha 45

- **Trecho associado:** `Carga a bordo: 16.718,333 t`
- **Contexto imediato:** valor mostrado no trecho Suape–Pecém da Figura 2, relativo à reconstrução da viagem `voyage_9612791_00011`.
- **Comentário:** “como se determina a carga a bordo?”
- **Resposta:** Criei uma subseção que mostra o cálculo da carga a bordo passo a passo. Ela calcula o saldo em cada escala, determina a carga inicial necessária para evitar valores negativos e atualiza a carga após cada porto.
- **Localização no relatório revisado:** Seções 4.3.4.1.3.1 e 4.3.4.1.3.2, Tabela 6 e Figura 5, p. 22–24.

## Comentário 9

- **Localização no relatório anterior:** Página 14, Linhas 54-58

- **Tipo de anotação:** destaque sem comentário textual.
- **Trecho destacado:** “Após reconstruir o percurso e a carga a bordo, é preciso estimar quanto combustível foi necessário para realizar esse transporte. Para isso, o sistema usa a intensidade de combustível, isto é, a quantidade de combustível associada ao transporte de uma tonelada por uma milha náutica. A unidade é grama por tonelada-milha náutica, ou g/(t · nm). Esse indicador é uma razão”
- **Resposta:** A Seção 3.1 agora justifica o uso de médias históricas na comparação entre os modais. A Seção 4.3.4.2 explica como o EU MRV forma e verifica a intensidade anual usada nos recortes.
- **Localização no relatório revisado:** Seção 3.1, p. 9; Seção 4.3.4.2, p. 24–29.

## Comentário 10

- **Localização no relatório anterior:** Página 14, Linha 57

- **Trecho associado:** “tonelada-milha náutica, ou g/(t · nm).”
- **Comentário:** “mas isso depende do tipo de navio e do seu calado??...”
- **Resposta:** Sim. Calado, velocidade, estado do casco e condições ambientais alteram o consumo de uma viagem específica. Deixei explícito que, como o estudo compara os modais em termos médios, o cálculo usa a intensidade anual verificada do mesmo IMO. Quando esse valor não está disponível, o cálculo usa uma estimativa baseada no mesmo tipo de navio.
- **Localização no relatório revisado:** Seção 3.1, p. 9; Seções 4.3.4.2 a 4.3.4.2.3, p. 24–27.

## Comentário 11

- **Localização no relatório anterior:** Página 15, Linha 6

- **Trecho associado:** “mesmo navio nessa base.”
- **Contexto imediato:** o número IMO registrado na ANTAQ é usado para procurar a mesma embarcação na base EU MRV.
- **Comentário:** “mostrar arquivo”
- **Resposta:** Incluí uma captura da planilha anual do EU MRV e uma tabela que identifica o arquivo, o IMO, o tipo do navio e o campo de intensidade utilizado.
- **Localização no relatório revisado:** Figura 6 e Tabela 7, p. 25–26.

## Comentário 12

- **Localização no relatório anterior:** Página 15, Linha 53

- **Trecho associado:** “navios do mesmo tipo.”
- **Comentário:** “como se identifica navios do mesmo tipo?”
- **Resposta:** O tipo é lido diretamente do campo `Ship type` do EU MRV. Navios com o mesmo rótulo, como `container ship`, são considerados do mesmo tipo. Essa identificação não usa o nome, a rota, o armador ou as dimensões do navio.
- **Localização no relatório revisado:** Seção 4.3.4.2.2, p. 26.

## Comentário 13

- **Localização no relatório anterior:** Página 16, Linha 14

- **Trecho associado:** “a classe do navio, que é o grupo mais específico disponível.”
- **Comentário:** “o que é a classe do navio?”
- **Resposta:** Removi a estimativa por classe para evitar ambiguidade. O cálculo usa primeiro o valor individual do mesmo IMO e, quando ele não está disponível, uma estimativa pelo tipo de navio informado no EU MRV.
- **Localização no relatório revisado:** Seções 4.3.4.2.2 a 4.3.4.2.4, p. 26–27.

## Comentário 14

- **Localização no relatório anterior:** Página 16, Linhas 43-45

- **Trecho destacado:** “Um recorte só entra nessa consolidação quando a origem e o destino são portos distintos da mesma viagem, aparecem na ordem do cenário e todos os subtrechos entre eles têm distância disponível. Se o navio repete a mesma ligação, o sistema usa o recorte direto;”
- **Comentário:** “nao entendi”
- **Resposta:** Reescrevi a regra de forma direta. O recorte deve pertencer à mesma viagem, ligar portos diferentes, apresentar a origem antes do destino e ter distância válida em todos os subtrechos. Se houver mais de uma opção na mesma viagem, uso primeiro o recorte direto; se ele não existir, uso o de menor distância.
- **Localização no relatório revisado:** Seção 4.3.4.3, p. 27–28.

## Comentário 15

- **Localização no relatório anterior:** Página 17, Linha 3

- **Trecho associado:** “uma viagem reconstruída, o trabalho entre a origem o e o destino d é:”
- **Contexto imediato:** introdução da equação de trabalho de transporte aplicada a cada recorte válido.
- **Comentário:** “fazer figura que sintetize e torne clara toda a explicação”
- **Resposta:** Incluí um exemplo completo com cinco recortes entre Santos e Manaus. A Figura 7 mostra os navios, os portos intermediários, a carga e a distância de cada subtrecho. Em seguida, o texto resolve os cálculos e informa que o mesmo processo é aplicado aos demais recortes.
- **Localização no relatório revisado:** Seção 4.3.4.5 e Figura 7, p. 30–33.

## Comentário 16

- **Localização no relatório anterior:** Página 20, Linhas 58-60

- **Trecho associado:** cabeçalho da coluna `Emissões operacionais TTW` da Tabela 9, que consolida os resultados da alternativa multimodal para uma remessa de 14 t.
- **Comentário:** “onde entra o peso da carga?”
- **Resposta:** A massa entra no cálculo do consumo. No navio, ela aparece em $M_{\mathrm{VLSFO}}=I\times m\times D/1000$; na rodovia, define o veículo e o número de viagens; e, nos portos, define a quantidade de TEUs. Como o consumo já considera a massa, ela não é multiplicada novamente na tabela final.
- **Localização no relatório revisado:** Seções 4.1 e 4.2.1, p. 10–11; Seções 4.3.2 e 4.3.3, p. 14–16; Seção 4.3.4.6, p. 33; consolidação nas Seções 4.3.5 a 4.3.7, p. 33–36.
