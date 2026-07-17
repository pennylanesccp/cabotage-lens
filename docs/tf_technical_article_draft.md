# CabotageLens: sistema computacional auditável para comparação porta a porta entre rodovia e cabotagem no Brasil

> **Documento de validação textual.**
>
> Durante esta etapa, este Markdown concentra o conteúdo editável do artigo técnico. As revisões de texto devem ser feitas aqui. O [arquivo LaTeX](article/cabotagelens_technical_article.tex) e o [PDF](article/cabotagelens_technical_article.pdf) serão sincronizados e compilados somente depois da aprovação do conteúdo.

**Autor:** Felipe de Sá Proença

**Status:** em validação textual

---

## Resumo

A escolha entre transporte rodoviário direto e transporte com cabotagem não depende apenas da distância percorrida. No Brasil, uma rota com cabotagem pode reduzir parte das emissões no trecho principal, mas também inclui deslocamentos rodoviários até os portos, operações portuárias, espera, movimentação de carga e o percurso real realizado pelo navio. Quando esses elementos são ignorados, a comparação entre os modais fica incompleta e pode levar a conclusões pouco confiáveis.

Este trabalho apresenta o CabotageLens, uma ferramenta desenvolvida para comparar, de forma mais assertiva, duas alternativas para a mesma origem, destino e carga: uma viagem totalmente rodoviária e uma cadeia logística formada por rodovia, cabotagem e rodovia. A ferramenta utiliza dados públicos de instituições públicas e privadas, combinando informações de rotas terrestres, movimentação portuária, viagens marítimas, consumo energético, emissões e custos modelados.

A principal contribuição do sistema é tratar a operação logística como uma cadeia completa, e não como trechos isolados. Na perna marítima, o sistema reconstrói o percurso observado dos navios, considera cargas transportadas ao longo dos subtrechos e evita assumir previamente um corredor fixo. Na comparação ambiental, inclui pontos de emissão que normalmente ficam fora de análises simplificadas, como acessos terrestres aos portos e emissões associadas às etapas portuárias quando há dados disponíveis.

Com isso, o CabotageLens fornece uma base mais transparente para avaliar custo e emissões de carbono entre alternativas rodoviárias e multimodais, permitindo que a decisão seja sustentada por dados rastreáveis, premissas explícitas e uma representação mais próxima da operação real.

**Palavras-chave**: cabotagem; transporte rodoviário; transporte multimodal; ANTAQ; EU MRV; emissões operacionais; logística; Brasil.

## 1. Introdução

O transporte de cargas no Brasil é fortemente concentrado nas rodovias. Em 2015, o modal rodoviário respondeu por 65% da atividade de transporte de cargas, medida em toneladas-quilômetro úteis (TKU). No mesmo recorte, a ferrovia correspondeu por 15% e a cabotagem por 11%. A distribuição ajuda a explicar por que o caminhão é a referência mais imediata para transportar cargas no país, inclusive em trajetos longos.

![Distribuição da atividade de transporte de cargas no Brasil em 2015.](images/grafico%20da%20atividade%20modal%20do%20transporte%20no%20Brasil%20em%202015.jpeg)

*Figura 1 — Distribuição da atividade de transporte de cargas no Brasil em 2015, medida em TKU. Fonte: [Sindicato dos Bancários de São Paulo, Osasco e Região (2018)](https://spbancarios.com.br/05/2018/brasil-e-dependente-do-transporte-rodoviario-de-cargas), com dados de 2015 do Plano Nacional de Logística, conforme informado pela publicação.*

Essa concentração não significa que a rodovia seja a melhor alternativa em todas as situações. O caminhão oferece uma ligação direta entre muitas origens e destinos, mas viagens longas também aumentam a exposição ao consumo de diesel, às condições da infraestrutura terrestre e ao custo de percorrer grandes distâncias. Quando a carga pode entrar e sair por portos, a cabotagem — o transporte marítimo entre portos do mesmo país — passa a ser uma alternativa possível [icct2022]. A pergunta, porém, não é se um caminhão ou um navio é melhor isoladamente. É qual alternativa consegue levar a mesma carga, do mesmo ponto de partida ao mesmo destino, com menor custo modelado e menores emissões operacionais.

Essa pergunta exige uma comparação porta a porta. Na alternativa rodoviária, a carga segue diretamente por estrada. Na alternativa multimodal, ela percorre um acesso rodoviário até o porto, uma perna marítima e outro acesso rodoviário até o destino final. Portos, distâncias, carga transportada e interfaces operacionais podem mudar o resultado [shortsea2019; modalshiftreview2020].

O CabotageLens organiza essa comparação. O usuário informa a origem da carga, o destino final e a massa da remessa. O sistema calcula cada trecho das duas rotas. Na alternativa com cabotagem, distingue o porto de embarque do local onde a carga começou a viagem e o porto de desembarque do endereço final. Depois, soma os trechos para apresentar a viagem completa. A saída mostra distância, consumo, emissões operacionais e custo modelado. Também mostra a fonte dos dados e a regra aplicada em cada cálculo. Esse registro recebe o nome de proveniência.

Dois limites são importantes. Primeiro, as emissões calculadas são operacionais TTW. Na rodovia, *tank-to-wheel* (tanque à roda) considera a queima do combustível no motor e as emissões liberadas pelo escapamento. Na navegação, *tank-to-wake* (tanque à esteira) considera a combustão e as emissões geradas a bordo. Essa fronteira começa com o combustível já disponível no veículo ou no navio e, por isso, não inclui sua produção, seu processamento, seu transporte nem sua distribuição. Uma avaliação WTW — *well-to-wheel* (do poço à roda), na rodovia, e *well-to-wake* (do poço à esteira), na navegação — acompanha toda a cadeia do combustível, desde sua origem até o uso no veículo ou no navio. Ainda assim, ela não equivale necessariamente a uma avaliação completa de ciclo de vida, que também pode incluir os veículos, os navios e a infraestrutura. Segundo, o custo calculado é um custo operacional modelado. Ele não representa frete comercial, tarifa contratada ou garantia de viabilidade logística [competitiveness2024; decarb2024; maritimelca2024].

Dentro dessa comparação porta a porta, a principal contribuição metodológica do artigo está na forma como o transporte marítimo é reconstruído. O sistema não obriga o navio a seguir uma sequência previamente escolhida, como Santos–Suape–Manaus. Para calcular Santos–Manaus, ele examina uma viagem de cada vez e lê suas escalas da mais antiga para a mais recente. Na viagem observada `voyage_9612791_00011`, o recorte Santos–Manaus foi Santos–Suape–Pecém–Manaus e contribuiu com três subtrechos consecutivos. Uma viagem Manaus–Suape–Santos pertence ao sentido contrário e não é usada nesse cálculo. Assim, entram tanto os recortes diretos quanto os recortes que chegaram a Manaus depois de passar por outros portos.

## 2. Revisão da literatura e fundamentação metodológica

A literatura mostra que a cabotagem pode ser relevante em viagens longas, mas o resultado muda de uma ligação para outra [icct2022]. Uma rota pode ter uma longa navegação e acessos rodoviários curtos. Outra pode exigir muitos quilômetros por estrada até o porto. Frequência, tempo, confiabilidade, estoque e disponibilidade do serviço também influenciam a decisão real [competitiveness2024]. O CabotageLens calcula rotas, combustível, emissões operacionais e custo modelado. Ele não representa por completo todas as condições comerciais.

Estudos de *short sea shipping*, ou navegação marítima de curta distância, também mostram que não existe uma vantagem ambiental automática. O resultado depende do tipo de navio, de sua utilização, das distâncias e da carga à qual o consumo é atribuído [shortsea2019]. Por isso, a unidade analisada deve ser a remessa completa, e não um navio e um caminhão considerados isoladamente [modalshiftreview2020].

Para representar essas diferenças com dados observados, o cálculo marítimo começa pela atividade registrada no Brasil. A ANTAQ fornece os movimentos de embarque e desembarque na tabela de Carga e informa, na tabela de Atracação, onde e quando cada navio esteve. A combinação dessas informações permite ordenar as escalas e estimar a carga que permaneceu a bordo em cada trecho [antaq2025].

Depois de reconstruir a atividade do navio, o modelo precisa associar a ela uma intensidade de consumo. Para isso, utiliza a base europeia de Monitoramento, Reporte e Verificação da União Europeia (EU MRV), que publica indicadores anuais por embarcação. O número de identificação da Organização Marítima Internacional (IMO) permite ligar o navio encontrado na ANTAQ ao indicador correspondente no EU MRV [eumrv2025].

Com a atividade da ANTAQ e a intensidade do EU MRV, o sistema calcula o trabalho de transporte e o consumo de combustível. A intensidade marítima é expressa em g/(t\(\cdot\)nm), ou gramas de combustível para transportar uma tonelada por uma milha náutica. No recorte direto da viagem `voyage_9612789_00004`, por exemplo, as 11.584,165 t a bordo e as 3.300,216 nm da matriz marítima produziram 38.230.246,479 t\(\cdot\)nm de trabalho de transporte. A intensidade de 9,322050 g/(t\(\cdot\)nm) aplicada a essa atividade resultou em 356.384,277 kg de combustível. Os valores exibidos estão arredondados, enquanto o cálculo armazenado conserva maior precisão.

A fronteira ambiental adotada é a de emissões operacionais TTW de CO\(_2\)e. Uma avaliação do ciclo de vida (LCA, do inglês *life-cycle assessment*) considera outras etapas, como a produção do combustível, a fabricação, a operação e o fim de vida dos equipamentos. Fatores WTW, resultados de LCA e fatores baseados exclusivamente em dióxido de carbono (CO\(_2\)), que contabilizam somente esse gás, não são intercambiáveis com a saída do sistema [decarb2024; maritimelca2024]. Operações portuárias e períodos de navio atracado também precisam de tratamento separado, pois dependem do terminal e da operação observada [berth2009; berthairquality2010; shipops2022].

**Tabela 1 — O que está dentro e fora da comparação.**

| Dimensão        | Incluído                                                                              | Fora da fronteira                                                                                 |
| :-------------- | :------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------ |
| Alternativas    | Rodovia direta e cadeia rodoviária–cabotagem–rodoviária porta a porta                 | Comparação de um navio isolado com uma viagem rodoviária completa                                 |
| Emissões        | Emissões operacionais TTW de CO\(_2\)e por remessa                                    | WTW, LCA, fabricação de ativos e inventário completo de poluentes locais                          |
| Custo           | Estimativa do custo operacional modelado                                              | Frete comercial, negociação, seguro, estoque, multas por permanência e reserva de espaço no navio |
| Dados marítimos | Escalas e cargas da ANTAQ, intensidades do EU MRV e valores substitutos identificados | Apresentar um valor substituto como se fosse medição individual do navio                          |
| Serviço         | Sequências de portos realmente registradas no período analisado                       | Garantia de frequência, espaço no navio ou disponibilidade comercial futura                       |

## 3. Metodologia

A metodologia acompanha a sequência necessária para transformar uma remessa em duas alternativas comparáveis. Primeiro, define o serviço que ambas devem prestar. Depois, reconstrói as viagens marítimas, atribui uma intensidade de consumo aos navios, calcula o indicador representativo da ligação e, por fim, reúne os resultados de todos os trechos da rota porta a porta.

### 3.1 Unidade funcional e alternativas

As duas alternativas precisam prestar o mesmo serviço. Neste trabalho, o serviço consiste em transportar a mesma carga, do mesmo ponto de partida até o mesmo destino. Esse serviço comum recebe o nome técnico de unidade funcional. A configuração de referência utiliza uma unidade equivalente a um contêiner de 20 pés (1 TEU, do inglês *twenty-foot equivalent unit*) e 14 t. O TEU permite expressar a carga conteinerizada em uma base comum de contêineres de 20 pés. O usuário pode informar outra massa.

**O que entra:** origem da carga, destino final e massa da remessa.

**O que o sistema faz:** constrói duas viagens completas. Na primeira, o caminhão segue da origem ao destino. Na segunda, o caminhão leva a carga até o primeiro porto, o navio transporta a carga entre os portos e outro caminhão completa o percurso. Essa segunda opção é a cadeia multimodal.

**O que sai:** resultados comparáveis para a mesma remessa e para os mesmos pontos inicial e final [shortsea2019; competitiveness2024].

A massa informada pelo usuário é a carga que ele deseja transportar. Ela não é a carga total do navio. O sistema reconstrói a carga histórica do navio com os registros da ANTAQ. Essa carga histórica reconstruída determina quanto cada recorte influencia a estimativa marítima.

### 3.2 Reconstrução das viagens e da carga a bordo

Depois de definir a carga, a origem e o destino que serão comparados, o cálculo marítimo começa pela reconstrução da atividade observada dos navios.

**O que entra:** três tabelas da ANTAQ. A tabela de Carga informa o que o navio embarcou e desembarcou. A tabela de Atracação identifica o navio e o porto. A tabela de Tempos informa quando cada escala aconteceu.

**O que o sistema faz:** primeiro, reúne as chamadas portuárias do mesmo navio por meio do IMO e coloca essas chamadas em ordem de data e hora. Chamadas consecutivas do mesmo porto são reunidas. O sistema encerra uma viagem quando o navio retorna ao porto que iniciou a sequência ou quando passam mais de 240 horas, equivalentes a 10 dias, entre duas paradas. A chamada seguinte inicia outra viagem.

Em cada escala, o sistema parte da carga que já estava a bordo. Soma o que foi embarcado e subtrai o que foi desembarcado. O resultado é a carga que segue para o próximo porto.

Às vezes, o período analisado começa quando a viagem já estava em andamento. Nesse caso, a primeira escala registrada pode mostrar um desembarque sem mostrar o embarque anterior. A conta ficaria negativa. Para evitar esse resultado impossível, o sistema acrescenta somente a menor carga inicial necessária para manter todos os saldos iguais ou maiores que zero.

Um mesmo complexo portuário pode aparecer com nomes diferentes na base. O sistema primeiro soma os embarques e desembarques dessas chamadas. Depois, reúne as chamadas consecutivas que representam o mesmo complexo. Assim, uma diferença de nome não cria uma parada que o navio não realizou.

**O que sai:** uma lista na ordem da navegação. Cada linha mostra de qual porto o navio saiu, a qual porto chegou, quanta carga levava, qual distância percorreu e de onde veio essa distância.

#### Viagem observada: reconstrução por subtrechos

A viagem `voyage_9612791_00011`, realizada pelo navio de IMO 9612791, registrou Santos–Suape–Pecém–Manaus antes de retornar a Santos. Se a reconstrução começasse em zero, a soma dos saldos atingiria (-2.976,894) t. O sistema acrescentou exatamente 2.976,894 t como carga inicial mínima para impedir uma carga negativa. Em Santos, o saldo entre embarques e desembarques foi positivo em 9.881,860 t; portanto, o navio saiu de Santos com 12.858,754 t. Em Suape, o saldo foi positivo em 3.859,579 t, elevando a carga a bordo para 16.718,333 t. Em Pecém, o saldo foi negativo em 4.392,433 t, e o navio seguiu para Manaus com 12.325,900 t. Em Manaus, o saldo foi negativo em 12.325,900 t. As três distâncias usadas na tabela seguinte vieram da matriz marítima; elas não são trajetórias medidas pelo Sistema de Identificação Automática (AIS, do inglês *Automatic Identification System*).

**Tabela 2 — Carga, distância, trabalho de transporte e combustível reconstruídos na viagem `voyage_9612791_00011`.**

| Subtrecho    | Carga a bordo |    Distância |                    Trabalho |    Combustível |
| :----------- | ------------: | -----------: | --------------------------: | -------------: |
| Santos–Suape |  12.858,754 t | 1.259,179 nm | 16.191.476,419 t\(\cdot\)nm | 120.302,670 kg |
| Suape–Pecém  |  16.718,333 t |   507,806 nm |  8.489.677,588 t\(\cdot\)nm |  63.078,304 kg |
| Pecém–Manaus |  12.325,900 t | 1.185,594 nm | 14.613.514,486 t\(\cdot\)nm | 108.578,413 kg |
| Total        |             — | 2.952,580 nm | 39.294.668,494 t\(\cdot\)nm | 291.959,387 kg |

As cargas, as distâncias e os resultados exibidos na tabela foram arredondados para três casas decimais. Os totais foram calculados com os valores armazenados em maior precisão; por isso, a soma manual das linhas já arredondadas pode diferir do total em 0,001 unidade.

O sistema multiplica a carga pela distância em cada trecho. Esse produto mede quanto transporte foi realizado. Seu nome técnico é trabalho de transporte. A viagem não é representada por uma única carga média: o cálculo usa a carga que realmente estava a bordo na saída de cada porto e soma os três resultados:

\[W=\sum_{s=1}^{3}m_s d_s
=39.294.668{,}494~\mathrm{t{\cdot}nm}.\]

O número IMO 9612791 foi encontrado diretamente no EU MRV. A intensidade registrada para o navio em 2023 foi 7,43 g/(t\(\cdot\)nm). O combustível associado a toda a atividade entre Santos e Manaus foi:

\[F=\frac{7{,}43\times39.294.668{,}494}{1000}=291.959{,}387~\mathrm{kg}.\]

Esse caso mostra por que uma escala intermediária não pode ser ignorada. A carga aumentou em Suape e diminuiu em Pecém. Por isso, cada trecho foi calculado com uma carga diferente.

Para formar uma ligação marítima, o sistema escolhe um porto de embarque \(o\) e um porto de desembarque \(d\). Depois, lê na ordem todos os portos de uma viagem. Na viagem `voyage_9612791_00011`, o recorte de Santos a Manaus mantém Santos–Suape, Suape–Pecém e Pecém–Manaus, pois esses foram os três trechos consecutivos percorridos pelo navio. Esse conjunto recebe o nome técnico de *recorte histórico viagem–OD*, em que OD significa origem–destino. Ele descreve a navegação de Santos para Manaus; não descreve a viagem no sentido contrário.

Entre \(o\) e \(d\), o navio pode seguir diretamente ou parar em outros portos. A lista completa desses portos, na ordem observada, recebe o nome de corredor. Cada recorte pertence integralmente a uma única viagem, mas o mesmo corredor pode aparecer em várias viagens. O sistema nunca junta o primeiro trecho de uma viagem com o segundo trecho de outra.

Uma mesma viagem fornece apenas um recorte para a ligação escolhida. Se o navio passa mais de uma vez por um dos portos, podem existir diferentes maneiras de recortar a sequência. O sistema escolhe primeiro uma passagem direta entre os dois portos. Se não houver passagem direta, escolhe a sequência completa de menor distância dentro daquela viagem.

Antes que um recorte influencie o indicador final, o sistema verifica quatro condições. Primeiro, a parte aproveitada deve começar no porto escolhido como saída e terminar no porto escolhido como chegada, dentro da mesma viagem. No cálculo Santos–Manaus, ela começa quando o navio sai de Santos e termina quando chega a Manaus; uma sequência Manaus–Suape–Santos não serve. Segundo, nenhum trecho navegado entre essas duas escalas pode estar ausente. Terceiro, deve existir uma intensidade do próprio navio ou uma estimativa identificada. Quarto, a soma da carga a bordo multiplicada pela distância de cada trecho precisa ser positiva para receber peso. Se o peso for zero, o recorte só participa da regra especial usada quando nenhum recorte da ligação possui peso positivo.

### 3.3 Intensidade marítima por IMO e fallback robusto

Com as viagens e as cargas a bordo reconstruídas, o passo seguinte é determinar qual intensidade de consumo será aplicada a cada navio.

**O que entra:** o IMO associado à viagem na tabela de Atracação da ANTAQ e os indicadores positivos de combustível publicados no EU MRV.

**O que o sistema faz:** procura o mesmo IMO no EU MRV. Quando encontra mais de um ano, usa o indicador positivo mais recente. Esse valor pertence ao próprio navio observado na ANTAQ.

Se o IMO não aparecer no EU MRV, ainda falta uma intensidade para calcular a viagem. O sistema não inventa um valor individual: ele procura um grupo de navios semelhantes. A classe é o agrupamento mais específico disponível no arquivo de eficiência; o tipo é uma categoria mais ampla, como *container ship*. O valor calculado para o grupo substitui o dado ausente e fica identificado como estimativa. Esse procedimento recebe o nome de fallback.

A ordem de busca é:

1. indicador positivo mais recente do mesmo IMO;

2. estatística robusta da classe do navio, quando a classe está disponível;

3. estatística robusta do tipo do navio;

4. tipo documentado *container ship* quando o recorte conteinerizado não possui metadado mais específico.

Poucos valores muito altos ou muito baixos podem deslocar a média de todo o grupo. Esses valores extremos recebem o nome de outliers. Para reduzir esse efeito, o sistema usa uma estatística robusta. Essa escolha não garante que o grupo represente perfeitamente o navio ausente; ela apenas reduz a influência de poucos valores extremos.

Para a classe do navio, o sistema usa a média já registrada no arquivo de eficiência depois da retirada dos valores abaixo do percentil 1 e acima do percentil 99. Em linguagem comum, são removidas as extremidades definidas por esses dois limites antes do cálculo da média. Se essa média não estiver disponível, o sistema usa a mediana da classe.

Para o tipo do navio, o sistema mantém um valor recente por IMO e ordena a lista. Em uma amostra com \(n\) navios, retira \(\lfloor0{,}01n\rfloor\) valores do início e a mesma quantidade do fim. Depois, calcula a média do que permaneceu. Se a lista for pequena demais para retirar pelo menos um valor de cada lado, usa a mediana.

Essa retirada de extremos vale apenas para calcular o valor substituto do grupo. Quando o sistema encontra o IMO exato, mantém a intensidade daquele navio. Ele não apaga nem troca o valor apenas porque está distante dos demais.

**O que sai:** cada recorte recebe uma intensidade e uma descrição da fonte. Essa descrição informa se o valor veio do IMO do próprio navio ou de um grupo de classe ou tipo. Quando houve fallback, o sistema também registra a estatística usada, o tamanho da amostra e quantos extremos foram retirados. Assim, um valor calculado para um grupo não aparece como se fosse uma medição individual.

### 3.4 Trabalho de transporte e intensidade da ligação

Depois de escolher os portos \(o\) e \(d\), o sistema separa os trechos navegados entre eles. A letra \(v\) identifica a viagem. A letra \(s\) identifica um trecho dessa viagem. Em cada trecho, \(m_{v,s}\) é a carga a bordo em toneladas e \(d_{v,s}\) é a distância em milhas náuticas.

O sistema multiplica carga por distância em cada trecho. Depois, soma os resultados. Essa soma é o trabalho de transporte da viagem entre \(o\) e \(d\):

\[W_{v,o,d}=\sum_{s\in\mathcal{S}*{v,o,d}}m*{v,s}\,d_{v,s}.\]

Para calcular o combustível da atividade observada, o sistema multiplica esse trabalho pela intensidade \(I_v\) do navio:

\[F_{v,o,d}^{\mathrm{obs}}=\frac{I_v}{1000}
\sum_{s\in\mathcal{S}*{v,o,d}}m*{v,s}\,d_{v,s},\]

Na equação, o sobrescrito \(\mathrm{obs}\) significa “observado”, e \(I_v\) está em g/(t\(\cdot\)nm). A divisão por 1.000 transforma gramas em quilogramas.

**O que entra:** um recorte de cada viagem na qual o navio saiu do primeiro porto escolhido e chegou ao segundo porto em uma escala posterior da mesma viagem. No cálculo Santos–Manaus, entram o recorte direto da viagem `voyage_9612789_00004` e o recorte Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`, além dos demais recortes que fizeram a ligação no mesmo sentido. Uma viagem Manaus–Suape–Santos não entra, porque nela o navio navegou de Manaus para Santos. Cada recorte contém a intensidade do navio e o trabalho realizado desde a saída do primeiro porto até a chegada ao segundo. No arquivo, esse objeto recebe o nome técnico de *recorte histórico viagem–OD*.

**O que o sistema faz:** reúne todos os recortes que começam no porto escolhido como saída e terminam no porto escolhido como chegada. Um recorte pode ser direto. Outro pode conter uma ou várias escalas. Todos permanecem na mesma lista depois de passar pelas quatro verificações descritas acima.

O sistema não dá o mesmo peso a todos os recortes. O peso de um recorte é seu trabalho de transporte: a soma, em todos os trechos, da carga a bordo multiplicada pela distância daquele trecho. Quanto maior essa soma, maior a influência do recorte. O cálculo que usa esses pesos recebe o nome de mediana ponderada.

**O que sai:** uma única intensidade para simular a ligação naquele sentido. Esse resultado recebe o nome de intensidade representativa. O sentido permanece explícito: Santos–Manaus e Manaus–Santos são calculados separadamente.

Para encontrar esse valor, o sistema ordena as intensidades da menor para a maior. Depois, soma o trabalho dos recortes nessa mesma ordem. A primeira intensidade em que a soma alcança pelo menos metade do trabalho total é escolhida. Formalmente, essa regra é a mediana ponderada inferior:

\[I_{o,d}^{\mathrm{rep}}=
\min\left\{x:\sum_{v:I_v\leq x}W_{v,o,d}
\geq\frac{1}{2}\sum_vW_{v,o,d}\right\}.\]

O sobrescrito \(\mathrm{rep}\) significa “representativa” e indica que essa é a intensidade escolhida para representar a ligação.

#### Resultado observado da mediana ponderada em Santos–Manaus

Os 89 recortes aceitos para Santos–Manaus somaram 3.153.328.821,755 t\(\cdot\)nm de trabalho de transporte. A metade desse total é 1.576.664.410,877 t\(\cdot\)nm. Para encontrar a mediana ponderada, o sistema ordenou os 89 recortes da menor para a maior intensidade e acumulou o trabalho de transporte nessa ordem.

Antes de incluir a viagem `voyage_9697002_00002`, a soma acumulada correspondia a 49,168% do trabalho total. O recorte dessa viagem, realizada pelo navio de IMO 9697002, seguiu Santos–Itapoá–Rio de Janeiro–Suape–Pecém–Manaus e acrescentou 34.357.307,013 t\(\cdot\)nm. Depois de incluí-lo, a soma chegou a 50,257%. Como foi nesse ponto que o acumulado alcançou 50%, a intensidade dessa observação, 9,322050 g/(t\(\cdot\)nm), tornou-se a intensidade representativa de Santos–Manaus. A fonte registrada é a média aparada em 1% para o tipo-padrão documentado *container ship*, usado porque não havia correspondência individual aplicável pelo IMO nem classe ou tipo específico informado nessa observação. Os outros 88 recortes continuam fazendo parte do cálculo: são eles que formam o trabalho acumulado antes e depois do ponto de 50%.

Um recorte com trabalho igual a zero recebe peso zero. Ele não muda a mediana enquanto existir pelo menos um recorte com trabalho positivo. Se todos tiverem trabalho zero, o sistema calcula a mediana sem pesos e registra essa situação.

### 3.5 Separação entre intensidade e sequência de portos

O cálculo ocorre em duas etapas que não devem ser confundidas. Na preparação da base, as cargas e as distâncias das viagens históricas da ANTAQ servem somente para calcular os pesos da intensidade representativa. Na execução de um novo cenário, o sistema usa essa intensidade uma única vez, junto com a carga informada pelo usuário e com a distância de uma rota completa escolhida. As cargas históricas não são somadas à carga do usuário, e o combustível das viagens históricas não é somado ao novo cenário.

**Preparação da intensidade:** o sistema reúne todos os recortes que começam em Santos e terminam em Manaus. Entre eles estão o recorte direto da viagem `voyage_9612789_00004`, Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`, Santos–Itapoá–Paranaguá–Suape–Manaus da viagem `voyage_9343974_00002` e Santos–Navegantes–Pecém–Manaus da viagem `voyage_9852365_00011`. O último exemplo mostra concretamente que o recorte não precisa passar por Suape. A mediana ponderada de todos os recortes aceitos fornece a intensidade representativa.

**Execução com uma distância:** o sistema precisa de um corredor concreto para somar as milhas atribuídas aos subtrechos do cenário. Considera somente corredores inteiros observados dentro de uma única viagem, com distância conhecida em todos os subtrechos e um valor de consumo disponível. Se existir um recorte direto entre os dois portos, usa esse corredor. Caso contrário, escolhe o corredor completo mais curto entre os que possuem escalas. Essa escolha não elimina os outros recortes da preparação do indicador.

Em Santos–Manaus, a base contém o recorte direto da viagem `voyage_9612789_00004` e recortes com escalas, como Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`. Os dois ajudam a estimar a intensidade representativa, assim como os demais recortes aceitos para essa direção. Como existe um recorte direto, o sistema usa as 3.300,216 nm que a matriz marítima atribui a ele para representar a distância do novo cenário. Os recortes com escalas e os outros corredores não são descartados da estimativa da intensidade; apenas não fornecem a distância escolhida para o cenário.

Depois dessas duas decisões, o usuário informa a carga \(M\). O sistema multiplica essa carga pela intensidade da ligação e pela distância da sequência escolhida. O consumo marítimo é:

\[F_{o,d}^{\mathrm{cen}}=\frac{I_{o,d}^{\mathrm{rep}}\,M}{1000}
\sum_{s\in\mathcal{S}^{*}_{o,d}}d_s.\]

O sobrescrito \(\mathrm{cen}\) significa “cenário” e diferencia esse consumo calculado para a nova remessa do consumo reconstruído nas viagens históricas.

O sistema procura a distância de cada trecho na matriz marítima. Se uma distância estiver ausente, pode calcular a distância de grande círculo entre as coordenadas dos dois portos. Isso ocorreu no recorte Santos–Itapoá–Paranaguá–Suape–Manaus da viagem `voyage_9343974_00002`, realizada pelo navio de IMO 9343974. Como a matriz não continha Itapoá–Paranaguá, o sistema estimou 40,974 nm por haversine e registrou essa fonte. A intensidade dessa viagem, 6,8 g/(t\(\cdot\)nm), veio da correspondência exata do IMO no EU MRV de 2024. A distância de haversine é uma aproximação entre coordenadas; ela não confirma que o navio poderia seguir exatamente aquela linha no mar.

### 3.6 Agregação de emissões, custos e operações portuárias

Depois de definir a intensidade e a sequência de portos, o sistema calcula os resultados de cada trecho e os reúne para representar a viagem completa.

**O que entra:** o consumo de cada trecho, o preço do combustível, o fator que converte combustível em emissões e os dados disponíveis das operações portuárias.

**O que o sistema faz:** calcula separadamente cada parte da viagem. Por exemplo, mantém distintos o primeiro acesso rodoviário, a navegação e o acesso rodoviário final. Depois, soma somente as partes que foram representadas no cenário:

\[E_a=\sum_{\ell\in L_a}E_{\ell},
\qquad
C_a=\sum_{\ell\in L_a}C_{\ell}.\]

**O que sai:** os totais de emissões operacionais e custo modelado. A saída também mostra quanto cada trecho acrescentou ao total.

O combustível marítimo é convertido em emissões e custo por meio dos fatores e preços registrados. O resultado econômico não inclui margem comercial, seguro, estoque, contrato, frequência ou tarifa final de mercado.

O sistema calcula as operações portuárias em linhas separadas quando encontra uma fonte utilizável. A saída informa se o valor veio de uma medição específica da operação naquele porto, de uma média do porto ou de uma referência da literatura. Se não houver dado, mostra que o componente está indisponível. Ele não transforma silenciosamente a ausência em consumo zero.

O indicador anual do MRV considera o combustível reportado pelo navio dentro de sua fronteira. Por isso, quando esse indicador é aplicado à navegação, o sistema não soma novamente o consumo do navio enquanto ele está atracado. Esse consumo atracado recebe o nome de hoteling. Somá-lo novamente contaria parte do combustível duas vezes. O consumo dos equipamentos do terminal continua separado quando existe dado para calculá-lo [berth2009; shipops2022].

## 4. Implementação computacional

As regras descritas na metodologia foram implementadas no CabotageLens, que funciona em uma página web construída com Streamlit. O usuário informa a origem da carga, o destino final e a massa. Os cálculos ficam em módulos separados da tela. Essa separação permite testar as contas sem depender da interface.

Uma execução segue estas etapas:

1. o usuário informa a origem da carga, o destino final e a massa;

2. o sistema localiza esses lugares no mapa e obtém as distâncias rodoviárias;

3. aplica as regras de seleção de portos para formar as opções com cabotagem;

4. para cada ligação portuária, lê a intensidade, a sequência de portos, a distância e a fonte dos dados;

5. calcula consumo, emissões e custo modelado de cada trecho;

6. apresenta os totais e mostra como cada trecho participou do resultado.

O sistema prepara os dados marítimos antes da consulta do usuário. Primeiro, ordena as linhas da ANTAQ para reconstruir cada viagem, cada escala e cada movimentação de carga. Depois, associa os navios ao EU MRV pelo IMO. Também calcula os valores substitutos por classe e tipo. Por fim, grava uma tabela de consulta. Para cada porto de embarque e porto de desembarque, essa tabela guarda os recortes usados, as sequências de portos, os trechos, as intensidades e suas fontes.

Para conferir uma viagem real sem gerar registros para toda a base, o pipeline aceita o identificador da viagem com `--audit-voyage-id` e exige `--log-level DEBUG`. Na viagem `voyage_9612791_00011`, o log mostra, em cada subtrecho, o embarque, o desembarque, o saldo da escala de partida, a carga inicial reconstruída, a carga a bordo, a distância e sua fonte, o trabalho de transporte, a intensidade e sua proveniência, e o combustível calculado. O log também identifica a viagem que cruza os 50% da mediana ponderada. Esse modo apenas expõe valores intermediários e não altera o arquivo resultante.

Quando o usuário executa um cenário, a aplicação lê essa tabela já preparada. O Supabase, serviço usado para armazenar os dados da aplicação, utiliza o banco de dados PostgreSQL, também chamado de Postgres, para guardar lugares, rotas e resultados que podem ser reutilizados. Essa cópia reutilizável recebe o nome de cache. O cache evita solicitar novamente a mesma rota a um provedor. Mesmo assim, o resultado continua sendo uma rota calculada. Ele não é uma trajetória registrada pelo Sistema de Posicionamento Global (GPS), isto é, não reproduz as posições reais percorridas durante uma viagem, e não garante a existência de um serviço comercial [cabotagelensrepo; cabotagelensapp].

## 5. Evidência empírica e resultados

Esta seção verifica como o método se comporta com os dados disponíveis. Primeiro, apresenta a cobertura do cruzamento entre ANTAQ e EU MRV. Em seguida, acompanha uma execução demonstrativa do cálculo marítimo entre Santos e Manaus e, por último, compara a direção dos resultados com uma referência externa.

### 5.1 Cobertura da base ANTAQ–EU MRV

A base processada contém 1.324 viagens de cabotagem conteinerizada registradas em 2025. Nessas viagens, o sistema identificou 6.797 paradas e 7.103 chamadas portuárias. Uma chamada é um registro original de atracação ou atendimento do navio; chamadas consecutivas que representam o mesmo local são reunidas em uma parada. O trecho navegado entre duas paradas consecutivas é um subtrecho. Um recorte entre dois portos pode conter um ou vários desses subtrechos. A base também contém 389 navios diferentes por número IMO.

O sistema procurou esses 389 números no EU MRV e encontrou 243 correspondências exatas. Esses 243 navios aparecem em 788 das 1.324 viagens. Nas outras 536 viagens, a execução atual usou um valor substituto por tipo de navio. Nenhuma viagem desta execução usou fallback de classe; essa regra permanece disponível para uma base que forneça esse metadado.

**Tabela 3 — Cobertura do cruzamento entre viagens ANTAQ e intensidade EU MRV.**

| Indicador                                |                              Valor | Cobertura |
| :--------------------------------------- | ---------------------------------: | --------: |
| IMOs com correspondência exata           |                         243 de 389 |     62,5% |
| Viagens com correspondência exata        |                       788 de 1.324 |     59,5% |
| Carga em massa com correspondência exata | 15.959.761,561 de 30.191.845,948 t |     52,9% |
| Carga em TEU com correspondência exata   |   1.454.351,75 de 2.872.715,00 TEU |     50,6% |

Esses percentuais precisam ser lidos com cuidado. Uma correspondência exata significa que o mesmo número IMO apareceu na ANTAQ e no MRV. Quando isso não ocorre, o sistema ainda pode usar a intensidade calculada para um grupo de navios semelhantes. A saída identifica esse valor como estimativa do grupo. Ela não o apresenta como dado medido para aquele navio.

O sistema encontrou 177 ligações portuárias quando preservou o sentido da navegação. Santos–Manaus e Manaus–Santos, por exemplo, contam como duas ligações diferentes porque representam sentidos opostos. Ao ler cada viagem, o sistema gerou 12.025 recortes históricos viagem–OD. Esse total é maior que as 1.324 viagens porque uma viagem com várias escalas pode servir para diferentes combinações de partida e chegada. Dentro da viagem `voyage_9612791_00011`, o prefixo Santos–Suape–Pecém–Manaus fornece seis recortes: Santos–Suape, Santos–Pecém, Santos–Manaus, Suape–Pecém, Suape–Manaus e Pecém–Manaus. A viagem completa ainda retorna de Manaus a Santos e, por isso, pode fornecer outras ligações. Cada recorte mantém o número da viagem e somente os subtrechos entre os dois portos que definem aquela ligação.

Os 12.025 recortes reutilizam 5.438 subtrechos navegados entre paradas consecutivas. Um mesmo subtrecho pode fazer parte de mais de um recorte da mesma viagem. A distância de 5.023 subtrechos veio da matriz marítima. Nos outros 415, o sistema precisou usar a aproximação de haversine. A intensidade de 3.290 subtrechos veio do IMO do navio. Nos outros 2.148, veio de uma estimativa de grupo. Portanto, todos os subtrechos possuem um número para o cálculo, mas nem todos possuem uma intensidade individual observada no MRV.

### 5.2 Execução demonstrativa: Santos–Manaus

Esta subseção mostra como os dados e as regras se combinam em uma execução concreta.

**Preparação do indicador:** o sistema encontrou 89 viagens nas quais o navio saiu de Santos e chegou a Manaus em uma escala posterior da mesma viagem. De cada viagem, foi aproveitado o recorte entre a saída de Santos e a chegada a Manaus. Todos os 89 recortes realizaram trabalho de transporte maior que zero.

Os 89 recortes não seguiram uma única sequência. O sistema encontrou 22 listas diferentes de portos entre Santos e Manaus. Um recorte foi direto. Os demais contêm uma ou mais escalas intermediárias. Cada lista completa é um corredor observado, e um corredor pode reunir vários recortes de viagens diferentes. A viagem `voyage_9852365_00011`, por exemplo, fornece Santos–Navegantes–Pecém–Manaus, um corredor que não passa por Suape.

Em 40 recortes, o sistema encontrou o IMO no EU MRV e usou a intensidade do próprio navio. Nos outros 49, usou o valor substituto do tipo de embarcação. Embora sejam 49 de 89 recortes, eles representam 59,54% de todo o trabalho de transporte acumulado nessa ligação.

**O que o sistema faz:** primeiro, ordena as intensidades dos 89 recortes. Depois, soma o trabalho de transporte nessa ordem. A soma alcança metade do trabalho total na intensidade de 9,322050 g/(t\(\cdot\)nm). Esse é o valor usado para representar Santos–Manaus. Os recortes dos 22 corredores participam dessa conta. O navio não precisa passar por Suape nem por qualquer outro porto predeterminado.

O ponto de 50% cai em uma viagem que usa o tipo-padrão documentado *container ship*, pois o registro não trazia classe ou tipo específico. Por isso, a intensidade final coincide com esse fallback robusto. Para calcular o fallback, o sistema reuniu 243 valores positivos, um por IMO. Ordenou a lista, retirou os dois menores e os dois maiores e calculou a média dos 239 restantes.

Sem retirar os extremos, a média dos 243 valores seria 21,661852 g/(t\(\cdot\)nm). A mediana simples da mesma lista seria 4,620000 g/(t\(\cdot\)nm). Esses dois números ajudam a entender a dispersão dos dados. O sistema não os usa no lugar da regra registrada para Santos–Manaus.

**Execução da nova remessa:** os 89 recortes históricos definem a intensidade de 9,322050 g/(t\(\cdot\)nm). As cargas históricas servem apenas para calcular os pesos. Elas não são somadas à carga informada pelo usuário, e o combustível das 89 viagens históricas não é somado ao novo cenário. A execução usa a intensidade uma vez e percorre a distância de uma única sequência concreta de portos.

Para escolher essa distância, o sistema encontrou um recorte direto de Santos a Manaus dentro da viagem `voyage_9612789_00004`. A regra dá preferência a esse recorte sem escala intermediária. A matriz marítima atribui 6.112 quilômetros (km), equivalentes a 3.300,216 nm, ao subtrecho. Essa escolha vale somente para a distância modelada do cenário. Os 89 recortes continuam participando da intensidade.

É possível conferir a mesma fórmula com o recorte direto observado em `voyage_9612789_00004`. O navio de IMO 9612789 saiu de Santos com 11.584,165 t e chegou a Manaus na escala seguinte. A matriz marítima atribuiu 3.300,216 nm ao subtrecho. A intensidade usada foi 9,322050 g/(t\(\cdot\)nm), obtida pela média aparada em 1% do tipo-padrão documentado *container ship*, porque não havia correspondência individual aplicável pelo IMO nem classe ou tipo específico informado:

\[\begin{split}
F_{\mathrm{Santos,Manaus}}
&=\frac{9{,}322050\times11.584{,}165\times3.300{,}216}{1000}\\
&\simeq356.384{,}277~\text{kg de combustível}.
\end{split}\]

**O que sai:** a reconstrução dessa viagem histórica resulta em 356.384,277 kg de combustível e 38.230.246,479 t\(\cdot\)nm de trabalho de transporte. Em um novo cenário, as 11.584,165 t observadas nessa viagem são substituídas pela carga informada pelo usuário; elas não são usadas como carga padrão.

Esse número não é o total da alternativa multimodal. Ele não inclui o acesso rodoviário da origem até Santos, o acesso rodoviário de Manaus até o destino final, nem as operações portuárias. Esses componentes são calculados e apresentados separadamente quando o cenário completo é executado.

### 5.3 Benchmark externo

Depois da análise detalhada de Santos–Manaus, a planilha associada aos estudos de Gustavo Costa fornece uma comparação externa [workbookdados]. Ela contém 21 ligações entre seis cidades. Em todas, a carga de referência é um contêiner de 14 t.

Na planilha, as emissões semanais agregadas são 7.614,97 toneladas de dióxido de carbono equivalente (tCO\(_2\)e) para o cenário rodoviário e 4.159,79 tCO\(_2\)e para o cenário com cabotagem. A diferença é aproximadamente 45,4%.

Esses valores mostram o sentido e a ordem de grandeza do resultado dentro das regras da própria planilha. Eles não servem para escolher ou ajustar a intensidade marítima do CabotageLens. As duas análises podem usar rotas, fatores e limites diferentes.

## 6. Discussão e limitações

Os resultados mostram que o cálculo marítimo depende da combinação de três tipos de informação. A ANTAQ mostra por quais portos o navio passou, o que ele embarcou ou desembarcou e qual é seu IMO. O EU MRV fornece a intensidade do próprio navio quando contém o mesmo IMO. Quando o IMO não aparece, o sistema estima o valor com embarcações semelhantes: procura primeiro o grupo mais específico, chamado de classe, e depois uma categoria mais ampla, chamada de tipo. A saída informa qual dessas fontes foi usada.

O sistema acompanha cada trecho entre duas escalas. Portanto, uma parada intermediária não desaparece da conta. A carga pode mudar nessa parada, e o trecho seguinte usa o novo valor.

O sistema examina todas as viagens nas quais o navio saiu do porto escolhido como início e chegou ao porto escolhido como fim. No cálculo Santos–Manaus, o recorte direto de `voyage_9612789_00004` e o recorte com escalas de `voyage_9612791_00011`, que passou por Suape e Pecém antes de chegar a Manaus, participam da mesma estimativa. Uma viagem Manaus–Suape–Santos não participa porque percorreu o sentido contrário. Nenhum subtrecho entre os dois portos pode estar ausente, e deve existir uma intensidade identificada. Somente os recortes em que a soma da carga a bordo multiplicada pela distância de cada subtrecho é maior que zero recebem peso na mediana.

As principais limitações são:

- **Período observado:** o recorte de 2025 não representa automaticamente outros anos. Viagens no começo ou no fim da janela podem estar incompletas.

- **Cobertura do MRV:** nem todos os navios aparecem na base europeia. O valor substituto representa um grupo de navios. Ele não é uma medição da embarcação ausente. Em Santos–Manaus, as viagens com esse valor concentram 59,54% do trabalho. Por isso, o ponto de 50% cai no fallback.

- **Valores extremos:** o sistema trata extremos somente ao calcular uma estimativa de grupo. Para a classe, usa os limites dos percentis 1 e 99 registrados no arquivo; para o tipo, retira uma quantidade inteira correspondente a 1% de cada lado quando a amostra permite. Uma intensidade encontrada pelo IMO permanece na base. Ela só determina a mediana ponderada se os pesos acumulados chegarem ao ponto de 50% naquele valor.

- **Distâncias marítimas:** a matriz contém distâncias calculadas para representar a navegação. Quando o sistema usa haversine, mede apenas a linha de grande círculo entre os portos. Essa linha pode não coincidir com uma rota navegável.

- **Oferta de serviço:** uma viagem observada mostra que a sequência ocorreu na janela analisada. Ela não garante frequência futura, espaço disponível ou serviço comercial regular.

- **Fronteira ambiental:** os resultados são emissões operacionais TTW de CO\(_2\)e. Não incluem produção do combustível, construção de veículos, navios ou infraestrutura, nem uma LCA completa.

- **Fronteira econômica:** o valor monetário estima componentes operacionais. Não é cotação de frete, contrato de armador ou análise comercial completa.

Por essas razões, um resultado favorável à cabotagem em determinado cenário não demonstra superioridade universal. A ferramenta é um instrumento de triagem e comparação auditável. Uma decisão logística ainda precisa considerar serviço, tempo, capacidade, terminais e preços comerciais [competitiveness2024; modalshiftreview2020].

## 7. Conclusão e trabalhos futuros

Em síntese, o CabotageLens compara duas maneiras de levar a mesma carga ao mesmo destino. Na primeira, o caminhão percorre toda a rota. Na segunda, caminhões fazem os acessos terrestres e um navio percorre o trecho entre os portos.

No cálculo marítimo, o sistema lê as escalas da ANTAQ na ordem em que aconteceram. Depois de cada escala, calcula quanto o navio leva para o próximo porto. Em seguida, procura o IMO no EU MRV. Se encontrar, usa a intensidade do próprio navio. Se não encontrar, usa um valor substituto de classe ou tipo e registra essa decisão.

Para analisar Santos–Manaus, o sistema examina uma viagem de cada vez e lê suas escalas na ordem em que aconteceram. Na viagem `voyage_9612791_00011`, o navio saiu de Santos, passou por Suape e Pecém e chegou a Manaus; por isso, os três subtrechos consecutivos entram no recorte Santos–Manaus. Uma viagem Manaus–Suape–Santos não entra, porque o navio fez o percurso no sentido contrário. O recorte aceito pode ser direto ou conter outros portos. Cada recorte recebe um peso igual à soma da carga a bordo multiplicada pela distância de cada subtrecho. A intensidade na qual o trabalho acumulado alcança metade do total representa Santos–Manaus.

Em uma etapa separada, o sistema escolhe o corredor usado para calcular a distância do cenário. Considera somente corredores inteiros observados dentro de uma única viagem, com distância conhecida em todos os subtrechos e um valor de consumo disponível. Se existir um recorte direto, usa esse corredor. Caso contrário, escolhe o corredor completo mais curto entre os que possuem escalas. Essa escolha não retira os outros recortes do cálculo da intensidade.

Em Santos–Manaus, 89 recortes históricos provenientes de 89 viagens distintas seguiram 22 sequências de portos. Desses recortes, 40 usam o IMO do próprio navio e 49 usam o valor substituto do tipo. O trabalho total é 3.153.328.821,755 t\(\cdot\)nm, e o ponto de 50% é cruzado pela viagem `voyage_9697002_00002`. Por isso, o cálculo resulta em 9,322050 g/(t\(\cdot\)nm). No recorte direto de `voyage_9612789_00004`, essa intensidade, aplicada a 11.584,165 t e às 3.300,216 nm da matriz marítima, corresponde a 356.384,277 kg de combustível de navegação. A conta não inclui acessos rodoviários nem operações portuárias.

Trabalhos futuros devem ampliar a janela da ANTAQ, aumentar a cobertura por IMO e incorporar informações de frequência e disponibilidade de serviço. Também são importantes distâncias marítimas mais detalhadas, operações portuárias baseadas em atividade observada, análise de incerteza, preços comerciais verificáveis e uma futura expansão da fronteira ambiental para WTW ou ciclo de vida.

## Referências

As citações permanecem identificadas por suas chaves, entre colchetes, para facilitar a validação e a posterior sincronização com o LaTeX. Os dados bibliográficos completos estão em [`docs/references.bib`](references.bib), e os limites de uso de cada fonte estão registrados no [mapa de citações da literatura](tf_support/writing/tf_literature_citation_map.md).
