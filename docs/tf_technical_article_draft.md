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

O transporte de cargas no Brasil é fortemente concentrado nas rodovias. Em 2015, o modal rodoviário respondeu por 65% da atividade de transporte de cargas, medida em toneladas-quilômetro úteis (TKU). No mesmo recorte, a ferrovia respondeu por 15% e a cabotagem por 11%. A distribuição ajuda a explicar por que o caminhão é a referência mais imediata para transportar cargas no país, inclusive em trajetos longos.

![Distribuição da atividade de transporte de cargas no Brasil em 2015.](images/grafico%20da%20atividade%20modal%20do%20transporte%20no%20Brasil%20em%202015.jpeg)

*Figura 1 — Distribuição da atividade de transporte de cargas no Brasil em 2015, medida em TKU. Fonte: [Sindicato dos Bancários de São Paulo, Osasco e Região (2018)](https://spbancarios.com.br/05/2018/brasil-e-dependente-do-transporte-rodoviario-de-cargas), com dados de 2015 do Plano Nacional de Logística, conforme informado pela publicação.*

Além do papel predominante na matriz, o transporte rodoviário de cargas depende principalmente do diesel e contribui para as emissões de gases de efeito estufa do setor. Por isso, políticas de transporte buscam transferir parte das viagens longas para modais mais eficientes. No Livro Branco dos Transportes, a Comissão Europeia definiu a meta de transferir, até 2030, 30% das cargas rodoviárias transportadas por mais de 300 km para ferrovias ou vias aquaviárias e, até 2050, mais de 50% [Comissão Europeia, 2011](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52011DC0144). Nesse contexto, a cabotagem — o transporte marítimo entre portos do mesmo país utilizando a navegação pela costa nacional ou por vias interiores — é uma alternativa possível para parte das cargas de longa distância no Brasil [icct2022].

Para saber se a cabotagem faz sentido em uma ligação específica, a comparação precisa ser porta a porta. Uma comparação porta a porta começa no local onde a carga está e termina no local em que ela será entregue. As duas alternativas precisam prestar exatamente o mesmo serviço: transportar a mesma massa entre esses dois pontos. No caminho rodoviário, o caminhão percorre todo o trajeto por estrada. Na alternativa com cabotagem, a carga segue de caminhão até o porto de embarque, é transportada pelo navio entre os portos e, depois, segue de caminhão do porto de desembarque até o destino final. Por isso, a análise soma distância, consumo, emissões e custo de todas essas etapas, em vez de comparar apenas o trecho marítimo com a viagem rodoviária completa. Os portos escolhidos, as distâncias de acesso, a carga e as operações de transbordo podem mudar o resultado [shortsea2019; modalshiftreview2020].

É para tornar essa comparação possível que foi desenvolvido o CabotageLens. O usuário informa a origem, o destino e a massa da carga, e o sistema constrói as duas alternativas de transporte. Para cada uma, apresenta a distância total, o consumo de combustível, as emissões operacionais e o custo modelado. Ao reunir essas informações em uma mesma base de comparação, a ferramenta permite avaliar, para cada ligação, como a alternativa com cabotagem se diferencia da rota feita inteiramente por estrada. Com isso, a comparação deixa de ser uma escolha abstrata entre caminhão e navio e passa a considerar a operação logística completa.

## 2. Revisão da literatura e fundamentação metodológica

A literatura mostra que a cabotagem pode ser relevante em viagens longas, mas o resultado muda de uma ligação para outra [icct2022]. Uma rota pode ter uma longa navegação e acessos rodoviários curtos. Outra pode exigir muitos quilômetros por estrada até o porto. Frequência, tempo, confiabilidade, estoque e disponibilidade do serviço também influenciam a decisão real [competitiveness2024]. O CabotageLens calcula rotas, combustível, emissões operacionais e custo modelado. Ele não representa por completo todas as condições comerciais.

Estudos de *short sea shipping*, ou navegação marítima de curta distância, também mostram que não existe uma vantagem ambiental automática. O resultado depende do tipo de navio, de sua utilização, das distâncias e da carga à qual o consumo é atribuído [shortsea2019]. Por isso, a unidade analisada deve ser a remessa completa, e não um navio e um caminhão considerados isoladamente [modalshiftreview2020].

Um princípio metodológico do estudo é dar preferência a dados públicos, oficiais, observados e auditáveis. A Agência Nacional de Transportes Aquaviários (ANTAQ), órgão federal que regula e acompanha o transporte aquaviário brasileiro, fornece os registros de escalas e de movimentação de carga. A base europeia de Monitoramento, Reporte e Verificação da União Europeia (EU MRV) publica indicadores anuais de consumo e atividade dos navios. Essas fontes permitem relacionar uma operação registrada no Brasil ao desempenho do navio identificado pelo número da Organização Marítima Internacional (IMO), uma identificação permanente da embarcação. Os campos utilizados, os arquivos de origem e a forma de reconstruir as viagens são apresentados na Seção 3.3 [antaq2025; eumrv2025].

A fronteira ambiental adotada é a de emissões operacionais TTW de CO$_2$e. Uma avaliação do ciclo de vida (LCA, do inglês *life-cycle assessment*) considera outras etapas, como a produção do combustível, a fabricação, a operação e o fim de vida dos equipamentos. Fatores WTW, resultados de LCA e fatores baseados exclusivamente em dióxido de carbono (CO$_2$), que contabilizam somente esse gás, não são intercambiáveis com a saída do sistema [decarb2024; maritimelca2024]. Operações portuárias e períodos de navio atracado também precisam de tratamento separado, pois dependem do terminal e da operação observada [berth2009; berthairquality2010; shipops2022].

**Tabela 4 — O que está dentro e fora da comparação.**

| Dimensão        | Incluído                                                                              | Fora da fronteira                                                                                 |
| :-------------- | :------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------ |
| Emissões        | Emissões operacionais TTW de CO$_2$e por remessa                                      | WTW, LCA, fabricação de ativos e inventário completo de poluentes locais                          |
| Custo           | Estimativa do custo operacional modelado                                              | Frete comercial, negociação, seguro, estoque, multas por permanência e reserva de espaço no navio |
| Dados marítimos | Escalas e cargas da ANTAQ, intensidades do EU MRV e valores substitutos identificados | Apresentar um valor substituto como se fosse medição individual do navio                          |
| Serviço         | Sequências de portos realmente registradas no período analisado                       | Garantia de frequência, espaço no navio ou disponibilidade comercial futura                       |

## 3. Metodologia

O ponto de partida do método é uma pergunta simples: qual é o consumo, o custo operacional e a emissão associados a levar uma mesma remessa de uma origem até um destino? Para respondê-la sem comparar serviços diferentes, o sistema monta duas alternativas completas para a mesma carga e os mesmos pontos inicial e final. Na alternativa rodoviária, a carga segue integralmente por caminhão. Na alternativa com cabotagem, ela percorre um acesso rodoviário até o porto de embarque, a perna marítima entre os portos e um acesso rodoviário final até o destino. Cada parte é calculada separadamente e, ao final, os resultados são somados.

Esta seção apresenta essa construção em termos logísticos e físicos. Primeiro, descreve como a alternativa rodoviária transforma distância e carga em consumo de diesel. Depois, explica como a atividade marítima observada é usada para formar a perna de navegação. A Seção 4 mostra como essas regras foram organizadas no sistema.

### 3.1 Serviço comparado e alternativas logísticas

As duas alternativas precisam prestar o mesmo serviço: transportar a mesma massa, do mesmo ponto de partida até o mesmo destino. Esse serviço comum recebe o nome técnico de unidade funcional. A configuração de referência corresponde a um contêiner de 20 pés (1 TEU, do inglês *twenty-foot equivalent unit*) com 14 t, mas o usuário pode informar outra massa. O TEU é uma unidade usada para expressar carga conteinerizada a partir do tamanho de um contêiner de 20 pés.

Na alternativa rodoviária, há um único trecho: origem → destino. Na alternativa com cabotagem, há três trechos: origem → porto de embarque; porto de embarque → porto de desembarque; e porto de desembarque → destino. Assim, a cabotagem não é comparada apenas com uma parte da rota terrestre: as duas opções começam e terminam nos mesmos lugares [shortsea2019; competitiveness2024].

A massa informada pelo usuário representa a remessa do cenário. Ela não é a carga total de um navio. Os registros históricos de carga dos navios são usados somente para estimar a intensidade da navegação e não são somados à carga da remessa.

### 3.2 Alternativa rodoviária: distância, veículo e consumo de diesel

O cálculo rodoviário começa pela distância total entre a origem e o destino. O sistema obtém uma rota rodoviária em quilômetros e utiliza essa distância para representar o percurso do caminhão. A mesma lógica é aplicada aos acessos terrestres da alternativa com cabotagem: um trecho entre a origem e o porto de embarque e outro entre o porto de desembarque e o destino.

Em seguida, a massa transportada define o veículo representativo. O modelo utiliza os rendimentos médios por número de eixos publicados pela **Agência Nacional de Transportes Terrestres (ANTT)**. Esses dados oficiais foram obtidos na tabela da Política Nacional de Pisos Mínimos do Transporte Rodoviário de Cargas, disponibilizada no [portal de legislação da ANTT (ANTTlegis)](https://anttlegis.antt.gov.br/action/UrlPublicasAction.php?acao=abrirAtoPublico&cod_menu=9230&cod_modulo=623&num_ato=00000001&seq_ato=ATT&sgl_orgao=SUROC%2FANTT%2FMT&sgl_tipo=POR&vlr_ano=2025). A tabela de referência adotada no modelo associa a faixa de carga ao número de eixos e relaciona cada configuração à eficiência básica em quilômetros por litro (km/L). A seleção automática é uma regra de modelagem para estimar consumo; não é uma verificação de limite legal de peso nem substitui o planejamento operacional de uma transportadora.

**Tabela 5 — Regra automática para o veículo rodoviário representativo e eficiência básica adotada.**

| Massa da remessa | Veículo representativo | Eixos | Eficiência básica |
| :--------------- | :--------------------- | ----: | ----------------: |
| Até 18 t | Carreta | 5 | 2,3 km/L |
| Acima de 18 t até 30 t | Carreta | 6 | 2,0 km/L |
| Acima de 30 t até 40 t | Bitrem | 7 | 2,0 km/L |
| Acima de 40 t | Rodotrem | 9 | 2,0 km/L |

*Fonte: elaboração do sistema a partir dos rendimentos médios por número de eixos publicados pela Agência Nacional de Transportes Terrestres (ANTT), no portal ANTTlegis.*

Com a distância rodoviária $D_{\mathrm{rod}}$, em quilômetros, a eficiência escolhida $\eta_{\mathrm{rod}}$, em km/L, e $N$ viagens carregadas necessárias para transportar a remessa, o consumo de diesel do trecho é calculado por:

$$
F_{\mathrm{rod}}=N\frac{D_{\mathrm{rod}}}{\eta_{\mathrm{rod}}}.
$$

Como exemplo real, usemos os 3.491 km de distância rodoviária entre São Paulo e Rio Branco. Para transportar uma remessa de 14 t nessa ligação, o modelo seleciona uma carreta de cinco eixos, com eficiência básica de 2,3 km/L. Como a remessa cabe em uma viagem carregada, o consumo estimado é $1\times3.491/2{,}3=1.517{,}826$ L de diesel. Quando a carga exige mais de uma viagem do veículo escolhido, o sistema multiplica esse consumo pelo número necessário de viagens carregadas. Os litros calculados são posteriormente convertidos em custo e emissões com os fatores e preços adotados pelo cenário.

### 3.3 Alternativa multimodal

A alternativa multimodal também precisa levar a remessa do ponto inicial ao ponto final. Ela é formada por três partes: o acesso rodoviário até o porto de embarque, a navegação entre os portos e o acesso rodoviário depois do desembarque. Portanto, o combustível é consumido não só pelo navio, em cada subtrecho marítimo, mas também nos deslocamentos da origem até o porto de embarque e do porto de desembarque até o destino final. Além disso, o sistema calcula separadamente o consumo das operações nos terminais portuários.

Os próximos subitens mostram como esses componentes são formados: a escolha dos portos define os extremos da ligação; os acessos terrestres usam o cálculo rodoviário; as viagens registradas permitem reconstruir a navegação e a carga a bordo; a intensidade define o consumo do navio; e a agregação reúne combustível, emissões, custo e operações portuárias.

#### 3.3.1 Escolha dos portos

O sistema associa a origem ao porto mais próximo disponível na base portuária e faz o mesmo para o destino. Esses dois portos definem a ligação marítima que será pesquisada. Essa regra fornece uma forma objetiva de montar o cenário, mas não afirma que o porto é necessariamente a melhor escolha comercial ou operacional. Um porto mais distante pode ser preferível na prática por motivos como frequência de navios, contrato, terminal, custo ou disponibilidade de espaço, fatores que não são decididos por essa seleção geográfica.

#### 3.3.2 Acessos rodoviários: *first mile* e *last mile*

O primeiro acesso, chamado de *first mile*, leva a carga da origem até o porto de embarque. O segundo, chamado de *last mile*, leva a carga do porto de desembarque até o destino final. Para cada um deles, o sistema obtém uma distância rodoviária e aplica a mesma regra de veículo, eficiência e consumo de diesel descrita na Seção 3.2.

#### 3.3.3 Operações portuárias

As operações portuárias são as atividades necessárias para transferir o contêiner entre o caminhão, o pátio, o cais e o navio. Elas podem consumir combustível nos equipamentos do terminal, como o guindaste de cais (*ship-to-shore*, ou STS), o guindaste sobre pneus do pátio (*rubber-tyred gantry*, ou RTG) e os caminhões que circulam internamente no terminal. Esse consumo não pertence ao trajeto rodoviário nem à navegação entre portos; por isso, é calculado e apresentado em separado.

O cálculo começa convertendo a carga do cenário em contêineres equivalentes. Quando o usuário não informa a quantidade de TEU, o sistema divide a massa por 14 t, arredonda o resultado para cima e usa essa quantidade como número de contêineres. Para cada porto atendido e para cada equipamento, multiplica o número de contêineres pelo número de movimentos necessários por contêiner e pelo consumo específico do equipamento. Para os equipamentos a diesel, o consumo em litros é convertido em massa de combustível:

$$
F_{\mathrm{porto},e}=P\times T\times a_e\times f_e\times\rho.
$$

Em que $P$ é o número de escalas portuárias consideradas, $T$ é a quantidade de contêineres equivalentes, $a_e$ é o número de movimentos do equipamento $e$ por contêiner, $f_e$ é o consumo de diesel do equipamento por movimento, em L/movimento, e $\rho$ é a densidade do diesel, em kg/L. O consumo portuário total é a soma dos resultados dos equipamentos com parâmetros disponíveis.

No cenário de referência baseado em Santos, uma escala que movimenta uma remessa de 14 t corresponde a 1 TEU. O RTG realiza quatro movimentos por contêiner; com o valor mediano de 0,355148 L por movimento, consome 1,421 L de diesel. O caminhão interno do terminal realiza dois movimentos; com 0,494671 L por movimento, consome 0,989 L. Assim, os equipamentos com fator de consumo disponível somam 2,410 L, ou 2,048 kg de diesel, em uma escala.

Substituindo esses valores na fórmula, o consumo de cada equipamento é:

$$
F_{\mathrm{porto,RTG}}
=1\times1\times4\times0{,}355148\times0{,}85
=1{,}208~\mathrm{kg}.
$$

$$
F_{\mathrm{porto,cam}}
=1\times1\times2\times0{,}494671\times0{,}85
=0{,}841~\mathrm{kg}.
$$

$$
F_{\mathrm{porto,total}}
=1{,}208+0{,}841
=2{,}048~\mathrm{kg}.
$$

#### 3.3.4 Reconstrução das viagens e da carga a bordo

Depois de definir a carga, a origem e o destino que serão comparados, o cálculo marítimo começa pela reconstrução da atividade observada dos navios. Os arquivos brutos não entregam uma viagem pronta: cada linha registra uma escala ou uma movimentação de carga. A reconstrução liga esses registros ao mesmo navio, coloca as escalas na ordem em que ocorreram e calcula a carga que permaneceu a bordo entre um porto e outro.

Os dados vêm da Agência Nacional de Transportes Aquaviários (ANTAQ). O arquivo de Carga informa a massa e os contêineres embarcados ou desembarcados em cada escala. O arquivo de Atracação identifica o porto, as datas e o número da Organização Marítima Internacional (IMO) do navio. A tabela a seguir mostra os campos brutos usados para reconstituir os movimentos de carga.

**Tabela 1 — Campos do arquivo `2025Carga.txt` usados para reconstruir os movimentos de carga.**

| Coluna | Uso na avaliação | Valor na viagem `voyage_9612791_00011` |
| :-- | :-- | :-- |
| `IDAtracacao` | Liga cada movimento de carga à escala correspondente. | Santos: `1618801`; Suape: `1625119`; Pecém: `1625546`; Manaus: `1620276`. |
| `Tipo Navegação` | Mantém somente os registros de cabotagem. | `Cabotagem` nas quatro escalas. |
| `TEU` | Ajuda a identificar a carga conteinerizada e registra a quantidade de contêineres em unidade equivalente a 20 pés. | Santos: 866/0; Suape: 881/804; Pecém: 187/541; Manaus: 621/1.639 (embarcados/desembarcados). |
| `Natureza da Carga` e `Carga Geral Acondicionamento` | Complementam a identificação da carga conteinerizada quando necessário. | `Carga Conteinerizada` e `Conteinerizada` em todas as linhas da viagem. |
| `VLPesoCargaBruta` | Informa a massa embarcada ou desembarcada, em toneladas. | Santos: 9.881,860/0; Suape: 11.862,199/8.002,620; Pecém: 3.231,914/7.624,347; Manaus: 7.571,660/19.897,560 t (embarcados/desembarcados). |
| `Sentido` | Indica se a massa foi embarcada ou desembarcada na escala. | Santos: `Embarcados`; nas demais escalas: `Embarcados` e `Desembarcados`. |
| `Origem` e `Destino` | Preservam os códigos dos portos de origem e destino declarados para a carga. | Santos reúne 3 pares declarados; Suape, 5; Pecém, 7; Manaus, 10. |

*Arquivo: `2025Carga.txt`. Fonte: [Agência Nacional de Transportes Aquaviários (ANTAQ), Painel Estatístico Aquaviário](https://estatistica.antaq.gov.br/ea/sense/download.html).*

*Nos campos `TEU` e `VLPesoCargaBruta`, os valores mostrados são a soma das linhas brutas do mesmo `IDAtracacao`, separadas por sentido.*

**Tabela 2 — Campos do arquivo `2025Atracacao.txt` usados para identificar e ordenar as escalas dos navios.**

| Coluna | Uso na avaliação | Valor na viagem `voyage_9612791_00011` |
| :-- | :-- | :-- |
| `IDAtracacao` | Liga a escala aos movimentos de carga do arquivo `2025Carga.txt`. | `1618801`; `1625119`; `1625546`; `1620276`. |
| `CDTUP` e `Porto Atracação` | Identificam o porto ou a instalação portuária da escala. | `BRSSZ` — Santos; `BRSUA` — Suape; `BRCE001` — Terminal Portuário do Pecém; `BRAM012` — Super Terminais Comércio e Indústria. |
| `Data Atracação` | Define a ordem cronológica das escalas. | 30/09/2025 03:57; 05/10/2025 10:06; 08/10/2025 03:23; 13/10/2025 18:00. |
| `Data Chegada` e `Data Desatracação` | Registram o intervalo observado da escala. | Santos: 29/09 05:45–30/09 17:30; Suape: 04/10 06:45–06/10 08:50; Pecém: 07/10 14:00–08/10 16:38; Manaus: 13/10 16:30–17/10 06:20. |
| `Tipo de Navegação da Atracação` | Registra o tipo de navegação informado para a escala. | Santos, Suape e Pecém: `Cabotagem`; Manaus: `Interior`. |
| `Terminal`, `Município` e `UF` | Complementam a identificação do local atendido. | Santos Brasil, Guarujá/SP; TECON Suape, Ipojuca/PE; Terminal do Pecém, São Gonçalo do Amarante/CE; Super Terminais, Manaus/AM. |
| `Nº do IMO` | Identifica o navio e permite procurá-lo no EU MRV. | `9612791` nas quatro escalas. |

*Arquivo: `2025Atracacao.txt`. Fonte: [Agência Nacional de Transportes Aquaviários (ANTAQ), Painel Estatístico Aquaviário](https://estatistica.antaq.gov.br/ea/sense/download.html).*

Na viagem `voyage_9612791_00011`, o navio de IMO 9612791 atracou em Santos em 30 de setembro de 2025 e embarcou 9.881,860 t. Em seguida, passou por Suape e Pecém. Em 13 de outubro, atracou no terminal Super Terminais Comércio e Indústria, em Manaus, onde desembarcou 19.897,560 t e embarcou 7.571,660 t. Esse exemplo mostra que os dados não descrevem somente uma ligação Santos–Manaus: eles registram o que aconteceu em cada escala, e é essa sequência que o sistema precisa reconstituir.

Além dos dois arquivos apresentados, a tabela de Tempos da ANTAQ registra os horários das escalas e ajuda a confirmar sua ordem. A reconstrução segue quatro passos.

1. Primeiro, o sistema reúne as escalas que possuem o mesmo IMO e as ordena por data e hora. Assim, deixa de tratar Santos, Suape, Pecém e Manaus como registros isolados e passa a enxergá-los como uma sequência percorrida pelo mesmo navio.

2. Em seguida, o sistema soma os embarques e desembarques de uma mesma escala. Quando há registros consecutivos que representam o mesmo complexo portuário, eles são reunidos para que uma diferença de nome não crie uma parada inexistente. Uma viagem termina quando o navio retorna ao porto que iniciou aquela sequência ou quando passam mais de 240 horas, equivalentes a 10 dias, entre duas paradas. A parada seguinte inicia outra viagem.

3. Para cada escala, o sistema começa pela carga que já estava a bordo, soma o que foi embarcado e subtrai o que foi desembarcado. O saldo resultante é a carga que parte para o próximo porto. Quando o período analisado começa no meio de uma viagem, o primeiro registro pode mostrar um desembarque sem mostrar o embarque anterior. Nessa situação, o sistema acrescenta somente a menor carga inicial necessária para que nenhum saldo fique negativo.

4. Por fim, o sistema cria um subtrecho entre cada par de paradas consecutivas. O resultado é uma lista na ordem da navegação: porto de saída, porto de chegada, carga a bordo, distância percorrida e fonte da distância. Essa lista é a base para calcular o trabalho de transporte e o consumo marítimo.

##### Viagem observada: reconstrução por subtrechos

A viagem `voyage_9612791_00011`, realizada pelo navio de IMO 9612791, registrou Santos–Suape–Pecém–Manaus antes de retornar a Santos. Se a reconstrução começasse em zero, a soma dos saldos atingiria (-2.976,894) t. O sistema acrescentou exatamente 2.976,894 t como carga inicial mínima para impedir uma carga negativa. Em Santos, o saldo entre embarques e desembarques foi positivo em 9.881,860 t; portanto, o navio saiu de Santos com 12.858,754 t. Em Suape, o saldo foi positivo em 3.859,579 t, elevando a carga a bordo para 16.718,333 t. Em Pecém, o saldo foi negativo em 4.392,433 t, e o navio seguiu para Manaus com 12.325,900 t. Em Manaus, o saldo foi negativo em 12.325,900 t. As três distâncias usadas na tabela seguinte vieram da matriz marítima; elas não são trajetórias medidas pelo Sistema de Identificação Automática (AIS, do inglês *Automatic Identification System*).

**Tabela 6 — Carga, distância, trabalho de transporte e combustível reconstruídos na viagem `voyage_9612791_00011`.**

| Subtrecho    | Carga a bordo |    Distância |                    Trabalho |    Combustível |
| :----------- | ------------: | -----------: | --------------------------: | -------------: |
| Santos–Suape |  12.858,754 t | 1.259,179 nm | 16.191.476,419 t$\cdot$nm   | 120.302,670 kg |
| Suape–Pecém  |  16.718,333 t |   507,806 nm |  8.489.677,588 t$\cdot$nm   |  63.078,304 kg |
| Pecém–Manaus |  12.325,900 t | 1.185,594 nm | 14.613.514,486 t$\cdot$nm   | 108.578,413 kg |
| Total        |             — | 2.952,580 nm | 39.294.668,494 t$\cdot$nm   | 291.959,387 kg |

As cargas, as distâncias e os resultados exibidos na tabela foram arredondados para três casas decimais. Os totais foram calculados com os valores armazenados em maior precisão; por isso, a soma manual das linhas já arredondadas pode diferir do total em 0,001 unidade.

O sistema multiplica a carga pela distância em cada trecho. Esse produto mede quanto transporte foi realizado. Seu nome técnico é trabalho de transporte. A viagem não é representada por uma única carga média: o cálculo usa a carga que realmente estava a bordo na saída de cada porto e soma os três resultados:

$$
W=\sum_{s=1}^{3}m_s d_s
=39.294.668{,}494~\mathrm{t{\cdot}nm}.
$$

O número IMO 9612791 foi encontrado diretamente no EU MRV. A intensidade registrada para o navio em 2023 foi 7,43 g/(t$\cdot$nm). O combustível associado a toda a atividade entre Santos e Manaus foi:

$$
F=\frac{7{,}43\times39.294.668{,}494}{1000}=291.959{,}387~\mathrm{kg}.
$$

Esse caso mostra por que uma escala intermediária não pode ser ignorada. A carga aumentou em Suape e diminuiu em Pecém. Por isso, cada trecho foi calculado com uma carga diferente.

Para formar uma ligação marítima, o sistema escolhe um porto de embarque $o$ e um porto de desembarque $d$. Depois, lê na ordem todos os portos de uma viagem. Na viagem `voyage_9612791_00011`, o recorte de Santos a Manaus mantém Santos–Suape, Suape–Pecém e Pecém–Manaus, pois esses foram os três trechos consecutivos percorridos pelo navio. Esse conjunto recebe o nome técnico de *recorte histórico viagem–OD*, em que OD significa origem–destino. Ele descreve a navegação de Santos para Manaus; não descreve a viagem no sentido contrário.

Entre $o$ e $d$, o navio pode seguir diretamente ou parar em outros portos. A lista completa desses portos, na ordem observada, recebe o nome de corredor. Cada recorte pertence integralmente a uma única viagem, mas o mesmo corredor pode aparecer em várias viagens. O sistema nunca junta o primeiro trecho de uma viagem com o segundo trecho de outra.

Uma mesma viagem fornece apenas um recorte para a ligação escolhida. Se o navio passa mais de uma vez por um dos portos, podem existir diferentes maneiras de recortar a sequência. O sistema escolhe primeiro uma passagem direta entre os dois portos. Se não houver passagem direta, escolhe a sequência completa de menor distância dentro daquela viagem.

Antes que um recorte influencie o indicador final, o sistema verifica quatro condições. Primeiro, a parte aproveitada deve começar no porto escolhido como saída e terminar no porto escolhido como chegada, dentro da mesma viagem. No cálculo Santos–Manaus, ela começa quando o navio sai de Santos e termina quando chega a Manaus; uma sequência Manaus–Suape–Santos não serve. Segundo, nenhum trecho navegado entre essas duas escalas pode estar ausente. Terceiro, deve existir uma intensidade do próprio navio ou uma estimativa identificada. Quarto, a soma da carga a bordo multiplicada pela distância de cada trecho precisa ser positiva para receber peso. Se o peso for zero, o recorte só participa da regra especial usada quando nenhum recorte da ligação possui peso positivo.

#### 3.3.5 Intensidade marítima por IMO e fallback robusto

Com as viagens e as cargas a bordo reconstruídas, o passo seguinte é determinar qual intensidade de consumo será aplicada a cada navio. Para isso, o sistema usa a base europeia de Monitoramento, Reporte e Verificação da União Europeia (EU MRV), que publica indicadores anuais de consumo, atividade e emissões por embarcação. O número IMO registrado na ANTAQ permite procurar o mesmo navio nessa base. Na viagem `voyage_9612791_00011`, o IMO 9612791 foi encontrado diretamente no EU MRV de 2023, com intensidade de $7{,}43\ \mathrm{g/(t\cdot nm)}$ [eumrv2025].

**Tabela 3 — Dados do EU MRV usados para a viagem `voyage_9612791_00011`.**

| Fonte ou campo | Valor usado | Papel no cálculo |
| :-- | :-- | :-- |
| Arquivo de origem | `2023-v85-08022026-EU MRV Publication of information.xlsx` | Publicação anual consultada para obter o indicador do navio. |
| `IMO Number` | `9612791` | Faz a correspondência direta com as escalas observadas na ANTAQ. |
| `Ship type` | `Container ship` | Classificação do navio informada na base. |
| `Annual average Fuel consumption per transport work (mass)` | $7{,}43\ \mathrm{g/(t\cdot nm)}$ | Intensidade de combustível aplicada aos subtrechos desse navio. |
| Regra de seleção | Valor positivo mais recente para o mesmo IMO | Mantém o indicador individual do navio; não utiliza valor substituto. |

*Fonte: [THETIS-MRV, Agência Europeia de Segurança Marítima (EMSA)](https://mrv.emsa.europa.eu/), publicação anual de informações do EU MRV.*

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

Para o tipo do navio, o sistema mantém um valor recente por IMO e ordena a lista. Em uma amostra com $n$ navios, retira $\lfloor0{,}01n\rfloor$ valores do início e a mesma quantidade do fim. Depois, calcula a média do que permaneceu. Se a lista for pequena demais para retirar pelo menos um valor de cada lado, usa a mediana.

Essa retirada de extremos vale apenas para calcular o valor substituto do grupo. Quando o sistema encontra o IMO exato, mantém a intensidade daquele navio. Ele não apaga nem troca o valor apenas porque está distante dos demais.

**O que sai:** cada recorte recebe uma intensidade e uma descrição da fonte. Essa descrição informa se o valor veio do IMO do próprio navio ou de um grupo de classe ou tipo. Quando houve fallback, o sistema também registra a estatística usada, o tamanho da amostra e quantos extremos foram retirados. Assim, um valor calculado para um grupo não aparece como se fosse uma medição individual.

#### 3.3.6 Trabalho de transporte e intensidade da ligação

Depois de escolher os portos $o$ e $d$, o sistema separa os trechos navegados entre eles. A letra $v$ identifica a viagem. A letra $s$ identifica um trecho dessa viagem. Em cada trecho, $m_{v,s}$ é a carga a bordo em toneladas e $d_{v,s}$ é a distância em milhas náuticas.

O sistema multiplica carga por distância em cada trecho. Depois, soma os resultados. Essa soma é o trabalho de transporte da viagem entre $o$ e $d$:

$$
W_{v,o,d}=\sum_{s\in\mathcal{S}*{v,o,d}}m*{v,s}\,d_{v,s}.
$$

Para calcular o combustível da atividade observada, o sistema multiplica esse trabalho pela intensidade $I_v$ do navio:

$$
F_{v,o,d}^{\mathrm{obs}}=\frac{I_v}{1000}
\sum_{s\in\mathcal{S}*{v,o,d}}m*{v,s}\,d_{v,s},
$$

Na equação, o sobrescrito $\mathrm{obs}$ significa “observado”, e $I_v$ está em g/(t$\cdot$nm). A divisão por 1.000 transforma gramas em quilogramas.

**O que entra:** um recorte de cada viagem na qual o navio saiu do primeiro porto escolhido e chegou ao segundo porto em uma escala posterior da mesma viagem. No cálculo Santos–Manaus, entram o recorte direto da viagem `voyage_9612789_00004` e o recorte Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`, além dos demais recortes que fizeram a ligação no mesmo sentido. Uma viagem Manaus–Suape–Santos não entra, porque nela o navio navegou de Manaus para Santos. Cada recorte contém a intensidade do navio e o trabalho realizado desde a saída do primeiro porto até a chegada ao segundo. No arquivo, esse objeto recebe o nome técnico de *recorte histórico viagem–OD*.

**O que o sistema faz:** reúne todos os recortes que começam no porto escolhido como saída e terminam no porto escolhido como chegada. Um recorte pode ser direto. Outro pode conter uma ou várias escalas. Todos permanecem na mesma lista depois de passar pelas quatro verificações descritas acima.

O sistema não dá o mesmo peso a todos os recortes. O peso de um recorte é seu trabalho de transporte: a soma, em todos os trechos, da carga a bordo multiplicada pela distância daquele trecho. Quanto maior essa soma, maior a influência do recorte. O cálculo que usa esses pesos recebe o nome de mediana ponderada.

**O que sai:** uma única intensidade para simular a ligação naquele sentido. Esse resultado recebe o nome de intensidade representativa. O sentido permanece explícito: Santos–Manaus e Manaus–Santos são calculados separadamente.

Para encontrar esse valor, o sistema ordena as intensidades da menor para a maior. Depois, soma o trabalho dos recortes nessa mesma ordem. A primeira intensidade em que a soma alcança pelo menos metade do trabalho total é escolhida. Formalmente, essa regra é a mediana ponderada inferior:

$$
I_{o,d}^{\mathrm{rep}}=
\min\left\{x:\sum_{v:I_v\leq x}W_{v,o,d}
\geq\frac{1}{2}\sum_vW_{v,o,d}\right\}.
$$

O sobrescrito $\mathrm{rep}$ significa “representativa” e indica que essa é a intensidade escolhida para representar a ligação.

##### Resultado observado da mediana ponderada em Santos–Manaus

Os 89 recortes aceitos para Santos–Manaus somaram 3.153.328.821,755 t$\cdot$nm de trabalho de transporte. A metade desse total é 1.576.664.410,877 t$\cdot$nm. Para encontrar a mediana ponderada, o sistema ordenou os 89 recortes da menor para a maior intensidade e acumulou o trabalho de transporte nessa ordem.

Antes de incluir a viagem `voyage_9697002_00002`, a soma acumulada correspondia a 49,168% do trabalho total. O recorte dessa viagem, realizada pelo navio de IMO 9697002, seguiu Santos–Itapoá–Rio de Janeiro–Suape–Pecém–Manaus e acrescentou 34.357.307,013 t$\cdot$nm. Depois de incluí-lo, a soma chegou a 50,257%. Como foi nesse ponto que o acumulado alcançou 50%, a intensidade dessa observação, 9,322050 g/(t$\cdot$nm), tornou-se a intensidade representativa de Santos–Manaus. A fonte registrada é a média aparada em 1% para o tipo-padrão documentado *container ship*, usado porque não havia correspondência individual aplicável pelo IMO nem classe ou tipo específico informado nessa observação. Os outros 88 recortes continuam fazendo parte do cálculo: são eles que formam o trabalho acumulado antes e depois do ponto de 50%.

Um recorte com trabalho igual a zero recebe peso zero. Ele não muda a mediana enquanto existir pelo menos um recorte com trabalho positivo. Se todos tiverem trabalho zero, o sistema calcula a mediana sem pesos e registra essa situação.

#### 3.3.7 Separação entre intensidade e sequência de portos

O cálculo ocorre em duas etapas que não devem ser confundidas. Na preparação da base, as cargas e as distâncias das viagens históricas da ANTAQ servem somente para calcular os pesos da intensidade representativa. Na execução de um novo cenário, o sistema usa essa intensidade uma única vez, junto com a carga informada pelo usuário e com a distância de uma rota completa escolhida. As cargas históricas não são somadas à carga do usuário, e o combustível das viagens históricas não é somado ao novo cenário.

**Preparação da intensidade:** o sistema reúne todos os recortes que começam em Santos e terminam em Manaus. Entre eles estão o recorte direto da viagem `voyage_9612789_00004`, Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`, Santos–Itapoá–Paranaguá–Suape–Manaus da viagem `voyage_9343974_00002` e Santos–Navegantes–Pecém–Manaus da viagem `voyage_9852365_00011`. O último exemplo mostra concretamente que o recorte não precisa passar por Suape. A mediana ponderada de todos os recortes aceitos fornece a intensidade representativa.

**Execução com uma distância:** o sistema precisa de um corredor concreto para somar as milhas atribuídas aos subtrechos do cenário. Considera somente corredores inteiros observados dentro de uma única viagem, com distância conhecida em todos os subtrechos e um valor de consumo disponível. Se existir um recorte direto entre os dois portos, usa esse corredor. Caso contrário, escolhe o corredor completo mais curto entre os que possuem escalas. Essa escolha não elimina os outros recortes da preparação do indicador.

Em Santos–Manaus, a base contém o recorte direto da viagem `voyage_9612789_00004` e recortes com escalas, como Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`. Os dois ajudam a estimar a intensidade representativa, assim como os demais recortes aceitos para essa direção. Como existe um recorte direto, o sistema usa as 3.300,216 nm que a matriz marítima atribui a ele para representar a distância do novo cenário. Os recortes com escalas e os outros corredores não são descartados da estimativa da intensidade; apenas não fornecem a distância escolhida para o cenário.

Depois dessas duas decisões, o usuário informa a carga $M$. O sistema multiplica essa carga pela intensidade da ligação e pela distância da sequência escolhida. O consumo marítimo é:

$$
F_{o,d}^{\mathrm{cen}}=\frac{I_{o,d}^{\mathrm{rep}}\,M}{1000}
\sum_{s\in\mathcal{S}^{*}_{o,d}}d_s.
$$

O sobrescrito $\mathrm{cen}$ significa “cenário” e diferencia esse consumo calculado para a nova remessa do consumo reconstruído nas viagens históricas.

O sistema procura a distância de cada trecho na matriz marítima. Se uma distância estiver ausente, pode calcular a distância de grande círculo entre as coordenadas dos dois portos. Isso ocorreu no recorte Santos–Itapoá–Paranaguá–Suape–Manaus da viagem `voyage_9343974_00002`, realizada pelo navio de IMO 9343974. Como a matriz não continha Itapoá–Paranaguá, o sistema estimou 40,974 nm por haversine e registrou essa fonte. A intensidade dessa viagem, 6,8 g/(t$\cdot$nm), veio da correspondência exata do IMO no EU MRV de 2024. A distância de haversine é uma aproximação entre coordenadas; ela não confirma que o navio poderia seguir exatamente aquela linha no mar.

#### 3.3.8 Agregação de emissões, custos e operações portuárias

Depois de definir a intensidade e a sequência de portos, o sistema calcula os resultados de cada trecho e os reúne para representar a viagem completa.

**O que entra:** o consumo de cada trecho, o preço do combustível, o fator que converte combustível em emissões e os dados disponíveis das operações portuárias.

**O que o sistema faz:** calcula separadamente cada parte da viagem. Por exemplo, mantém distintos o primeiro acesso rodoviário, a navegação e o acesso rodoviário final. Depois, soma somente as partes que foram representadas no cenário:

$$
E_a=\sum_{\ell\in L_a}E_{\ell},
\qquad
C_a=\sum_{\ell\in L_a}C_{\ell}.
$$

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

**Tabela 7 — Cobertura do cruzamento entre viagens ANTAQ e intensidade EU MRV.**

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

**O que o sistema faz:** primeiro, ordena as intensidades dos 89 recortes. Depois, soma o trabalho de transporte nessa ordem. A soma alcança metade do trabalho total na intensidade de 9,322050 g/(t$\cdot$nm). Esse é o valor usado para representar Santos–Manaus. Os recortes dos 22 corredores participam dessa conta. O navio não precisa passar por Suape nem por qualquer outro porto predeterminado.

O ponto de 50% cai em uma viagem que usa o tipo-padrão documentado *container ship*, pois o registro não trazia classe ou tipo específico. Por isso, a intensidade final coincide com esse fallback robusto. Para calcular o fallback, o sistema reuniu 243 valores positivos, um por IMO. Ordenou a lista, retirou os dois menores e os dois maiores e calculou a média dos 239 restantes.

Sem retirar os extremos, a média dos 243 valores seria 21,661852 g/(t$\cdot$nm). A mediana simples da mesma lista seria 4,620000 g/(t$\cdot$nm). Esses dois números ajudam a entender a dispersão dos dados. O sistema não os usa no lugar da regra registrada para Santos–Manaus.

**Execução da nova remessa:** os 89 recortes históricos definem a intensidade de 9,322050 g/(t$\cdot$nm). As cargas históricas servem apenas para calcular os pesos. Elas não são somadas à carga informada pelo usuário, e o combustível das 89 viagens históricas não é somado ao novo cenário. A execução usa a intensidade uma vez e percorre a distância de uma única sequência concreta de portos.

Para escolher essa distância, o sistema encontrou um recorte direto de Santos a Manaus dentro da viagem `voyage_9612789_00004`. A regra dá preferência a esse recorte sem escala intermediária. A matriz marítima atribui 6.112 quilômetros (km), equivalentes a 3.300,216 nm, ao subtrecho. Essa escolha vale somente para a distância modelada do cenário. Os 89 recortes continuam participando da intensidade.

É possível conferir a mesma fórmula com o recorte direto observado em `voyage_9612789_00004`. O navio de IMO 9612789 saiu de Santos com 11.584,165 t e chegou a Manaus na escala seguinte. A matriz marítima atribuiu 3.300,216 nm ao subtrecho. A intensidade usada foi 9,322050 g/(t$\cdot$nm), obtida pela média aparada em 1% do tipo-padrão documentado *container ship*, porque não havia correspondência individual aplicável pelo IMO nem classe ou tipo específico informado:

$$
\begin{split}
F_{\mathrm{Santos,Manaus}}
&=\frac{9{,}322050\times11.584{,}165\times3.300{,}216}{1000}\\
&\simeq356.384{,}277~\text{kg de combustível}.
\end{split}
$$

**O que sai:** a reconstrução dessa viagem histórica resulta em 356.384,277 kg de combustível e 38.230.246,479 t$\cdot$nm de trabalho de transporte. Em um novo cenário, as 11.584,165 t observadas nessa viagem são substituídas pela carga informada pelo usuário; elas não são usadas como carga padrão.

Esse número não é o total da alternativa multimodal. Ele não inclui o acesso rodoviário da origem até Santos, o acesso rodoviário de Manaus até o destino final, nem as operações portuárias. Esses componentes são calculados e apresentados separadamente quando o cenário completo é executado.

### 5.3 Benchmark externo

Depois da análise detalhada de Santos–Manaus, a planilha associada aos estudos de Gustavo Costa fornece uma comparação externa [workbookdados]. Ela contém 21 ligações entre seis cidades. Em todas, a carga de referência é um contêiner de 14 t.

Na planilha, as emissões semanais agregadas são 7.614,97 toneladas de dióxido de carbono equivalente (tCO$_2$e) para o cenário rodoviário e 4.159,79 tCO$_2$e para o cenário com cabotagem. A diferença é aproximadamente 45,4%.

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

- **Fronteira ambiental:** os resultados são emissões operacionais TTW de CO$_2$e. Não incluem produção do combustível, construção de veículos, navios ou infraestrutura, nem uma LCA completa.

- **Fronteira econômica:** o valor monetário estima componentes operacionais. Não é cotação de frete, contrato de armador ou análise comercial completa.

Por essas razões, um resultado favorável à cabotagem em determinado cenário não demonstra superioridade universal. A ferramenta é um instrumento de triagem e comparação auditável. Uma decisão logística ainda precisa considerar serviço, tempo, capacidade, terminais e preços comerciais [competitiveness2024; modalshiftreview2020].

## 7. Conclusão e trabalhos futuros

Em síntese, o CabotageLens compara duas maneiras de levar a mesma carga ao mesmo destino. Na primeira, o caminhão percorre toda a rota. Na segunda, caminhões fazem os acessos terrestres e um navio percorre o trecho entre os portos.

No cálculo marítimo, o sistema lê as escalas da ANTAQ na ordem em que aconteceram. Depois de cada escala, calcula quanto o navio leva para o próximo porto. Em seguida, procura o IMO no EU MRV. Se encontrar, usa a intensidade do próprio navio. Se não encontrar, usa um valor substituto de classe ou tipo e registra essa decisão.

Para analisar Santos–Manaus, o sistema examina uma viagem de cada vez e lê suas escalas na ordem em que aconteceram. Na viagem `voyage_9612791_00011`, o navio saiu de Santos, passou por Suape e Pecém e chegou a Manaus; por isso, os três subtrechos consecutivos entram no recorte Santos–Manaus. Uma viagem Manaus–Suape–Santos não entra, porque o navio fez o percurso no sentido contrário. O recorte aceito pode ser direto ou conter outros portos. Cada recorte recebe um peso igual à soma da carga a bordo multiplicada pela distância de cada subtrecho. A intensidade na qual o trabalho acumulado alcança metade do total representa Santos–Manaus.

Em uma etapa separada, o sistema escolhe o corredor usado para calcular a distância do cenário. Considera somente corredores inteiros observados dentro de uma única viagem, com distância conhecida em todos os subtrechos e um valor de consumo disponível. Se existir um recorte direto, usa esse corredor. Caso contrário, escolhe o corredor completo mais curto entre os que possuem escalas. Essa escolha não retira os outros recortes do cálculo da intensidade.

Em Santos–Manaus, 89 recortes históricos provenientes de 89 viagens distintas seguiram 22 sequências de portos. Desses recortes, 40 usam o IMO do próprio navio e 49 usam o valor substituto do tipo. O trabalho total é 3.153.328.821,755 t$\cdot$nm, e o ponto de 50% é cruzado pela viagem `voyage_9697002_00002`. Por isso, o cálculo resulta em 9,322050 g/(t$\cdot$nm). No recorte direto de `voyage_9612789_00004`, essa intensidade, aplicada a 11.584,165 t e às 3.300,216 nm da matriz marítima, corresponde a 356.384,277 kg de combustível de navegação. A conta não inclui acessos rodoviários nem operações portuárias.

Trabalhos futuros devem ampliar a janela da ANTAQ, aumentar a cobertura por IMO e incorporar informações de frequência e disponibilidade de serviço. Também são importantes distâncias marítimas mais detalhadas, operações portuárias baseadas em atividade observada, análise de incerteza, preços comerciais verificáveis e uma futura expansão da fronteira ambiental para WTW ou ciclo de vida.

## Referências

As citações permanecem identificadas por suas chaves, entre colchetes, para facilitar a validação e a posterior sincronização com o LaTeX. Os dados bibliográficos completos estão em [`docs/references.bib`](references.bib), e os limites de uso de cada fonte estão registrados no [mapa de citações da literatura](tf_support/writing/tf_literature_citation_map.md).
