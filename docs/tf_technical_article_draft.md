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

**Tabela 1 — O que está dentro e fora da comparação.**

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

**Tabela 2 — Regra automática para o veículo rodoviário representativo e eficiência básica adotada.**

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

#### 3.3.4 Consumo de combustível na perna marítima

A perna marítima é o consumo de combustível estimado para levar a remessa pelo mar, em uma viagem de cabotagem, entre o porto de embarque e o porto de desembarque.

##### 3.3.4.1 Atividade observada na ANTAQ e reconstrução das viagens

Para estimar esse consumo, o sistema primeiro precisa reconstruir o que o navio realmente fez. Os arquivos brutos da ANTAQ não trazem uma viagem pronta, como “Santos–Manaus”. Cada linha registra apenas um evento: uma escala em um porto ou uma movimentação de carga. O sistema reúne os registros do mesmo navio, coloca as escalas na ordem em que ocorreram e calcula a carga que permaneceu a bordo em cada trecho entre dois portos.

Os dados são fornecidos pela Agência Nacional de Transportes Aquaviários (ANTAQ). O arquivo de Carga informa a massa e os contêineres embarcados ou desembarcados em cada escala. O arquivo de Atracação identifica o porto, as datas e o número da Organização Marítima Internacional (IMO) do navio. As tabelas a seguir mostram os campos brutos usados para reconstituir os movimentos de carga.

**Tabela 3 — Campos do arquivo `2025Carga.txt` usados para reconstruir os movimentos de carga.**

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

**Tabela 4 — Campos do arquivo `2025Atracacao.txt` usados para identificar e ordenar as escalas dos navios.**

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

A integração desses dados permite afirmar que na viagem `voyage_9612791_00011`, o navio de IMO 9612791 atracou em Santos em 30 de setembro de 2025 e embarcou 9.881,860 t. Em seguida, passou por Suape e Pecém. Em 13 de outubro, atracou no terminal Super Terminais Comércio e Indústria, em Manaus, onde desembarcou 19.897,560 t e embarcou 7.571,660 t. Esse exemplo mostra que os dados não descrevem somente uma ligação Santos–Manaus: eles registram o que aconteceu em cada escala, e é essa sequência que o sistema reconstrói.

Para tornar a reconstrução concreta, a Figura 2 mostra somente a parte de ida da viagem `voyage_9612791_00011`, entre Santos e Manaus. Em cada seta, a carga é aquela que estava a bordo enquanto o navio navegava para o porto seguinte.

```mermaid
flowchart LR
    S[Santos] -->|1.259,179 nm<br/>Carga a bordo: 12.858,754 t| U[Suape]
    U -->|507,806 nm<br/>Carga a bordo: 16.718,333 t| P[Pecém]
    P -->|1.185,594 nm<br/>Carga a bordo: 12.325,900 t| M[Manaus]
```

*Figura 2 — Parte de ida reconstruída da viagem `voyage_9612791_00011`. Fonte: elaboração própria com dados de Carga e Atracação da ANTAQ e distâncias da matriz marítima do sistema.*

O período observado começou quando o navio já levava 2.976,894 t a bordo. Essa é a menor carga inicial necessária para que os saldos da viagem não fiquem negativos. Em Santos, o navio embarcou 9.881,860 t e saiu com 12.858,754 t. Em Suape, embarcou mais carga do que desembarcou, por isso a carga a bordo aumentou para 16.718,333 t. Em Pecém, desembarcou mais do que embarcou e seguiu para Manaus com 12.325,900 t.

O fluxo mostra por que as escalas intermediárias não podem ser ignoradas: cada uma altera a carga que será transportada no subtrecho seguinte. Para representar uma ligação entre dois portos, o sistema usa apenas a sequência contínua observada dentro de uma mesma viagem e no mesmo sentido. Assim, Santos–Suape–Pecém–Manaus pode contribuir para a ligação Santos–Manaus, enquanto Manaus–Suape–Santos não pode.

##### 3.3.4.2 Atribuição do consumo com dados do EU MRV

A ANTAQ informa por onde o navio passou e qual carga levava, mas não informa diretamente quanto combustível ele consumiu. Essa atribuição é feita com a base de Monitoramento, Reporte e Verificação da União Europeia (EU MRV), que publica indicadores anuais de consumo, atividade e emissões por embarcação. O número IMO registrado na ANTAQ permite procurar o mesmo navio nessa base. Na viagem `voyage_9612791_00011`, o IMO 9612791 foi encontrado diretamente no EU MRV de 2023, com intensidade de $7{,}43\ \mathrm{g/(t\cdot nm)}$ [eumrv2025].

**Tabela 5 — Dados do EU MRV usados para a viagem `voyage_9612791_00011`.**

| Fonte ou campo | Valor usado | Papel no cálculo |
| :-- | :-- | :-- |
| Arquivo de origem | `2023-v85-08022026-EU MRV Publication of information.xlsx` | Publicação anual consultada para obter o indicador do navio. |
| `IMO Number` | `9612791` | Faz a correspondência direta com as escalas observadas na ANTAQ. |
| `Ship type` | `Container ship` | Classificação do navio informada na base. |
| `Annual average Fuel consumption per transport work (mass)` | $7{,}43\ \mathrm{g/(t\cdot nm)}$ | Intensidade de combustível aplicada aos subtrechos desse navio. |
| Regra de seleção | Valor positivo mais recente para o mesmo IMO | Mantém o indicador individual do navio; não utiliza valor substituto. |

*Fonte: [THETIS-MRV, Agência Europeia de Segurança Marítima (EMSA)](https://mrv.emsa.europa.eu/), publicação anual de informações do EU MRV.*

O sistema procura primeiro o mesmo IMO no EU MRV. Quando encontra mais de um ano para o mesmo navio, usa o indicador positivo mais recente. Esse é o melhor caso: a intensidade pertence ao próprio navio que apareceu na ANTAQ.

Mesmo quando há correspondência por IMO, o sistema verifica se o indicador é compatível com os valores observados para navios do mesmo tipo. Quando a base tem pelo menos 20 navios desse tipo, valores acima do percentil 95 são tratados como anômalos. A viagem da ANTAQ continua no cálculo, com sua carga e suas distâncias, mas sua intensidade é substituída pela estatística robusta da classe, se ela estiver disponível, ou do tipo do navio. A saída registra o IMO encontrado, o valor original, o limiar aplicado, o tamanho do grupo de comparação e a fonte da estimativa usada.

Essa regra é necessária porque uma intensidade muito alta, embora publicada no EU MRV, pode dominar a média de uma ligação. No conjunto de 243 navios classificados como *container ship*, o percentil 95 é $24{,}073\ \mathrm{g/(t\cdot nm)}$. Em Santos–Manaus, os IMOs 9603221 (*Fernão de Magalhães*, $228{,}83\ \mathrm{g/(t\cdot nm)}$), 9603233 (*Américo Vespúcio*, $49{,}00\ \mathrm{g/(t\cdot nm)}$) e 9602875 (*Sebastião Caboto*, $230{,}23\ \mathrm{g/(t\cdot nm)}$) ultrapassam esse limiar. Os 21 recortes dessas embarcações permanecem entre as viagens observadas, mas recebem a estimativa documentada do tipo *container ship*, de $9{,}322050\ \mathrm{g/(t\cdot nm)}$.

Nem todos os navios que operam no Brasil aparecem na base europeia. Quando isso ocorre, o sistema continua usando os valores publicados no EU MRV, mas busca um grupo de navios semelhantes. Primeiro, procura a classe do navio, que é o grupo mais específico disponível. Se ela não estiver disponível, procura o tipo, que é uma categoria mais ampla, como *container ship*. Para recortes conteinerizados sem outro metadado, usa o grupo documentado como *container ship*. O valor obtido é identificado como uma estimativa do grupo, e não como uma medição do navio ausente.

Para calcular essa estimativa, o sistema evita que poucos valores muito altos ou muito baixos definam o resultado do grupo. Na classe, usa a média depois de retirar os valores abaixo do percentil 1 e acima do percentil 99; se essa média não estiver disponível, usa a mediana. No tipo, guarda um valor recente por IMO, retira 1% dos extremos de cada lado quando a quantidade de navios permite e calcula a média dos valores restantes. Quando o grupo é pequeno demais para essa retirada, usa a mediana.

Cada recorte recebe uma intensidade e uma descrição clara de sua origem: IMO do próprio navio, estimativa pela classe ou estimativa pelo tipo. Quando o indicador individual ultrapassa o limiar de anomalia, a saída registra também o valor original e a regra que levou à estimativa de grupo. Quando a intensidade vem de um grupo, a saída informa a estatística usada, o tamanho da amostra e quantos valores extremos foram retirados. Assim, uma estimativa coletiva não aparece como se fosse uma medição individual.

###### Exemplo de estimativa pelo tipo de navio

A viagem `voyage_9974486_00001`, realizada pelo navio de IMO 9974486, passou por Paranaguá, Rio de Janeiro e Salvador. Esse IMO aparece nos registros da ANTAQ, mas não possui correspondência individual no EU MRV. Como o registro também não traz uma classe mais específica, o sistema usa os dados do tipo documentado *container ship* na própria base do EU MRV.

Para formar esse valor, o sistema reuniu um indicador positivo e mais recente de cada um dos 243 navios classificados como *container ship* no EU MRV. Depois de ordenar os valores, retirou os dois menores e os dois maiores, equivalentes a 1% da amostra em cada extremidade. Restaram 239 valores para o cálculo:

$$
I_{\mathrm{container\ ship}}
=\frac{\sum_{j=1}^{239} I_j}{239}
=9{,}322050\ \mathrm{g/(t\cdot nm)}.
$$

Portanto, todos os subtrechos dessa viagem recebem a intensidade de $9{,}322050\ \mathrm{g/(t\cdot nm)}$. A saída identifica esse número como uma estimativa baseada no tipo *container ship*, e não como uma medição do navio de IMO 9974486.

##### 3.3.4.3 Trabalho de transporte e intensidade da ligação

Uma viagem pode ter uma ou várias escalas entre os dois portos escolhidos. Para saber quanto transporte ela realizou, o sistema não usa uma carga média para toda a viagem. Ele calcula cada subtrecho com a carga que o navio levava ao sair daquele porto.

O resultado de multiplicar a carga pela distância recebe o nome de trabalho de transporte. Para uma viagem $v$, entre a origem $o$ e o destino $d$, o cálculo é:

$$
W_{v,o,d}=\sum_{s\in\mathcal{S}_{v,o,d}}m_{v,s}\,d_{v,s}.
$$

Nessa fórmula, $\mathcal{S}_{v,o,d}$ reúne os subtrechos da viagem entre os dois portos escolhidos, $m_{v,s}$ é a carga a bordo no subtrecho $s$, em toneladas, e $d_{v,s}$ é a distância desse subtrecho, em milhas náuticas. O resultado $W_{v,o,d}$ é expresso em tonelada-milha náutica ($\mathrm{t\cdot nm}$).

Na viagem `voyage_9612791_00011`, o recorte Santos–Manaus contém três subtrechos, mostrados na Figura 2. O trabalho de transporte é:

$$
\begin{aligned}
W_{\mathrm{Santos,Manaus}}
&=(12.858{,}754\times1.259{,}179)\\
&+(16.718{,}333\times507{,}806)\\
&+(12.325{,}900\times1.185{,}594)\\
&\approx39.294.668{,}494\ \mathrm{t\cdot nm}.
\end{aligned}
$$

As cargas e as distâncias exibidas na Figura 2 foram arredondadas para três casas decimais. O valor final da fórmula foi calculado com os números armazenados com maior precisão; por isso, uma conta manual feita apenas com os valores exibidos pode apresentar pequena diferença.

Como a intensidade do navio de IMO 9612791 é $7{,}43\ \mathrm{g/(t\cdot nm)}$, o consumo associado a essa atividade observada é:

$$
F_{\mathrm{Santos,Manaus}}=
\frac{7{,}43\times39.294.668{,}494}{1000}
=291.959{,}387\ \mathrm{kg}.
$$

Para formar uma ligação, o sistema repete esse cálculo em todas as viagens que saíram do porto de origem e chegaram ao porto de destino no mesmo sentido. Cada sequência contínua entre os dois portos é um recorte histórico da viagem. Ela pode ser direta, como Santos–Manaus, ou conter escalas intermediárias, como Santos–Suape–Pecém–Manaus. O sistema nunca combina trechos de viagens diferentes, nem usa uma viagem no sentido contrário.

As viagens não recebem o mesmo peso na escolha da intensidade da ligação. Uma viagem que transportou mais carga por uma distância maior representa uma parcela maior da atividade observada. Por isso, o peso de cada recorte é o seu trabalho de transporte. A intensidade representativa é a média ponderada: cada intensidade é multiplicada pelo trabalho de transporte da própria viagem, e a soma desses produtos é dividida pelo trabalho total.

$$
I_{o,d}^{\mathrm{rep}}=
\frac{\sum_v I_v\,W_{v,o,d}}
{\sum_v W_{v,o,d}}.
$$

Em Santos–Manaus, os 89 recortes aceitos somaram $3.153.328.821{,}755\ \mathrm{t\cdot nm}$ de trabalho de transporte. Depois de aplicar a regra para valores anômalos do EU MRV, o sistema calcula a soma de $I_v\,W_{v,o,d}$ para todos os recortes e divide pelo trabalho total. O resultado é $9{,}009824\ \mathrm{g/(t\cdot nm)}$. Assim, cada viagem influencia a média na proporção da carga que transportou e da distância que percorreu; nenhuma viagem isolada é escolhida para representar toda a ligação.

Recortes com trabalho de transporte igual a zero não entram na média ponderada quando houver pelo menos um recorte com trabalho positivo. Se todos os recortes tiverem peso zero, o sistema calcula a média simples das intensidades disponíveis e registra essa condição.

##### 3.3.4.4 Distância do cenário e escolha do corredor

O cálculo ocorre em duas etapas que não devem ser confundidas. Na preparação da base, as cargas e as distâncias das viagens históricas da ANTAQ servem somente para calcular os pesos da intensidade representativa. Na execução de um novo cenário, o sistema usa essa intensidade uma única vez, junto com a carga informada pelo usuário e com a distância de uma rota completa escolhida. As cargas históricas não são somadas à carga do usuário, e o combustível das viagens históricas não é somado ao novo cenário.

**Preparação da intensidade:** o sistema reúne todos os recortes que começam em Santos e terminam em Manaus. Entre eles estão o recorte direto da viagem `voyage_9612789_00004`, Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`, Santos–Itapoá–Paranaguá–Suape–Manaus da viagem `voyage_9343974_00002` e Santos–Navegantes–Pecém–Manaus da viagem `voyage_9852365_00011`. O último exemplo mostra concretamente que o recorte não precisa passar por Suape. A média ponderada de todos os recortes aceitos fornece a intensidade representativa.

**Execução com uma distância:** o sistema precisa de um corredor concreto para somar as milhas atribuídas aos subtrechos do cenário. Considera somente corredores inteiros observados dentro de uma única viagem, com distância conhecida em todos os subtrechos e um valor de consumo disponível. Se existir um recorte direto entre os dois portos, usa esse corredor. Caso contrário, escolhe o corredor completo mais curto entre os que possuem escalas. Essa escolha não elimina os outros recortes da preparação do indicador.

Em Santos–Manaus, a base contém o recorte direto da viagem `voyage_9612789_00004` e recortes com escalas, como Santos–Suape–Pecém–Manaus da viagem `voyage_9612791_00011`. Os dois ajudam a estimar a intensidade representativa, assim como os demais recortes aceitos para essa direção. Como existe um recorte direto, o sistema usa as 3.300,216 nm que a matriz marítima atribui a ele para representar a distância do novo cenário. Os recortes com escalas e os outros corredores não são descartados da estimativa da intensidade; apenas não fornecem a distância escolhida para o cenário.

Depois dessas duas decisões, o usuário informa a carga $M$. O sistema multiplica essa carga pela intensidade da ligação e pela distância da sequência escolhida. O consumo marítimo é:

$$
F_{o,d}^{\mathrm{cen}}=\frac{I_{o,d}^{\mathrm{rep}}\,M}{1000}
\sum_{s\in\mathcal{S}^{*}_{o,d}}d_s.
$$

O sobrescrito $\mathrm{cen}$ significa “cenário” e diferencia esse consumo calculado para a nova remessa do consumo reconstruído nas viagens históricas.

O sistema procura a distância de cada trecho na matriz marítima. Se uma distância estiver ausente, pode calcular a distância de grande círculo entre as coordenadas dos dois portos. Isso ocorreu no recorte Santos–Itapoá–Paranaguá–Suape–Manaus da viagem `voyage_9343974_00002`, realizada pelo navio de IMO 9343974. Como a matriz não continha Itapoá–Paranaguá, o sistema estimou 40,974 nm por haversine e registrou essa fonte. A intensidade dessa viagem, 6,8 g/(t$\cdot$nm), veio da correspondência exata do IMO no EU MRV de 2024. A distância de haversine é uma aproximação entre coordenadas; ela não confirma que o navio poderia seguir exatamente aquela linha no mar.

#### 3.3.5 Consolidação de emissões e custos

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

Para conferir uma viagem real sem gerar registros para toda a base, o pipeline aceita o identificador da viagem com `--audit-voyage-id` e exige `--log-level DEBUG`. Na viagem `voyage_9612791_00011`, o log mostra, em cada subtrecho, o embarque, o desembarque, o saldo da escala de partida, a carga inicial reconstruída, a carga a bordo, a distância e sua fonte, o trabalho de transporte, a intensidade e sua proveniência, e o combustível calculado. Para cada ligação, o mesmo log informa o trabalho total, a média ponderada e as fontes que contribuíram para o resultado. Esse modo apenas expõe valores intermediários e não altera o arquivo resultante.

Quando o usuário executa um cenário, a aplicação lê essa tabela já preparada. O Supabase, serviço usado para armazenar os dados da aplicação, utiliza o banco de dados PostgreSQL, também chamado de Postgres, para guardar lugares, rotas e resultados que podem ser reutilizados. Essa cópia reutilizável recebe o nome de cache. O cache evita solicitar novamente a mesma rota a um provedor. Mesmo assim, o resultado continua sendo uma rota calculada. Ele não é uma trajetória registrada pelo Sistema de Posicionamento Global (GPS), isto é, não reproduz as posições reais percorridas durante uma viagem, e não garante a existência de um serviço comercial [cabotagelensrepo; cabotagelensapp].

## 5. Evidência empírica e resultados

Esta seção verifica como o método se comporta com os dados disponíveis. Primeiro, apresenta a cobertura do cruzamento entre ANTAQ e EU MRV. Em seguida, acompanha uma execução demonstrativa do cálculo marítimo entre Santos e Manaus e, por último, compara a direção dos resultados com uma referência externa.

### 5.1 Cobertura da base ANTAQ–EU MRV

A base processada contém 1.324 viagens de cabotagem conteinerizada registradas em 2025. Nessas viagens, o sistema identificou 6.797 paradas e 7.103 chamadas portuárias. Uma chamada é um registro original de atracação ou atendimento do navio; chamadas consecutivas que representam o mesmo local são reunidas em uma parada. O trecho navegado entre duas paradas consecutivas é um subtrecho. Um recorte entre dois portos pode conter um ou vários desses subtrechos. A base também contém 389 navios diferentes por número IMO.

O sistema procurou esses 389 números no EU MRV e encontrou 243 correspondências exatas. Esses 243 navios aparecem em 788 das 1.324 viagens. Nas outras 536 viagens, a execução atual usou uma estimativa baseada no tipo de navio. Nenhuma viagem desta execução precisou de uma estimativa pela classe; essa regra permanece disponível para uma base que forneça esse metadado.

**Tabela 6 — Cobertura do cruzamento entre viagens ANTAQ e intensidade EU MRV.**

| Indicador                                |                              Valor | Cobertura |
| :--------------------------------------- | ---------------------------------: | --------: |
| IMOs com correspondência exata           |                         243 de 389 |     62,5% |
| Viagens com correspondência exata        |                       788 de 1.324 |     59,5% |
| Carga em massa com correspondência exata | 15.959.761,561 de 30.191.845,948 t |     52,9% |
| Carga em TEU com correspondência exata   |   1.454.351,75 de 2.872.715,00 TEU |     50,6% |

Esses percentuais precisam ser lidos com cuidado. Uma correspondência exata significa que o mesmo número IMO apareceu na ANTAQ e no MRV. Quando isso não ocorre, o sistema ainda pode usar a intensidade calculada para um grupo de navios semelhantes. A saída identifica esse valor como estimativa do grupo. Ela não o apresenta como dado medido para aquele navio.

O sistema encontrou 177 ligações portuárias quando preservou o sentido da navegação. Santos–Manaus e Manaus–Santos, por exemplo, contam como duas ligações diferentes porque representam sentidos opostos. Ao ler cada viagem, o sistema gerou 12.025 recortes históricos viagem–OD. Esse total é maior que as 1.324 viagens porque uma viagem com várias escalas pode servir para diferentes combinações de partida e chegada. Dentro da viagem `voyage_9612791_00011`, o prefixo Santos–Suape–Pecém–Manaus fornece seis recortes: Santos–Suape, Santos–Pecém, Santos–Manaus, Suape–Pecém, Suape–Manaus e Pecém–Manaus. A viagem completa ainda retorna de Manaus a Santos e, por isso, pode fornecer outras ligações. Cada recorte mantém o número da viagem e somente os subtrechos entre os dois portos que definem aquela ligação.

Os 12.025 recortes reutilizam 5.438 subtrechos navegados entre paradas consecutivas. Um mesmo subtrecho pode fazer parte de mais de um recorte da mesma viagem. A distância de 5.023 subtrechos veio da matriz marítima. Nos outros 415, o sistema precisou usar a aproximação de haversine. Todos os subtrechos que entram no cálculo possuem uma intensidade identificada; ela pode vir do IMO, da classe ou do tipo do navio. A proveniência mantém essas situações separadas, inclusive quando um valor individual do MRV é substituído pela regra de valores anômalos.

### 5.2 Execução demonstrativa: Santos–Manaus

Esta subseção mostra como os dados e as regras se combinam em uma execução concreta.

**Preparação do indicador:** o sistema encontrou 89 viagens nas quais o navio saiu de Santos e chegou a Manaus em uma escala posterior da mesma viagem. De cada viagem, foi aproveitado o recorte entre a saída de Santos e a chegada a Manaus. Todos os 89 recortes realizaram trabalho de transporte maior que zero.

Os 89 recortes não seguiram uma única sequência. O sistema encontrou 22 listas diferentes de portos entre Santos e Manaus. Um recorte foi direto. Os demais contêm uma ou mais escalas intermediárias. Cada lista completa é um corredor observado, e um corredor pode reunir vários recortes de viagens diferentes. A viagem `voyage_9852365_00011`, por exemplo, fornece Santos–Navegantes–Pecém–Manaus, um corredor que não passa por Suape.

Em 40 recortes, o sistema encontrou o IMO no EU MRV. Desses, 19 permaneceram com a intensidade individual. Em 21, a intensidade do IMO ultrapassou o percentil 95 do tipo *container ship* e foi substituída pela estimativa robusta do tipo. Nos outros 49, não havia correspondência individual e também foi usada a estimativa do tipo. A fonte de cada recorte fica registrada, de modo que uma estimativa de grupo não é confundida com uma medição individual.

**O que o sistema faz:** para cada um dos 89 recortes, multiplica a intensidade pelo trabalho de transporte. Em seguida, soma esses produtos e divide pelo trabalho total. O resultado é $9{,}009824\ \mathrm{g/(t\cdot nm)}$, que representa Santos–Manaus. Os recortes dos 22 corredores participam dessa conta. O navio não precisa passar por Suape nem por qualquer outro porto predeterminado.

A estimativa do tipo *container ship* é calculada a partir de 243 valores positivos, um por IMO. Depois de ordenar a lista, o sistema retira os dois menores e os dois maiores e calcula a média dos 239 valores restantes. O resultado é $9{,}322050\ \mathrm{g/(t\cdot nm)}$. Ele é usado nos recortes sem IMO correspondente e nos recortes cujo indicador individual ultrapassa o limiar de anomalia.

Sem retirar os extremos, a média dos 243 valores seria 21,661852 g/(t$\cdot$nm). A mediana simples da mesma lista seria 4,620000 g/(t$\cdot$nm). Esses dois números ajudam a entender a dispersão dos dados. O sistema não os usa no lugar da regra registrada para Santos–Manaus.

**Execução da nova remessa:** os 89 recortes históricos definem a intensidade de $9{,}009824\ \mathrm{g/(t\cdot nm)}$. As cargas históricas servem apenas para calcular os pesos. Elas não são somadas à carga informada pelo usuário, e o combustível das 89 viagens históricas não é somado ao novo cenário. A execução usa essa intensidade uma vez e percorre a distância de uma única sequência concreta de portos.

Para escolher essa distância, o sistema encontrou um recorte direto de Santos a Manaus dentro da viagem `voyage_9612789_00004`. A regra dá preferência a esse recorte sem escala intermediária. A matriz marítima atribui 6.112 quilômetros (km), equivalentes a 3.300,216 nm, ao subtrecho. Essa escolha vale somente para a distância modelada do cenário. Os 89 recortes continuam participando da intensidade.

É possível conferir a reconstrução histórica com o recorte direto observado em `voyage_9612789_00004`. O navio de IMO 9612789 saiu de Santos com 11.584,165 t e chegou a Manaus na escala seguinte. A matriz marítima atribuiu 3.300,216 nm ao subtrecho. Como não há correspondência individual aplicável para esse IMO, a intensidade reconstruída da viagem é $9{,}322050\ \mathrm{g/(t\cdot nm)}$, obtida pela média aparada em 1% do tipo-padrão documentado *container ship*:

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

O sistema examina todas as viagens nas quais o navio saiu do porto escolhido como início e chegou ao porto escolhido como fim. No cálculo Santos–Manaus, o recorte direto de `voyage_9612789_00004` e o recorte com escalas de `voyage_9612791_00011`, que passou por Suape e Pecém antes de chegar a Manaus, participam da mesma estimativa. Uma viagem Manaus–Suape–Santos não participa porque percorreu o sentido contrário. Nenhum subtrecho entre os dois portos pode estar ausente, e deve existir uma intensidade identificada. Somente os recortes em que a soma da carga a bordo multiplicada pela distância de cada subtrecho é maior que zero recebem peso na média ponderada.

As principais limitações são:

- **Período observado:** o recorte de 2025 não representa automaticamente outros anos. Viagens no começo ou no fim da janela podem estar incompletas.

- **Cobertura do MRV:** nem todos os navios aparecem na base europeia. A estimativa por grupo representa navios semelhantes; ela não é uma medição da embarcação ausente. Em Santos–Manaus, 49 recortes não possuem correspondência individual e 21 tiveram o indicador individual substituído pela regra de valores anômalos. A fonte de cada intensidade precisa, portanto, ser considerada ao interpretar a média.

- **Valores extremos:** para uma intensidade encontrada por IMO, o sistema compara o valor com a distribuição de navios do mesmo tipo no EU MRV. Quando há pelo menos 20 navios no grupo e o valor está acima do percentil 95, a carga e a distância da viagem são preservadas, mas a intensidade é substituída pela estatística robusta da classe ou do tipo. Para as estimativas de grupo, a classe usa os limites dos percentis 1 e 99 registrados no arquivo; o tipo retira uma quantidade inteira correspondente a 1% de cada lado quando a amostra permite. A regra, o limiar, o indicador original e a fonte efetivamente utilizada ficam registrados na saída.

- **Distâncias marítimas:** a matriz contém distâncias calculadas para representar a navegação. Quando o sistema usa haversine, mede apenas a linha de grande círculo entre os portos. Essa linha pode não coincidir com uma rota navegável.

- **Oferta de serviço:** uma viagem observada mostra que a sequência ocorreu na janela analisada. Ela não garante frequência futura, espaço disponível ou serviço comercial regular.

- **Fronteira ambiental:** os resultados são emissões operacionais TTW de CO$_2$e. Não incluem produção do combustível, construção de veículos, navios ou infraestrutura, nem uma LCA completa.

- **Fronteira econômica:** o valor monetário estima componentes operacionais. Não é cotação de frete, contrato de armador ou análise comercial completa.

Por essas razões, um resultado favorável à cabotagem em determinado cenário não demonstra superioridade universal. A ferramenta é um instrumento de triagem e comparação auditável. Uma decisão logística ainda precisa considerar serviço, tempo, capacidade, terminais e preços comerciais [competitiveness2024; modalshiftreview2020].

## 7. Conclusão e trabalhos futuros

Em síntese, o CabotageLens compara duas maneiras de levar a mesma carga ao mesmo destino. Na primeira, o caminhão percorre toda a rota. Na segunda, caminhões fazem os acessos terrestres e um navio percorre o trecho entre os portos.

No cálculo marítimo, o sistema lê as escalas da ANTAQ na ordem em que aconteceram. Depois de cada escala, calcula quanto o navio leva para o próximo porto. Em seguida, procura o IMO no EU MRV. Se encontrar, usa a intensidade do próprio navio, exceto quando o valor ultrapassa o limiar de anomalia definido para o mesmo tipo de embarcação. Se não encontrar, usa uma estimativa de classe ou tipo e registra essa decisão.

Para analisar Santos–Manaus, o sistema examina uma viagem de cada vez e lê suas escalas na ordem em que aconteceram. Na viagem `voyage_9612791_00011`, o navio saiu de Santos, passou por Suape e Pecém e chegou a Manaus; por isso, os três subtrechos consecutivos entram no recorte Santos–Manaus. Uma viagem Manaus–Suape–Santos não entra, porque o navio fez o percurso no sentido contrário. O recorte aceito pode ser direto ou conter outros portos. Cada recorte recebe um peso igual à soma da carga a bordo multiplicada pela distância de cada subtrecho. A intensidade de Santos–Manaus é a média dessas intensidades, ponderada por esses pesos.

Em uma etapa separada, o sistema escolhe o corredor usado para calcular a distância do cenário. Considera somente corredores inteiros observados dentro de uma única viagem, com distância conhecida em todos os subtrechos e um valor de consumo disponível. Se existir um recorte direto, usa esse corredor. Caso contrário, escolhe o corredor completo mais curto entre os que possuem escalas. Essa escolha não retira os outros recortes do cálculo da intensidade.

Em Santos–Manaus, 89 recortes históricos provenientes de 89 viagens distintas seguiram 22 sequências de portos. O trabalho total é $3.153.328.821{,}755\ \mathrm{t\cdot nm}$ e, depois do tratamento explícito dos valores anômalos do MRV, a média ponderada resulta em $9{,}009824\ \mathrm{g/(t\cdot nm)}$. No recorte direto de `voyage_9612789_00004`, a reconstrução histórica usa $9{,}322050\ \mathrm{g/(t\cdot nm)}$ e corresponde a 356.384,277 kg de combustível de navegação. Esse valor histórico não inclui acessos rodoviários nem operações portuárias e não é somado ao novo cenário.

Trabalhos futuros devem ampliar a janela da ANTAQ, aumentar a cobertura por IMO e incorporar informações de frequência e disponibilidade de serviço. Também são importantes distâncias marítimas mais detalhadas, operações portuárias baseadas em atividade observada, análise de incerteza, preços comerciais verificáveis e uma futura expansão da fronteira ambiental para WTW ou ciclo de vida.

## Referências

As citações permanecem identificadas por suas chaves, entre colchetes, para facilitar a validação e a posterior sincronização com o LaTeX. Os dados bibliográficos completos estão em [`docs/references.bib`](references.bib), e os limites de uso de cada fonte estão registrados no [mapa de citações da literatura](tf_support/writing/tf_literature_citation_map.md).
