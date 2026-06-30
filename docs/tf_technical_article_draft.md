# CabotageLens: framework computacional auditável para comparação porta a porta entre rodovia e cabotagem no Brasil

## Resumo

Comparações entre transporte rodoviário e cabotagem podem se tornar enganosas quando tratam modos isolados, ignoram acessos terrestres ou misturam fronteiras ambientais e econômicas. Este artigo apresenta o CabotageLens, um framework computacional auditável para comparar alternativas rodoviárias diretas e cadeias rodoviária-cabotagem-rodoviária em corredores brasileiros. A contribuição central é uma implementação rastreável que organiza origem, destino, portos, pernas logísticas, proveniência de distâncias, componentes portuários, emissões operacionais TTW CO2e e proxy de custo operacional modelado sob uma mesma unidade funcional. A estratégia de evidência combina análise de sensibilidade interna e benchmark externo compacto. As sensibilidades executadas indicam que, nos três cenários rastreados, a alternativa multimodal apresentou menor custo modelado e menores emissões operacionais TTW CO2e do que a alternativa rodoviária direta. O benchmark externo acrescenta plausibilidade direcional: nos 21 pares origem-destino positivos e suportados, CabotageLens e o workbook externo apontaram a mesma direção modal para emissões. Esses resultados não constituem validação calibrada de magnitude, não demonstram superioridade universal da cabotagem e não transformam custo modelado em frete comercial. O valor do artigo está em mostrar como comparações rota a rota podem ser formuladas com fronteiras explícitas, metadados de proveniência e classificação conservadora da evidência.

**Palavras-chave**: cabotagem; transporte rodoviário; transporte multimodal; emissões operacionais; CO2e; logística; Brasil; framework computacional.

## 1. Introdução

O transporte de cargas no Brasil permanece fortemente dependente do modo rodoviário. Essa configuração oferece capilaridade e flexibilidade, mas também torna corredores longos sensíveis ao consumo de diesel, ao custo operacional e à pressão por redução de emissões. A cabotagem surge como alternativa relevante em parte desses fluxos, especialmente quando uma remessa pode ser organizada como cadeia porta a porta com acesso rodoviário ao porto, perna marítima e acesso rodoviário final [icct2022].

A pergunta técnica, entretanto, não é se "navio é melhor que caminhão" em abstrato. O resultado depende do corredor, dos portos escolhidos, das distâncias terrestres e marítimas, da utilização da embarcação, dos componentes portuários, da alocação de carga e da fronteira adotada [shortsea2019] [modalshiftreview2020]. Comparar uma perna marítima isolada com uma viagem rodoviária completa favorece uma leitura artificial; do mesmo modo, rejeitar a cabotagem com base apenas em médias nacionais perde informação de rota.

Este artigo apresenta o CabotageLens como resposta computacional a essa lacuna. O framework compara uma alternativa rodoviária direta e uma alternativa rodoviária-cabotagem-rodoviária para a mesma unidade funcional, preservando a proveniência dos insumos e os limites de uso dos resultados. O objetivo não é criar um cotador de frete, uma plataforma de booking, uma super-rede multimodal nacional ou uma confirmação de disponibilidade operacional. O objetivo é oferecer uma estrutura auditável e rastreável para formular comparações técnicas academicamente defensáveis.

## 2. Contexto e lacuna metodológica

A literatura sobre cabotagem brasileira e BR do Mar justifica a relevância do tema, mas não substitui uma avaliação rota a rota [icct2022]. Estudos de competitividade e super-rede mostram que a decisão modal real inclui serviço, frequência, tempo, estoque, risco, terminais, custos comerciais e rede de operadores [competitiveness2024]. Esses elementos são essenciais para a logística real, mas ultrapassam a fronteira atual do CabotageLens.

Na literatura de short sea shipping, a vantagem ambiental do transporte marítimo costeiro também é condicional. A direção e a magnitude do resultado dependem de distância, acessos terrestres, tipo de navio, utilização e premissas de cálculo [shortsea2019]. Revisões de mudança modal reforçam que custo, qualidade de serviço, confiabilidade e integração terrestre condicionam a adoção efetiva [modalshiftreview2020].

Outra fonte recorrente de erro é a fronteira ambiental. Resultados TTW, WTW e LCA não são intercambiáveis. O CabotageLens adota como linha de base emissões operacionais TTW CO2e. Fontes WTW, LCA ou CO2-only são úteis para discutir limites e trabalhos futuros, mas não calibram automaticamente a saída atual [decarb2024] [maritimelca2024]. A mesma disciplina vale para o resultado monetário: a saída é um proxy de custo operacional modelado, não frete comercial, cotação de mercado, tarifa contratada ou viabilidade econômica.

## 3. Metodologia

A unidade funcional é o transporte de uma quantidade especificada de carga conteinerizada entre uma origem e um destino no Brasil. Nos artefatos de validação e sensibilidade usados neste artigo, a configuração recorrente é `1 TEU / 14 t` por remessa. Essa base permite comparar duas alternativas sob a mesma carga e o mesmo par origem-destino, sem transformá-la em valor universal para todos os usos futuros do framework.

A alternativa rodoviária direta modela uma perna origem-destino por caminhão. A alternativa multimodal decompõe a mesma remessa em quatro blocos: pre-carriage rodoviário da origem ao porto de origem, perna marítima entre portos, operações portuárias e hoteling quando incluídos e com proveniência defensável, e on-carriage rodoviário do porto de destino ao destino final. A comparação, portanto, é porta a porta; a perna marítima nunca é interpretada isoladamente como substituta de toda a viagem rodoviária.

As distâncias terrestres são rotas modeladas por provedor e cache, não trajetórias GPS observadas nem rotas contratuais. As distâncias marítimas podem vir de matriz marítima, referência externa documentada, override manual rastreado ou fallback geométrico. O fallback por haversine é mantido como triagem, não como rota navegável confirmada. Portos selecionados, portos forçados e portos alternativos também possuem significados diferentes: Pecém não confirma silenciosamente Porto de Fortaleza, e Suape não confirma Porto do Recife.

As operações portuárias e o hoteling entram apenas quando o modelo possui base representável. A proveniência desses componentes deve indicar observação disponível, média ponderada de portos observados, default documentado ou indisponibilidade. Dado indisponível não é zero silencioso; é uma limitação de fronteira que impede incorporar o componente sem base defensável.

## 4. Implementação computacional

O CabotageLens é implementado como aplicação Streamlit com lógica de domínio separada em módulos reutilizáveis. A interface recebe origem, destino, carga, parâmetros de veículo, configuração de portos, classe de embarcação e opções de componentes portuários. O backend resolve coordenadas, consulta ou reaproveita rotas terrestres em cache, seleciona portos, resolve distância marítima, calcula combustível, custo modelado e emissões por perna, e preserva avisos de qualidade e metadados de proveniência.

Essa arquitetura foi organizada para auditabilidade. Em vez de apresentar apenas um total rodoviário e um total multimodal, a ferramenta registra pernas, portos, fonte de distância marítima, status de cache, componentes incluídos ou excluídos, razões de fallback e classificação de uso. Supabase/Postgres fornece persistência operacional para lugares, rotas, cenários e resultados; ele melhora reprodutibilidade, mas não transforma uma rota modelada em evidência de serviço real.

O custo é calculado como proxy operacional modelado. Ele pode incluir combustível rodoviário, combustível marítimo e componentes operacionais representados, mas não inclui margem comercial, negociação, seguro, demurrage, detention, inventário, confiabilidade, frequência, disponibilidade de slot ou tarifas completas de mercado. As emissões são reportadas como emissões operacionais TTW CO2e; diferenças entre CO2, CO2e e CO2eq só podem ser tratadas como equivalentes quando a fonte, os gases e a fronteira sustentam essa leitura.

## 5. Estratégia de evidência

A estratégia de evidência não busca um veredito binário de validação. Ela classifica o que cada camada pode sustentar. Os primeiros lotes internos foram usados para diagnosticar problemas de rota, fallback e seleção de portos; em seguida, três sensibilidades foram executadas para testar hipóteses documentadas de distância marítima e portos alternativos. Essas linhas são evidências condicionadas, não resultados principais irrestritos.

O benchmark externo Gustavo/Costa é usado de forma compacta, como evidência de plausibilidade direcional. A pergunta do artigo não é se o CabotageLens reconstrói o workbook nem se o workbook é verdade de referência. A pergunta é mais restrita: quando há pares comparáveis, o framework aponta a mesma direção modal de emissões que uma referência externa familiar ao problema? A resposta é interpretada junto com lacunas de magnitude e diferenças de fronteira.

Assim, a classificação de evidência separa três usos: resultados de sensibilidade, apoio direcional de benchmark e diagnóstico de lacunas metodológicas. Nenhum caso atual é tratado como conclusão principal irrestrita, e nenhum resultado é promovido a conclusão universal sobre cabotagem.

## 6. Resultados

As sensibilidades internas executadas indicaram menor custo modelado e menores emissões operacionais TTW CO2e para a alternativa multimodal nos três cenários rastreados. A Tabela 1 resume apenas os valores necessários para a leitura do artigo.

| Sensibilidade | Hipótese testada | Custo rodoviário / multimodal (BRL/remessa) | Emissões rodoviárias / multimodais (kg CO2e/remessa) |
| --- | --- | ---: | ---: |
| Santos/Manaus | Distância marítima de referência | 16.347,22 / 1.144,38 | 6.937,54 / 1.079,70 |
| Manaus/Pecém | Porto alternativo para a região de Fortaleza | 22.986,28 / 621,84 | 9.984,32 / 549,12 |
| Rio Grande/Suape | Porto alternativo para a região de Recife | 15.074,20 / 1.906,34 | 6.755,66 / 1.176,70 |

Essas linhas permanecem classificadas como sensíveis. Elas mostram comportamento do modelo sob hipóteses nomeadas; não confirmam os portos originalmente selecionados, não demonstram disponibilidade de serviço e não substituem evidência operacional externa.

A rerodada de 30 de junho de 2026 das validações, incorporando a exposição dos componentes de operações portuárias e *hoteling* conforme a metodologia atual, manteve a conclusão modal dos cenários avaliados.[^rerodada-portops-hoteling] Foram executadas 24 linhas de validação/modelo, com emissões médias rodoviárias de 6.258,34 kg CO2e e emissões médias multimodais por cabotagem de 467,43 kg CO2e, resultando em economia média de 91,97%. Em todos os cenários executados, a cabotagem permaneceu como alternativa de menor emissão.

O benchmark externo baseado no workbook Gustavo/Costa apresentou alinhamento direcional em todos os 21 pares origem-destino positivos e suportados: tanto o workbook quanto o CabotageLens favoreceram a cabotagem/multimodal em emissões frente ao rodoviário direto. Quinze células da matriz original foram puladas antes da execução por não serem comparáveis na fronteira adotada: seis self-pairs e nove linhas rodoviárias zero ou não positivas.

A magnitude, entretanto, permaneceu divergente. A classificação rastreada do benchmark é `same_direction_large_gap`, isto é, apoio direcional com lacuna material de magnitude. O rerun com cache reduziu a hipótese de instabilidade computacional como causa principal, registrando 63 route-cache hits e 0 misses. A reconciliação de fator rodoviário mostrou que premissas de consumo e fator de emissão rodoviários explicam parte importante da lacuna road-only, mas esse teste é diagnóstico e não substitui o modelo de linha de base.

## 7. Discussão

Os resultados sustentam uma leitura técnica limitada e útil. Primeiro, a comparação porta a porta é indispensável: acessos terrestres, portos e componentes portuários podem alterar o resultado, e por isso a cabotagem não deve ser descrita como intrinsecamente superior. Segundo, a proveniência da distância marítima e da seleção de portos condiciona a força da evidência. Uma sensibilidade com porto alternativo é informativa, mas não resolve automaticamente a lacuna do porto selecionado original.

Terceiro, o benchmark externo fortalece a plausibilidade direcional do framework sem transformar o artigo em uma reconstrução de Gustavo/Costa. A concordância de direção sugere que o sinal modal observado não é apenas artefato interno do protótipo. A lacuna de magnitude, por sua vez, é coerente com diferenças de distância, carga, veículo, alocação, serviço, portos, tratamento de port-ops/hoteling e fronteira TTW/WTW/LCA/CO2/CO2e.

Quarto, custo e emissões permanecem dimensões separadas. Um menor proxy de custo operacional modelado não implica frete comercial mais barato, e menor emissão operacional TTW CO2e não implica benefício WTW ou LCA. O CabotageLens deve ser lido como ferramenta de triagem técnica e de pesquisa, capaz de organizar perguntas e lacunas antes de uma avaliação comercial, operacional ou ambiental mais ampla.

## 8. Limitações

As principais limitações decorrem das fronteiras adotadas. A fronteira ambiental é operacional TTW CO2e; etapas a montante do combustível, fabricação de ativos, infraestrutura, ciclo de vida e poluentes locais completos não estão incorporados. A fronteira econômica é um proxy de custo operacional modelado, não uma análise de frete comercial ou viabilidade econômica.

O framework também não modela uma super-rede multimodal completa. Não há confirmação de frequência de serviço, disponibilidade de navio, slot, terminal, janela operacional, confiabilidade, inventário em trânsito ou contrato. Portos selecionados e distâncias de fallback são controles metodológicos, não evidência de operação disponível.

Por fim, o benchmark externo permanece parcial. Gustavo/Costa serve como contraste direcional compacto, não como verdade de referência, alvo de calibração ou reconstrução completa. A análise das diferenças rodoviárias ajuda a explicar parte do desalinhamento, mas não recalibra o CabotageLens nem autoriza misturar TTW, WTW, LCA, CO2 e CO2e.

## 9. Conclusões

O CabotageLens oferece um framework computacional auditável para comparar alternativas rodoviárias diretas e rodoviária-cabotagem-rodoviária em corredores brasileiros. Sua contribuição principal não é demonstrar uma hierarquia modal universal, mas tornar explícitas as condições sob as quais uma comparação é produzida: unidade funcional, rota, portos, distâncias, componentes portuários, proxy de custo operacional modelado, emissões operacionais TTW CO2e e qualidade da evidência.

As sensibilidades internas, a rerodada consolidada e o benchmark externo sustentam interpretação direcional cautelosa. Nos três cenários de sensibilidade, a alternativa multimodal foi menor em custo modelado e emissões operacionais TTW CO2e; na rerodada consolidada, 24 de 24 linhas executadas/modelo classificaram a cabotagem como alternativa de menor emissão; e, nos 21 pares comparáveis do benchmark, a direção modal de emissões coincidiu com a referência externa. Essas evidências são suficientes para mostrar plausibilidade metodológica e utilidade do framework, mas não para afirmar validação calibrada, reconstrução de Gustavo/Costa, disponibilidade operacional ou superioridade universal da cabotagem.

Como artigo técnico, o resultado central é a estrutura: um modo rastreável de formular comparações multimodais com fronteiras explícitas. Trabalhos futuros devem ampliar a cobertura de distâncias marítimas, melhorar a verificação de portos e serviços, incorporar fronteiras WTW/LCA separadas quando houver fatores compatíveis, e adicionar camadas comerciais apenas quando houver dados de frete, frequência, contrato e confiabilidade adequadamente documentados.

[^rerodada-portops-hoteling]: Nos cenários desta validação, o componente de *hoteling* foi tratado como incorporado à intensidade agregada de transporte marítimo, evitando dupla contagem. As operações portuárias foram incluídas explicitamente por valor-padrão documentado de literatura, sem uso de registros observados por porto ou médias estimadas de portos observados no artefato ativo. As diferenças antigo-novo do Batch 001B não são interpretadas como efeito puro de portops/*hoteling*, pois pernas rodoviárias resolvidas por cache/provedor também mudaram.

## Referências e artefatos pendentes

As chaves de citação preservadas neste rascunho seguem o mapa de citações rastreado do projeto: `[icct2022]`, `[competitiveness2024]`, `[shortsea2019]`, `[modalshiftreview2020]`, `[decarb2024]` e `[maritimelca2024]`. A formatação ABNT, a conversão para LaTeX, figuras, legendas de tabelas e metadados bibliográficos completos permanecem pendentes para a etapa final de produção. Artefatos internos de validação, cache, SeaMatrix, port-ops e benchmark Gustavo/Costa devem ser referidos por seus documentos rastreados, sem inventar novas chaves bibliográficas.
