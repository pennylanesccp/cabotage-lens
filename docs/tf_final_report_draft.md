# Rascunho do relatorio final de TF - CabotageLens

Este documento e um rascunho completo, em formato de relatorio academico, para o Trabalho de Formatura associado ao projeto CabotageLens. O texto foi redigido a partir dos artefatos rastreados no repositorio e preserva os limites metodologicos atualmente documentados. As citacoes aparecem como chaves temporarias entre colchetes, sem formatacao ABNT final.

## 1. Introducao

O transporte de cargas no Brasil e historicamente marcado por forte dependencia do modo rodoviario. Essa configuracao facilita uma rede capilar de atendimento porta a porta, mas tambem cria vulnerabilidades tecnicas e economicas em corredores longos: maior exposicao ao preco do diesel, consumo elevado de combustivel por tonelada transportada, riscos operacionais em longas distancias e pressao para reduzir emissoes de gases de efeito estufa. Nesse contexto, a cabotagem aparece como uma alternativa relevante para parte dos fluxos nacionais, principalmente quando a origem e o destino podem ser conectados por uma cadeia logistica com pre-carriage rodoviario, perna maritima e on-carriage rodoviario [icct2022].

A discussao sobre cabotagem no Brasil ganhou novo peso com politicas de incentivo e reorganizacao setorial, incluindo a agenda associada ao BR do Mar. A motivacao dessas politicas nao deve ser interpretada como prova de superioridade universal da cabotagem. A literatura e a experiencia operacional indicam que a competitividade do transporte maritimo costeiro depende de distancia, acesso terrestre, frequencia de servico, disponibilidade de navios, terminais, custos portuarios, tempo de transito, confiabilidade e escala de carga [icct2022] [competitiveness2024] [modalshiftreview2020]. Assim, o problema tecnico nao e simplesmente afirmar que "navio emite menos que caminhao", mas comparar cadeias completas sob uma unidade funcional comum.

O CabotageLens foi desenvolvido para responder a esse problema como uma ferramenta computacional de apoio a decisao e pesquisa aplicada. A ferramenta compara uma alternativa rodoviaria direta com uma alternativa rodoviario-cabotagem-rodoviario para pares origem-destino no Brasil. Para cada cenario, o modelo explicita distancias, pernas logisticas, fontes de distancia, consumo, estimativas de custo operacional modelado e emissoes operacionais TTW CO2e. O objetivo nao e substituir uma cotacao comercial de frete, nem representar uma super-rede completa de servicos de cabotagem, mas oferecer uma estrutura auditavel para comparar alternativas e documentar onde as conclusoes sao robustas, sensiveis, inconclusivas ou invalidadas por limitacoes de rota e dados.

Este rascunho final do Trabalho de Formatura assume uma postura conservadora. A evidencia atualmente consolidada no repositorio indica que os resultados numericos disponiveis para discussao sao, no maximo, resultados de sensibilidade. Nenhum caso atual esta classificado como `headline_candidate` para conclusoes numericas principais. Portanto, a contribuicao central do trabalho e metodologica: o CabotageLens organiza uma comparacao porta a porta reprodutivel, torna visiveis os limites de dados e classificacao e evita transformar resultados sensiveis em afirmacoes gerais sobre a superioridade da cabotagem.

## 2. Objetivos

O objetivo geral deste trabalho e desenvolver e documentar o CabotageLens como um prototipo computacional auditavel para comparacao entre transporte rodoviario direto e transporte multimodal rodoviario-cabotagem-rodoviario em corredores brasileiros, considerando estimativas de custo operacional modelado e emissoes operacionais TTW CO2e sob fronteiras explicitas.

Os objetivos especificos sao:

- comparar alternativas rodoviarias diretas e alternativas rodoviario-cabotagem-rodoviario para pares origem-destino selecionados;
- tornar explicitas as hipoteses de rota, incluindo pre-carriage, perna maritima, on-carriage, selecao de portos e fonte das distancias;
- estimar emissoes operacionais TTW CO2e e estimativas de custo modelado por remessa, preservando as unidades e os limites de interpretacao;
- expor a proveniencia das distancias e as limitacoes da selecao de portos, especialmente quando ha distancia maritima por fallback, caso same-port, porto alternativo ou referencia exata ausente;
- classificar os resultados de forma conservadora para uso academico, separando resultados historicos, bloqueados, excluidos, sensiveis e candidatos a conclusao principal.

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

### 4.1 Fronteira do sistema e unidade funcional

A unidade funcional do estudo e o transporte de uma massa especificada de carga conteinerizada, em toneladas ou TEU, entre uma origem e um destino definidos no Brasil. Nos artefatos de validacao Batch 001 e Batch 001B, o benchmark recorrente e `14 t / 1 TEU` por remessa. Os resultados sao interpretados por remessa e podem ser normalizados por tonelada, por TEU ou por tonelada-quilometro quando a comparacao exigir.

A fronteira ambiental e operacional TTW CO2e. Para a alternativa rodoviaria direta, a fronteira inclui a perna rodoviaria entre origem e destino. Para a alternativa multimodal, a fronteira inclui pre-carriage rodoviario da origem ao porto de origem, perna maritima de cabotagem entre portos, possiveis operacoes portuarias modeladas e on-carriage rodoviario do porto de destino ao destino final. A fronteira exclui fabricacao de veiculos e navios, construcao de infraestrutura, ciclo de vida completo dos combustiveis, externalidades sociais e custos comerciais completos, salvo quando um componente for explicitamente modelado.

### 4.2 Alternativa rodoviaria direta

A alternativa rodoviaria direta representa o transporte da remessa por caminhao da origem ao destino. A distancia e expressa em quilometros (`km`). O consumo de combustivel, o custo modelado e as emissoes TTW CO2e sao calculados a partir da distancia rodoviaria, do preset de veiculo, da massa da carga, dos parametros de combustivel e dos fatores de emissao implementados.

De forma conceitual, para uma perna rodoviaria:

- distancia rodoviaria: `d_road` em `km`;
- consumo de diesel: funcao de `d_road`, eficiencia do veiculo em `km/L`, carga e numero de viagens;
- custo rodoviario modelado: litros de diesel multiplicados pelo preco aplicavel em `BRL/L`;
- emissoes rodoviarias: combustivel consumido multiplicado pelo fator TTW CO2e aplicavel, em `kg CO2e`.

Essa formulacao e adequada para uma comparacao padronizada, mas nao reconstrui telemetria real de caminhoes, politica de paradas, variacao de velocidade, congestionamento, pedagios ou contratos de frete.

### 4.3 Alternativa rodoviario-cabotagem-rodoviario

A alternativa multimodal e composta por tres partes principais:

- pre-carriage: transporte rodoviario da origem ao porto de origem, em `km`;
- perna maritima: transporte por cabotagem entre porto de origem e porto de destino, em `km` e, quando aplicavel, `nm`;
- on-carriage: transporte rodoviario do porto de destino ao destino final, em `km`.

Quando operacoes portuarias ou hoteling sao incluidos, os componentes devem preservar a fronteira operacional e evitar dupla contagem. Em particular, quando uma intensidade maritima observada ja representa consumo operacional agregado, adicionar hoteling separadamente pode superestimar emissoes. Por outro lado, quando uma decomposicao por classe ou cenario exige hoteling separado, a inclusao precisa ser indicada em resultado e metodologia.

### 4.4 Proveniencia de rotas e distancias

A metodologia depende da proveniencia das distancias. As distancias rodoviarias sao resultados de roteamento, cache ou provedor e devem ser interpretadas como estimativas de rota sob o perfil usado. As distancias maritimas podem vir de matriz maritima, evidencia observada, referencia externa, override manual ou fallback. No Batch 001B, a classificacao do tipo de fonte tornou-se parte da interpretacao.

As distancias maritimas em milhas nauticas sao convertidas por `1 nm = 1,852 km`. Sempre que uma referencia externa e registrada em `nm`, o valor convertido em `km` deve preservar a unidade original e a conversao. Uma distancia `haversine_fallback` e apenas uma estimativa de triagem. Ela pode explicar a necessidade de correcao, sensibilidade ou referencia adicional, mas nao deve sustentar conclusoes numericas fortes.

### 4.5 Tipos de fonte maritima

Os artefatos de validacao distinguem fontes de distancia maritima, incluindo:

- `external_reference`: referencia externa documentada para um par de portos especifico ou forçado;
- `haversine_fallback`: distancia aproximada por fallback geometrico, insuficiente para conclusao forte por si so;
- `seamatrix` ou matriz maritima quando a distancia esta registrada para o par de portos;
- preservacao da fonte original do Batch 001 quando o valor historico e mantido apenas para diagnostico.

Essa distincao impede que uma distancia aproximada seja tratada como rota operacional validada. Tambem impede substituicoes silenciosas entre portos proximos.

### 4.6 Avisos same-port e qualidade de rota

Casos em que o porto de origem e o porto de destino sao o mesmo porto nao representam uma cadeia normal de cabotagem. O caso Sao Paulo, SP -> Santos, SP com Porto de Santos -> Porto de Santos e um exemplo de limite metodologico. Ele pode ser usado para mostrar a necessidade de avisos de rota, mas nao para concluir desempenho da cabotagem.

O repositorio tambem registra avisos de qualidade associados a perna maritima muito pequena, fallback maritimo, acesso terrestre dominante e escolhas de porto. Esses avisos sao heuristicas de interpretacao e transparencia. Eles nao substituem uma analise de servico, frequencia, terminal, contrato ou viabilidade comercial.

### 4.7 Fronteira de emissoes

As emissoes reportadas neste trabalho sao operacionais TTW CO2e, em `kg CO2e` por remessa, salvo indicacao contraria. Essa fronteira inclui emissoes diretas associadas ao combustivel consumido nas pernas representadas e nao inclui WTW, LCA ou etapas upstream. Portanto, resultados do CabotageLens nao devem ser comparados diretamente com fatores WTW ou LCA da literatura sem ajuste explicito de fronteira, unidade e fator.

### 4.8 Fronteira de custo

Os custos reportados sao estimativas modeladas dos componentes incluidos. A unidade principal e `BRL` por remessa. Eles nao sao fretes comerciais. A metodologia exclui, salvo expansao futura, componentes como tarifas portuarias completas, margens, contratos, seguros, inventario, tempo de transito, confiabilidade, demurrage, frequencia de servico, disponibilidade de slots e custos administrativos.

Por isso, a interpretacao correta e "menor custo modelado dentro da fronteira operacional", e nao "frete comercial menor". Essa diferenca e mantida em Resultados, Discussao, Limitacoes e Conclusao.

### 4.9 Validacao e classificacao conservadora

A validacao do trabalho nao busca equivalencia perfeita com uma operacao real especifica. Ela busca plausibilidade, consistencia dimensional, proveniencia de dados e classificacao adequada da incerteza. Os artefatos Batch 001B separam:

- `historical_diagnostic`: resultados historicos preservados para diagnostico;
- `record_only_warning`: linhas mantidas para registrar avisos, como same-port;
- `reference_needed`: casos que ainda precisam de distancia exata para o par de portos selecionado;
- `excluded`: casos invalidos para a fronteira atual;
- `planned_blocked_methodology_decision`: casos bloqueados por decisao metodologica ou porto faltante;
- `sensitivity_only`: cenarios adequados apenas para analise de sensibilidade;
- `sensitive`: linhas executadas cujo resultado e condicional e nao robusto;
- `headline_candidate`: categoria possivel para resultado principal, atualmente sem casos.

Essa classificacao evita que resultados bloqueados, excluidos, historicos, fallback-only ou alternate-port sejam promovidos a conclusoes principais.

## 5. Ferramenta computacional

O CabotageLens e um prototipo computacional de apoio a decisao e pesquisa, implementado como aplicacao Streamlit com suporte a fluxos de linha de comando e modulos reutilizaveis. O usuario informa origem, destino, carga e parametros operacionais. A ferramenta resolve localizacoes, constroi uma alternativa rodoviaria direta, seleciona ou recebe portos para a alternativa multimodal, calcula pernas rodoviarias e maritimas e consolida distancias, custos modelados e emissoes operacionais TTW CO2e.

A arquitetura do repositorio separa responsabilidades. O diretorio `app/` organiza a interface Streamlit e a interacao com o usuario. O diretorio `modules/` concentra logica de dominio, como roteamento, avaliacao multimodal, combustivel, emissoes, custos, persistencia, proveniencia de distancia e avisos de qualidade de rota. O diretorio `scripts/` contem fluxos reprodutiveis para execucao e manutencao. O diretorio `data/` armazena insumos estaticos e artefatos processados rastreados. O diretorio `supabase/migrations/` registra a evolucao do esquema do Supabase Postgres, que e o backend duravel do projeto. O diretorio `docs/` contem metodologia, validacao, auditoria e planejamento academico.

Na interface, os resultados devem deixar visiveis os principais elementos de interpretacao: distancias por perna, fonte da distancia maritima, avisos de rota, fronteira de emissoes, fronteira de custo, inclusao ou exclusao de operacoes portuarias e dados de exportacao quando disponiveis. Esse comportamento e importante porque, em um trabalho academico, o valor do numero depende da rastreabilidade do caminho que produziu o numero.

O CabotageLens tambem possui artefatos de validacao e exportacao que permitem preservar registros de cenarios, resultados, configuracoes, bloqueios e decisoes metodologicas. Esses artefatos sao parte da contribuicao academica: eles tornam claro quando uma linha foi executada, planejada, bloqueada, excluida ou mantida apenas como registro historico.

Apesar dessas capacidades, a ferramenta nao deve ser descrita como motor comercial de cotacao de frete. Ela nao resolve uma super-rede nacional completa, nao otimiza frequencias de servico, nao confirma disponibilidade real de navios, nao precifica contratos e nao incorpora todos os custos logisticos comerciais. Sua funcao e oferecer uma comparacao tecnica reprodutivel e transparente, adequada ao escopo de um Trabalho de Formatura em Engenharia Naval.

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

### 6.3 Casos excluidos, bloqueados, reference-needed e record-only

O caso `TF-VAL-001B-001` e mantido como `record_only_warning`, pois Santos -> Santos e um caso same-port, inadequado para representar uma cadeia normal de cabotagem. O caso `TF-VAL-001B-004A` e `excluded`, pois a cadeia Angra dos Reis -> Salvador nao e defensavel para o benchmark conteinerizado de `1 TEU / 14 t` sob a fronteira atual.

Os casos `TF-VAL-001B-003A` e `TF-VAL-001B-005A` permanecem `reference_needed`, porque faltam referencias exatas para Porto de Manaus -> Porto de Fortaleza e Porto do Rio Grande -> Porto do Recife. Pecem nao pode validar Fortaleza, e Suape nao pode validar Recife.

O caso `TF-VAL-001B-004B` permanece bloqueado por decisao metodologica, pois nao ha porto alternativo de origem defensavel e documentado para Brasilia -> Salvador, nem distancia maritima associada. Ele deve aparecer como trabalho futuro ou bloqueio, nao como resultado numerico.

### 6.4 Casos de sensibilidade executados

Tres casos foram executados como sensibilidade Batch 001B:

- `TF-VAL-001B-SENS-002-REFDIST`: Santos/Manaus com distancia de referencia `3300 nm / 6111,6 km`;
- `TF-VAL-001B-SENS-003B-ALTPECEM`: Manaus/Pecem como porto alternativo para a regiao de Fortaleza, com `1569 nm / 2905,788 km`;
- `TF-VAL-001B-SENS-005B-ALTSUAPE`: Rio Grande/Suape como porto alternativo para a regiao de Recife, com `1844 nm / 3415,088 km`.

Essas linhas sao `sensitive`, nao `robust`. Elas podem ser discutidas como comportamento do modelo sob hipoteses documentadas, mas nao substituem as linhas de base de Fortaleza e Recife e nao produzem uma conclusao universal sobre cabotagem.

## 7. Resultados

### 7.1 Classificacao geral

A sintese final de resultados estabelece que nenhum caso atual se qualifica como `headline_candidate`. Isso significa que o TF nao deve apresentar uma tabela de "resultados principais validados" como se houvesse conclusoes robustas por corredor. O uso academico correto e apresentar o inventario de casos e, em seguida, discutir as tres linhas de sensibilidade executadas com suas restricoes.

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

## 8. Discussao

Os resultados reforcam que o desempenho da cabotagem e especifico por corredor. Em corredores longos com acesso portuario coerente e distancia maritima documentada, a alternativa multimodal pode apresentar forte reducao modelada de consumo rodoviario, custo operacional e TTW CO2e. No entanto, esse comportamento depende da qualidade da distancia maritima, da escolha do porto, da disponibilidade real de servico e da fronteira de custo. A propria literatura de short sea shipping indica que a vantagem ambiental nao e automatica [shortsea2019] [modalshiftreview2020].

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

## 10. Conclusao

O CabotageLens cumpre, no estado atual do projeto, uma funcao academica defensavel: fornece uma estrutura auditavel, reprodutivel e explicita em fronteiras para comparar transporte rodoviario direto e alternativas rodoviario-cabotagem-rodoviario em corredores brasileiros. A ferramenta organiza entradas, rotas, distancias, fontes, custos modelados, emissoes TTW CO2e e avisos de interpretacao em um fluxo coerente para analise de engenharia.

A principal melhoria recente e a camada Batch 001B, que aumenta a rastreabilidade da validacao. Em vez de aceitar resultados historicos com fallback maritimo como conclusoes, o Batch 001B separa linhas historicas, same-port, excluidas, bloqueadas, reference-needed e sensibilidade. Essa separacao e essencial para um Trabalho de Formatura, pois mostra maturidade metodologica e evita conclusoes mais fortes do que a evidencia permite.

As tres sensibilidades executadas indicam que, nos cenarios nomeados Santos/Manaus com distancia de referencia, Manaus/Pecem como porto alternativo e Rio Grande/Suape como porto alternativo, o multimodal permanece menor que o rodoviario direto em custo modelado e TTW CO2e operacional. Contudo, essas linhas sao `sensitive`, nao `robust`, e nao substituem linhas de base validadas.

Assim, a conclusao geral deve ser conservadora: o trabalho demonstra que o CabotageLens e capaz de estruturar comparacoes defensaveis e revelar potencial vantagem modelada da cabotagem em cenarios especificos, mas nao demonstra que a cabotagem e universalmente melhor. O valor cientifico do projeto esta na transparencia da comparacao, na exposicao das limitacoes e na disciplina de classificacao dos resultados.

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
