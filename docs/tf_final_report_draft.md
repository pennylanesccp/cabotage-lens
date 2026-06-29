# Rascunho do relatorio final de TF - CabotageLens

Este documento e um scaffold de relatorio academico para o Trabalho de Formatura associado ao projeto CabotageLens. Ele cobre as principais secoes esperadas, mas nao deve ser tratado como texto final de submissao. O texto foi redigido a partir dos artefatos rastreados no repositorio e preserva os limites metodologicos atualmente documentados. As citacoes aparecem como chaves temporarias entre colchetes, sem formatacao ABNT final.

Nota de fluxo de escrita: a proxima etapa de redacao deve ser um artigo tecnico conciso derivado da sintese consolidada de resultados. Depois disso, o texto final do TF pode ser expandido secao por secao a partir da narrativa do artigo e deste scaffold. Este documento nao cria o artigo e nao substitui uma futura passada completa de escrita.

## 1. Introducao

O transporte de cargas no Brasil e historicamente marcado por forte dependencia do modo rodoviario. Essa configuracao facilita uma rede capilar de atendimento porta a porta, mas tambem cria vulnerabilidades tecnicas e economicas em corredores longos: maior exposicao ao preco do diesel, consumo elevado de combustivel por tonelada transportada, riscos operacionais em longas distancias e pressao para reduzir emissoes de gases de efeito estufa. Nesse contexto, a cabotagem aparece como uma alternativa relevante para parte dos fluxos nacionais, principalmente quando a origem e o destino podem ser conectados por uma cadeia logistica com pre-carriage rodoviario, perna maritima e on-carriage rodoviario [icct2022].

A discussao sobre cabotagem no Brasil ganhou novo peso com politicas de incentivo e reorganizacao setorial, incluindo a agenda associada ao BR do Mar. A motivacao dessas politicas nao deve ser interpretada como prova de superioridade universal da cabotagem. A literatura e a experiencia operacional indicam que a competitividade do transporte maritimo costeiro depende de distancia, acesso terrestre, frequencia de servico, disponibilidade de navios, terminais, custos portuarios, tempo de transito, confiabilidade e escala de carga [icct2022] [competitiveness2024] [modalshiftreview2020]. Assim, o problema tecnico nao e simplesmente afirmar que "navio emite menos que caminhao", mas comparar cadeias completas sob uma unidade funcional comum.

O CabotageLens foi desenvolvido para responder a esse problema como uma ferramenta computacional de apoio a decisao e pesquisa aplicada. A ferramenta compara uma alternativa rodoviaria direta com uma alternativa rodoviario-cabotagem-rodoviario para pares origem-destino no Brasil. Para cada cenario, o modelo explicita distancias, pernas logisticas, fontes de distancia, consumo, estimativas de custo operacional modelado e emissoes operacionais TTW CO2e. O objetivo nao e substituir uma cotacao comercial de frete, nem representar uma super-rede completa de servicos de cabotagem, mas oferecer uma estrutura auditavel para comparar alternativas e documentar onde as conclusoes sao robustas, sensiveis, inconclusivas ou invalidadas por limitacoes de rota e dados.

Este scaffold do Trabalho de Formatura assume uma postura conservadora. A evidencia atualmente consolidada no repositorio combina a camada Batch 001/001B de diagnostico e sensibilidade com o Batch 002, que acrescenta um benchmark externo Gustavo/Costa. Essa evidencia fortalece a defesa direcional, mas nao transforma os resultados em validacao calibrada de magnitude. Nenhum caso atual deve ser promovido a `headline_candidate` de linha de base robusta.

A contribuicao atual deve ser apresentada como: uma estrutura computacional auditavel; uma comparacao route-aware entre alternativas rodoviarias diretas e rodoviario-cabotagem-rodoviario; um metodo com fronteiras explicitas de TTW CO2e operacional e custo modelado; e uma estrategia de validacao que combina sensibilidade interna com benchmark externo. Essa formulacao evita afirmar que a cabotagem e universalmente superior.

## 2. Objetivos

O objetivo geral deste trabalho e desenvolver e documentar o CabotageLens como um prototipo computacional auditavel para comparacao entre transporte rodoviario direto e transporte multimodal rodoviario-cabotagem-rodoviario em corredores brasileiros, considerando estimativas de custo operacional modelado e emissoes operacionais TTW CO2e sob fronteiras explicitas.

Os objetivos especificos sao:

- comparar alternativas rodoviarias diretas e alternativas rodoviario-cabotagem-rodoviario para pares origem-destino selecionados;
- tornar explicitas as hipoteses de rota, incluindo pre-carriage, perna maritima, on-carriage, selecao de portos, distancia, custo modelado e emissoes;
- estimar emissoes operacionais TTW CO2e e estimativas de custo modelado por remessa, preservando as unidades e os limites de interpretacao;
- expor a proveniencia das distancias e as limitacoes da selecao de portos, especialmente quando ha distancia maritima por fallback, caso same-port, porto alternativo ou referencia exata ausente;
- classificar os resultados de forma conservadora para uso academico, separando resultados historicos, bloqueados, excluidos, sensiveis, benchmark-limited e candidatos a conclusao principal;
- usar evidencia de sensibilidade e benchmark externo para sustentar uma interpretacao defensavel, sem tratar diferencas de fronteira ou magnitude como reproducao exata.

Esses objetivos refletem uma decisao metodologica importante: o trabalho prioriza rastreabilidade e defensabilidade sobre abrangencia excessiva. Em vez de forcar uma conclusao modal unica, a ferramenta registra a qualidade de evidencia que sustenta cada comparacao.

## 3. Revisao bibliografica

### 3.1 Cabotagem brasileira e BR do Mar

A cabotagem brasileira e frequentemente apresentada como alternativa para reduzir a dependencia de longas viagens rodoviarias. O argumento e plausivel em um pais com extenso litoral, grandes centros urbanos costeiros e corredores de longa distancia entre regioes produtoras, consumidoras e portuarias. A literatura de contexto nacional tambem associa a cabotagem a oportunidades de descarbonizacao e a discussoes de politica publica, incluindo o BR do Mar [icct2022].

Contudo, o uso dessa literatura no presente trabalho precisa respeitar a fronteira dos dados. Valores nacionais de participacao modal, emissoes setoriais ou custos medios ajudam a justificar o problema, mas nao validam diretamente resultados rota a rota do CabotageLens. O modelo trabalha com uma remessa, uma origem, um destino, uma cadeia de pernas logisticas e uma fronteira operacional especifica. Assim, a literatura de cabotagem brasileira e usada principalmente para contextualizacao, motivacao e comparacao qualitativa, nao para substituir distancias, fatores ou resultados calculados.

### 3.2 Competitividade da cabotagem e estudos em super-rede

Estudos de competitividade da cabotagem conteinerizada brasileira mostram que a decisao modal real depende de uma estrutura de rede mais rica do que uma comparacao direta entre caminhao e navio. Uma super-rede pode incorporar servicos disponiveis, frequencia, tempo de espera, custos comerciais, inventario, restricoes de terminal e alternativas de roteamento [competitiveness2024]. Essa abordagem e mais completa que o escopo atual do CabotageLens.

O papel desses estudos neste TF e duplo. Primeiro, eles justificam por que a comparacao deve ser porta a porta: a perna maritima so faz sentido quando conectada aos acessos terrestres. Segundo, eles estabelecem uma limitacao clara: o CabotageLens nao e uma super-rede comercial. A ferramenta e um estimador de rota e fronteira operacional explicita, adequado para analise metodologica e triagem academica, mas nao para afirmar disponibilidade real de servico, frequencia de escala ou preco contratado.

### 3.3 Short sea shipping versus transporte rodoviario

A literatura internacional sobre short sea shipping mostra que a alternativa maritima pode apresentar melhor desempenho ambiental em determinados corredores, mas essa conclusao nao e universal. Resultados dependem de distancia, utilizacao da embarcacao, tipo de navio, intensidade de combustivel, acessos terrestres, operacoes portuarias e unidade funcional [shortsea2019]. Revisoes sobre mudanca modal tambem indicam que barreiras logisticas, custo total, qualidade do servico e confiabilidade podem limitar a transferencia de cargas da rodovia para o mar [modalshiftreview2020].

Essa literatura e central para evitar uma interpretacao simplista dos resultados. No CabotageLens, mesmo quando uma linha de sensibilidade mostra menor custo modelado e menor TTW CO2e para o multimodal, isso nao implica que a cabotagem seja sempre melhor. A conclusao deve permanecer condicionada ao corredor, aos portos, a distancia maritima, aos parametros de combustivel e ao limite de custo representado.

### 3.4 Limitacoes de mudanca modal

Mudanca modal e uma decisao operacional, economica e institucional. Alem de custo e emissoes, transportadores e embarcadores consideram prazo, variabilidade, disponibilidade de slots, integracao terrestre, risco de avaria, frequencia, burocracia e confiabilidade [modalshiftreview2020]. Por isso, uma ferramenta que calcula custo modelado e TTW CO2e deve ser interpretada como uma camada da decisao, nao como o proprio processo de decisao.

No contexto brasileiro, essa cautela e ainda mais importante para rotas com portos proximos, portos alternativos ou corredores amazonicos. Um porto geometricamente proximo pode nao ser o porto operacionalmente adequado. Um porto alternativo pode ser util para sensibilidade, mas nao valida automaticamente o porto originalmente selecionado. Esses pontos aparecem explicitamente nas decisoes metodologicas do Batch 001B.

### 3.5 Port hotelling e emissoes em porto

Operacoes portuarias e hoteling podem afetar o desempenho ambiental da cadeia multimodal. O navio pode consumir combustivel ou energia auxiliar durante atracacao, carregamento, descarga e espera, e equipamentos de patio tambem podem contribuir para emissoes e custo operacional [berth2009] [shipops2022] [berthairquality2010].

No CabotageLens, essa literatura e usada como suporte de metodo e limitacao. Ela nao substitui automaticamente fatores do modelo. O repositorio documenta que as emissoes de operacoes portuarias seguem o caminho operacional TTW CO2e do restante da ferramenta, e que valores WTW, LCA ou fatores regionais especificos de outros portos devem permanecer como referencia, sensibilidade futura ou trabalho futuro ate que uma decisao de fronteira seja implementada.

### 3.6 Fronteiras TTW, WTW, LCA, CO2 e CO2e

Uma das distincoes mais importantes do trabalho e a diferenca entre TTW, WTW e LCA. O CabotageLens, no estado atual, reporta emissoes operacionais TTW CO2e. Isso significa que a comparacao se concentra nas emissoes diretas associadas ao consumo operacional de combustivel dentro da fronteira definida. A literatura sobre descarbonizacao e combustiveis maritimos inclui resultados WTW e LCA, mas esses resultados incorporam etapas a montante e hipoteses de ciclo de vida que nao estao implementadas na linha de base atual [decarb2024] [maritimelca2024].

Da mesma forma, CO2 e CO2e nao devem ser misturados. Estudos que reportam CO2 por tonelada-quilometro ou por TEU-quilometro sao uteis para contexto e cautela, mas nao podem ser convertidos implicitamente em TTW CO2e do CabotageLens. O presente TF usa esses trabalhos para delimitar fronteiras, nao para calibrar numericamente o modelo quando a unidade, o combustivel ou a fronteira nao coincidem.

### 3.7 Limitacoes da fronteira de custo

O custo reportado pelo CabotageLens e uma estimativa de custo modelado dentro da fronteira operacional representada. Ele inclui componentes como combustivel rodoviario, combustivel maritimo e, quando aplicavel, operacoes portuarias modeladas. Ele nao representa frete comercial completo. Tarifas portuarias, margens, seguros, pedagios, custo de estoque, tempo em transito, demurrage, frequencia, disponibilidade de servico e negociacao contratual nao estao plenamente incorporados [competitiveness2024] [modalshiftreview2020].

Essa distincao e decisiva para a interpretacao dos resultados. Uma linha que mostra menor custo modelado para o multimodal nao prova que o frete comercial contratado sera menor. Ela indica que, na fronteira operacional representada, os componentes modelados ficaram abaixo dos componentes modelados da alternativa rodoviaria.

## 4. Metodologia

### 4.1 Unidade funcional e base de carga

A unidade funcional adotada neste trabalho e o transporte de uma massa especificada de carga conteinerizada entre uma origem e um destino no Brasil. Essa definicao e mantida como base de comparacao ao longo do TF: o que se compara nao e um modo isolado, mas a entrega da mesma remessa sob duas alternativas de transporte.

As duas alternativas avaliadas pelo CabotageLens atendem, portanto, a mesma unidade funcional. A primeira e a alternativa rodoviaria direta, na qual a remessa segue por caminhao entre origem e destino. A segunda e a alternativa rodoviario-cabotagem-rodoviario, na qual a mesma remessa inclui acesso rodoviario ao porto de origem, perna maritima de cabotagem, componentes portuarios quando modelados e acesso rodoviario final ao destino. Essa equivalencia de servico e necessaria para evitar que a comparacao seja reduzida ao trecho maritimo ou ao trecho rodoviario isolado.

Nos artefatos de validacao e benchmark deste TF, a base recorrente de referencia e `1 TEU / 14 t` por remessa. Essa base aparece de forma repetida nos lotes Batch 001, Batch 001B e Batch 002, inclusive nas linhas de sensibilidade executadas e no alinhamento com o workbook Gustavo/Costa. Ela deve ser lida como base recorrente de validacao e benchmark, nao como suposicao universal de carga para todo uso possivel do CabotageLens. Outros cenarios do aplicativo podem empregar massas ou quantidades de TEU distintas, desde que a unidade funcional seja explicitada antes da comparacao.

Os resultados principais deste TF sao interpretados por remessa, pois a decisao modal analisada se refere a um movimento concreto entre um par origem-destino. Quando apropriado, esses resultados podem ser normalizados por tonelada, por TEU, por conteiner ou por tonelada-quilometro, desde que a normalizacao nao oculte a base de carga, a distancia considerada e a fronteira de emissoes. Em particular, comparacoes por conteiner so sao defensaveis quando a equivalencia de carga e alocacao for tratada como uma condicao metodologica, nao como uma consequencia automatica da unidade `kg CO2e/container`.

| Item | Definicao neste TF | Limite de interpretacao |
| --- | --- | --- |
| Unidade funcional | Movimento de uma quantidade especificada de carga conteinerizada entre origem e destino no Brasil. | Nao representa uma afirmacao universal sobre todos os perfis de carga ou servico logistico. |
| Base recorrente de validacao | `1 TEU / 14 t` por remessa nos artefatos de benchmark e sensibilidade. | Base recorrente, nao suposicao obrigatoria para todo uso do CabotageLens. |
| Alternativa rodoviaria direta | Transporte da mesma remessa por caminhao entre origem e destino. | Resultados de custo sao estimativas modeladas, nao fretes comerciais contratados. |
| Alternativa rodoviario-cabotagem-rodoviario | Pre-carriage rodoviario, cabotagem, componentes portuarios quando modelados e on-carriage rodoviario. | Nao equivale a comparar apenas a perna maritima com a viagem rodoviaria completa. |
| Nivel de comparabilidade do Batch 002 | Alinhamento com o workbook Gustavo/Costa no nivel reportado de `kg CO2e/container`. | Comparabilidade por conteiner nao implica reproducao exata da logica interna de alocacao do workbook. |
| O que nao esta totalmente reconciliado | Massa interna, definicao de TEU, fator de carga do caminhao, alocacao, base de distancia e fronteiras de emissoes. | Suporta interpretacao direcional; nao valida magnitudes calibradas nem torna o workbook verdade absoluta. |

O Batch 002 usa o workbook Gustavo/Costa como benchmark externo, nao como verdade de referencia. A execucao do CabotageLens foi alinhada ao nivel reportado de `kg CO2e/container`, mas a equivalencia interna de carga e alocacao nao foi demonstrada de forma completa. Permanecem em aberto a massa util assumida internamente, a definicao operacional de TEU, o fator de carga do veiculo rodoviario, a logica de alocacao por conteiner, a base de distancias e as fronteiras de emissoes adotadas no workbook. Por isso, a comparabilidade cargo/alocacao sustenta apenas interpretacao direcional e discussao metodologica, nao validacao calibrada de magnitude nem reproducao exata do workbook.

Por fim, a unidade funcional tambem controla a linguagem dos resultados. Custos produzidos pelo modelo permanecem estimativas de custo sob a fronteira implementada, e nao tarifas, cotacoes ou fretes comerciais. Emissoes permanecem CO2e operacional TTW por remessa, salvo indicacao explicita em contrario. Evidencias WTW, LCA, CO2-only ou fatores de outro limite ambiental nao devem ser misturadas com os resultados TTW CO2e do CabotageLens sem mudanca documentada de fronteira. Essa disciplina de unidade funcional, base de carga e fronteira evita que linhas de sensibilidade ou benchmark sejam promovidas a conclusoes gerais que os artefatos rastreados ainda nao sustentam.

### 4.2 Alternativa rodoviária direta

A alternativa rodoviária direta representa o movimento da mesma remessa definida na unidade funcional diretamente por caminhão entre a origem e o destino. Ela funciona como a cadeia de comparação rodoviária do CabotageLens: a carga, a massa representada e o par origem-destino permanecem os mesmos, enquanto a solução logística é limitada a uma perna rodoviária única. Portanto, trata-se de uma alternativa modelada de comparação, não de uma reconstrução de uma viagem real específica de caminhão.

A distância dessa perna é expressa em quilômetros (`km`) e corresponde à distância de rota produzida pela lógica de roteamento e cache configurada para o cenário. Essa distância deve ser lida como rota modelada, rastreável aos artefatos de provedor/cache, e não como trajetória GPS medida, verdade de terreno exata ou registro operacional de uma viagem executada. A estabilidade do provedor e do cache melhora a rastreabilidade da entrada de distância, mas não elimina as limitações próprias de uma rota calculada.

Sobre essa distância rodoviária, o modelo calcula consumo de combustível, custo modelado e emissões operacionais TTW CO2e a partir do preset de veículo, da massa de carga, dos parâmetros de combustível e dos fatores de emissão implementados. O custo rodoviário permanece uma estimativa de custo dentro da fronteira operacional representada; não deve ser interpretado como tarifa, cotação ou frete comercial negociado. Da mesma forma, as emissões rodoviárias permanecem CO2e operacional TTW, sem conversão implícita para WTW, LCA ou CO2 isolado.

O escopo da alternativa rodoviária direta também define o que não está sendo reconstruído. O método não representa comportamento do motorista, perfil real de velocidade, congestionamento, padrões de parada, contratos detalhados de pedágio, despacho de frota ou negociação comercial de frete. Esses elementos podem afetar uma operação real, mas ficam fora da fronteira metodológica desta comparação.

| Componente | Papel na alternativa rodoviária direta | Limite de interpretação |
| --- | --- | --- |
| Distância rodoviária | Entrada em `km` para a perna direta origem-destino. | Rota modelada por provedor/cache, não trajetória GPS medida nem verdade de terreno exata. |
| Preset de veículo e massa de carga | Define o veículo representativo e a carga associada à mesma unidade funcional. | Não reconstrói configuração real de frota, escala de despacho ou alocação operacional de uma viagem específica. |
| Consumo de combustível | Resultado modelado a partir de distância, veículo, carga e parâmetros de combustível. | Não captura perfil real de velocidade, congestionamento, paradas ou condução. |
| Custo modelado | Estimativa operacional dentro da fronteira implementada. | Não equivale a frete comercial, tarifa contratada, cotação spot ou negociação logística completa. |
| Emissões TTW CO2e | Emissões operacionais associadas à combustão de combustível na perna rodoviária representada. | Não são WTW, LCA nem CO2-only, e não devem ser misturadas com fatores de outra fronteira. |
| Fator rodoviário diagnóstico | Sensibilidade de alinhamento com o benchmark Gustavo/Costa usando `0.8602944 kgCO2e/km`. | Não substitui, recalibra ou se mostra mais correto que a linha de base rodoviária do CabotageLens. |

No Batch 002, a reexecução com Supabase/cache indicou que a instabilidade de provedor ou cache provavelmente não é a explicação principal para a lacuna de magnitude no lado rodoviário. Essa evidência é útil para separar um possível problema de distância/cache de diferenças metodológicas mais amplas, mas estabilidade de rota e cache não valida, por si só, a magnitude calibrada das emissões. Em outras palavras, a rota rastreável é uma condição de auditabilidade, não uma prova de que todos os resultados rodoviários reproduzem um benchmark externo.

A reconciliação diagnóstica com o fator Gustavo/Costa deve permanecer separada da linha de base implementada. O fator `0.8602944 kgCO2e/km` explica parte importante da diferença rodoviária observada no Batch 002, pois testa uma hipótese de alinhamento de consumo e fator de emissão mantendo as distâncias cacheadas. Ainda assim, ele não recalibra a ferramenta, não substitui o modelo rodoviário operacional TTW do CabotageLens e não autoriza misturar fronteiras TTW, WTW, LCA, CO2 e CO2e. Seu papel no TF é metodológico e interpretativo: mostrar sensibilidade a premissas rodoviárias, sem transformar a sensibilidade em novo baseline.

### 4.3 Alternativa rodoviário-cabotagem-rodoviário

A alternativa rodoviário-cabotagem-rodoviário representa a mesma remessa definida na unidade funcional, mas organizada como uma cadeia porta a porta composta por trechos terrestres, trecho marítimo e, quando habilitados no cenário, componentes portuários. Assim como na alternativa rodoviária direta, a comparação é feita para o movimento completo entre origem e destino final. Portanto, a perna marítima não deve ser lida isoladamente como substituta da viagem rodoviária completa, pois os acessos terrestres e as operações associadas aos portos também condicionam custo, emissões e interpretação do resultado.

A cadeia começa pelo *pre-carriage*, isto é, o deslocamento rodoviário da origem ao porto de origem. Esse trecho é medido em quilômetros (`km`) e permanece dentro da mesma fronteira operacional usada para os demais componentes rodoviários do modelo. Em seguida, a remessa é transferida para a perna marítima de cabotagem entre o porto de origem e o porto de destino. A distância marítima é representada em quilômetros (`km`) e, quando a fonte de distância ou o artefato de validação assim registra, também em milhas náuticas (`nm`). A cadeia se encerra com o *on-carriage*, novamente rodoviário, entre o porto de destino e o destino final, também medido em `km`.

Os componentes portuários entram apenas quando modelados e habilitados no cenário. Nessa categoria estão as operações portuárias representadas pelo modelo e o *hoteling* associado às escalas, quando aplicável. Esses componentes permanecem dentro da fronteira operacional do TF: custos são estimativas modeladas e emissões são operacionais TTW CO2e, salvo indicação explícita em contrário. A inclusão de operações portuárias e *hoteling* deve evitar dupla contagem. Se uma intensidade marítima ou fator agregado já representar consumo operacional em porto, acrescentar *hoteling* de forma separada pode superestimar as emissões; se o cenário separar navegação, operação portuária e permanência atracada, essa decomposição precisa ficar explícita na metodologia e na interpretação do resultado.

| Componente | Papel na cadeia multimodal | Unidade / fronteira | Limite de interpretação |
| --- | --- | --- | --- |
| *Pre-carriage* | Levar a remessa da origem ao porto de origem por rodovia. | `km`; componente rodoviário da mesma unidade funcional. | Integra o resultado porta a porta: altera a distância total, o custo modelado e o TTW CO2e da cadeia. |
| Perna marítima de cabotagem | Transportar a remessa entre os portos selecionados ou forçados no cenário. | `km` e, quando registrado, `nm`; distância marítima com proveniência. | A perna marítima sozinha não representa a alternativa multimodal completa. |
| Operações portuárias | Representar atividades portuárias incluídas no cenário. | Fronteira operacional quando habilitada. | Não equivale a tarifa portuária completa nem a produtividade real do terminal. |
| *Hoteling* | Representar permanência/consumo associado às escalas, quando separado pelo modelo. | Fronteira operacional TTW CO2e quando habilitado. | Não deve ser somado se já estiver coberto por intensidade marítima agregada. |
| *On-carriage* | Levar a remessa do porto de destino ao destino final por rodovia. | `km`; componente rodoviário da mesma unidade funcional. | Pode alterar substancialmente a leitura da alternativa, especialmente em portos afastados do destino. |
| Porto forçado ou alternativo | Testar uma configuração de sensibilidade com porto diferente do originalmente selecionado. | Cenário explícito de sensibilidade, com proveniência própria. | Não valida silenciosamente o porto selecionado originalmente; Pecém não valida Fortaleza e Suape não valida Recife. |
| Caso de mesmo porto | Registrar situação em que origem e destino marítimos recaem no mesmo porto. | Limitação, exemplo ou exclusão conforme classificação rastreada. | Não representa uma cadeia normal de cabotagem e não deve sustentar comparação modal de referência. |

Essa alternativa é, portanto, uma construção modelada de comparação porta a porta. Ela não demonstra, por si só, disponibilidade real de serviço de cabotagem, escala operacional, frequência, cronograma, viabilidade comercial, roteamento de armador ou aceitação de carga por um operador específico. A seleção de portos e a proveniência da distância marítima controlam diretamente a qualidade do resultado: distâncias de triagem, lacunas de referência, portos alternativos e casos de mesmo porto reduzem o grau de confiança que pode ser atribuído à linha analisada.

Os cenários com portos forçados ou alternativos devem permanecer classificados como sensibilidade quando essa for a decisão rastreada. Assim, uma linha Manaus/Pecém pode informar uma discussão regional ou um teste de porto alternativo, mas não valida automaticamente uma linha Manaus/Fortaleza com Porto de Fortaleza selecionado. De forma análoga, um cenário Rio Grande/Suape não valida silenciosamente uma linha Rio Grande/Recife com Porto do Recife selecionado. Promover essas sensibilidades a validações robustas de porto originalmente selecionado confundiria hipótese de cenário com evidência de rota.

Por fim, a interpretação econômica e ambiental desta alternativa segue as mesmas fronteiras do restante do TF. Custos multimodais são estimativas de custo do modelo, não fretes comerciais, tarifas contratadas ou cotações de mercado. Emissões multimodais são operacionais TTW CO2e por remessa, salvo mudança explícita e documentada de fronteira. Resultados TTW não devem ser misturados com evidências WTW, LCA, CO2 isolado ou CO2e de outra fronteira, e nenhuma linha de sensibilidade deve ser tratada como conclusão universal sobre superioridade da cabotagem.

### 4.4 Seleção de portos e construção de rota

A seleção de portos é a etapa que transforma a unidade funcional em cadeias de transporte comparáveis. Para cada cenário, o CabotageLens parte da mesma origem, do mesmo destino e da mesma base de carga definida para a remessa. A alternativa rodoviária direta e a alternativa rodoviário-cabotagem-rodoviário, portanto, não representam demandas distintas: elas são duas construções modeladas para entregar a mesma carga entre os mesmos pontos finais.

Na alternativa exclusivamente rodoviária, a rota é representada como uma perna direta entre a origem e o destino. Na alternativa multimodal, a rota é decomposta em três trechos principais: o deslocamento rodoviário da origem ao porto de origem, a perna marítima entre o porto de origem e o porto de destino, e o deslocamento rodoviário do porto de destino ao destino final. Essa decomposição é necessária porque a escolha dos portos altera simultaneamente as distâncias de acesso terrestre, a distância marítima, os custos modelados, as emissões operacionais TTW CO2e e a interpretação metodológica do resultado.

A lógica de seleção de portos usada pelo CabotageLens é determinística e auditável. Em cenários ordinários, a ferramenta pode selecionar o porto elegível mais próximo, com base geométrica, dentro do conjunto de portos configurados como elegíveis. Em cenários definidos pelo usuário ou por validação, portos específicos também podem ser forçados para representar uma hipótese explícita. Em ambos os casos, a escolha do porto deve permanecer rastreável, pois ela faz parte da premissa do cenário e não apenas de uma etapa operacional invisível.

Essa lógica não deve ser confundida com uma otimização completa de rede de serviços multimodais. O método não modela grade de navegação, frequência de escalas, disponibilidade de armador, disponibilidade de espaço, aceitação comercial da carga, confiabilidade de serviço, tempo de trânsito, custo de estoque ou decisão comercial de roteamento. Assim, uma seleção por porto mais próximo ou por lista de portos elegíveis é transparente e reproduzível, mas não necessariamente operacionalmente ótima nem comercialmente correta.

| Elemento da construção de rota | Papel no CabotageLens | Limite de interpretação |
| --- | --- | --- |
| Origem e destino | Definem os pontos finais da mesma remessa comparada. | Não especificam, por si só, serviço logístico contratado ou terminal efetivamente disponível. |
| Rota rodoviária direta | Representa a alternativa rodoviária origem-destino. | É uma rota modelada para comparação, não uma cotação comercial de transporte. |
| Porto de origem | Conecta a origem ao início da perna marítima. | Pode ser selecionado por elegibilidade/proximidade ou forçado; isso não comprova disponibilidade real de serviço. |
| Perna marítima | Representa a cabotagem entre os portos definidos no cenário. | Depende da proveniência da distância e não prova frequência, escala ou aceitação operacional. |
| Porto de destino | Conecta a perna marítima ao destino final. | Um porto regionalmente próximo não equivale automaticamente ao porto originalmente selecionado. |
| *On-carriage* | Representa o trecho rodoviário do porto de destino ao destino final. | Pode alterar materialmente custo e TTW CO2e, sobretudo em cenários com porto alternativo. |
| Porto forçado ou alternativo | Permite testar uma hipótese explícita de sensibilidade. | Deve ser rotulado como sensibilidade; não valida silenciosamente o porto originalmente selecionado. |
| Caso de mesmo porto | Registra situações em que origem e destino marítimos recaem no mesmo porto. | É limitação, exclusão ou caso não comparável; não representa uma cadeia normal de cabotagem. |

Os portos forçados ou alternativos devem, portanto, ser tratados como cenários de sensibilidade quando essa for a classificação rastreada. O uso de Pecém em um cenário alternativo para uma rota associada a Fortaleza não valida o Porto de Fortaleza, assim como o uso de Suape em uma sensibilidade associada a Recife não valida o Porto do Recife. Mesmo quando esses portos têm relação regional com o destino final, a mudança altera acessos rodoviários, distância marítima, terminal considerado e condição de interpretação; por isso, não pode ser apresentada como substituição silenciosa.

Casos em que a origem e o destino marítimos recaem no mesmo porto também não representam uma alternativa normal de cabotagem. Eles podem ser úteis para revelar limitação da lógica de seleção, para documentar uma exclusão ou para justificar classificação como caso não comparável, mas não devem sustentar conclusão sobre desempenho relativo entre rodovia e cabotagem. Nesses casos, a cadeia rodoviário-cabotagem-rodoviário deixa de representar uma alternativa modal substantiva.

Por fim, a seleção de portos não altera as fronteiras gerais do estudo. Os custos calculados continuam sendo estimativas de custo do modelo, e não fretes comerciais, tarifas contratadas ou cotações de mercado. As emissões continuam sendo emissões operacionais TTW CO2e, salvo indicação explícita em contrário, e não devem ser confundidas com WTW, LCA, CO2 isolado ou CO2e sob outra fronteira. A seção, portanto, define como a rota é construída e como seus limites devem ser lidos, sem transformar a escolha de portos em prova de disponibilidade comercial ou de superioridade universal da cabotagem.

### 4.5 Proveniência da distância rodoviária e lógica de roteamento/cache

A proveniência da distância rodoviária é um controle metodológico central no CabotageLens, porque a distância entra tanto na alternativa rodoviária direta quanto nas pernas rodoviárias de acesso da alternativa multimodal. No primeiro caso, ela representa a rota origem-destino usada para calcular custo modelado e emissões operacionais TTW CO2e da viagem exclusivamente rodoviária. No segundo, ela aparece no *pre-carriage* entre origem e porto de origem e no *on-carriage* entre porto de destino e destino final. Portanto, a qualidade dessa entrada afeta a comparação porta a porta, e não apenas uma etapa auxiliar do cálculo.

As distâncias rodoviárias usadas pela ferramenta devem ser lidas como distâncias roteadas/modeladas sob um provedor, perfil e configuração específicos, não como trajetórias GPS medidas nem como verdade observada de campo. Neste trabalho, a distância rodoviária é associada à camada de provedor/cache, com uso do OpenRouteService (ORS), no perfil `driving-hgv`, quando essa configuração está disponível no cenário executado. Essa proveniência torna explícito que o número de quilômetros é produto de uma lógica computacional de roteamento, e não uma medição direta de uma viagem executada.

O uso de cache complementa essa lógica ao registrar e reutilizar saídas já obtidas do provedor de rota. Isso melhora a reprodutibilidade e a auditabilidade, pois reduz variações acidentais entre execuções, evita chamadas desnecessárias ao provedor e permite distinguir uma mudança de premissa metodológica de uma simples instabilidade de consulta. Ao mesmo tempo, uma distância em cache não prova que a rota seja a única possível, a rota comercialmente usada por uma transportadora ou a rota operacionalmente correta para toda data e condição de tráfego.

| Elemento | Papel na proveniência da distância rodoviária | Limite de interpretação |
| --- | --- | --- |
| Provedor/perfil de roteamento | Produz a distância rodoviária modelada sob a configuração adotada, como ORS `driving-hgv` quando esse provedor/perfil está configurado. | É estimativa roteada sob aquela configuração, não distância observada de campo nem rota necessariamente usada por transportador real. |
| Cache de rotas | Registra e reutiliza saídas do provedor/cache para tornar a entrada de distância rastreável e reprodutível. | Reutilização não valida, por si só, a correção operacional da rota. |
| Distância rodoviária direta | Alimenta a alternativa road-only entre origem e destino. | Representa rota modelada para comparação, não trajetória GPS nem frete comercial. |
| Distância de *pre-carriage* | Alimenta o trecho rodoviário da origem ao porto de origem. | Depende da seleção ou imposição do porto e não comprova despacho real. |
| Distância de *on-carriage* | Alimenta o trecho rodoviário do porto de destino ao destino final. | Depende da seleção ou imposição do porto e não comprova escolha comercial de rota. |
| Rerun cache Batch 002 | Verificou estabilidade da camada Supabase/cache para as pernas rodoviárias do benchmark. | 63 hits, 0 misses, 0 escritas de provedor e nenhuma falha de leitura/escrita reduzem a hipótese de instabilidade de cache, mas não validam magnitude calibrada. |
| Lacuna metodológica remanescente | Separa qualidade da entrada de distância de outras premissas do modelo. | Estabilidade de distância não resolve diferenças de veículo, consumo, fator de emissão, carga/alocação ou fronteira TTW/WTW/LCA. |

No Batch 002, o rerun com Supabase/cache registrou 63 *route-cache hits*, 0 *misses*, 0 escritas de distância pelo provedor e nenhuma falha de leitura/escrita. Esse resultado sustenta a interpretação conservadora de que a instabilidade da camada provedor/cache é improvável como explicação principal para a lacuna de magnitude no lado rodoviário do benchmark. A conclusão, porém, deve parar nesse ponto: o rerun não demonstra reprodução exata de Gustavo/Costa, não valida a magnitude calibrada das emissões e não transforma a distância roteada em evidência de operação real.

A estabilidade da distância rodoviária também não elimina diferenças metodológicas mais amplas. Permanecem relevantes as premissas de veículo, consumo de combustível, fatores de emissão, massa e alocação de carga, além das fronteiras TTW, WTW, LCA, CO2 e CO2e. Assim, uma comparação com referência externa só é defensável quando explicita se está tratando emissões operacionais TTW CO2e ou outra fronteira ambiental. No CabotageLens, salvo indicação explícita em contrário, as emissões permanecem operacionais TTW CO2e.

A camada de provedor/cache tampouco modela comportamento do motorista, dinâmica de congestionamento, despacho real, fechamentos viários, escolha comercial de rota ou contratos logísticos. Ela fornece uma entrada roteada e auditável para um cenário de comparação, não uma simulação completa da operação de transporte. Da mesma forma, os custos calculados a partir dessas rotas continuam sendo estimativas de custo do modelo, e não tarifas contratadas, cotações ou fretes comerciais.

Desse modo, a proveniência da distância rodoviária deve ser tratada como controle de qualidade da entrada e como parte da trilha de auditoria do estudo. Ela melhora a capacidade de revisar e reproduzir o cenário calculado, mas não substitui validação operacional, não prova disponibilidade comercial da rota e não apaga lacunas de fronteira, carga, alocação ou parâmetros de emissão. Essa distinção é necessária para que a comparação entre rodovia e cabotagem permaneça tecnicamente rastreável sem ultrapassar o que os artefatos do projeto demonstram.

### 4.6 Proveniência da distância marítima e hierarquia de fallback

A distância marítima é uma entrada central da alternativa rodoviário-cabotagem-rodoviário, pois define a extensão da perna de cabotagem entre o porto de origem e o porto de destino do cenário. No CabotageLens, essa distância é registrada em quilômetros (`km`) e, quando o artefato de origem usa essa unidade, também em milhas náuticas (`nm`). A conversão adotada nos artefatos rastreados é `1 nm = 1.852 km`. Essa informação não é apenas uma unidade de cálculo: ela faz parte da proveniência do resultado e condiciona a confiança que pode ser atribuída à linha analisada.

A hierarquia metodológica privilegia evidência documentada para o par exato de portos selecionado ou explicitamente forçado no cenário. Uma referência marítima externa (`external_reference`) ou uma matriz marítima/SeaMatrix (`seamatrix`) é mais forte quando identifica o par de portos correspondente, preserva unidade e origem da informação, e não depende de substituição silenciosa por outro terminal. Mesmo nessa situação, proveniência de distância marítima não é a mesma coisa que disponibilidade efetiva de serviço: a distância documentada continua sendo uma entrada de rota ou de sensibilidade; ela não prova disponibilidade comercial de serviço, escala, frequência, cronograma, armador disponível, capacidade de slot, terminal operacional ou roteamento efetivamente contratado.

Quando a distância vem de `haversine_fallback`, a interpretação deve ser mais restrita. Esse fallback geométrico pode ser útil para triagem, diagnóstico histórico, identificação de lacunas e priorização de correções, mas não representa uma rota marítima validada. Por isso, uma linha sustentada apenas por `haversine_fallback` não deve apoiar conclusões numéricas fortes de custo modelado ou TTW CO2e. Nesses casos, o uso adequado é manter a linha como `reference_needed`, registro diagnóstico, exclusão metodológica ou preparação de sensibilidade, conforme a classificação rastreada nos artefatos de validação.

Referências externas associadas a portos forçados ou alternativos também exigem separação explícita. Uma distância documentada para um porto alternativo pode apoiar a interpretação de uma sensibilidade nomeada, mas não valida automaticamente o porto originalmente selecionado. Assim, Pecém não valida Fortaleza, e Suape não valida Recife. Do mesmo modo, uma referência vinculada a um cenário de porto forçado deve permanecer vinculada àquele cenário; ela não pode ser promovida silenciosamente a evidência do caso-base selecionado pelo modelo.

| Fonte de distância marítima | Papel no CabotageLens | Limite de interpretação |
| --- | --- | --- |
| Referência exata para portos selecionados (`external_reference`) | Entrada mais forte quando documenta o par exato de portos do cenário. | Não comprova serviço comercial, frequência, escala, preço de frete ou roteamento real. |
| Matriz marítima / SeaMatrix (`seamatrix`) | Fonte matricial para distância entre portos quando há registro aplicável. | Depende de par de portos, unidade e ausência de fallback; ainda é distância modelada/documentada, não prova operacional. |
| Referência externa ou manual para porto forçado | Sustenta uma sensibilidade ou cenário alternativo explicitamente nomeado. | Não valida o porto originalmente selecionado nem substitui o caso-base sem decisão metodológica. |
| `haversine_fallback` | Estimativa geométrica de triagem quando não há distância marítima documentada. | Não valida rota marítima e não sustenta conclusão numérica forte por si só. |
| Valor histórico diagnóstico | Preserva saídas do Batch 001 para auditoria e comparação metodológica. | Não é resultado corrigido nem evidência de validação final. |
| Referência exata ausente | Sinaliza lacuna de evidência para o par de portos selecionado. | Pode exigir `reference_needed`, tratamento apenas em sensibilidade ou classificação conservadora. |
| Perna marítima same-port | Registra caso-limite em que origem e destino marítimos coincidem. | Serve como aviso de qualidade de rota; não deve ser tratado como comparação normal de cabotagem. |

Essa hierarquia de fontes controla a classificação de uso no TF. Distância exata para o par selecionado, distância de matriz aplicável, referência de porto forçado, fallback geométrico e valor histórico não têm o mesmo peso metodológico. Promover evidência aproximada, histórica ou de porto próximo ao mesmo nível de uma referência exata para o par selecionado criaria falsa robustez. Por isso, a ausência de distância marítima exata para o porto selecionado pode manter o caso como lacuna de referência, bloquear conclusão principal ou limitar a leitura a uma sensibilidade conservadora.

Por fim, a proveniência da distância marítima não altera as demais fronteiras do estudo. Os custos continuam sendo estimativas de custo do modelo, e não tarifas ou cotações comerciais de frete. As emissões continuam sendo operacionais TTW CO2e, salvo indicação explícita em contrário. Valores, estudos ou artefatos que tratem CO2, WTW ou LCA não devem ser misturados à fronteira atual sem reconciliação metodológica explícita. Essa separação evita que uma distância marítima bem documentada seja interpretada como validação completa da alternativa multimodal.

### 4.7 Avisos same-port e qualidade de rota

Os avisos de qualidade de rota no CabotageLens funcionam como controles interpretativos, não como mensagens cosméticas. Eles registram quando a construção modelada da alternativa rodoviário-cabotagem-rodoviário é fraca, incompleta ou inadequada para sustentar uma conclusão de nível TF. O objetivo desses avisos é impedir que uma linha tecnicamente rastreável, mas metodologicamente limitada, seja lida como comparação modal robusta.

O caso mais direto é o aviso *same-port*, que ocorre quando o porto de origem e o porto de destino da perna marítima são o mesmo porto. Nessa situação, a cadeia não representa uma alternativa normal de cabotagem, porque não há uma perna marítima efetiva entre portos distintos. O exemplo São Paulo/SP -> Santos/SP com Porto de Santos -> Porto de Santos deve ser tratado como limitação metodológica, diagnóstico ou registro de exclusão, não como evidência de desempenho da cabotagem. Isso não significa que o par origem-destino seja irrelevante para logística; significa apenas que a cadeia de cabotagem modelada naquele resultado não é uma alternativa multimodal válida para conclusão comparativa.

Outros avisos indicam fragilidades diferentes: perna marítima muito curta, distância marítima `haversine_fallback`, acesso rodoviário dominante, porto alternativo ou forçado, ausência de referência exata para o par de portos selecionado, rota histórica preservada apenas para diagnóstico ou construção de baixa confiança. Esses sinais não provam que a rota seja impossível no mundo real. Eles indicam que, dentro da fronteira documentada do modelo e dos artefatos disponíveis, a linha é fraca para sustentar uma conclusão acadêmica forte.

| Aviso ou condição de qualidade | O que indica | Uso seguro no TF |
| --- | --- | --- |
| Caso same-port | Porto marítimo de origem e destino coincidem. | Limitação, diagnóstico ou `record_only_warning`; não é comparação normal de cabotagem. |
| Perna marítima muito curta | A etapa marítima pode ser artificial ou pouco representativa. | Aviso de qualidade de rota; não sustenta conclusão modal principal por si só. |
| `haversine_fallback` | Distância marítima aproximada por triagem geométrica. | `reference_needed`, diagnóstico ou preparação de sensibilidade; não valida rota. |
| Referência exata ausente | Falta evidência para o par de portos selecionado. | Lacuna metodológica, bloqueio conservador ou tratamento de referência pendente. |
| Porto alternativo ou forçado | O cenário usa porto diferente do originalmente selecionado. | Sensibilidade nomeada; não substitui o caso-base selecionado. |
| Acesso rodoviário dominante | A cadeia multimodal depende fortemente dos trechos terrestres. | Discussão de composição da rota e limitação, sem conclusão automática. |
| Rota histórica diagnóstica | Resultado antigo preservado para auditoria. | `historical_diagnostic`; não é resultado corrigido. |
| Rota excluída | A construção não é válida para a fronteira atual. | Justificativa de exclusão ou exemplo de limitação. |

Essas condições alimentam a classificação conservadora dos resultados. Uma linha com aviso pode permanecer como `record_only_warning`, `reference_needed`, `excluded`, `sensitivity_only` ou `sensitive`, conforme a decisão metodológica aplicável. Essa classificação deve impedir que rotas fallback-only, same-port, alternate-port ou de baixa confiança sejam promovidas a `headline_candidate`. Do mesmo modo, a ausência de um aviso específico não deve ser interpretada como prova de disponibilidade real de serviço ou de validação comercial da rota.

Os avisos também não substituem análises que estão fora da fronteira atual do CabotageLens. Eles não verificam serviço real de cabotagem, terminal disponível, cronograma de armador, frequência, capacidade de slot, contrato, tarifa ou viabilidade comercial. Um aviso, portanto, não é prova de inviabilidade operacional; e uma linha sem aviso não é prova de que existe serviço regular, economicamente contratável e operacionalmente disponível.

Por fim, a leitura dos avisos deve manter as fronteiras gerais do estudo. Custos calculados em linhas com ou sem aviso continuam sendo estimativas de custo do modelo, não fretes comerciais. Emissões continuam sendo operacionais TTW CO2e, salvo indicação explícita em contrário, e não devem ser tratadas como CO2 isolado, WTW ou LCA. Assim, os avisos de qualidade de rota reforçam a transparência e a interpretação conservadora, evitando que resultados frágeis sejam convertidos em afirmações gerais sobre superioridade da cabotagem.

### 4.8 Fronteira de emissões

As emissões reportadas pelo CabotageLens neste TF são emissões operacionais TTW CO2e, salvo indicação explícita em contrário. A unidade principal é `kg CO2e` por remessa, pois a comparação metodológica parte de uma carga definida transportada entre a mesma origem e o mesmo destino. Normalizações por tonelada, TEU, contêiner ou tonelada-quilômetro podem ser úteis para comparação, mas somente quando preservam a unidade funcional, a base de carga, a distância considerada e a mesma fronteira ambiental.

Nesta fronteira, TTW cobre emissões diretas associadas ao combustível consumido nas pernas de transporte e nos componentes operacionais incluídos no cenário. Assim, a alternativa rodoviária direta, o *pre-carriage*, a perna marítima, o *on-carriage* e, quando modelados, os componentes de operação portuária e *hoteling* devem permanecer dentro do mesmo limite de interpretação. O resultado não deve ser lido como uma avaliação climática completa da cadeia logística, mas como uma estimativa operacional comparável entre alternativas modeladas sob a mesma fronteira.

O limite TTW CO2e exclui etapas a montante e efeitos de ciclo de vida. Portanto, este TF não incorpora, na linha de base, produção, refino e distribuição de combustíveis, construção e manutenção de infraestrutura, fabricação de caminhões ou navios, fim de vida de ativos, nem uma avaliação completa de ciclo de vida. Qualquer mudança para WTW, LCA ou uma métrica CO2-only exigiria documentação metodológica explícita, fatores compatíveis, unidades coerentes e separação clara em relação à linha de base atual.

Essa disciplina de fronteira é especialmente importante na comparação com literatura e benchmarks externos. Evidências WTW, LCA, CO2-only ou CO2e com outro limite operacional não podem ser misturadas diretamente com os resultados TTW CO2e do CabotageLens. Do mesmo modo, fatores ou resultados reportados apenas como CO2 não são automaticamente equivalentes a CO2e. Antes de comparar magnitudes, é necessário verificar unidade, base de carga, regra de alocação, base de distância, fator de emissão, gases incluídos e fronteira ambiental.

| Fronteira ou tipo de evidência | Significado neste TF | Limite de interpretação |
| --- | --- | --- |
| TTW CO2e | Fronteira operacional da linha de base do CabotageLens. | Não representa WTW, LCA ou impacto climático completo. |
| WTW | Inclui etapas a montante do combustível quando adotado por outra fonte. | Não pode calibrar a linha de base TTW sem reconciliação explícita. |
| LCA | Avalia ciclo de vida mais amplo, conforme escopo da fonte. | Não é executado pelo CabotageLens neste TF. |
| CO2-only | Evidência limitada ao dióxido de carbono quando assim reportada. | Não é automaticamente equivalente a CO2e. |
| Operações portuárias | Componentes operacionais incluídos somente quando modelados no cenário. | Devem usar a mesma fronteira das demais pernas combinadas. |
| *Hoteling* | Consumo associado à permanência ou escala quando separado pelo modelo. | Pode gerar dupla contagem se a intensidade marítima já incluir essa operação. |
| Benchmark externo | Referência comparativa para direção e lacunas metodológicas. | Acordo direcional não valida magnitude exata. |
| Fator rodoviário diagnóstico | Sensibilidade de reconciliação do Batch 002. | Não substitui nem recalibra o modelo de emissões de linha de base. |

A inclusão de operações portuárias e *hoteling* exige atenção adicional porque esses componentes podem estar representados de formas diferentes em fatores agregados. Se a intensidade marítima usada em um cenário já incorpora consumo associado a permanência em porto, adicionar *hoteling* ou operação portuária separadamente pode duplicar emissões. Se o cenário separa navegação, operação portuária e permanência atracada, essa decomposição precisa continuar explícita na metodologia e na interpretação do resultado.

O Batch 002 reforça essa cautela. A reconciliação de fator rodoviário é diagnóstica e sensível à fronteira adotada: ela ajuda a explicar parte da diferença entre o CabotageLens e o benchmark externo no lado rodoviário, mas não constitui validação calibrada de todas as magnitudes, não substitui o modelo de emissões de linha de base e não autoriza misturar TTW, WTW, LCA, CO2 e CO2e. Da mesma forma, concordância direcional com um benchmark externo indica consistência interpretativa sob condições comparáveis, não prova reprodução exata da metodologia externa.

Consequentemente, os resultados de emissões deste TF devem ser usados como estimativas operacionais TTW CO2e, específicas do corredor, da carga, da rota, dos portos e dos componentes modelados. Eles não devem sustentar afirmações de superioridade ambiental universal da cabotagem. A conclusão defensável é sempre condicionada à fronteira adotada, à qualidade das distâncias, à seleção de portos, à base de carga e à separação explícita entre evidência operacional TTW CO2e e outras métricas ambientais.

### 4.9 Fronteira de custo

Os custos reportados pelo CabotageLens neste TF são estimativas modeladas dentro da fronteira operacional definida. A unidade principal é `BRL` por remessa, pois a comparação parte da mesma unidade funcional transportada entre uma origem e um destino. A função do modelo é tornar transparente a comparação entre alternativas construídas sob hipóteses explícitas, não produzir preço de mercado, cotação comercial ou recomendação de contratação.

Na alternativa rodoviária direta, o custo road-only é formado pelos componentes modelados da perna rodoviária incluída no cenário. Na alternativa multimodal, o custo pode ser formado por *pre-carriage*, perna marítima, *on-carriage* e componentes portuários modelados quando estiverem habilitados. Assim, o número final representa a soma dos itens que o cenário efetivamente inclui, e não uma tarifa logística completa para executar a cadeia no mercado.

Essa fronteira deve ser separada de frete comercial. O custo modelado não é cotação de frete, não é tarifa de transportador, não é preço de armador, não é frete contratado e não deve ser usado diretamente para compras, contratação de transporte ou decisão comercial. A interpretação correta é "menor custo modelado dentro da fronteira definida", e não "menor frete comercial" ou "menor custo logístico total".

| Elemento de custo ou item de fronteira | Papel neste TF | Limite de interpretação |
| --- | --- | --- |
| Custo rodoviário modelado | Representa a alternativa road-only com os componentes rodoviários incluídos no cenário. | Não equivale a frete rodoviário comercial, tarifa negociada ou preço de mercado. |
| Custo de *pre-carriage* | Representa o acesso rodoviário da origem ao porto de origem. | Não é uma cotação independente de coleta, drayage ou serviço porta-porto. |
| Custo da perna marítima | Representa o componente marítimo modelado da cadeia de cabotagem. | Não estima tarifa de armador, contrato, slot, booking ou frete marítimo contratado. |
| Custo de *on-carriage* | Representa o acesso rodoviário do porto de destino ao destino final. | Não é uma cotação independente de entrega ou serviço porto-porta. |
| Componente portuário modelado | Entra apenas quando o cenário habilita componente portuário ou operacional correspondente. | Não representa tarifa portuária completa, tabela terminal, demurrage, detention ou todos os encargos locais. |
| Frete comercial de mercado | Fica fora da fronteira corrente do modelo. | Não pode ser inferido diretamente a partir do custo modelado. |
| Contrato, tarifa ou cotação | Só entrariam no estudo se fossem explicitamente modelados em uma fronteira futura. | Não são produzidos pelo CabotageLens neste TF. |
| Inventário, confiabilidade e cronograma | São dimensões logísticas relevantes, mas excluídas salvo modelagem explícita. | Não permitem concluir disponibilidade real, frequência de serviço, confiabilidade, restrição de cronograma ou disponibilidade de slot. |
| Resultado de sensibilidade de custo | Mostra como o custo modelado responde a uma hipótese documentada. | Não constitui conclusão comercial robusta nem valida preço praticado no mercado. |

A comparação de custos só é defensável quando os cenários preservam a mesma unidade funcional, a mesma base de carga, a mesma lógica de construção de rota, os portos selecionados ou forçados de forma explícita e a mesma regra sobre quais componentes entram no total. Se dois cenários usam componentes diferentes, a comparação precisa explicar o que está incluído e excluído em cada lado. Caso contrário, uma diferença em `BRL` pode refletir mudança de fronteira, e não diferença econômica entre modos.

Além disso, a fronteira corrente exclui, salvo modelagem explícita, margens comerciais, contratos negociados, preços spot ou de mercado, tarifas portuárias completas, seguros, tributos e taxas não modelados, custos administrativos, custo de inventário, custo de confiabilidade, restrições de cronograma, frequência de serviço, disponibilidade de slots, demurrage e detention. Esses itens são relevantes para uma decisão logística real, mas não fazem parte do núcleo de custo modelado usado para comparar as alternativas neste TF.

As sensibilidades de custo ajudam a avaliar dependência em relação a distância marítima, seleção de portos, componentes habilitados e outras hipóteses documentadas. Contudo, uma linha de sensibilidade com menor custo multimodal permanece uma evidência sensível à fronteira, não uma prova de viabilidade comercial, disponibilidade operacional ou competitividade contratual. O resultado também não demonstra que um transportador, armador ou operador logístico ofereceria frete menor no mundo real.

Por fim, custo e emissões devem permanecer como dimensões distintas. Um cenário pode apresentar menor custo modelado e menor TTW CO2e operacional, mas essa coincidência não autoriza transformar `BRL` e `kg CO2e` em um único vencedor sem regra de decisão explícita. Da mesma forma, menor custo modelado não prova superioridade econômica universal da cabotagem; a conclusão válida é sempre condicionada ao corredor, à carga, à rota, aos portos, aos componentes incluídos e à fronteira de custo adotada.

### 4.10 Validação e classificação conservadora

A validação adotada neste TF é conservadora e hierarquizada por evidência. Ela não busca demonstrar equivalência perfeita entre o CabotageLens e uma operação real específica, nem transformar um benchmark externo em verdade de referência. O objetivo metodológico é mais restrito: verificar plausibilidade, consistência dimensional, rastreabilidade das entradas, disciplina de fronteira e classificação explícita da incerteza. Por isso, a classificação não é um apêndice posterior aos resultados; ela faz parte da metodologia e define, antes da interpretação final, o que cada linha pode ou não pode sustentar.

Essa abordagem impede que "resultado executado" seja tratado automaticamente como "resultado válido para conclusão principal". Uma linha pode ter sido preservada por auditoria, planejada para sensibilidade, executada com hipótese condicional, bloqueada por lacuna de referência, excluída por inadequação de fronteira ou usada apenas como diagnóstico de benchmark. O uso acadêmico seguro depende dessa distinção. Assim, resultados fallback-only, same-port, alternate-port, históricos, bloqueados, excluídos ou `reference_needed` não devem ser promovidos a conclusões principais, mesmo quando contêm números rastreáveis.

No Batch 001B, a camada de decisão metodológica separa diagnósticos históricos, avisos preservados, casos excluídos, casos bloqueados, lacunas de referência, cenários apenas de sensibilidade e linhas sensíveis executadas. `historical_diagnostic` preserva resultados anteriores para auditoria e comparação metodológica, não para defender a versão corrigida da conclusão. `record_only_warning` pode manter um aviso, como same-port, sem tornar a cadeia uma comparação válida de cabotagem. `reference_needed` indica que ainda falta referência exata para o par de portos selecionado. `excluded` indica caso inválido ou fora da fronteira atual. `planned_blocked_methodology_decision` indica bloqueio por decisão metodológica, porto elegível ausente ou condição ainda não resolvida. `sensitivity_only` limita a linha a discussão de sensibilidade, e `sensitive` identifica resultado executado que permanece condicional.

| Classificação | Significado no TF | Uso seguro |
| --- | --- | --- |
| `historical_diagnostic` | Resultado anterior preservado para rastreabilidade e comparação metodológica. | Auditoria, histórico e explicação de evolução do método. |
| `record_only_warning` | Registro mantido para documentar aviso de qualidade, como same-port. | Limitação ou exemplo metodológico; não valida cabotagem. |
| `reference_needed` | Falta referência exata para o par de portos selecionado. | Lacuna de evidência e prioridade de validação futura. |
| `excluded` | Caso inválido ou fora da fronteira atual. | Justificativa de exclusão; não sustenta resultado numérico. |
| `planned_blocked_methodology_decision` | Caso bloqueado por decisão metodológica ou condição não atendida. | Registro de bloqueio e requisito para trabalho futuro. |
| `sensitivity_only` | Cenário adequado apenas como hipótese de sensibilidade. | Discussão de sensibilidade, sem substituir o caso-base. |
| `sensitive` | Linha executada com resultado condicional e não robusto. | Evidência sensível à hipótese; não é conclusão principal. |
| `headline_candidate` | Possível resultado principal após validação e sensibilidade suficientes. | Deve permanecer vazio até que os artefatos rastreados sustentem a promoção. |
| `same_direction_large_gap` | Linha de benchmark com mesma direção modal, mas grande diferença de magnitude. | Consistência direcional; não validação calibrada. |
| `benchmark_supports_direction` | Benchmark externo apoia a direção da comparação de emissões. | Interpretação direcional e limitada por fronteira. |
| `benchmark_supports_road_factor_explanation` | Reconciliação diagnóstica explica parte da lacuna rodoviária. | Diagnóstico de premissas rodoviárias, não recalibração. |
| `benchmark_methodology_gap` | Diferença atribuída a lacunas metodológicas não reconciliadas. | Discussão de método, alocação, distância, rota e parâmetros. |
| `benchmark_boundary_mismatch` | Diferença associada a fronteiras ambientais, operacionais ou de alocação distintas. | Caveat de comparabilidade; não valida magnitude exata. |

No estado atual dos artefatos, não há `headline_candidate` robusto. As sensibilidades executadas podem apoiar a discussão sobre dependência de distância marítima, porto alternativo e hipótese de fronteira, mas não devem ser tratadas como achados principais universais. Em particular, uma linha `sensitive` pode indicar que a alternativa multimodal permanece menor em custo modelado e TTW CO2e operacional sob uma hipótese nomeada, mas essa leitura continua condicionada ao cenário, à origem-destino, aos portos usados, à distância adotada e aos componentes incluídos. Ela não valida automaticamente o porto originalmente selecionado nem demonstra superioridade geral da cabotagem.

O Batch 002 acrescenta uma camada específica de benchmark. Suas categorias indicam apoio direcional, explicação diagnóstica de lacunas e incompatibilidades de fronteira, não reprodução exata do workbook Gustavo/Costa. A classificação `same_direction_large_gap` significa que o benchmark e o CabotageLens apontam a mesma direção modal nas linhas suportadas, mas com diferença de magnitude ainda grande. Portanto, concordância direcional não equivale a concordância calibrada. O Batch 002 pode fortalecer a defesa metodológica ao mostrar que o sinal comparativo é coerente sob determinadas condições, mas não valida magnitudes exatas de emissões, custos, portos, serviços, alocação interna do workbook ou equivalência com fretes comerciais.

A reconciliação de fator rodoviário deve ser lida na mesma chave. Ela ajuda a explicar parte da lacuna de magnitude no lado road-only por diferenças de premissa rodoviária, mas permanece diagnóstica e não substitui o modelo de linha de base do CabotageLens. O fator testado nesse exercício não recalibra a aplicação, não altera a fronteira operacional do TF e não autoriza misturar TTW, WTW, LCA, CO2 e CO2e. Emissões continuam sendo interpretadas como CO2e operacional TTW, salvo indicação explícita em contrário; custos continuam sendo estimativas modeladas, não tarifas, cotações ou fretes comerciais.

Por fim, a classificação conservadora também delimita o que este TF não prova. Uma linha classificada como direcionalmente coerente, sensível ou metodologicamente útil não demonstra disponibilidade real de serviço de cabotagem, frequência, escala, slot, aceitação de carga, contrato, viabilidade comercial ou decisão de armador. A contribuição metodológica está em tornar essas limitações explícitas, preservando rastreabilidade e evitando que resultados condicionais sejam apresentados como validação operacional completa. Dessa forma, a metodologia se encerra com uma regra de interpretação: cada resultado só pode ser usado até o limite da evidência e da classificação que os artefatos rastreados sustentam.

## 5. Ferramenta computacional

### 5.1 Visão geral da ferramenta e arquitetura do protótipo

O CabotageLens é o protótipo computacional desenvolvido neste trabalho para apoiar a comparação acadêmica entre uma alternativa rodoviária direta e uma alternativa rodoviário-cabotagem-rodoviário em corredores brasileiros. A ferramenta não é tratada como produto de cotação comercial nem como sistema operacional de contratação de transporte. Seu papel no TF é tornar rastreáveis as escolhas de rota, porto, distância, custo modelado e emissões operacionais TTW CO2e discutidas na metodologia.

Do ponto de vista de uso, o protótipo combina uma interface Streamlit com fluxos reprodutíveis por scripts e linha de comando disponíveis no repositório. Na interface, o usuário informa origem, destino, base de carga e parâmetros operacionais ou de modelo. A partir dessas entradas, a ferramenta constrói uma alternativa rodoviária direta e uma alternativa multimodal composta por perna rodoviária de acesso, perna marítima, perna rodoviária final e componentes modelados quando habilitados, como operações portuárias e hoteling.

As saídas esperadas incluem distâncias modeladas por perna, custos modelados, emissões operacionais TTW CO2e, portos selecionados, avisos de qualidade de rota, proveniência das distâncias e artefatos de exportação ou validação quando disponíveis. Essa apresentação é deliberadamente mais próxima de um instrumento de auditoria metodológica do que de um simulador comercial. O resultado numérico só é interpretável junto com a fronteira do cenário, a origem da distância, os parâmetros de modelo e a classificação de qualidade associada.

A organização do repositório reflete essa separação de responsabilidades. A interface permanece concentrada em `app/`, enquanto a lógica reutilizável de domínio fica em `modules/`. Os scripts preservam fluxos reproduzíveis de execução, validação, exportação ou manutenção; os dados rastreados ficam em `data/`; as migrações registram a evolução do esquema Supabase/Postgres; e os documentos do TF ficam em `docs/`, incluindo metodologia, fronteiras, validação, auditoria e planejamento acadêmico.

| Componente | Papel no CabotageLens | Interpretação no TF |
| --- | --- | --- |
| `app/` | Interface Streamlit, organização de páginas, sessão e apresentação dos resultados. | Camada de interação e demonstração do protótipo. |
| `modules/` | Lógica reutilizável de roteamento, avaliação multimodal, combustível, emissões, custos, persistência, proveniência e avisos de qualidade de rota. | Núcleo computacional auditável, separado da interface. |
| `scripts/` | Fluxos reprodutíveis para execução, validação, exportação ou manutenção. | Apoio à repetibilidade e à revisão dos resultados. |
| `data/` | Insumos estáticos e artefatos processados rastreados. | Base material dos dados versionados usados pelo protótipo. |
| `supabase/migrations/` | Evolução do esquema do backend durável em Supabase/Postgres. | Registro da camada de persistência e cache compartilhado. |
| `docs/` e artefatos de validação/exportação | Metodologia, fronteiras, sínteses, inventários, resultados rastreados e evidências de classificação quando disponíveis. | Trilha de auditoria acadêmica e suporte à interpretação conservadora. |

A persistência em Supabase/Postgres é relevante porque o protótipo depende de caches e registros reaproveitáveis para rotas, lugares, cenários e resultados. Essa camada melhora a rastreabilidade e reduz a dependência de chamadas repetidas a provedores externos, mas não transforma o protótipo em uma fonte independente de verdade operacional. Os registros persistidos documentam o que foi calculado sob determinadas condições; eles não confirmam, por si só, a disponibilidade real de serviço, escala, slot, terminal, contrato ou tarifa.

Os artefatos de validação e exportação cumprem função semelhante. Eles ajudam a preservar configurações, saídas, bloqueios, exclusões, sensibilidades e decisões metodológicas, o que facilita a revisão posterior dos resultados. Entretanto, a existência desses artefatos aumenta a auditabilidade do processo, não a validade operacional automática de uma rota real. Uma linha exportada ou validada internamente continua limitada pela qualidade da distância, pela seleção de portos, pelo cache ou provedor usado, pelos parâmetros adotados e pela fronteira do cenário.

Por isso, a arquitetura do CabotageLens deve ser lida como arquitetura de protótipo acadêmico. A ferramenta não resolve uma super-rede multimodal nacional, não verifica horários de navegação, frequência de escalas, disponibilidade de transportadores, aceitação de carga em terminais, tarifas negociadas, contratos ou viabilidade comercial. Também não produz preços de mercado: os custos reportados permanecem estimativas modeladas, distintas de cotações, tarifas ou fretes comerciais.

De modo análogo, as emissões reportadas permanecem emissões operacionais TTW CO2e, salvo indicação explícita em contrário. O protótipo não executa análise WTW nem LCA nesta versão, e seus resultados não devem ser usados para afirmar superioridade universal da cabotagem. A contribuição computacional está em oferecer uma estrutura transparente, modular e reproduzível para comparação condicionada entre alternativas, deixando explícito o que foi modelado, o que foi aproximado e o que permanece fora da fronteira do trabalho.

### 5.2 Fluxo de uso e entradas do usuário

O fluxo de uso do CabotageLens começa pela definição de um cenário de comparação, não pela solicitação de uma cotação ou pela reserva de transporte. Na interface Streamlit, e nos fluxos reprodutíveis por scripts quando aplicável, o usuário informa uma origem, um destino, uma base de carga e parâmetros operacionais ou de modelo que delimitam a análise. Esses campos não são apenas entradas de tela: eles definem a fronteira do cenário avaliado, isto é, quais locais, volumes, componentes, fontes de distância e hipóteses entram no cálculo comparativo.

As entradas de origem e destino são resolvidas em localizações utilizadas pela construção de rota. A partir dessas localizações, a ferramenta monta duas alternativas conceituais: uma alternativa rodoviária direta entre origem e destino e uma alternativa rodoviário-cabotagem-rodoviário, composta por acesso rodoviário ao porto de origem, perna marítima e acesso rodoviário final a partir do porto de destino. A alternativa multimodal depende dos portos selecionados pelo procedimento do cenário ou, em fluxos de validação e sensibilidade, de portos elegíveis, forçados ou alternativos explicitamente configurados. Essa configuração deve ser interpretada como uma hipótese de modelagem, não como prova de serviço real entre os portos.

Além dos pontos geográficos, o cenário inclui a base de carga e parâmetros que afetam a alocação dos resultados. A massa transportada, a quantidade em TEU quando informada, a conversão padrão entre toneladas e TEU, o modo de alocação da parcela marítima, o fator de carga, o tipo de caminhão, a classe representativa de embarcação e a ativação de componentes como hoteling e operações portuárias influenciam os resultados calculados. Portanto, alterar a base de carga, a forma de construção de rota, a escolha de portos, os componentes habilitados ou a fonte de distância pode alterar tanto a magnitude quanto a interpretação da comparação.

| Elemento de entrada ou fluxo | Papel no cenário | Limite de interpretação |
| --- | --- | --- |
| Origem | Define o ponto inicial e a base para geocodificação, rota direta e acesso ao porto de origem. | Não garante disponibilidade de coleta, terminal ou serviço real. |
| Destino | Define o ponto final e a base para rota direta e acesso rodoviário final. | Não confirma entrega comercial, janela operacional ou aceitação de carga. |
| Base de carga | Define massa, TEU e alocação usada para custos e emissões por remessa. | Mudanças de carga podem alterar a comparação; não representam todos os perfis logísticos. |
| Rota rodoviária direta | Alternativa de referência para transporte por caminhão entre origem e destino. | Depende de provedor/cache e não substitui rota contratada real. |
| Seleção de portos / porto forçado | Define os nós marítimos usados na alternativa multimodal. | Porto selecionado ou forçado não prova serviço de armador, frequência, slot ou viabilidade comercial. |
| Perna marítima | Representa a cabotagem entre os portos do cenário. | Fonte de distância e avisos de qualidade condicionam a confiança da leitura. |
| Componentes habilitados | Incluem ou excluem parcelas como hoteling e operações portuárias quando modeladas. | Componentes desabilitados ou aproximados mudam a fronteira do resultado. |
| Parâmetros de custo | Transformam consumo e componentes modelados em estimativas monetárias. | São estimativas de modelo, não tarifas, cotações ou fretes comerciais. |
| Parâmetros de emissões | Aplicam a fronteira operacional TTW CO2e aos combustíveis e pernas representadas. | Não são WTW nem LCA, salvo indicação explícita de outra fronteira. |
| Avisos de qualidade de rota | Indicam cautelas como caso same-port, distância marítima ausente, pequena ou estimada por fallback. | São alertas de interpretação, não validação automática nem otimização de rota. |
| Registro de exportação ou validação | Preserva entradas, saídas, portos, proveniência e classificação quando disponível. | Aumenta auditabilidade, mas não transforma o cenário em recomendação operacional final. |

O resultado apresentado ao usuário deve ser lido junto com os componentes que o produziram. Distâncias por perna, portos usados, origem da distância marítima, avisos de qualidade de rota, custos modelados, emissões TTW CO2e e eventuais classificações de validação formam um conjunto interpretativo. Separar o número final desses metadados enfraquece a rastreabilidade do protótipo, pois uma economia aparente de custo ou emissão pode depender de uma distância de menor confiança, de um porto alternativo, de um componente habilitado ou de uma fronteira de custo mais restrita.

Também é essencial distinguir o cenário modelado de uma operação logística real. Um cenário de entrada não comprova aceitação efetiva da carga, disponibilidade de serviço de cabotagem, frequência de navegação, disponibilidade de slot, aceitação por terminal, janela de atracação, contrato, tarifa negociada ou viabilidade comercial. Da mesma forma, a seleção de um porto pelo protótipo ou por uma configuração de sensibilidade não significa que esse porto seja comercialmente ótimo ou operacionalmente disponível para a carga analisada.

Quando há exportações, registros persistidos ou artefatos de validação, sua função é preservar a memória técnica do que foi calculado: entradas de cenário, parâmetros relevantes, saídas do modelo, proveniência de distância, portos usados, avisos e classificação de uso. Esses registros apoiam auditoria, repetição controlada e revisão acadêmica posterior. Eles não eliminam as limitações do cenário nem convertem a interface em ferramenta de decisão automática. Assim, o fluxo de uso do CabotageLens deve ser entendido como suporte transparente à comparação condicionada entre alternativas, mantendo explícito o que foi informado pelo usuário, o que foi calculado pelo modelo e o que permanece fora da fronteira do TF.

### 5.3 Construção das alternativas de rota

A construção das alternativas de rota é a etapa em que as entradas do cenário são transformadas em duas cadeias comparáveis: uma rota rodoviária direta e uma cadeia rodoviário-cabotagem-rodoviário. O objetivo não é simular todas as opções logísticas possíveis no território nacional, mas gerar uma representação rastreável das alternativas necessárias para a comparação acadêmica definida na unidade funcional. Por isso, a rota construída deve ser lida como cenário modelado, condicionado às entradas, aos portos, às fontes de distância e aos componentes habilitados.

Na alternativa road-only, o CabotageLens representa o transporte da origem ao destino por uma perna rodoviária direta dentro da fronteira do modelo. Essa perna fornece a distância rodoviária usada para estimar consumo, custo modelado e emissões operacionais TTW CO2e da alternativa exclusivamente terrestre. A existência dessa rota calculada não comprova uma viagem real executada, uma rota contratada específica ou uma condição comercial de frete; ela funciona como referência modelada para comparar a mesma remessa com a alternativa multimodal.

Na alternativa rodoviário-cabotagem-rodoviário, a ferramenta decompõe a cadeia em três trechos principais: acesso rodoviário da origem ao porto de origem, perna marítima entre porto de origem e porto de destino, e acesso rodoviário final do porto de destino ao destino. Quando habilitados no cenário, componentes como operações portuárias e hoteling integram a avaliação sob a mesma lógica de fronteira operacional. Cada trecho contribui para a distância modelada, o custo modelado e as emissões operacionais TTW CO2e, de modo que a perna marítima não deve ser analisada isoladamente como se representasse toda a alternativa multimodal.

| Elemento da rota | Papel no modelo | Limite de interpretação |
| --- | --- | --- |
| Perna road-only | Representa a alternativa rodoviária direta entre origem e destino. | É rota modelada para comparação, não frete comercial nem prova de operação real. |
| *Pre-carriage* | Conecta a origem ao porto de origem por rodovia. | Pode alterar materialmente custo e TTW CO2e; não é etapa acessória desprezível. |
| Perna marítima | Representa a cabotagem entre os portos do cenário. | Depende da proveniência da distância e não comprova serviço marítimo real. |
| *On-carriage* | Conecta o porto de destino ao destino final por rodovia. | Pode mudar a leitura do multimodal quando o porto está afastado do destino. |
| Porto selecionado | Define o nó marítimo escolhido pela lógica do cenário. | Não prova serviço de armador, aceitação terminal, slot, frequência ou viabilidade comercial. |
| Porto forçado ou alternativo | Permite representar uma hipótese explícita de sensibilidade. | Não substitui silenciosamente o porto selecionado nem valida o caso-base. |
| Caso same-port | Indica coincidência entre porto de origem e de destino. | Não representa cadeia normal de cabotagem nem conclusão principal robusta. |
| Distância por fallback | Permite triagem quando falta distância marítima mais forte. | Não valida rota sozinha e deve ser tratada com cautela metodológica. |
| Aviso de qualidade de rota | Sinaliza limitações de construção, distância ou interpretação. | É controle interpretativo, não otimização nem validação automática. |

A escolha dos portos é decisiva nessa construção. Em cenários ordinários, portos selecionados a partir do conjunto elegível definem os nós da perna marítima e, por consequência, os acessos rodoviários de entrada e saída. Em cenários de validação ou sensibilidade, portos forçados ou alternativos podem ser usados para testar uma hipótese documentada. Essa flexibilidade aumenta a auditabilidade, mas também exige disciplina interpretativa: porto selecionado, elegível, forçado ou alternativo é uma premissa do cenário, não prova de disponibilidade de serviço, escala, frequência, slot, aceitação por terminal, contrato ou viabilidade comercial.

Da mesma forma, a proveniência das distâncias condiciona o uso do resultado. Distâncias rodoviárias calculadas por provedor/cache e distâncias marítimas oriundas de matriz, referência externa ou fallback não têm o mesmo peso metodológico. Casos same-port, casos sustentados apenas por fallback, cenários de porto alternativo, registros históricos, linhas bloqueadas, excluídas ou classificadas como `reference_needed` devem permanecer fora de conclusões principais robustas. Eles podem informar limitações, sensibilidade, diagnóstico ou trabalho futuro, mas não devem ser promovidos a evidência de superioridade modal.

Assim, a construção de rota no CabotageLens deve ser interpretada em conjunto com a seleção de portos, a proveniência das distâncias, os componentes habilitados, os avisos de qualidade, a fronteira de custo e a fronteira de emissões. O modelo não otimiza uma rede multimodal nacional completa, não escolhe a rota comercialmente ótima e não automatiza uma recomendação de decisão. Seus custos permanecem estimativas modeladas, não fretes comerciais; suas emissões permanecem operacionais TTW CO2e, salvo indicação explícita em contrário. A contribuição da ferramenta está em tornar a comparação entre alternativas transparente e auditável, sem transformar uma rota modelada em prova de operação real ou de superioridade universal da cabotagem.

### 5.4 Cálculo de distância, custo modelado e emissões operacionais

Após a construção das alternativas de rota, o CabotageLens consolida as distâncias, os custos modelados e as emissões operacionais em saídas de cenário. Essa consolidação parte das pernas definidas na seção anterior: a perna rodoviária direta no caso road-only e, no caso multimodal, o *pre-carriage*, a perna marítima e o *on-carriage*, com componentes adicionais apenas quando estiverem habilitados no cenário. Esta subseção descreve essa consolidação em nível de relatório; ela não introduz novas fórmulas, fatores de emissão, taxas de custo, parâmetros de combustível ou premissas de modelo.

As distâncias são preservadas por perna antes de serem agregadas para interpretação do cenário. A alternativa rodoviária direta tem uma distância origem-destino; a alternativa multimodal combina as distâncias dos acessos rodoviários e da perna marítima. O total modelado, porém, não deve apagar a decomposição: a distância marítima, a distância de acesso terrestre, os portos selecionados ou forçados, a proveniência da distância e os avisos de qualidade de rota continuam determinando a confiança e o uso acadêmico do resultado.

O custo modelado é calculado a partir dos componentes incluídos no cenário, como trechos rodoviários, perna marítima e componentes portuários quando aplicáveis. A saída em `BRL` representa uma estimativa operacional dentro da fronteira adotada, não uma cotação de frete, tarifa de transportador, preço de armador, contrato, booking ou custo logístico total de mercado. Portanto, uma diferença de custo entre road-only e multimodal deve ser lida como diferença de custo modelado sob as hipóteses do cenário, não como prova de superioridade comercial.

As emissões são consolidadas separadamente como emissões operacionais TTW CO2e, de acordo com a fronteira definida no Capítulo 4. Essa fronteira cobre os componentes de transporte e operação explicitamente representados, mas não equivale a WTW, LCA ou evidência CO2-only. Resultados, fatores ou benchmarks com outra fronteira ambiental só podem ser comparados quando a diferença de unidade, gases incluídos, base de carga, alocação e escopo for explicitamente reconhecida. Assim, o resultado de emissões do protótipo permanece uma estimativa operacional por cenário, não uma avaliação completa de ciclo de vida.

| Dimensão de saída | O que representa | Limite de interpretação |
| --- | --- | --- |
| Distância por perna | Quilometragem associada a road-only, *pre-carriage*, perna marítima e *on-carriage*. | Deve ser lida com a proveniência da distância e os avisos de qualidade. |
| Distância total modelada | Soma interpretativa das pernas incluídas na alternativa avaliada. | Não substitui a leitura por perna nem prova rota operacional real. |
| Custo modelado | Estimativa em `BRL` dos componentes incluídos no cenário. | Não é frete comercial, tarifa, cotação ou custo logístico total. |
| Emissões TTW CO2e | Emissões operacionais dos componentes representados. | Não são WTW, LCA nem CO2-only. |
| Operações portuárias | Parcela de custo e emissões quando o cenário inclui esse componente. | Deve ser compatível com a fronteira adotada para evitar comparação inconsistente. |
| *Hoteling* | Parcela associada à permanência/escala quando habilitada e não incorporada em outra intensidade. | Pode causar dupla contagem se somada a fator que já inclui esse consumo. |
| Comparação custo-emissões | Apresenta diferenças entre alternativas em dimensões separadas. | Não define vencedor único sem regra de decisão explícita. |
| Comparação diagnóstica com benchmark | Ajuda a explicar lacunas de magnitude e sensibilidade a premissas. | Não valida magnitudes exatas nem recalibra a linha de base. |

Os componentes habilitados exigem atenção especial. Operações portuárias e *hoteling* podem melhorar a completude operacional do cenário quando sua inclusão é compatível com a fronteira adotada, mas adicioná-los sem verificar o que já está representado em uma intensidade agregada pode criar dupla contagem ou comparação inconsistente. Do mesmo modo, desabilitar componentes altera a fronteira do cenário e deve ser considerado na interpretação do custo e das emissões. A comparabilidade depende de manter explícito o que entrou no cálculo e o que ficou fora.

Por fim, o uso de benchmarks e diagnósticos não altera a linha de base do protótipo. A reconciliação de fator rodoviário do Batch 002 é útil para mostrar que parte da lacuna de magnitude pode estar associada a premissas rodoviárias, mas ela é uma sensibilidade de alinhamento com benchmark, não uma recalibração do CabotageLens. Ela não substitui o modelo de linha de base, não valida magnitudes exatas, não transforma WTW em TTW e não autoriza misturar CO2, CO2e, WTW e LCA sem reconciliação explícita. As saídas de distância, custo e emissões devem, portanto, ser interpretadas como resultados condicionados pela construção de rota, pelos portos, pela proveniência dos dados, pelos componentes habilitados e pelos parâmetros do cenário.

### 5.5 Persistência, cache e proveniência dos dados

A persistência e o cache têm papel metodológico no CabotageLens porque ajudam a preservar a memória técnica das execuções e a reduzir a dependência de chamadas repetidas a provedores externos. O repositório documenta o Supabase/Postgres como backend durável do protótipo, com uso associado a cache de rotas, pontos de localização, registros de cenário, resultados e fluxos de comparação. Essa camada, porém, não deve ser lida como documentação operacional de transporte: ela registra evidências computacionais produzidas sob condições definidas, não confirma a existência de uma operação logística real.

No fluxo de construção de rota, o cache rodoviário pode reaproveitar distâncias já resolvidas entre locais normalizados, enquanto o cache de lugares preserva coordenadas associadas a entradas geográficas. Esse reaproveitamento melhora a repetibilidade do processo e evita variações desnecessárias causadas por novas consultas a provedores. Ainda assim, uma distância em cache continua dependente do provedor, do momento de obtenção, da configuração disponível, do perfil de roteamento e da forma como origem e destino foram resolvidos. Um cache hit indica que o protótipo reutilizou uma evidência anterior compatível com aquela consulta, não que a rota seja comercialmente disponível, contratável ou operacionalmente ótima.

A proveniência cumpre função semelhante para as pernas marítimas e para os artefatos de validação. O relatório deve distinguir distâncias vindas de matriz interna, referência externa, substituição manual documentada, fallback geométrico, registro histórico ou informação ausente. Essas categorias não têm o mesmo peso interpretativo. Distâncias exatas ou documentadas tendem a sustentar melhor a leitura do cenário; distâncias por fallback, registros históricos, casos bloqueados, excluídos ou classificados como `reference_needed` servem principalmente para auditoria, diagnóstico, sensibilidade ou trabalho futuro.

| Elemento persistido ou de proveniência | Papel no protótipo | Limite de interpretação |
| --- | --- | --- |
| Backend Supabase/Postgres | Camada durável para registros reutilizáveis do protótipo. | Não é base de mercado nem confirmação de serviço real. |
| Cache de rota | Reaproveita distâncias rodoviárias resolvidas anteriormente. | Reduz chamadas a provedor, mas não prova disponibilidade ou qualidade comercial da rota. |
| Cache de lugares/localização | Preserva coordenadas e nomes resolvidos para entradas geográficas. | Depende da resolução original e pode carregar ambiguidades da entrada. |
| Registro de cenário/resultado | Documenta entradas, parâmetros e saídas calculadas sob uma fronteira definida. | Registra o que foi modelado, não uma operação executada. |
| Fonte de provedor | Indica a origem computacional de uma distância ou localização. | Provedor identificado não equivale a verificação independente de serviço logístico. |
| Proveniência de distância | Classifica fonte, fallback, referência, substituição ou lacuna. | Deve ser lida junto com avisos de qualidade e classificação metodológica. |
| Evidência de rerun/cache hit | Mostra repetição controlada ou reaproveitamento de dados em cache. | Apoia reprodutibilidade, mas não valida magnitude de custo ou emissões. |
| Registro histórico | Preserva resultados anteriores para rastreabilidade. | Não deve ser promovido a conclusão principal quando a classificação limita seu uso. |

Os reruns e os cache hits são úteis para avaliar a estabilidade do processo computacional. Quando uma execução posterior reproduz a mesma fronteira de cenário usando registros de cache, ela fortalece a rastreabilidade e ajuda a separar instabilidade de provedor de diferenças metodológicas mais profundas. Esse tipo de evidência, entretanto, não valida por si só a viabilidade comercial, a disponibilidade de escala marítima, a aceitação por terminal, a frequência de serviço, a disponibilidade de slot ou a magnitude exata de custos e emissões.

Também é necessário interpretar registros persistidos junto com avisos de qualidade de rota e classificações metodológicas. Um resultado salvo com distância por fallback, porto alternativo, caso same-port, caso histórico ou lacuna de referência continua sujeito à limitação indicada, mesmo que esteja registrado de forma completa no banco ou em artefato de exportação. A persistência aumenta a auditabilidade, mas não corrige automaticamente lacunas de fonte, fronteira, seleção de porto, compatibilidade de serviço ou premissas de modelo.

Por fim, a camada de persistência não altera as fronteiras substantivas já definidas. Custos persistidos permanecem estimativas modeladas, não fretes comerciais, cotações ou tarifas de mercado. Emissões persistidas permanecem emissões operacionais TTW CO2e, salvo indicação explícita em contrário, e não se transformam em WTW, LCA ou evidência CO2-only por estarem registradas em cache ou exportação. A utilidade acadêmica da persistência está em permitir auditoria, repetição controlada e comparação transparente entre cenários, mantendo explícito o que foi calculado, em que condições e com quais limites de interpretação.

### 5.6 Saídas, avisos e registros de exportação

As saídas do CabotageLens devem ser entendidas como um conjunto interpretativo, não como uma soma de totais finais isolados. Para que a comparação seja auditável, o resultado precisa mostrar as pernas da rota, os portos selecionados ou forçados quando aplicável, a proveniência das distâncias, os custos modelados, as emissões operacionais TTW CO2e, os avisos de qualidade de rota e os campos de classificação ou status disponíveis nos artefatos de validação. Essa combinação permite reconstruir por que uma alternativa apresentou determinado custo ou emissão e qual nível de confiança metodológica pode ser atribuído ao caso.

Os avisos de qualidade de rota fazem parte do fluxo de interpretação. Eles indicam condições como porto de origem igual ao porto de destino, distância marítima ausente, distância marítima muito pequena, uso de fallback ou situação em que o acesso rodoviário domina uma cadeia marítima local. Esses avisos não são rótulos cosméticos: eles sinalizam que o resultado deve ser usado com cautela, como diagnóstico, limitação, triagem ou sensibilidade, conforme a classificação metodológica correspondente. Ao mesmo tempo, a presença de aviso não prova impossibilidade operacional; ela apenas mostra que a conclusão não pode ser tratada como robusta sem evidência adicional.

A ausência de aviso também tem limite. Um resultado sem alerta explícito não comprova disponibilidade real de serviço, frequência de navegação, escala, slot, aceitação por terminal, contrato, tarifa ou viabilidade comercial. Significa apenas que, dentro das regras de qualidade implementadas, não foi identificado um problema específico daquele tipo. Por isso, a leitura do resultado deve continuar condicionada à fronteira do cenário, à seleção de portos, à fonte de distância, aos componentes habilitados e à classificação de uso atribuída nos artefatos de validação.

| Saída ou registro | Por que importa | Limite de interpretação |
| --- | --- | --- |
| Pernas da rota | Mostram road-only, acesso rodoviário, perna marítima e acesso final quando aplicáveis. | Não provam operação real nem otimizam uma rede completa. |
| Portos selecionados ou forçados | Identificam os nós marítimos usados no cenário. | Não confirmam serviço de armador, escala, slot ou aceitação terminal. |
| Proveniência de distância | Indica fonte, fallback, referência, substituição ou lacuna. | Deve governar a confiança atribuída ao resultado. |
| Custo modelado | Resume a estimativa monetária dos componentes incluídos. | Não é frete comercial, cotação, tarifa ou contrato. |
| Emissões TTW CO2e | Resume emissões operacionais dentro da fronteira do modelo. | Não são WTW nem LCA, salvo declaração explícita de outra fronteira. |
| Avisos de qualidade de rota | Alertam limitações de construção, distância ou interpretação. | Não validam nem invalidam sozinhos uma operação real. |
| Classificação/status | Define o uso permitido do resultado no TF. | Não deve ser ignorada para promover resultado frágil a conclusão principal. |
| Registro de exportação | Preserva entradas, saídas, avisos e metadados quando disponível. | Aumenta rastreabilidade, não validação comercial ou operacional. |
| Registro de validação | Documenta bloqueios, exclusões, sensibilidades e uso metodológico. | Não transforma benchmark ou cenário em prova de magnitude exata. |

As classificações e status são a camada que transforma uma saída numérica em evidência utilizável no TF. Um caso `record_only_warning` pode documentar um comportamento de rota, mas não sustenta conclusão de desempenho modal. Um caso `reference_needed` preserva uma lacuna de fonte. Um caso `sensitivity_only` ou `sensitive` pode ser discutido como sensibilidade, desde que a hipótese esteja visível. Categorias de benchmark, como apoio direcional com grande lacuna de magnitude, permitem discutir consistência qualitativa, mas não reprodução exata, validação calibrada ou superioridade universal da cabotagem.

Os registros de exportação e validação dão suporte a essa disciplina porque preservam, quando disponíveis, entradas de cenário, portos, distâncias, proveniência, custos modelados, emissões TTW CO2e, avisos e classificações. Eles facilitam repetição controlada, revisão posterior e comparação entre versões do método. Contudo, uma linha exportada não é automaticamente uma rota real validada; ela continua sendo um registro de cálculo sob uma fronteira específica. Da mesma forma, exportar um custo não o converte em frete de mercado, e exportar uma emissão não altera sua fronteira operacional TTW CO2e.

Assim, a saída final do protótipo deve ser lida como evidência computacional classificada. O valor acadêmico está em tornar visível o que foi calculado, quais avisos foram acionados, qual proveniência sustenta as distâncias e qual uso metodológico é permitido. Essa estrutura evita que resultados frágeis sejam promovidos a conclusões principais e mantém a função do CabotageLens como ferramenta de comparação transparente e auditável, não como sistema automático de decisão, contratação ou validação operacional.

### 5.7 Limitações computacionais e uso correto da ferramenta

As seções anteriores mostram que o CabotageLens deve ser usado como protótipo de pesquisa para comparação transparente entre uma alternativa rodoviária direta e uma alternativa rodoviário-cabotagem-rodoviário. Seu valor está em tornar explícitas as entradas, pernas de rota, portos, fontes de distância, custos modelados, emissões operacionais TTW CO2e, avisos e classificações que sustentam cada cenário. O uso correto da ferramenta, portanto, é analítico e acadêmico: apoiar discussão técnica, análise de sensibilidade, rastreabilidade, reprodutibilidade e identificação de lacunas metodológicas.

Essa função não deve ser confundida com uma plataforma logística comercial. O CabotageLens não é um sistema de precificação de frete em produção, não cota frete e não gera tarifas de transportadores, tarifas de armadores, taxas negociadas, bookings ou contratos. Também não confirma disponibilidade real de serviço, programação de navegação, frequência de escala, disponibilidade de slot, aceitação por terminal, aceitação por transportador ou viabilidade comercial de uma cadeia. Um cenário modelado pode ser útil para comparar alternativas sob fronteiras explícitas, mas não substitui consulta operacional, negociação comercial ou validação de serviço.

Os resultados também não representam otimização completa de uma rede multimodal nacional. A construção de rota e a seleção de portos são mecanismos transparentes para formar cenários comparáveis, incluindo casos selecionados, elegíveis, forçados ou alternativos quando documentados. Eles não modelam todas as linhas, operadores, transbordos, horários, restrições de capacidade, tempos de espera, confiabilidade, custos de inventário ou regras comerciais de roteamento. Por isso, a alternativa calculada deve ser lida como uma cadeia modelada dentro da fronteira do TF, não como a melhor rota comercial disponível.

| Capacidade da ferramenta | O que apoia | O que não prova |
| --- | --- | --- |
| Comparação de rotas | Comparar road-only e road-cabotage-road sob o mesmo cenário. | Superioridade universal da cabotagem ou rota comercial ótima. |
| Estimativa de custo | Quantificar componentes de custo incluídos na fronteira do modelo. | Frete cotado, tarifa, taxa negociada ou contrato. |
| Estimativa de emissões | Calcular emissões operacionais TTW CO2e dos componentes representados. | WTW, LCA ou emissões reais exatas de uma operação contratada. |
| Seleção de portos | Tornar visível a hipótese portuária usada no cenário. | Serviço de armador, escala, slot, terminal ou aceitação comercial. |
| Cache e proveniência | Rastrear fontes, reuso de dados e qualidade da distância. | Verdade operacional independente ou disponibilidade de rota real. |
| Avisos e classificação | Definir cautelas e uso permitido no TF. | Permissão para ignorar limitações metodológicas. |
| Registro de exportação/validação | Preservar cenário, saída, aviso e classificação para auditoria. | Validação comercial, operacional ou de magnitude exata. |
| Análise de sensibilidade | Testar hipóteses documentadas e fronteiras alternativas. | Substituição automática da linha de base ou conclusão principal robusta. |

A interpretação dos custos e das emissões deve preservar as fronteiras substantivas do trabalho. Custos modelados são estimativas dentro da fronteira operacional implementada; não são cotações de frete, tarifas, preços contratados ou custos logísticos totais de mercado. Emissões reportadas permanecem operacionais TTW CO2e, salvo indicação explícita em contrário; não são WTW, LCA nem equivalentes a evidências ambientais com outra fronteira. Misturar essas categorias enfraquece a comparabilidade e pode transformar uma saída condicionada em uma afirmação que o modelo não sustenta.

Do mesmo modo, a classificação metodológica deve governar o uso de cada resultado. Resultados de sensibilidade, diagnósticos, fallback-only, same-port, porto alternativo, históricos, bloqueados, excluídos ou marcados como `reference_needed` não devem ser convertidos em conclusões principais. Eles são úteis para explicar incerteza, testar hipóteses, preservar histórico, documentar exclusões ou orientar trabalho futuro, mas não devem ser promovidos a evidência robusta de desempenho econômico ou ambiental. Nenhuma saída do protótipo, isoladamente, prova superioridade econômica ou ambiental universal da cabotagem.

Consequentemente, os estudos de caso do Capítulo 6 devem herdar essas limitações. Seus resultados precisam ser lidos em conjunto com as entradas do cenário, a escolha ou imposição de portos, a proveniência das distâncias, a lógica de cache/provedor, os parâmetros do modelo, os componentes habilitados, os avisos de qualidade, a fronteira de custo, a fronteira de emissões e a classificação conservadora atribuída. O fechamento deste capítulo é, portanto, uma regra de uso: o CabotageLens apoia comparação transparente e auditável, mas não automatiza decisão comercial, contratação de transporte, validação operacional ou conclusão universal sobre a cabotagem.

## 6. Estudos de caso e validacao

### 6.1 Batch 001 como diagnostico historico

O Batch 001 foi a primeira camada historica de avaliacao dos casos de validacao. Ele preserva resultados numericos para cinco pares origem-destino, mas todos os casos ficaram associados a necessidade de referencia ou revisao posterior. A principal limitacao diagnosticada foi o uso de distancias maritimas `haversine_fallback` em casos onde a distancia de navegacao e a plausibilidade de servico exigem evidencia mais forte.

Os cinco casos historicos foram:

| Caso | Par origem-destino | Portos historicos | Uso seguro no TF |
| --- | --- | --- | --- |
| `TF-VAL-001` | Sao Paulo, SP -> Santos, SP | Santos -> Santos | Diagnostico de caso same-port e limite de rota. |
| `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | Santos -> Manaus | Diagnostico historico; base para sensibilidade de distancia de referencia. |
| `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | Manaus -> Fortaleza | Diagnostico historico; referencia exata de Fortaleza permanece faltante. |
| `TF-VAL-004` | Brasilia, DF -> Salvador, BA | Angra dos Reis -> Salvador | Diagnostico historico; cadeia de Angra dos Reis depois excluida para o benchmark conteinerizado. |
| `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | Rio Grande -> Recife | Diagnostico historico; referencia exata de Recife permanece faltante. |

Essas linhas nao devem ser tratadas como resultados corrigidos. Elas sao importantes porque mostram onde a metodologia precisava separar fallback, selecao de porto, sensibilidade e exclusao.

### 6.2 Batch 001B como camada de auditabilidade

O Batch 001B nao executou novos modelos para todos os casos. Ele reorganizou a evidencia em uma camada de auditabilidade, preservando portos selecionados ou forcados, fonte de distancia maritima, unidade, conversao, status metodologico e uso permitido no TF. O resultado foi uma matriz de decisoes que separa casos executaveis, sensiveis, bloqueados, excluidos e apenas registrados.

Nenhum caso Batch 001B planejado foi classificado como pronto para conclusao principal. O principal ganho foi metodologico: o trabalho passou a registrar de forma explicita por que uma linha nao deve ser executada, por que uma referencia proxima nao substitui o porto selecionado e por que uma sensibilidade nao e uma linha de base validada.

### 6.3 Batch 001B como camada de decisão metodológica

O Batch 001B deve ser lido como uma camada de decisão metodológica e auditabilidade, não como uma nova rodada que transformou todos os casos em resultados finais validados. Sua função principal foi reorganizar a evidência histórica do Batch 001 em linhas com portos selecionados ou forçados, fonte de distância marítima, unidade, conversão, status metodológico e uso permitido no TF. Esse arranjo preserva a rastreabilidade das escolhas, mas também limita explicitamente o que cada linha pode sustentar.

A classificação controla a interpretação. Um caso planejado, bloqueado, excluído, `reference_needed` ou `record_only_warning` não deve ser executado ou narrado como conclusão numérica robusta. Do mesmo modo, uma linha preparada para sensibilidade não se torna resultado principal apenas porque possui uma hipótese documentada. No estado atual dos artefatos, nenhum caso planejado do Batch 001B deve ser promovido a conclusão principal robusta sem evidência rastreada adicional que justifique essa mudança.

| Classificação/status | Significado | Uso seguro no TF |
| --- | --- | --- |
| `historical_diagnostic` | Preserva os resultados originais do Batch 001 para auditoria e comparação metodológica. | Histórico diagnóstico; não é resultado corrigido nem validação final. |
| `record_only_warning` | Mantém um aviso ou caso-limite, como Santos -> Santos same-port. | Exemplo de limitação de construção de rota; não representa cabotagem normal nem desempenho modal. |
| `excluded` | Caso fora da fronteira atual ou inadequado para conclusão numérica. | Justificativa de exclusão; não deve ser executado como evidência de resultado. |
| `reference_needed` | Falta referência exata para o par de portos selecionado. | Lacuna de evidência; permanece não resolvida até que a referência exata seja documentada. |
| `methodology_blocked` | Falta decisão metodológica ou porto defensável antes da execução. | Registro de bloqueio e trabalho futuro; não sustenta conclusão numérica. |
| `sensitivity_only` / `sensitive` | Cenário preparado ou executado sob hipótese nomeada. | Discussão de sensibilidade com ressalvas; não é linha de base robusta. |

Essa disciplina explica casos concretos do lote. Santos -> Santos permanece como exemplo same-port e, portanto, como limite da lógica de rota, não como cadeia normal de cabotagem. Angra dos Reis -> Salvador fica excluído para a fronteira atual de benchmark conteinerizado, pois a cadeia selecionada não é defensável como base numérica sob os critérios documentados. Esses casos podem aparecer como diagnóstico, exclusão ou limitação, mas não como evidência de vantagem modal.

Os casos com referência ausente também permanecem restritos. Manaus -> Fortaleza e Rio Grande -> Recife continuam dependentes de referências exatas para os portos selecionados; uma referência para Pecém não valida silenciosamente Fortaleza, e uma referência para Suape não valida silenciosamente Recife. Quando Pecém ou Suape aparecem em linhas posteriores, eles devem ser lidos como portos alternativos explicitamente rotulados, não como substitutos metodológicos dos portos originalmente selecionados.

Por fim, o Batch 001B não prova disponibilidade de serviço, viabilidade comercial, frete contratado, frequência de escala ou validade operacional completa da cadeia. Mesmo quando uma linha se torna sensibilidade executada, os custos permanecem estimativas modeladas e as emissões permanecem operacionais TTW CO2e, salvo indicação explícita em contrário. A contribuição do Batch 001B é criar a disciplina necessária antes de executar, comparar ou discutir sensibilidades, evitando que registros históricos, bloqueios ou hipóteses condicionais sejam promovidos a resultados finais.

### 6.4 Casos de sensibilidade executados

Tres casos foram executados como sensibilidade Batch 001B:

- `TF-VAL-001B-SENS-002-REFDIST`: Santos/Manaus com distancia de referencia `3300 nm / 6111,6 km`;
- `TF-VAL-001B-SENS-003B-ALTPECEM`: Manaus/Pecem como porto alternativo para a regiao de Fortaleza, com `1569 nm / 2905,788 km`;
- `TF-VAL-001B-SENS-005B-ALTSUAPE`: Rio Grande/Suape como porto alternativo para a regiao de Recife, com `1844 nm / 3415,088 km`.

Essas linhas sao `sensitive`, nao `robust`. Elas podem ser discutidas como comportamento do modelo sob hipoteses documentadas, mas nao substituem as linhas de base de Fortaleza e Recife e nao produzem uma conclusao universal sobre cabotagem.

### 6.5 Batch 002 como benchmark externo Gustavo/Costa

O Batch 002 adicionou uma camada de benchmark externo baseada no workbook Gustavo/Costa. Esse workbook e util porque pertence ao mesmo contexto amplo de comparacao entre transporte rodoviario e cabotagem no Brasil, mas nao e tratado como verdade absoluta. O objetivo foi verificar se o CabotageLens aponta para a mesma direcao modal sob uma base comparavel de `1 TEU / 14 t`, nao reproduzir exatamente as magnitudes do workbook ou do artigo.

O inventario consolidado do Batch 002 registra:

| Item | Resultado consolidado |
| --- | ---: |
| Celulas de matriz do workbook parseadas | 36 |
| Pares OD positivos e suportados benchmarkados | 21 |
| Linhas executadas com sucesso | 21 |
| Celulas puladas antes da execucao do modelo | 15 |
| Classificacao rastreada atual | 21 `same_direction_large_gap` |

As 15 celulas puladas correspondem a 6 self-pairs e 9 linhas rodoviarias zero ou nao positivas. Para os 21 pares OD positivos e suportados, workbook e CabotageLens ficaram direcionalmente alinhados: em ambos, as emissoes de cabotagem/multimodal ficaram abaixo das emissoes road-only. Essa e uma evidencia externa importante para a defesa do metodo, mas a precisao de magnitude da linha de base ainda nao e suficiente para afirmar validacao calibrada ou reproducao exata do workbook.

### 6.6 Rerun Supabase/cache e reconciliacao rodoviaria

O rerun Supabase/cache verificou se instabilidade de cache ou provedor de rota explicava a grande diferenca workbook-vs-modelo. A leitura e escrita de cache Supabase funcionaram, e o rerun usou apenas distancias rodoviarias em cache. O registro consolidado mostra 63 route-cache hits e 0 misses. A diferenca agregada do lado rodoviario mudou apenas ligeiramente, de 201,0%/150,5% para 199,8%/149,3% em media/mediana absoluta. A diferenca multimodal nao melhorou. Portanto, instabilidade de cache/provedor e improvavel como principal causa da lacuna rodoviaria.

A reconciliacao de fator rodoviario testou uma explicacao metodologica especifica. As premissas Gustavo/Costa usadas no diagnostico foram `FDc = 0.28 L/km`, `FDe = 35.52 MJ/L` e `FDf = 86.5 gCO2eq/MJ`, resultando em:

```text
0.28 L/km * 35.52 MJ/L * 86.5 gCO2eq/MJ / 1000 = 0.8602944 kgCO2e/km
```

Aplicar esse fator diagnostico as mesmas distancias rodoviarias em cache reduziu a diferenca rodoviaria media/mediana de 199,8%/149,3% para 43,9%/19,6%. Isso indica que premissas de consumo rodoviario e fator de emissao explicam uma parte grande da diferenca de magnitude road-only. O diagnostico nao elimina toda a lacuna, nao substitui o modelo rodoviario de linha de base do CabotageLens e nao deve ser apresentado como recalibracao.

## 7. Resultados

### 7.1 Classificacao geral

A sintese final de resultados estabelece que nenhum caso Batch 001/001B e nenhuma linha Batch 002 se qualifica como `headline_candidate`. Isso significa que o TF nao deve apresentar uma tabela de "resultados principais validados" como se houvesse conclusoes robustas por corredor. O uso academico correto e apresentar o inventario de casos, discutir as tres linhas de sensibilidade executadas com suas restricoes e usar o Batch 002 como evidencia externa direcional e limitada por fronteiras.

As categorias finais sao:

| Categoria | Significado | Casos associados |
| --- | --- | --- |
| `headline_candidate` | Possivel candidato a conclusao principal apos validacao e sensibilidade. | Nenhum. |
| `sensitivity_discussion` | Evidencia de sensibilidade executada ou planejada, com avisos de fronteira. | Santos/Manaus, Manaus/Pecem e Rio Grande/Suape, alem de suas linhas planejadas. |
| `limitation_example` | Exemplo de limite de rota ou metodo. | Same-port Santos/Santos. |
| `excluded` | Invalido ou fora do escopo para conclusoes numericas. | Angra dos Reis -> Salvador no benchmark atual. |
| `reference_needed` | Falta referencia exata para o par de portos selecionado. | Manaus/Fortaleza e Rio Grande/Recife. |
| `methodology_blocked` | Falta decisao metodologica ou porto defensavel. | Brasilia/Salvador com alternativo nao definido. |
| `historical_diagnostic` | Registro historico preservado para rastreabilidade. | Batch 001 original. |
| `benchmark_supports_direction` | Evidencia externa de que workbook e CabotageLens favorecem a mesma direcao modal de emissoes. | 21 pares OD positivos e suportados do Batch 002. |
| `benchmark_supports_road_factor_explanation` | Sensibilidade diagnostica mostra que premissas rodoviarias explicam grande parte da lacuna road-only. | Reconciliacao com `0.8602944 kgCO2e/km`. |
| `benchmark_methodology_gap` | Benchmark util para discutir diferencas de metodo, nao reproducao calibrada. | Diferencas de magnitude road-only e multimodal no Batch 002. |
| `benchmark_boundary_mismatch` | Fronteiras e alocacoes seguem parcialmente nao reconciliadas. | TTW/WTW/LCA/CO2/CO2e, carga, rotas, portos, servico e port-ops/hoteling. |
| `not_comparable` | Celulas do workbook sem comparacao executavel na fronteira atual. | 15 celulas puladas do Batch 002. |

### 7.2 Resultados numericos das sensibilidades executadas

As tres linhas executadas de sensibilidade mostram que, sob a fronteira atual de custo modelado e TTW CO2e operacional, a alternativa multimodal permanece menor que a alternativa rodoviaria direta nos dois indicadores. Essa direcao e relevante, mas a classificacao continua sendo `sensitive`.

| Caso | Papel | Portos | Custo rodoviario / multimodal | Emissoes rodoviario / multimodal | Classificacao |
| --- | --- | --- | ---: | ---: | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Sensibilidade de distancia Santos/Manaus | Santos -> Manaus | BRL 18456,45 / BRL 1263,50 | 6961,76 / 1104,67 kg TTW CO2e | `sensitive` |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Sensibilidade de porto alternativo Pecem | Manaus -> Pecem | BRL 26391,03 / BRL 727,33 | 9989,83 / 573,48 kg TTW CO2e | `sensitive` |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Sensibilidade de porto alternativo Suape | Rio Grande -> Suape | BRL 18121,99 / BRL 2122,38 | 7013,27 / 1127,46 kg TTW CO2e | `sensitive` |

Esses valores nao sao substitutos das linhas de base validadas. O caso Santos/Manaus e uma sensibilidade de distancia de referencia. O caso Manaus/Pecem e uma sensibilidade de porto alternativo e nao valida Porto de Fortaleza. O caso Rio Grande/Suape e uma sensibilidade de porto alternativo e nao valida Porto do Recife.

### 7.3 Interpretacao dos resultados

O resultado mais importante nao e a existencia de tres linhas favoraveis ao multimodal, mas o modo como elas devem ser classificadas. Nos tres casos, o multimodal e menor em custo modelado e em TTW CO2e operacional. Porem, a evidencia ainda nao testou faixas completas de carga, consumo rodoviario, intensidade maritima, operacoes portuarias, hoteling, preco de combustivel e expansao de fronteira de custo.

Portanto, o TF pode afirmar que as sensibilidades executadas sugerem potencial vantagem modelada em cenarios nomeados, mas deve evitar qualquer uma das seguintes leituras: cabotagem universalmente melhor; resultado robusto; validacao de Fortaleza por Pecem; validacao de Recife por Suape; custo modelado equivalente a frete comercial; TTW CO2e equivalente a WTW ou LCA.

O Batch 002 acrescenta outro tipo de resultado: evidencia externa de consistencia direcional. Nos 21 pares positivos suportados, o workbook Gustavo/Costa e o CabotageLens favorecem cabotagem/multimodal em emissoes quando comparados a road-only. A classificacao rastreada, porem, e `same_direction_large_gap` para todas as 21 linhas. Logo, o resultado e melhor descrito como apoio direcional com diferenca de magnitude, nao como reproducao exata ou validacao calibrada.

## 8. Discussao

Os resultados reforcam que o desempenho da cabotagem e especifico por corredor. Em corredores longos com acesso portuario coerente e distancia maritima documentada, a alternativa multimodal pode apresentar forte reducao modelada de consumo rodoviario, custo operacional e TTW CO2e. No entanto, esse comportamento depende da qualidade da distancia maritima, da escolha do porto, da disponibilidade real de servico e da fronteira de custo. A propria literatura de short sea shipping indica que a vantagem ambiental nao e automatica [shortsea2019] [modalshiftreview2020].

O Batch 002 melhora a defesa do trabalho porque introduz uma referencia externa familiar ao contexto do TF. O ponto defendido, no entanto, e estreito: todos os 21 pares OD positivos e suportados ficaram direcionalmente alinhados, mas as magnitudes continuam distantes. Essa diferenca nao deve ser narrada como falha simples do modelo nem como prova de que o workbook e verdade absoluta. Ela deve ser apresentada como transparencia metodologica sobre fronteiras, parametros e alocacoes ainda nao reconciliados.

A lacuna road-only tornou-se metodologicamente explicavel. O rerun com cache mostrou que a instabilidade de rota/provedor nao e a causa principal, enquanto a reconciliacao rodoviaria reduziu fortemente a diferenca quando aplicou o fator diagnostico Gustavo/Costa. Permanecem lacunas associadas a base de distancia rodoviaria, construcao de rota, premissas de veiculo e carregamento, alocacao por conteiner, selecao de portos e servicos, tratamento de port-ops/hoteling e diferencas TTW/WTW/LCA/CO2/CO2e. Esses pontos sustentam uma discussao de metodo, nao uma afirmacao de validacao exata.

A proveniencia da distancia maritima e um dos pontos mais sensiveis. O Batch 001 mostrou que fallback geometrico pode produzir distancias muito diferentes de referencias documentadas. No caso Santos/Manaus, substituir o fallback historico por `3300 nm / 6111,6 km` ainda manteve o multimodal abaixo do rodoviario nas saidas modeladas, mas alterou a magnitude e mostrou por que a distancia de fallback nao deve validar uma rota sozinha.

A selecao de portos tambem muda a interpretacao. Pecem nao e Fortaleza. Suape nao e Recife. Ainda que Pecem e Suape sejam portos relevantes em suas regioes, usa-los como portos forcados cria cenarios alternativos, nao validacoes dos portos originalmente selecionados. O on-carriage, a distancia maritima, a disponibilidade de servico e a estrutura comercial podem mudar. Assim, as linhas `ALTPECEM` e `ALTSUAPE` devem ser lidas como sensibilidades de porto alternativo.

O caso same-port ilustra outro limite. Uma rota Sao Paulo -> Santos que seleciona Santos -> Santos nao e uma cadeia cabotagem normal. Esse tipo de linha pode ser util para testar avisos de qualidade e comportamento de fronteira, mas nao para discutir vantagem modal.

Tambem e necessario separar custo e emissoes. Um resultado com menor custo modelado e menor TTW CO2e em uma linha de sensibilidade e facil de comunicar, mas o metodo precisa continuar distinguindo as duas dimensoes. Se, em outros casos, custo e emissoes apontarem para modos diferentes, nao ha "vencedor" unico sem uma regra de decisao explicita. O presente trabalho nao define uma funcao objetivo unica que combine `BRL` e `kg CO2e`.

Em relacao a literatura, os resultados sao coerentes com a ideia de que cabotagem pode ser promissora em corredores longos e que super-redes ou analises de rede completa sao necessarias para avaliar competitividade real [competitiveness2024]. Ao mesmo tempo, os resultados tambem confirmam a cautela da literatura: as conclusoes dependem da rota, do acesso terrestre, do porto, da frequencia, da fronteira de custo e da fronteira ambiental [shortsea2019] [modalshiftreview2020].

## 9. Limitacoes

Este trabalho possui limitacoes deliberadas e limitacoes ainda nao resolvidas.

Primeiro, a fronteira ambiental e TTW operacional. O trabalho nao e uma avaliacao WTW nem LCA. Isso significa que emissoes de producao, transporte e processamento dos combustiveis, construcao de infraestrutura, fabricacao de veiculos e navios e fim de vida nao estao incorporados. Fontes sobre WTW, LCA e HVO sao usadas como contexto ou trabalho futuro, nao como calibracao da linha de base [decarb2024] [maritimelca2024].

Segundo, os custos sao estimativas modeladas, nao fretes comerciais. O modelo nao incorpora integralmente tarifas, margens, inventario, servico, frequencia, confiabilidade, demurrage, negociacao contratual, seguro e outros custos logisticos. Portanto, uma diferenca em `BRL` deve ser lida dentro da fronteira de custo representada.

Terceiro, a ferramenta nao modela horarios, frequencia de escalas, disponibilidade de servico, capacidade de navio, tempo de espera, confiabilidade ou conexoes comerciais. Esses fatores podem ser decisivos para a escolha modal real e sao caracteristicos de estudos de super-rede mais completos [competitiveness2024].

Quarto, o CabotageLens nao implementa uma super-rede completa. A selecao de portos e a construcao de rota fornecem uma alternativa deterministica e auditavel, mas nao otimizam uma rede nacional com multiplas linhas, operadores, transbordos e horarios.

Quinto, permanecem lacunas de distancia maritima exata para portos selecionados. Manaus -> Porto de Fortaleza e Porto do Rio Grande -> Porto do Recife continuam sem evidencia exata suficiente nos artefatos atuais. Pecem e Suape nao podem ser usados como substitutos silenciosos.

Sexto, casos same-port e casos com perna maritima artificial precisam ser tratados como limitacao ou exclusao. Eles ajudam a melhorar a ferramenta, mas nao sustentam comparacao modal.

Setimo, as sensibilidades de porto alternativo sao limitadas. Elas mostram comportamento sob uma hipotese documentada, mas nao cobrem toda a variacao possivel de porto, servico, custo, acesso terrestre ou intensidade maritima.

Oitavo, fontes pendentes de auditoria ou marcadas como futuro trabalho nao foram usadas para calibracao numerica. Isso inclui, quando aplicavel, fontes de iso-emission mapping, LCA maritima e fatores portuarios ainda nao suficientemente extraidos para implementacao direta [isoemission2019] [maritimelca2024] [berth2009] [shipops2022] [berthairquality2010].

Nono, o Batch 002 nao e uma reproducao completa do workbook ou do artigo Gustavo/Costa. O workbook nao e tratado como ground truth, e permanecem nao resolvidas sua massa interna de carga, definicao de TEU, premissa de veiculo, fator de carga, logica de alocacao, base de distancia, portos/servicos e fronteira de emissoes. A comparacao e valida como benchmark externo direcional e como evidencia de lacunas metodologicas.

Decimo, o fator rodoviario diagnostico de `0.8602944 kgCO2e/km` e apenas uma sensibilidade de alinhamento com benchmark. Ele nao recalibra o CabotageLens, nao substitui a linha de base TTW operacional e nao autoriza misturar TTW, WTW, LCA, CO2 e CO2e. Do mesmo modo, o trabalho nao faz afirmacao WTW/LCA, nao transforma custos modelados em fretes comerciais e nao conclui superioridade universal da cabotagem.

## 10. Conclusao

O CabotageLens cumpre, no estado atual do projeto, uma funcao academica defensavel: fornece uma estrutura auditavel, reprodutivel e explicita em fronteiras para comparar transporte rodoviario direto e alternativas rodoviario-cabotagem-rodoviario em corredores brasileiros. A ferramenta organiza entradas, rotas, distancias, fontes, custos modelados, emissoes TTW CO2e e avisos de interpretacao em um fluxo coerente para analise de engenharia.

A camada Batch 001B aumentou a rastreabilidade da validacao ao separar linhas historicas, same-port, excluidas, bloqueadas, reference-needed e sensibilidade. As tres sensibilidades executadas indicam que, nos cenarios nomeados Santos/Manaus com distancia de referencia, Manaus/Pecem como porto alternativo e Rio Grande/Suape como porto alternativo, o multimodal permanece menor que o rodoviario direto em custo modelado e TTW CO2e operacional. Contudo, essas linhas sao `sensitive`, nao `robust`, e nao substituem linhas de base validadas.

O Batch 002 fortalece a defesa porque usa um benchmark externo familiar ao contexto do TF. Os 21 pares OD positivos e suportados ficam alinhados na direcao modal de emissoes, mas classificados como `same_direction_large_gap`, portanto sustentam interpretacao direcional cautelosa e nao validacao calibrada de magnitude. A reconciliacao rodoviaria tambem explica grande parte da lacuna road-only por diferencas de consumo e fator de emissao, sem substituir o modelo rodoviario de linha de base.

Assim, a conclusao geral deve permanecer conservadora: o CabotageLens demonstra uma contribuicao metodologica e computacional auditavel para comparar cadeias road-only e road-cabotage-road sob fronteiras explicitas. O projeto revela potencial vantagem modelada da cabotagem em cenarios especificos e evidencia direcional externa no Batch 002, mas nao demonstra superioridade universal da cabotagem, reproducao exata do workbook Gustavo/Costa ou equivalencia a fretes comerciais.

## 11. Trabalhos futuros

Os proximos desenvolvimentos devem atacar diretamente as limitacoes que impedem conclusoes robustas:

- obter evidencia exata de distancia maritima para os pares de portos selecionados ainda pendentes, especialmente Manaus -> Porto de Fortaleza e Porto do Rio Grande -> Porto do Recife;
- expandir a fronteira ambiental para WTW ou LCA somente com fatores, unidades, combustiveis e documentacao compativeis;
- implementar cenarios de HVO e combustiveis alternativos como modulos explicitamente separados da linha de base TTW;
- incorporar modelagem de frete comercial, tarifas, inventario, tempo, confiabilidade e custos nao energeticos com fontes adequadas;
- adicionar horarios, frequencia, disponibilidade de servico e restricoes operacionais de linhas de cabotagem;
- evoluir para uma super-rede multimodal completa quando houver dados e escopo para isso;
- desenvolver mapas de iso-emissao e visualizacoes de sensibilidade geografica apos estabilizar proveniencia de distancia;
- refinar produtividade portuaria, hoteling, equipamentos de patio, eletricidade e fatores locais de porto;
- ampliar validacao com referencias independentes de distancia rodoviaria, distancia maritima, custos e intensidades de emissao;
- preservar manifestos de execucao com versao de codigo, parametros, artefatos, cache e status de fallback para cada resultado usado no TF.

Esses trabalhos futuros nao reduzem a utilidade do prototipo atual. Eles delimitam a transicao de uma ferramenta academica de comparacao auditavel para uma ferramenta mais proxima de planejamento logistico operacional.

## 12. Citation placeholders

As chaves abaixo foram usadas como placeholders de citacao. Elas devem ser formatadas em etapa posterior, sem inventar metadados bibliograficos que nao estejam disponiveis nos artefatos do repositorio.

| Chave | Uso no rascunho | Limite de uso |
| --- | --- | --- |
| `[icct2022]` | Contexto brasileiro de cabotagem, BR do Mar, modal share, emissao e motivacao de politica publica. | Referencia de contexto; nao valida custos ou resultados rota a rota do CabotageLens. |
| `[competitiveness2024]` | Competitividade da cabotagem brasileira, super-rede, frequencia, custo comercial e limitacoes de rede. | Comparacao e limitacao; nao transforma o CabotageLens em super-rede ou cotador comercial. |
| `[shortsea2019]` | Evidencia de que short sea/cabotagem nao e automaticamente superior e depende de corredor, utilizacao e hipoteses. | Limitacao e discussao; nao calibra fatores brasileiros. |
| `[modalshiftreview2020]` | Complexidade da mudanca modal, barreiras logisticas, qualidade de servico e decisao alem de custo/emissao. | Referencia qualitativa; nao valida numericamente os resultados. |
| `[decarb2024]` | Descarbonizacao da cabotagem brasileira, HVO, WTW/CO2e e trabalhos futuros. | Futuro trabalho e contraste de fronteira; nao substitui a linha de base TTW. |
| `[berth2009]` | Contexto metodologico de combustivel/emissoes em navios atracados. | Referencia ou futuro trabalho; nao calibracao direta. |
| `[shipops2022]` | Metodologia de hoteling, carga/descarga e produtividade portuaria. | Referencia ou futuro trabalho; fatores regionais nao sao parametros brasileiros diretos. |
| `[berthairquality2010]` | Impacto de emissoes em porto e distincao de fases portuarias. | Contexto portuario; nao validacao modal completa. |
| `[maritimelca2024]` | Distincao LCA/WTW e futuras extensoes de ciclo de vida. | Pendente/futuro; nao define a metodologia TTW atual. |
| `[isoemission2019]` | Inspiracao para mapas de iso-emissao e visualizacao futura. | Futuro trabalho; nao implica que o CabotageLens ja implemente esse recurso. |
