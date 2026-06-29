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

### 4.1 Unidade funcional e alternativas comparadas

A unidade funcional adotada neste trabalho é o transporte de uma massa especificada de carga conteinerizada entre uma origem e um destino no Brasil. Essa definição mantém constante o serviço a ser atendido: o objeto de comparação não é um modo isolado, mas a entrega da mesma remessa sob duas alternativas metodologicamente comparáveis.

A primeira alternativa é a rota rodoviária direta, na qual a remessa é transportada por caminhão entre origem e destino. A segunda é a cadeia rodoviária-cabotagem-rodoviária, composta pelo acesso rodoviário ao porto de origem, pela perna marítima de cabotagem, por componentes portuários quando modelados e pelo acesso rodoviário final ao destino. A equivalência porta a porta é necessária para evitar uma comparação artificial entre apenas o trecho marítimo e uma viagem rodoviária completa.

Nos artefatos de validação e sensibilidade deste TF, a base recorrente de referência é `1 TEU / 14 t` por remessa. Essa base deve ser lida como configuração recorrente do estudo, não como hipótese universal de carga para todo uso possível do CabotageLens. Outros cenários podem empregar massas ou quantidades de TEU diferentes, desde que a unidade funcional seja explicitada antes da comparação.

Os resultados são interpretados por remessa. Normalizações por tonelada, TEU, contêiner ou tonelada-quilômetro podem ser úteis, mas somente quando preservam a base de carga, a distância considerada, a regra de alocação e a fronteira ambiental e econômica do cenário. Assim, a unidade funcional também disciplina a linguagem do trabalho: uma conclusão só é válida para a carga, a rota, os portos, os componentes e as fronteiras que foram efetivamente modelados.

| Elemento metodológico | Definição neste TF | Limite de interpretação |
| --- | --- | --- |
| Unidade funcional | Movimento de uma quantidade especificada de carga conteinerizada entre origem e destino no Brasil. | Não representa todos os perfis de carga, serviço logístico ou contrato de transporte. |
| Base recorrente do estudo | `1 TEU / 14 t` por remessa nos artefatos de validação e sensibilidade. | Base recorrente, não valor obrigatório para todo cenário do CabotageLens. |
| Alternativa rodoviária direta | Cadeia porta a porta formada por uma perna rodoviária origem-destino. | Rota modelada para comparação, não reconstrução de uma operação real específica. |
| Alternativa rodoviária-cabotagem-rodoviária | Cadeia porta a porta com acesso rodoviário, perna marítima, componentes portuários quando habilitados e acesso final. | Não equivale a comparar apenas navio contra caminhão. |
| Comparação entre alternativas | Avalia custo modelado e emissões operacionais para a mesma remessa. | Não define superioridade universal de um modo nem substitui análise comercial ou operacional. |

### 4.2 Fronteiras metodológicas do estudo

O CabotageLens é tratado neste TF como uma ferramenta de comparação metodológica entre alternativas de transporte. Sua função é tornar explícitas as premissas de rota, distância, carga, custo modelado, emissões operacionais e qualidade da evidência. A ferramenta não é apresentada como cotador de frete, otimizador comercial de rede, sistema de contratação logística ou validação de disponibilidade real de serviço.

A fronteira ambiental de linha de base é operacional. Nas pernas rodoviárias, ela corresponde às emissões diretas associadas ao uso de combustível no veículo, isto é, uma leitura de tanque-à-roda (*Tank-to-Wheel*, TTW). Na perna marítima, corresponde às emissões diretas da combustão a bordo, isto é, uma leitura *Tank-to-Wake* (TTW). O emprego da mesma sigla operacional para modos distintos exige essa explicitação, pois uma comparação multimodal combina componentes terrestres e marítimos.

As emissões são reportadas como dióxido de carbono equivalente, indicado no texto como CO2e ou, quando a notação matemática for útil, como $\text{CO}_{2\text{eq}}$. Essa notação deve ser lida de acordo com os fatores efetivamente implementados e documentados no projeto. Resultados CO2-only, fatores WTW, estudos de LCA ou inventários com outro escopo de gases não são automaticamente comparáveis à linha de base deste TF sem alinhamento explícito de unidade funcional, fonte de fator, gases incluídos, regra de equivalência climática, distância e alocação.

A fronteira econômica é a de custo modelado. Os valores em `BRL` representam a agregação dos componentes incluídos no cenário, como combustível, custos operacionais representados e componentes portuários quando habilitados. Eles não representam frete comercial, tarifa contratada, cotação spot, preço de armador, tabela terminal completa, contrato logístico, custo de inventário, confiabilidade, seguro, margem comercial ou todos os encargos locais.

Essas fronteiras também delimitam o uso das evidências externas. Literatura, referências externas e artefatos de validação podem apoiar comparação, diagnóstico, discussão ou identificação de lacunas, mas não substituem automaticamente a metodologia implementada. Quando houver confronto com uma referência externa, ele deve ser apresentado como contexto metodológico, não como verdade absoluta nem como eixo central do Capítulo 4.

| Dimensão de fronteira | Definição neste TF | Fora da fronteira de linha de base |
| --- | --- | --- |
| Emissões rodoviárias | Emissões operacionais TTW associadas ao combustível consumido nas pernas terrestres. | WTW, LCA, emissões de infraestrutura, fabricação de veículos e fatores de outra fronteira. |
| Emissões marítimas | Emissões operacionais TTW associadas ao combustível consumido na perna marítima e em componentes habilitados. | Ciclo de vida completo, combustíveis alternativos futuros ou fatores WTW importados sem alinhamento metodológico. |
| CO2e / $\text{CO}_{2\text{eq}}$ | Métrica reportada conforme fatores implementados e documentados. | Equivalência automática com CO2-only ou com fontes que adotem gases e GWP sem alinhamento documentado. |
| Custo modelado | Estimativa dos componentes representados no cenário. | Frete comercial, tarifa contratada, cotação, margem, serviço real, disponibilidade de slot ou decisão de compra. |
| Escopo operacional | Comparação de alternativas modeladas para uma remessa e um par origem-destino. | Otimização nacional de rede, grade de armador, cronograma, frequência, confiabilidade e viabilidade comercial. |

### 4.3 Construção da alternativa rodoviária direta

A alternativa rodoviária direta representa o transporte da mesma remessa por uma perna rodoviária origem-destino. Ela funciona como a referência terrestre da comparação: a origem, o destino, a carga e a unidade funcional permanecem constantes, enquanto a cadeia logística é limitada ao deslocamento por caminhão.

A distância dessa alternativa é expressa em quilômetros (`km`) e deriva da lógica de roteamento rodoviário e de cache disponível para o cenário. Ela deve ser interpretada como distância roteada/modelada sob provedor, perfil e configuração definidos, não como trajetória GPS observada nem como registro de uma viagem executada.

A cadeia conceitual da alternativa rodoviária é:

```text
origem/destino -> distância rodoviária modelada
distância + veículo + carga -> consumo de combustível estimado
combustível + fator implementado -> emissões operacionais CO2e
combustível + preço/insumos de custo -> custo modelado da perna rodoviária
```

Essa cadeia não introduz novo fator, coeficiente ou alteração de linha de base; ela apenas torna explícita a sequência lógica já usada pelo modelo. O preset de veículo, a massa de carga, o consumo estimado, a fonte de preço e o fator de emissão devem permanecer rastreáveis aos módulos e dados implementados, sem substituição por valores externos não incorporados à linha de base.

| Elemento | Papel metodológico | Limite de interpretação |
| --- | --- | --- |
| Distância rodoviária | Entrada em `km` para a perna direta origem-destino. | Rota modelada, não medição de campo nem rota comercial obrigatória. |
| Veículo e carga | Definem a configuração representativa da remessa. | Não reconstroem despacho real, frota específica ou contrato. |
| Consumo estimado | Liga distância, veículo e carga ao uso de combustível. | Não captura integralmente velocidade real, congestionamento, condução ou paradas. |
| Emissões operacionais | Aplicam o fator implementado ao combustível estimado. | Não são WTW, LCA nem CO2-only sem alinhamento explícito. |
| Custo modelado | Agrega os componentes representados na fronteira do cenário. | Não é frete comercial, tarifa, cotação ou preço contratado. |

### 4.4 Construção da alternativa rodoviária-cabotagem-rodoviária

A alternativa rodoviária-cabotagem-rodoviária representa a mesma remessa organizada como uma cadeia porta a porta. A perna marítima não substitui sozinha a viagem rodoviária completa; ela é combinada com os acessos terrestres e, quando habilitados, com componentes operacionais associados aos portos.

A cadeia é composta por quatro blocos metodológicos. O primeiro é o *pre-carriage*, isto é, o deslocamento rodoviário da origem ao porto de origem. O segundo é a perna marítima de cabotagem entre o porto de origem e o porto de destino. O terceiro inclui operações portuárias e *hoteling* somente quando esses componentes estão modelados e habilitados no cenário. O quarto é o *on-carriage*, que leva a remessa do porto de destino ao destino final por rodovia.

A cadeia conceitual da alternativa multimodal é:

```text
origem -> porto de origem -> porto de destino -> destino
pre-carriage + perna marítima + componentes portuários habilitados + on-carriage
distâncias por perna + carga/alocação + parâmetros implementados -> emissões operacionais e custo modelado
```

A decomposição por perna é metodologicamente indispensável. O resultado agregado da alternativa multimodal só é interpretável quando o leitor consegue identificar os acessos rodoviários, a distância marítima, os portos usados, os componentes portuários incluídos, a regra de alocação da carga e a proveniência das distâncias.

| Componente | Papel na cadeia multimodal | Limite de interpretação |
| --- | --- | --- |
| *Pre-carriage* | Liga a origem ao porto de origem por rodovia. | Pode dominar a cadeia quando a origem está distante do porto. |
| Perna marítima | Representa a cabotagem entre os portos definidos no cenário. | Não prova serviço real, escala, frequência ou disponibilidade de slot. |
| Operações portuárias | Representam atividades portuárias incluídas no cenário. | Não equivalem a tarifa portuária completa nem produtividade real do terminal. |
| *Hoteling* | Representa permanência/consumo associado à escala quando separado pelo modelo. | Deve ser tratado com cautela para evitar dupla contagem. |
| *On-carriage* | Liga o porto de destino ao destino final por rodovia. | Pode alterar substancialmente custo e emissões da alternativa. |
| Alocação da carga | Atribui à remessa uma parcela dos componentes marítimos e operacionais. | Não deve ser confundida com a lógica interna de referências externas não alinhadas. |

### 4.5 Seleção de portos e definição de cenários

A seleção de portos transforma a unidade funcional em uma cadeia multimodal concreta. Para cada cenário, a origem, o destino e a carga permanecem os mesmos; o que muda é a forma de construir a alternativa multimodal, incluindo os portos escolhidos, as distâncias de acesso e a perna marítima.

Em cenários ordinários, a ferramenta pode selecionar portos elegíveis por uma lógica determinística e auditável, como proximidade geográfica dentro do conjunto de portos configurados. Em cenários definidos para estudo, validação ou sensibilidade, portos específicos podem ser forçados. A seleção automática e a imposição manual são situações metodológicas diferentes e devem permanecer identificáveis no texto, nas saídas e nos artefatos de validação.

Essa lógica não é uma otimização completa de super-rede multimodal. O método não modela grade de navegação, frequência de escalas, disponibilidade de armador, slot, tempo de trânsito, confiabilidade, estoque em trânsito ou decisão comercial de roteamento. A escolha de portos é uma regra transparente para construir cenários comparáveis, não uma prova de que aquele serviço existe ou é comercialmente contratável.

| Situação de porto | Papel metodológico | Limite de interpretação |
| --- | --- | --- |
| Porto selecionado | Porto definido pela lógica do cenário ordinário. | Não comprova disponibilidade de serviço, frequência ou terminal adequado. |
| Porto forçado | Porto imposto explicitamente para um cenário documentado. | Não deve ser confundido com seleção automática nem com caso-base. |
| Porto alternativo | Porto diferente do selecionado originalmente, usado para testar uma hipótese. | Deve permanecer como cenário alternativo ou sensibilidade. |
| Porto próximo | Porto regionalmente relacionado ao destino ou origem. | Não substitui silenciosamente o porto originalmente selecionado. |
| Caso de mesmo porto | Origem e destino marítimos recaem no mesmo porto. | Indica limitação, exclusão ou aviso; não é cabotagem substantiva. |

Portos alternativos exigem disciplina de nomenclatura. Pecém não valida Porto de Fortaleza, e Suape não valida Porto do Recife. Mesmo quando o porto alternativo é logisticamente plausível para uma região, a mudança altera acessos rodoviários, terminal, distância marítima e interpretação do cenário. Por isso, a alternativa deve ser identificada como tal, sem conversão silenciosa em validação do porto originalmente selecionado.

### 4.6 Proveniência das distâncias e hierarquia de confiança

A distância é uma entrada metodológica comum às duas alternativas. Na alternativa rodoviária direta, ela define a perna origem-destino. Na alternativa multimodal, aparece no *pre-carriage*, na perna marítima e no *on-carriage*. Por isso, a confiança no resultado depende da proveniência de cada distância, não apenas do total agregado.

As distâncias rodoviárias devem ser interpretadas como rotas modeladas por provedor, perfil e configuração de roteamento, com possível reaproveitamento por cache. O cache melhora rastreabilidade e repetição controlada, mas não transforma a rota em medição de campo, rota comercial obrigatória ou prova de operação real.

As distâncias marítimas exigem hierarquia própria. Uma distância de matriz ou referência externa é mais forte quando corresponde ao par exato de portos selecionado ou explicitamente forçado, preserva unidade e fonte, e não depende de substituição silenciosa por outro terminal. Uma distância `manual_override` só é aceitável quando a decisão, a unidade e a motivação estão documentadas. Uma distância `haversine_fallback` é apenas uma estimativa geométrica de triagem; ela não representa uma rota navegável validada nem distância de serviço.

| Proveniência | Uso metodológico | Limite de interpretação |
| --- | --- | --- |
| Roteamento rodoviário/cache | Distância modelada para pernas terrestres. | Não é trajetória GPS medida nem rota comercial efetivamente usada. |
| `seamatrix` | Distância marítima matricial para par de portos aplicável. | Não comprova escala, frequência, serviço ou contrato. |
| `external_reference` | Referência documentada para o par de portos do cenário. | Só vale para o par e a unidade documentados. |
| `manual_override` | Substituição explícita e rastreável para um cenário. | Exige motivação documentada; não deve ser generalizada. |
| `haversine_fallback` | Estimativa geométrica quando falta distância marítima documentada. | Triagem ou lacuna de evidência; não valida rota marítima. |
| Referência ausente | Indica que a distância necessária não está suficientemente documentada. | Pode bloquear conclusão ou limitar o caso a sensibilidade. |

A hierarquia de proveniência afeta a classificação da evidência, mas não altera a fronteira ambiental ou econômica. Uma distância bem documentada melhora a rastreabilidade da rota; não prova disponibilidade real de serviço. Uma distância frágil, por outro lado, pode tornar inadequada uma conclusão numérica forte mesmo que o cálculo tenha sido executado corretamente.

### 4.7 Cadeias conceituais de cálculo de emissões e custos

Os cálculos do CabotageLens devem ser lidos como cadeias conceituais auditáveis, não como caixas-pretas nem como ajustes de linha de base a partir de referências externas. Esta seção resume a ordem lógica dos cálculos sem introduzir novos fatores, coeficientes ou valores de referência.

Para as pernas rodoviárias, a sequência é:

```text
distância rodoviária + veículo + carga -> combustível rodoviário estimado
combustível rodoviário + fator implementado -> emissões operacionais rodoviárias
combustível rodoviário + preço/insumos aplicáveis -> custo rodoviário modelado
```

Para a perna marítima, a sequência é:

```text
distância marítima + carga/alocação + classe/parâmetros implementados -> combustível marítimo alocado
combustível marítimo alocado + fator implementado -> emissões operacionais marítimas
combustível marítimo alocado + preço/insumos aplicáveis -> custo marítimo modelado
```

Para a alternativa multimodal, os resultados são agregados por perna e componente:

```text
resultado multimodal = pre-carriage + perna marítima + componentes portuários habilitados + on-carriage
```

A agregação deve preservar a distinção entre distância, consumo, custo e emissões. Custos e emissões são dimensões diferentes e não definem, por si só, um vencedor único sem regra de decisão explícita. A consistência metodológica exige que os dois lados da comparação mantenham a mesma unidade funcional e que os componentes incluídos no total sejam declarados.

| Cadeia | O que torna auditável | Cuidado metodológico |
| --- | --- | --- |
| Rodoviária direta | Distância, veículo, carga, combustível, fator e custo por perna. | Não importar fator externo como novo baseline sem mudança metodológica formal. |
| Multimodal | Separação entre acessos terrestres, perna marítima e componentes portuários. | Não ocultar acessos terrestres nem alocação marítima no total agregado. |
| Alocação marítima | Regra que atribui à remessa uma parcela da operação marítima. | Não tratar a alocação como equivalência automática com referências externas. |
| Comparação custo-emissões | Mantém `BRL` e CO2e como saídas distintas. | Não converter menor custo modelado em competitividade comercial universal. |

### 4.8 Operações portuárias, hoteling e prevenção de dupla contagem

As operações portuárias e o *hoteling* entram na metodologia apenas quando explicitamente modelados e habilitados no cenário. Eles não são uma camada automática de validação operacional; são componentes adicionais de custo e emissões dentro da mesma fronteira operacional definida para a comparação.

Operações portuárias representam atividades de terminal incluídas pelo modelo, como movimentações e equipamentos quando parametrizados. *Hoteling* representa consumo associado à permanência da embarcação em escala quando essa parcela é tratada separadamente. Ambos devem ser interpretados como aproximações operacionais modeladas, não como tarifa portuária completa, produtividade real de terminal, tempo de permanência observado ou inventário local de emissões atmosféricas.

A regra metodológica central é evitar dupla contagem. Se a intensidade marítima ou o fator agregado usado em um cenário já incorpora consumo operacional associado ao navio em porto, acrescentar *hoteling* separado pode superestimar emissões e custos. Se o cenário separa navegação, permanência em porto e operação de terminal, essa decomposição deve permanecer explícita na interpretação.

| Componente | Quando entra | Cuidado metodológico |
| --- | --- | --- |
| Operações portuárias | Quando o cenário habilita o componente portuário modelado. | Não representa tarifa terminal completa nem todos os encargos locais. |
| *Hoteling* | Quando a permanência da embarcação é modelada separadamente. | Não deve duplicar consumo já embutido em intensidade marítima agregada. |
| Equipamentos de terminal | Quando há parâmetro operacional específico no modelo. | Não substitui inventário local de produtividade ou qualidade do ar. |
| Eletricidade ou combustível em porto | Quando a fonte e o parâmetro estão documentados no cenário. | Não deve receber fatores pendentes ou externos sem mudança metodológica formal. |

Essa disciplina é suficiente para o Capítulo 4. Discussões sobre atualização de fatores, literatura específica de emissões em berço, dados de produtividade portuária ou ampliação da fronteira de porto pertencem às limitações e aos trabalhos futuros, salvo se uma etapa posterior do projeto alterar explicitamente a metodologia.

### 4.9 Qualidade de rota, classificação de evidências e limites de uso

A metodologia adota uma leitura conservadora da qualidade de rota e da força da evidência. Um resultado calculado não é automaticamente um resultado adequado para conclusão principal. Antes de interpretar uma linha, é necessário verificar se a cadeia representa uma alternativa comparável, se a distância tem proveniência suficiente, se os portos pertencem ao cenário declarado, se a fronteira de custo e emissões foi preservada e se há avisos que limitem o uso acadêmico do resultado.

Os avisos de qualidade de rota funcionam como controles interpretativos. Um caso *same-port*, uma distância `haversine_fallback`, um porto alternativo, uma referência ausente ou um acesso rodoviário dominante não prova, por si só, impossibilidade operacional. Esses sinais indicam que a linha deve ser lida com cautela e classificada conforme seu uso metodológico permitido.

| Condição ou classificação | Significado metodológico | Uso seguro |
| --- | --- | --- |
| `historical_diagnostic` | Resultado preservado para rastreabilidade histórica do método. | Auditoria e explicação de evolução metodológica. |
| `record_only_warning` | Registro mantido para documentar aviso, como caso *same-port*. | Limitação ou exemplo metodológico, sem conclusão modal. |
| `reference_needed` | Falta evidência suficiente para uma distância ou premissa necessária. | Lacuna de evidência e prioridade de validação futura. |
| `excluded` | Caso inválido ou fora da fronteira adotada. | Justificativa de exclusão, sem uso numérico conclusivo. |
| `planned_blocked_methodology_decision` | Há decisão metodológica pendente antes de executar ou interpretar o caso. | Registro de bloqueio e requisito para trabalho futuro. |
| `sensitivity_only` | Cenário adequado apenas como hipótese de sensibilidade. | Discussão condicional, sem substituir o caso-base. |
| `sensitive` | Resultado executado sob hipótese condicional. | Evidência dependente da hipótese, não conclusão principal. |
| `headline_candidate` | Categoria reservada para resultado principal após evidência suficiente. | Só deve ser usada quando artefatos rastreados sustentarem a promoção. |

Benchmarks externos, incluindo materiais associados a Gustavo/Costa, entram nesse esquema apenas como contexto de comparação e diagnóstico de fronteiras. Eles não definem automaticamente a metodologia do CabotageLens, não substituem o caso-base, não validam magnitudes sem alinhamento metodológico completo e não transformam custos modelados em fretes comerciais.

A regra final de uso é simples: cada resultado só pode sustentar afirmações compatíveis com sua proveniência, fronteira e classificação. Assim, linhas com fallback, porto alternativo, mesma origem e destino marítimos, referência ausente, bloqueio metodológico ou sensibilidade condicional não devem ser promovidas a conclusões gerais sobre a superioridade da cabotagem. O papel da metodologia é preservar essa disciplina antes que os capítulos de validação, resultados, discussão, limitações e conclusão interpretem os artefatos finais.

## 5. Ferramenta computacional

### 5.1 Visão geral da ferramenta e arquitetura do protótipo

O CabotageLens é o protótipo computacional desenvolvido neste trabalho para operacionalizar a metodologia do Capítulo 4. Sua função é transformar uma unidade funcional, um par origem-destino, uma base de carga e parâmetros de cenário em uma comparação rastreável entre uma alternativa rodoviária direta e uma cadeia rodoviária-cabotagem-rodoviária. A ferramenta não é apresentada como produto comercial de contratação de transporte, mas como uma estrutura acadêmica para tornar explícitas as escolhas de rota, porto, distância, custo modelado, emissões operacionais TTW CO2e, proveniência e avisos de qualidade.

A arquitetura separa quatro responsabilidades. A interface Streamlit organiza entradas, execução e apresentação dos resultados. O núcleo de domínio resolve endereços, constrói rotas, consulta dados marítimos, calcula combustível, custo e emissões, e produz metadados de qualidade. A camada de dados mantém insumos processados, como portos, matriz marítima, preços de diesel, preços de combustível marítimo, classes de eficiência de embarcações e artefatos ANTAQ/MRV. A camada Supabase/Postgres preserva caches e registros duráveis, enquanto Supabase Storage pode funcionar como repositório opcional de ativos de dados ou logs quando configurado.

Essa separação é importante para o argumento do TF porque evita que o resultado final seja apenas um número agregado. O protótipo registra de onde vieram coordenadas, distâncias, parâmetros de combustível, intensidades marítimas, avisos e classificações. Assim, cada comparação pode ser revisitada como uma cadeia de transformação: entrada do cenário, resolução geográfica, construção de pernas, consulta a fontes internas ou externas, cálculo por fronteira metodológica e saída classificada.

### 5.2 Pipeline computacional de ponta a ponta

Em nível de sistema, o fluxo do CabotageLens pode ser descrito como uma sequência de oito etapas. Primeiro, o usuário define origem, destino, carga, parâmetros operacionais, portos quando aplicável, controles de rota, componentes opcionais e parâmetros de custo/emissões. Segundo, a ferramenta resolve origem e destino em coordenadas e metadados geográficos normalizados. Terceiro, as pernas rodoviárias são buscadas no cache ou calculadas por provedores de rota. Quarto, os portos são selecionados ou recebidos como hipóteses forçadas/alternativas. Quinto, a matriz marítima fornece a distância da perna de cabotagem e, quando disponível, estatísticas direcionais observadas derivadas de ANTAQ/MRV. Sexto, os dados de custo e emissão são resolvidos a partir de preços, especificações de caminhão, eficiência de embarcação, alocação de carga e componentes portuários. Sétimo, o avaliador consolida a alternativa rodoviária direta e a cadeia multimodal em custos modelados e emissões operacionais TTW CO2e. Oitavo, a interface, os caches e os artefatos de exportação preservam saídas, fontes, avisos e classificações.

| Etapa computacional | Transformação principal | Evidência preservada |
| --- | --- | --- |
| Entradas do cenário | Origem, destino, carga, portos, controles e parâmetros viram uma fronteira de cálculo. | Campos de entrada, base de carga, toggles e premissas. |
| Resolução geográfica | Texto ou coordenadas são normalizados para pontos utilizáveis na rota. | Coordenadas, rótulos, UF e fonte/cache de localização. |
| Roteamento terrestre | Trechos rodoviários são recuperados de cache ou calculados por provedor. | Distância, perfil, provedor, fonte, status de cache e metadados de rota. |
| Construção multimodal | Portos e pernas formam *pre-carriage*, perna marítima e *on-carriage*. | Portos usados, distância marítima, proveniência e avisos de qualidade. |
| Dados ANTAQ/MRV | Processamentos offline atualizam viagens observadas e enriquecem a matriz marítima. | Pares observados, segmentos, match de IMO e estatísticas direcionais. |
| Avaliação custo-emissões | Combustível, preço, alocação, operações portuárias e *hoteling* são agregados. | Detalhe por perna, fatores de entrada, fontes e componentes incluídos/excluídos. |
| Persistência e saída | Resultados são exibidos, registrados ou exportados conforme o fluxo. | Cartões, tabelas, avisos, premissas, CSV/JSON e registros Supabase. |

Esse pipeline não deve ser confundido com uma simulação operacional completa. Ele descreve o que o programa faz para tornar a metodologia executável e auditável. Não prova disponibilidade de serviço para todos os cenários, não estima frete comercial completo e não transforma estabilidade de cache em validação de magnitude.

### 5.3 Entradas do cenário e resolução geográfica

As entradas do cenário definem a fronteira computacional da comparação. A origem e o destino determinam os pontos da unidade funcional; a massa e a quantidade em TEU definem a base de carga; os parâmetros de alocação controlam como a parcela marítima é atribuída à remessa; e os controles de portos permitem usar a seleção padrão, portos forçados ou portos alternativos em cenários documentados. Outros parâmetros habilitam ou desabilitam componentes como operações portuárias e *hoteling*, selecionam classe de embarcação, caminhão representativo, preço de diesel explícito ou por consulta, preço de combustível marítimo e opções de exportação ou validação.

A resolução geográfica ocorre antes da construção das rotas. Quando o usuário informa nomes de lugares, a ferramenta tenta recuperar coordenadas já persistidas; quando isso não é possível, usa a fachada de provedores rodoviários para geocodificação. O encadeamento primário é OpenRouteService, com uma ou mais chaves configuradas, e LocationIQ funciona como fallback quando tokens estão disponíveis. O retorno é normalizado para que o restante do sistema trabalhe com rótulo, latitude, longitude, UF quando identificável e metadados de provedor, independentemente de qual serviço respondeu.

O mesmo princípio vale para as rotas terrestres. Cada perna rodoviária é resolvida por um fluxo cache-first: primeiro a ferramenta procura uma distância já registrada por coordenadas ou rótulos normalizados; se não houver registro compatível, chama o provedor configurado e depois tenta persistir o resultado. A resposta usada pelo modelo conserva distância, perfil solicitado/usado, fonte, provedor, indicador de cache e, quando disponível na resposta do provedor, metadados como duração. Essas rotas são rotas modeladas por provedor, não trajetórias GPS observadas nem confirmação de uma viagem real.

### 5.4 Construção das rotas e seleção de portos

Com origem e destino resolvidos, o CabotageLens constrói duas alternativas comparáveis. A alternativa rodoviária direta liga origem e destino por uma única perna terrestre. A cadeia rodoviária-cabotagem-rodoviária é formada por acesso rodoviário ao porto de origem (*pre-carriage*), perna marítima entre portos e acesso rodoviário final (*on-carriage*). Essa decomposição é preservada porque os acessos terrestres podem alterar de forma relevante custo, emissões e interpretação do resultado multimodal.

Os portos entram de três formas. No uso padrão, a ferramenta seleciona portos elegíveis a partir dos pontos de origem e destino. Em análises de validação ou sensibilidade, portos podem ser forçados para reproduzir uma hipótese específica ou alternativos para testar uma cadeia distinta. Esses estados precisam permanecer visíveis: porto selecionado, porto forçado e porto alternativo não têm o mesmo significado metodológico e não devem ser misturados na interpretação do caso-base.

A perna marítima é consultada na matriz marítima do projeto. Quando há distância de par ou distância direcional/corredor enriquecida, essa informação substitui ou complementa a distância-base preservando a proveniência. Quando não há valor mais forte, a matriz pode recorrer a estimativa geométrica por `haversine_fallback`, que serve como triagem e não como validação de distância operacional. Em todos os casos, a ferramenta registra fonte, tipo de fonte, unidade, eventuais notas e metadados associados à distância.

Depois da construção da rota, os avisos de qualidade indicam limitações como `same-port`, distância marítima ausente ou muito pequena, uso de `fallback` e domínio dos acessos rodoviários sobre uma cadeia marítima local. Esses avisos são controles de interpretação. A presença de um aviso não prova impossibilidade operacional, mas impede tratar a linha como evidência robusta sem suporte adicional; a ausência de aviso também não comprova serviço, escala, frequência, slot ou viabilidade comercial.

### 5.5 Fontes de dados, atualização ANTAQ/MRV e matriz marítima

Além do fluxo interativo, o projeto possui uma pipeline offline de apoio para atualizar dados marítimos. Essa pipeline pode baixar as tabelas TXT necessárias da ANTAQ para anos selecionados, reconstruir viagens observadas de cabotagem, materializar saídas tabulares de viagens, paradas e chamadas, e opcionalmente garantir o esquema e fazer *upsert* dessas tabelas em Supabase/Postgres. Quando configurado, o mesmo processo pode sincronizar a árvore de dados com Supabase Storage para uso como ativo remoto.

A atualização também alimenta a matriz marítima. As viagens e paradas materializadas são cruzadas com informações de eficiência MRV por IMO quando há correspondência disponível. A partir desses segmentos, o enriquecimento calcula estatísticas direcionais ponderadas por tonelada-milha náutica, como distância, número de segmentos, viagens, embarcações e intensidade média de combustível por transporte. O resultado é anexado à matriz marítima para que a avaliação possa preferir evidência direcional observada quando ela existe, mantendo a distância-base e sua proveniência quando for necessário.

Essa integração melhora a rastreabilidade da perna marítima, mas não deve ser lida como prova universal de disponibilidade operacional. ANTAQ e MRV ajudam a documentar pares observados, segmentos e intensidades quando há cobertura, mas não garantem que todo cenário do usuário tenha serviço regular, capacidade, janela, aceitação terminal ou equivalência exata com uma rota comercial. Pares sem cobertura suficiente continuam dependentes de matriz-base, referência documentada ou `haversine_fallback`, com a cautela correspondente.

### 5.6 Cálculo de custo operacional modelado e emissões

A etapa de avaliação usa a geometria construída e os dados de entrada para calcular combustível, custo modelado e emissões operacionais TTW CO2e. Na alternativa rodoviária direta, a distância origem-destino alimenta o modelo de combustível rodoviário a partir do caminhão representativo e da carga. O preço do diesel pode ser informado explicitamente; caso contrário, a ferramenta consulta o CSV processado de preços por UF e calcula uma referência a partir das UFs de origem e destino, usando comportamento de fallback quando uma UF ou o arquivo não estiver disponível.

Na cadeia multimodal, o mesmo modelo rodoviário é aplicado ao *pre-carriage* e ao *on-carriage*. A perna marítima usa preço de combustível marítimo persistido para Santos, com fallback configurado quando o arquivo não está disponível ou não pode ser lido, e dados de eficiência da classe de embarcação. Quando a matriz marítima enriquecida contém intensidade direcional de combustível por tonelada-milha náutica, essa informação pode ser usada para a perna; caso contrário, a avaliação recorre à eficiência da classe de embarcação e à lógica de alocação de carga. A alocação considera massa, TEU, capacidade e fator de carga quando esses campos são aplicáveis, preservando o modo efetivamente usado.

Operações portuárias e *hoteling* entram como componentes condicionais. As operações portuárias podem adicionar combustível, custo e CO2e conforme o cenário selecionado e os movimentos/calls representados. O *hoteling* pode ser solicitado com horas por chamada e número de chamadas, mas a implementação registra sua inclusão ou exclusão. Quando a intensidade de transporte MRV já incorpora consumo operacional agregado, o *hoteling* separado pode ser omitido para reduzir risco de dupla contagem, preservando o motivo da exclusão nos metadados.

O resultado da avaliação preserva a composição por perna. Para a alternativa rodoviária direta, são registrados distância, combustível, custo proxy e CO2e. Para a alternativa multimodal, são registrados primeiro acesso rodoviário, perna marítima, componentes portuários/*hoteling* quando aplicáveis, último acesso rodoviário, total multimodal e comparação final. Essa comparação é uma diferença entre estimativas modeladas sob a fronteira definida, não uma afirmação de competitividade comercial.

### 5.7 Persistência, cache, saídas e rastreabilidade

Supabase/Postgres funciona como camada durável para cache e registros de cenário/resultado. Na prática, isso permite reaproveitar lugares geocodificados, rotas terrestres, distâncias e resultados de avaliações quando a consulta é compatível. O ganho metodológico é reduzir variação por chamadas repetidas a provedores e permitir auditoria posterior da execução. Um `cache hit`, porém, indica reutilização de evidência computacional; não valida a magnitude de custo ou emissão e não prova viabilidade comercial da rota.

Supabase Storage tem papel opcional. Quando configurado, pode receber ativos de dados ou logs compactados, incluindo produtos de atualização da pasta `data/`. Esse uso melhora portabilidade e operação em ambiente Streamlit Cloud, mas não altera as fronteiras substantivas do modelo. Um arquivo sincronizado para Storage continua sujeito à mesma proveniência, data de atualização, cobertura e limitação metodológica que tinha localmente.

As saídas visíveis na interface organizam a interpretação do resultado. Os cartões resumem custo modelado, emissões TTW CO2e e distâncias; as tabelas de detalhes mostram pernas, portos, componentes, premissas, fonte de diesel, fonte marítima, fronteira de custo e fronteira de emissões; os avisos aparecem junto do resultado para sinalizar limitações; e os artefatos de exportação ou validação preservam entradas, saídas, portos, distâncias, fontes, status e classificações quando disponíveis.

| Saída ou registro | O que torna rastreável | Limite de interpretação |
| --- | --- | --- |
| Cartões e detalhes da interface | Totais, pernas, portos, custos modelados, emissões TTW CO2e e premissas. | Não substituem análise metodológica do cenário. |
| Cache de localização e rota | Coordenadas, distâncias terrestres, perfil, fonte, provedor e reuso. | Não representa viagem observada nem rota comercial validada. |
| Matriz marítima e proveniência | Distância, tipo de fonte, `fallback`, estatísticas ANTAQ/MRV quando disponíveis. | Evidência de rota/eficiência depende da cobertura e da qualidade da fonte. |
| Registros de avaliação | Combustível, custo, CO2e, alocação, portos, componentes e avisos. | Estimativas permanecem condicionadas à fronteira do modelo. |
| Exportações de validação | Status, classificações, bloqueios, sensibilidades e metadados. | Não promovem automaticamente uma linha a evidência robusta. |

### 5.8 Limitações computacionais e uso correto da ferramenta

O uso correto do CabotageLens é analítico e acadêmico. A ferramenta apoia comparação transparente entre a alternativa rodoviária direta e a cadeia rodoviária-cabotagem-rodoviária, análise de sensibilidade, rastreabilidade, reprodutibilidade e identificação de lacunas metodológicas. Ela não automatiza decisão comercial, contratação de transporte, validação operacional ou conclusão universal sobre a cabotagem.

As principais fronteiras de uso são quatro. Primeiro, a fronteira econômica: custos modelados são proxy operacional limitado e não fretes, cotações, tarifas, contratos ou custos logísticos totais de mercado. Segundo, a fronteira ambiental: emissões reportadas permanecem operacionais TTW CO2e, não WTW, LCA ou evidência CO2-only. Terceiro, a fronteira de rota: ORS e LocationIQ fornecem geocodificação e rotas modeladas por provedor, não trajetórias GPS observadas. Quarto, a fronteira operacional: ANTAQ/MRV, Supabase, cache, ausência de aviso ou exportação completa não comprovam serviço regular, capacidade, escala, frequência, slot, aceitação terminal ou viabilidade comercial.

Consequentemente, os estudos de caso do Capítulo 6 devem herdar essas cautelas. Cada resultado precisa ser interpretado junto com entradas, portos, distâncias, proveniência, cache, componentes habilitados, avisos e classificação conservadora. O fechamento deste capítulo é, portanto, uma regra de leitura: o CabotageLens torna a implementação metodológica visível e auditável, mas a força de cada conclusão depende da qualidade da evidência associada ao cenário.

## 6. Validação, benchmark e classificação de evidências

### 6.1 Estratégia de validação como classificação de evidências

A validação adotada neste TF não é um veredito binário de aprovação ou reprovação do modelo. Ela é uma estratégia de classificação de evidências: cada execução, decisão metodológica, sensibilidade ou comparação externa recebe um uso permitido antes que os resultados sejam apresentados no Capítulo 7. O objetivo deste capítulo é, portanto, responder como a evidência foi avaliada e controlada, não quais são os resultados finais nem o que eles significam para a conclusão do trabalho.

Essa abordagem é necessária porque as saídas do CabotageLens combinam distâncias modeladas, seleção de portos, fontes marítimas com níveis diferentes de confiança, custos modelados, emissões operacionais e benchmarks externos com fronteiras nem sempre equivalentes. Uma linha numericamente executada não se torna, por esse motivo, uma conclusão principal. A classificação indica se a evidência pode ser usada como diagnóstico histórico, sensibilidade, limitação, exclusão, bloqueio metodológico, lacuna de referência, apoio direcional de benchmark ou diagnóstico de premissas.

| Camada de evidência | Papel no Capítulo 6 | Interpretação segura |
| --- | --- | --- |
| Batch 001 histórico | Preserva a primeira camada diagnóstica de casos OD. | Evidência histórica e motivação para correções; não resultado final validado. |
| Batch 001B metodológico | Classifica decisões, exclusões, bloqueios, lacunas de referência, avisos e sensibilidades. | Camada de auditabilidade que controla o uso permitido de cada caso. |
| Sensibilidades Batch 001B | Testam hipóteses documentadas de distância marítima ou porto alternativo. | Evidência sensível; não resultado robusto nem `headline_candidate`. |
| Batch 002 Gustavo/Costa | Compara o modelo com referência externa associada aos trabalhos Gustavo/Costa. | Apoio direcional de benchmark; não reprodução calibrada de magnitude. |
| Rerun Supabase/cache | Verifica se instabilidade de provedor/cache explica a lacuna rodoviária. | Evidência de estabilidade computacional; não prova operacional ou comercial. |
| Reconciliação rodoviária | Testa premissas rodoviárias como explicação diagnóstica da lacuna road-only. | Explica parte do desalinhamento; não recalibra nem substitui a linha de base. |
| Categorias finais de uso | Define o que cada linha pode sustentar no TF. | Controle de afirmação que deve ser herdado pelo Capítulo 7. |

As fronteiras substantivas atravessam todas as camadas. Custos continuam sendo estimativas modeladas, não fretes, tarifas ou cotações. Emissões continuam sendo operacionais e expressas como CO2e dentro da fronteira implementada; para as pernas rodoviárias, a leitura operacional corresponde a *Tank-to-Wheel* (TTW), e para a perna marítima corresponde a *Tank-to-Wake* (TTW). Evidências WTW, LCA, CO2-only ou CO2e sob outro escopo só podem ser usadas como contraste, limitação ou trabalho futuro quando a diferença de fronteira estiver explícita.

### 6.2 Batch 001 como diagnóstico histórico

O Batch 001 foi a primeira camada histórica de avaliação dos casos de validação. Ele preserva resultados numéricos para cinco pares origem-destino, mas todos os casos ficaram associados à necessidade de referência, revisão posterior ou reclassificação metodológica. A principal limitação diagnosticada foi o uso de distâncias marítimas `haversine_fallback` em casos nos quais a distância de navegação e a plausibilidade de serviço exigiam evidência mais forte.

Os cinco casos históricos foram:

| Caso | Par origem-destino | Portos históricos | Uso seguro no TF |
| --- | --- | --- | --- |
| `TF-VAL-001` | São Paulo, SP -> Santos, SP | Santos -> Santos | Diagnóstico de caso same-port e limite de rota. |
| `TF-VAL-002` | São Paulo, SP -> Manaus, AM | Santos -> Manaus | Diagnóstico histórico; base para sensibilidade de distância de referência. |
| `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | Manaus -> Fortaleza | Diagnóstico histórico; referência exata de Fortaleza permanece faltante. |
| `TF-VAL-004` | Brasília, DF -> Salvador, BA | Angra dos Reis -> Salvador | Diagnóstico histórico; cadeia de Angra dos Reis depois excluída para o benchmark conteinerizado. |
| `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | Rio Grande -> Recife | Diagnóstico histórico; referência exata de Recife permanece faltante. |

Essas linhas não devem ser tratadas como resultados corrigidos. Seu valor está em mostrar por que o TF precisou separar fallback, seleção de porto, sensibilidade, exclusão e lacuna de referência antes de usar qualquer número como evidência. Por isso, o Batch 001 entra na classificação final como `historical_diagnostic`, não como validação calibrada, prova comercial ou conclusão de desempenho modal.

### 6.3 Batch 001B como camada de decisão metodológica

O Batch 001B deve ser lido como uma camada de decisão metodológica e auditabilidade. Ele não transformou os casos históricos em resultados finais validados; reorganizou a evidência em linhas com portos selecionados ou forçados, fonte de distância marítima, unidade, conversão, status metodológico e uso permitido no TF. Essa camada é a ponte entre o diagnóstico histórico e a classificação final usada nos capítulos seguintes.

| Status ou decisão Batch 001B | Categoria final associada | Uso seguro no TF |
| --- | --- | --- |
| Registro histórico preservado | `historical_diagnostic` | Mostrar evolução do método e motivação das correções; não apresentar como resultado corrigido. |
| Caso same-port ou aviso de rota | `limitation_example` | Explicar limite de construção de rota; não tratar como cabotagem normal. |
| Caso fora da fronteira atual | `excluded` | Justificar exclusão metodológica; não executar nem interpretar como resultado. |
| Referência exata ausente | `reference_needed` | Registrar lacuna para o par de portos selecionado; não declarar lacuna resolvida. |
| Decisão metodológica ausente | `methodology_blocked` | Registrar bloqueio e trabalho futuro; não converter em conclusão numérica. |
| Hipótese preparada ou executada como sensibilidade | `sensitivity_discussion` / `sensitive` | Discutir comportamento sob premissa nomeada; não promover a linha de base robusta. |

Essa disciplina explica os principais casos do lote. Santos -> Santos permanece como exemplo same-port e, portanto, como limite da lógica de rota, não como cadeia normal de cabotagem. Angra dos Reis -> Salvador fica excluído para a fronteira atual de benchmark conteinerizado, pois a cadeia selecionada não é defensável como base numérica sob os critérios documentados. Manaus -> Fortaleza e Rio Grande -> Recife continuam dependentes de referências exatas para os portos selecionados.

Também é necessário preservar a diferença entre porto selecionado e porto alternativo. Uma referência para Pecém não valida silenciosamente Porto de Fortaleza, e uma referência para Suape não valida silenciosamente Porto do Recife. Quando Pecém ou Suape aparecem em linhas posteriores, eles devem ser lidos como portos alternativos explicitamente rotulados, não como substitutos metodológicos dos portos originalmente selecionados.

### 6.4 Sensibilidades Batch 001B: evidência sensível, não robusta

Três casos foram executados como sensibilidades do Batch 001B: Santos/Manaus com distância marítima de referência documentada, Manaus/Pecém como sensibilidade de porto alternativo para a região de Fortaleza e Rio Grande/Suape como sensibilidade de porto alternativo para a região de Recife. Esses casos testam hipóteses metodológicas rastreadas: correção de proveniência de distância, uso explícito de porto alternativo e separação entre porto regionalmente próximo e porto originalmente selecionado.

O ponto central desta subseção é a classificação, não a magnitude numérica. As três linhas executadas permanecem classificadas como `sensitive`. Elas podem ser usadas para discutir como a escolha de rota, porto e distância marítima afeta custo modelado e emissões operacionais, mas não substituem validação robusta, não criam casos `headline_candidate` e não encerram as lacunas dos casos-base ainda dependentes de referência exata.

| Sensibilidade | Hipótese testada | Interpretação segura | Limitação |
| --- | --- | --- | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Santos/Manaus com distância marítima de referência documentada. | Mostra o comportamento do modelo quando a distância marítima histórica de fallback é tratada como hipótese de sensibilidade. | Não valida todos os casos com `haversine_fallback` nem transforma a linha em conclusão robusta. |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Manaus/Pecém como porto alternativo para a região de Fortaleza. | Permite discutir sensibilidade a porto alternativo, acesso rodoviário e distância marítima. | Pecém não valida Porto de Fortaleza e não substitui a linha-base selecionada. |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Rio Grande/Suape como porto alternativo para a região de Recife. | Permite discutir sensibilidade a porto alternativo, acesso rodoviário e distância marítima. | Suape não valida Porto do Recife e não substitui a linha-base selecionada. |

Assim, as sensibilidades são úteis porque mostram comportamento condicionado do modelo sob hipóteses documentadas. Elas não autorizam extrapolação para todos os casos com `haversine_fallback`, não provam disponibilidade de serviço e não estabelecem superioridade universal da cabotagem. Os valores numéricos dessas três linhas pertencem ao inventário de resultados do Capítulo 7; neste capítulo, seu papel é justificar por que permanecem como evidência sensível.

### 6.5 Batch 002 Gustavo/Costa como benchmark externo direcional

O Batch 002 acrescenta uma camada de benchmark externo baseada no workbook Gustavo/Costa, associado a trabalhos já mapeados na bibliografia do projeto \citep{competitiveness2024, decarb2024}. Esse benchmark é importante para a defesa porque confronta o CabotageLens com uma referência externa ao próprio protótipo. Seu papel, entretanto, é estritamente metodológico: verificar consistência direcional e expor lacunas de comparabilidade, não reproduzir exatamente o workbook nem tratá-lo como referência absoluta.

A leitura segura começa pela diferença entre direção e magnitude. A pergunta defensável para o Capítulo 6 é se, nos pares OD positivos e suportados, o workbook e o CabotageLens apontam para o mesmo lado da comparação de emissões. A pergunta que o Batch 002 não responde é se as magnitudes são calibradas, se a lógica interna do workbook foi reconstruída integralmente ou se cada rota representa uma operação comercial disponível.

| Item de classificação do Batch 002 | Valor rastreado | Interpretação segura |
| --- | ---: | --- |
| Células de matriz do workbook parseadas | 36 | Inventário inicial do benchmark; nem todas são comparáveis ou executáveis. |
| Pares OD positivos e suportados | 21 | Denominador efetivo da comparação direcional. |
| Células puladas antes da execução | 15 | Seis self-pairs e nove linhas rodoviárias zero ou não positivas; não são falhas do modelo. |
| Pares com acordo direcional | 21 de 21 | Workbook e CabotageLens favorecem cabotagem/multimodal em emissões frente ao road-only. |
| Classificação rastreada atual | 21 `same_direction_large_gap` | Apoio direcional cauteloso com lacunas relevantes de magnitude. |

O denominador relevante, portanto, é o conjunto de 21 pares OD positivos e suportados, não a matriz inteira sem qualificação. Para esses pares, a concordância direcional mostra que o sinal modal geral não é produzido apenas internamente pelo protótipo. Ao mesmo tempo, a classificação `same_direction_large_gap` deve permanecer visível porque a lacuna de magnitude continua material.

Diferenças de distância, seleção de portos, lógica de serviço, carga, alocação, tratamento de port-ops/hoteling e fronteira ambiental podem explicar parte das lacunas. A concordância direcional não valida magnitude exata, não demonstra reprodução completa de Gustavo/Costa, não confirma disponibilidade de serviço e não transforma custos modelados em fretes ou tarifas de mercado. Consequentemente, o Batch 002 não cria um `headline_candidate`; ele sustenta `benchmark_supports_direction` e, ao mesmo tempo, preserva `benchmark_methodology_gap` e `benchmark_boundary_mismatch`.

### 6.6 Rerun Supabase/cache como verificação de estabilidade computacional

O rerun Supabase/cache testou uma hipótese operacional específica do Batch 002: se a diferença de magnitude entre o workbook Gustavo/Costa e o CabotageLens, especialmente no lado rodoviário, poderia ser explicada por instabilidade de provedor de rota, leitura de cache ou escrita de cache. Essa verificação não buscou recalibrar o modelo nem forçar aproximação numérica ao benchmark; seu objetivo foi separar instabilidade computacional de diferenças metodológicas mais profundas.

No rerun, as distâncias rodoviárias vieram apenas de cache. O artefato consolidado registra que a conexão e a leitura/escrita de cache Supabase funcionaram, que as pernas rodoviárias necessárias foram atendidas por registros existentes e que não houve necessidade de novas escritas de distância por provedor.

| Verificação do rerun | Resultado observado | Interpretação |
| --- | --- | --- |
| Fonte de distância rodoviária | Distâncias rodoviárias em cache | Reduz a hipótese de instabilidade por chamada em tempo real ao provedor. |
| `route-cache hits` | 63 | As 21 pernas diretas, 21 pernas de acesso inicial e 21 pernas de acesso final foram atendidas por cache. |
| `route-cache misses` | 0 | Não houve lacuna de cache rodoviário no rerun. |
| Escritas de distância por provedor | 0 | O rerun não dependeu de novas distâncias de provedor. |
| Falhas de leitura/escrita de cache | 0 | Não houve evidência de falha operacional de cache no lote. |
| Diferença média/mediana de emissões rodoviárias | 201,0%/150,5% -> 199,8%/149,3% | A mudança agregada foi pequena; a lacuna permanece. |

Essa estabilidade reduz a probabilidade de que a grande lacuna rodoviária do Batch 002 seja explicada principalmente por ruído de provedor, falha de cache ou variação de rota entre execuções. A evidência aponta para uma leitura mais conservadora: a diferença deve ser investigada sobretudo como diferença de método, fronteira, parâmetro, carga, alocação ou base de distância.

Ao mesmo tempo, estabilidade de cache não valida magnitudes exatas. *Cache hits* indicam que o processo reaproveitou entradas rastreáveis, mas não provam que a rota representa disponibilidade comercial, serviço contratado, tarifa praticada, frequência de escala ou viabilidade operacional. O uso seguro dessa camada é `benchmark_methodology_gap`: ela fortalece a auditabilidade do benchmark, mas não encerra os desencontros com Gustavo/Costa.

### 6.7 Reconciliação rodoviária como diagnóstico de premissas

A reconciliação rodoviária do Batch 002 deve ser lida como diagnóstico de alinhamento com benchmark, não como atualização do modelo de linha de base do CabotageLens. Depois que o rerun Supabase/cache reduziu a hipótese de instabilidade de rota, esta etapa testou quanto da lacuna de magnitude no lado rodoviário poderia ser explicado por diferenças de premissas de consumo de combustível e fator de emissão em relação à família Gustavo/Costa.

O diagnóstico manteve fixas as mesmas distâncias rodoviárias em cache do Batch 002 e aplicou, apenas para comparação, as premissas rodoviárias rastreadas no benchmark: `FDc = 0.28 L/km`, `FDe = 35.52 MJ/L` e `FDf = 86.5 gCO2eq/MJ`. A combinação desses valores gera o fator diagnóstico:

```text
0.28 L/km * 35.52 MJ/L * 86.5 gCO2eq/MJ / 1000 = 0.8602944 kg CO2eq/km
```

| Item diagnóstico | Valor ou observação | Limite de interpretação |
| --- | --- | --- |
| Premissa de consumo rodoviário | `FDc = 0.28 L/km` | Usada apenas no diagnóstico de alinhamento; não substitui o preset rodoviário da ferramenta. |
| Conteúdo energético do diesel | `FDe = 35.52 MJ/L` | Mantém o teste vinculado ao benchmark, não a uma nova calibração geral. |
| Fator de emissão | `FDf = 86.5 gCO2eq/MJ` | Fator de fronteira WTW do benchmark; não substitui a fronteira operacional TTW da linha de base. |
| Fator diagnóstico resultante | `0.8602944 kg CO2eq/km` | Sensibilidade de alinhamento, não fator de linha de base do CabotageLens. |
| Diferença média de emissões rodoviárias | `199,8%` -> `43,9%` | Redução substancial, mas não eliminação da lacuna. |
| Diferença mediana de emissões rodoviárias | `149,3%` -> `19,6%` | Indica que premissas rodoviárias explicam grande parte do desalinhamento. |

O efeito do teste é metodologicamente relevante: aplicar o fator diagnóstico às mesmas distâncias rodoviárias em cache reduz substancialmente a diferença média e mediana do lado road-only. Isso sugere que uma parte importante da divergência com o workbook está associada a premissas rodoviárias de consumo e emissão, e não apenas à rota ou ao cache.

Essa redução, porém, não resolve todo o problema. Permanecem lacunas associadas à base de distância rodoviária, construção de rota, carga por contêiner, alocação, fronteira TTW versus WTW/LCA, gases incluídos, escolhas do workbook e demais parâmetros ainda não reconciliados. O uso seguro dessa camada é `benchmark_supports_road_factor_explanation`: ela explica parte do desalinhamento, mas não valida magnitude calibrada, não recalibra o aplicativo e não substitui o modelo rodoviário de linha de base.

### 6.8 Categorias de uso no TF e passagem para os resultados

O fechamento do Capítulo 6 transforma as camadas anteriores em uma regra prática de uso da evidência. Um resultado executado não é automaticamente um resultado utilizável como conclusão principal do TF. A classificação atribuída a cada linha controla a força da afirmação permitida e o tipo de ressalva exigida antes que o Capítulo 7 apresente números, tabelas ou sínteses.

| Categoria de uso no TF | Significado | Uso permitido | Uso proibido |
| --- | --- | --- | --- |
| `headline_candidate` | Resultado apto a conclusão principal após validação e sensibilidade suficientes. | Nenhum uso atual; categoria reservada para evidência futura mais forte. | Promover qualquer caso atual a resultado principal robusto. |
| `sensitivity_discussion` | Linha planejada ou executada sob hipótese nomeada. | Discutir comportamento do modelo sob premissas documentadas. | Tratar como linha de base, validação robusta ou prova geral de vantagem modal. |
| `limitation_example` | Caso útil para mostrar limite de construção de rota ou interpretação. | Explicar limitações, como casos same-port. | Usar como desempenho normal de cabotagem ou conclusão numérica modal. |
| `excluded` | Caso fora da fronteira atual ou inadequado para conclusão numérica. | Justificar exclusão e limite metodológico. | Executar ou interpretar numericamente como evidência de resultado. |
| `reference_needed` | Falta evidência exata para referência, distância ou porto selecionado. | Registrar lacuna e requisito de evidência futura. | Declarar que a lacuna foi resolvida ou usar como resultado principal. |
| `methodology_blocked` | Falta decisão metodológica antes de execução defensável. | Apontar bloqueio e trabalho futuro. | Converter em conclusão numérica ou sensibilidade executada sem decisão rastreada. |
| `historical_diagnostic` | Registro histórico preservado para auditoria. | Mostrar evolução do método e motivação das correções. | Apresentar como resultado corrigido, validado ou calibrado. |
| `benchmark_supports_direction` | Benchmark externo aponta a mesma direção modal sob fronteiras distintas. | Sustentar consistência direcional cautelosa. | Alegar validação calibrada, reprodução exata ou superioridade universal. |
| `benchmark_supports_road_factor_explanation` | Diagnóstico rodoviário explica parte importante da lacuna road-only. | Discutir sensibilidade a premissas rodoviárias. | Substituir o modelo de linha de base pelo fator diagnóstico. |
| `benchmark_methodology_gap` | Diferenças de método permanecem relevantes. | Explicar lacunas de rota, carga, alocação, serviço e parâmetros. | Tratar o benchmark como referência absoluta plenamente reconciliada. |
| `benchmark_boundary_mismatch` | Fronteiras ambientais ou funcionais não coincidem totalmente. | Preservar cautela entre TTW, WTW, LCA, CO2 e CO2e. | Misturar fronteiras ou unidades como equivalentes. |
| `not_comparable` | Linha ou evidência sem comparabilidade suficiente na fronteira atual. | Usar como limitação ou justificativa de não execução. | Transformar em evidência numérica ou conclusão de desempenho. |

No estado atual dos artefatos rastreados, nenhum caso é um `headline_candidate`. As sensibilidades apoiam discussão condicionada, o Batch 002 apoia interpretação direcional com lacunas de magnitude, o rerun de cache fortalece a reprodutibilidade computacional e a reconciliação rodoviária explica parte do desalinhamento sem substituir a linha de base.

Esses controles também delimitam o que o trabalho não demonstra. Nenhuma linha atual prova superioridade universal da cabotagem, viabilidade comercial, disponibilidade de serviço, aceitação por transportador, disponibilidade de slot, frequência de escala, frete contratado, validação operacional ou reprodução calibrada de Gustavo/Costa. O Capítulo 7 deve herdar essas categorias integralmente: ele pode apresentar valores observados e inventários finais, mas deve manter cada evidência dentro do uso metodológico permitido neste capítulo.

## 7. Resultados

### 7.1 Inventário de evidências e categorias de uso

Este capítulo apresenta os resultados observados sob as categorias de evidência definidas no Capítulo 6. A pergunta aqui é descritiva: quais resultados foram obtidos, quais linhas ficaram planejadas, bloqueadas, excluídas ou não comparáveis, e qual uso cada grupo pode ter no TF. A interpretação logística, política ou decisória mais ampla fica para o Capítulo 8.

O inventário final combina cinco camadas de evidência. A tabela resume a escala de cada camada sem reproduzir integralmente os artefatos de validação.

| Camada de evidência | Escala no inventário | Situação no Capítulo 7 | Uso permitido |
| --- | ---: | --- | --- |
| Batch 001 histórico | 5 casos executados | Resultados preservados como `historical_diagnostic`. | Rastrear a evolução do método e os problemas originais de fallback/rota. |
| Batch 001B decisão metodológica | 8 linhas de decisão | Linhas record-only, planejadas, bloqueadas, excluídas ou preparadas para sensibilidade. | Separar limitação, lacuna, bloqueio e preparação de sensibilidade. |
| Sensibilidades executadas | 3 linhas executadas | Todas classificadas como `sensitive`. | Mostrar comportamento sob hipóteses documentadas, sem substituir a linha de base. |
| Batch 002 benchmark externo | 21 pares OD positivos e suportados | Todos classificados como `same_direction_large_gap` após o rerun. | Registrar apoio direcional externo com lacuna de magnitude. |
| Células Batch 002 não comparáveis | 15 células puladas | 6 self-pairs e 9 linhas rodoviárias zero ou não positivas. | Registrar limite de comparabilidade, não falha de execução nem evidência numérica. |

As categorias de uso que controlam este capítulo são as seguintes.

| Categoria | Evidência associada | Uso seguro no Capítulo 7 |
| --- | --- | --- |
| `headline_candidate` | Nenhum caso atual. | Registrar a ausência de resultado principal robusto. |
| `historical_diagnostic` | Saídas originais Batch 001. | Mostrar histórico e motivação das decisões posteriores, não resultado corrigido. |
| `sensitivity_discussion` / `sensitive` | Sensibilidades Batch 001B planejadas ou executadas. | Apresentar comportamento sob hipóteses nomeadas, não linha de base validada. |
| `limitation_example`, `excluded`, `reference_needed`, `methodology_blocked` | Linhas Batch 001B sem uso numérico principal. | Preservar limitação, exclusão, lacuna ou bloqueio sem inferência de desempenho modal. |
| `benchmark_supports_direction` | 21 pares OD positivos e suportados do Batch 002. | Usar como apoio direcional, sem validação calibrada de magnitude. |
| `benchmark_methodology_gap` / `benchmark_boundary_mismatch` | Diferenças remanescentes no rerun Batch 002. | Registrar divergência metodológica e de fronteira sem tratar o workbook como verdade absoluta. |
| `benchmark_supports_road_factor_explanation` | Reconciliação rodoviária com fator diagnóstico. | Tratar como diagnóstico de alinhamento, não recalibração do CabotageLens. |
| `not_comparable` | Células puladas ou evidência fora da fronteira comparável. | Registrar a exclusão da comparação, sem resultado numérico. |

Essas categorias preservam as fronteiras materiais dos resultados. Custos são estimativas modeladas por remessa, não tarifas, cotações, contratos ou fretes comerciais. Emissões são reportadas como CO2e operacional TTW, salvo indicação explícita em contrário; valores WTW, LCA ou CO2-only não devem ser misturados com a saída atual sem reconciliação metodológica. Nenhum grupo de evidência deste capítulo prova superioridade universal da cabotagem, disponibilidade de serviço ou viabilidade comercial.

### 7.2 Resultados históricos e decisões metodológicas Batch 001/001B

O Batch 001 preserva cinco resultados históricos executados. O Batch 001B não converteu essas linhas em validação final; ele reorganizou a evidência em registros de limitação, exclusão, lacuna de referência, bloqueio metodológico e preparação de sensibilidade. Essa separação é necessária para impedir que resultados históricos ou planejados sejam tratados como conclusões numéricas principais.

| Grupo | Casos | Quantidade | Classificação final | Uso no Capítulo 7 |
| --- | --- | ---: | --- | --- |
| Batch 001 histórico | `TF-VAL-001` a `TF-VAL-005` | 5 | `historical_diagnostic` | Preservar saídas iniciais e limitações de fallback/rota como diagnóstico histórico. |
| Limitação same-port | `TF-VAL-001B-001` | 1 | `limitation_example` | Registrar a cadeia Santos/Santos como limitação de construção de rota, sem conclusão modal. |
| Preparação de sensibilidade | `TF-VAL-001B-002`, `TF-VAL-001B-003B`, `TF-VAL-001B-005B` | 3 | `sensitivity_discussion` | Explicar de onde vieram as três sensibilidades executadas posteriormente. |
| Referência pendente | `TF-VAL-001B-003A`, `TF-VAL-001B-005A` | 2 | `reference_needed` | Manter Manaus/Fortaleza e Rio Grande/Recife selecionados como lacunas de distância exata. |
| Caso excluído | `TF-VAL-001B-004A` | 1 | `excluded` | Excluir a cadeia Angra dos Reis/Salvador do uso numérico atual. |
| Bloqueio metodológico | `TF-VAL-001B-004B` | 1 | `methodology_blocked` | Registrar que Brasília/Salvador ainda depende de decisão defensável de porto alternativo. |

O resultado importante desta camada é classificatório. O Batch 001 mostra onde a primeira execução produziu valores sob fontes frágeis ou escolhas de rota problemáticas; o Batch 001B mostra quais dessas linhas puderam virar sensibilidade, quais ficaram bloqueadas e quais devem permanecer apenas como limitação ou exclusão. Nenhuma linha dessa camada é `headline_candidate`, e nenhuma linha planejada do Batch 001B deve ser lida como execução numérica.

### 7.3 Resultados das sensibilidades executadas

Foram executadas três linhas de sensibilidade do Batch 001B: `TF-VAL-001B-SENS-002-REFDIST`, `TF-VAL-001B-SENS-003B-ALTPECEM` e `TF-VAL-001B-SENS-005B-ALTSUAPE`. A tabela apresenta apenas os valores já rastreados nos artefatos de validação e mantém a classificação de cada linha como `sensitive`.

| Caso | Papel da sensibilidade | Portos forçados | Custo modelado rodoviário (BRL/remessa) | Custo modelado multimodal (BRL/remessa) | Emissões rodoviárias (kg CO2e/remessa; fronteira operacional TTW) | Emissões multimodais (kg CO2e/remessa; fronteira operacional TTW) | Classificação |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Distância de referência Santos/Manaus | Santos -> Manaus | 18.456,45 | 1.263,50 | 6.961,76 | 1.104,67 | `sensitive` |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Porto alternativo Pecém | Manaus -> Pecém | 26.391,03 | 727,33 | 9.989,83 | 573,48 | `sensitive` |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Porto alternativo Suape | Rio Grande -> Suape | 18.121,99 | 2.122,38 | 7.013,27 | 1.127,46 | `sensitive` |

Nos três cenários de sensibilidade executados, a alternativa multimodal apresentou menor custo modelado e menor CO2e operacional TTW do que a alternativa rodoviária direta. Essa afirmação vale apenas para essas hipóteses nomeadas de distância ou porto alternativo, e cada linha continua `sensitive`, não linha de base validada nem `headline_candidate`.

A diferença entre os custos rodoviários e multimodais deve ser lida dentro da fronteira de custo do modelo. Na alternativa rodoviária direta, a remessa é atribuída a um veículo rodoviário dedicado; na alternativa multimodal, a perna marítima distribui custos e consumo de navio pela capacidade/carga representada no cenário. Essa estrutura explica por que o custo multimodal modelado pode ficar muito menor, mas não transforma o valor em frete comercial, tarifa portuária completa ou cotação contratável.

O caso Santos/Manaus é uma sensibilidade de distância de referência. Ele não valida automaticamente todos os casos que dependem de `haversine_fallback`. As linhas Manaus/Pecém e Rio Grande/Suape são sensibilidades de porto alternativo: Pecém não valida Porto de Fortaleza, e Suape não valida Porto do Recife.

### 7.4 Resultados do benchmark externo Batch 002

O Batch 002 registra o benchmark externo Gustavo/Costa como camada comparativa, não como verdade de referência. A função desta seção é apresentar o inventário e a classificação do lote; as causas e implicações das diferenças de magnitude são discutidas no Capítulo 8.

| Métrica | Valor observado | Classificação ou interpretação |
| --- | ---: | --- |
| Células da matriz do workbook parseadas | 36 | Inventário completo da matriz 6 x 6 lida para o benchmark. |
| Pares OD positivos e suportados | 21 | Linhas elegíveis para comparação na base reportada do workbook. |
| Execuções bem-sucedidas | 21 | Todos os pares positivos suportados foram processados. |
| Células puladas antes da execução | 15 | 6 self-pairs e 9 linhas rodoviárias zero ou não positivas; `not_comparable`, não falhas de modelo. |
| Alinhamento direcional | 21/21 | Workbook e CabotageLens apontam emissões menores para cabotagem/multimodal do que para rodoviário direto. |
| Classificação após rerun | 21 x `same_direction_large_gap` | Há concordância de direção, mas lacuna material de magnitude. |
| Validação calibrada de magnitude | 0 linhas | O lote não sustenta reprodução exata nem calibração contra o workbook. |

O resultado central do Batch 002 é direcional: nos 21 pares OD positivos e suportados, o workbook e o CabotageLens apontam a mesma direção modal de emissões. Essa concordância deve aparecer sempre junto da classificação `same_direction_large_gap`, porque a magnitude permanece divergente e impede tratar o benchmark como calibração, reprodução exata, validação plena de rota ou prova de premissas internas do workbook.

As 15 células puladas permanecem fora da comparação por critérios explícitos de comparabilidade. Elas não devem ser tratadas como falha do CabotageLens, mas também não devem ser convertidas em evidência favorável ou desfavorável. O Batch 002, portanto, não cria `headline_candidate`; ele fornece apoio externo de direção dentro de um conjunto comparável e limitado.

### 7.5 Resultados do rerun/cache e da reconciliação rodoviária

O rerun Supabase/cache e a reconciliação rodoviária qualificam o resultado do Batch 002. O primeiro testa se a lacuna de magnitude poderia ser explicada principalmente por instabilidade de provedor ou cache. A segunda testa, apenas como diagnóstico, quanto a lacuna de emissões rodoviárias observada seria reduzida ao aplicar o fator rodoviário da família Gustavo/Costa às mesmas distâncias cacheadas.

| Verificação | Resultado observado | Classificação | Uso seguro |
| --- | --- | --- | --- |
| Rerun Supabase/cache | 21/21 pares positivos executados; 63 route-cache hits; 0 misses; 0 escritas de distância pelo provedor; 0 falhas de leitura/escrita. | Evidência de rastreabilidade computacional. | Mostrar que o rerun reutilizou distâncias cacheadas, sem validar magnitude ou serviço comercial. |
| Divergência percentual de emissões rodoviárias, média/mediana | 201.0% / 150.5% -> 199.8% / 149.3%. | `benchmark_methodology_gap` | Registrar que cache/provedor é improvável como causa principal da lacuna road-only. |
| Divergência percentual de emissões multimodais, média/mediana | 53.5% / 52.9% -> 60.8% / 63.7%. | `benchmark_boundary_mismatch` | Registrar que a divergência multimodal residual permanece metodológica e de fronteira. |
| Fator rodoviário diagnóstico | `0.8602944 kgCO2e/km`, aplicado às distâncias rodoviárias cacheadas. | `benchmark_supports_road_factor_explanation` | Usar apenas como sensibilidade de alinhamento com o benchmark, não como novo fator de linha de base. |
| Divergência percentual de emissões rodoviárias após diagnóstico, média/mediana | 199.8% / 149.3% -> 43.9% / 19.6%. | Diagnóstico de premissa rodoviária. | Dizer que a lacuna observada foi reduzida e que o resultado é sensível às premissas rodoviárias. |

O rerun fortalece a reprodutibilidade computacional do Batch 002, mas não valida a magnitude exata das emissões. A divergência rodoviária agregada mudou pouco após a troca para distâncias cacheadas, e a divergência multimodal não melhorou. Assim, o resultado do rerun é compatível com a leitura de que as lacunas remanescentes são metodológicas ou de fronteira, não simples instabilidade de cache.

A reconciliação rodoviária reduziu a lacuna observada no lado road-only, mas não a eliminou. O resultado indica sensibilidade forte a premissas de consumo e fator de emissão rodoviários, sem recalibrar o CabotageLens, sem substituir o modelo rodoviário de linha de base e sem transformar o workbook em referência normativa. O fator `0.8602944 kgCO2e/km` permanece diagnóstico, não coeficiente operacional TTW da aplicação.

### 7.6 Síntese dos resultados classificados e transição para a discussão

O Capítulo 7 não produz uma conclusão universal sobre cabotagem. Ele organiza resultados observados e classificações de uso. A síntese segura é que há evidência de sensibilidade favorável em três cenários nomeados, apoio direcional externo no Batch 002, estabilidade computacional no rerun e redução diagnóstica da lacuna rodoviária quando se aplica uma premissa de benchmark. Nenhum desses grupos, isolado ou em conjunto, autoriza validação calibrada, superioridade universal ou uso comercial direto.

| Grupo de evidência | Observação obtida | Classificação | Uso seguro | O que não sustenta |
| --- | --- | --- | --- | --- |
| Batch 001 | 5 casos históricos executados com limitações de referência/rota. | `historical_diagnostic` | Rastrear a origem das decisões metodológicas. | Resultado corrigido ou validação final. |
| Batch 001B | 8 linhas de decisão, incluindo limitação, exclusão, lacuna, bloqueio e preparação de sensibilidade. | `limitation_example`, `excluded`, `reference_needed`, `methodology_blocked`, `sensitivity_discussion` | Controlar quais linhas podem ou não ser usadas numericamente. | Execução numérica de todas as linhas planejadas. |
| Sensibilidades executadas | 3 linhas `sensitive`, todas com multimodal menor em custo modelado e CO2e operacional TTW. | `sensitive` | Resultado de sensibilidade sob hipóteses documentadas. | Linha de base robusta, validação do porto original ou frete comercial. |
| Batch 002 | 21/21 pares comparáveis alinhados em direção, todos `same_direction_large_gap`. | `benchmark_supports_direction` | Apoio externo direcional com lacuna de magnitude. | Reprodução exata, calibração ou workbook como verdade de referência. |
| Rerun Supabase/cache | 63 cache hits, 0 misses e divergências agregadas ainda grandes. | `benchmark_methodology_gap` | Evidência de estabilidade computacional e rastreabilidade. | Validação de magnitude, rota comercial ou serviço disponível. |
| Reconciliação rodoviária | Divergência rodoviária média/mediana reduzida para 43.9% / 19.6% no diagnóstico. | `benchmark_supports_road_factor_explanation` | Indicar sensibilidade a premissas rodoviárias. | Recalibração da aplicação ou substituição da linha de base. |
| Resultado principal robusto | 0 casos. | Sem `headline_candidate` atual. | Manter leitura direcional, diagnóstica e condicionada. | Superioridade universal da cabotagem. |

Com essa classificação, o capítulo responde ao que foi obtido e como cada evidência deve ser usada. O Capítulo 8 parte desses resultados para discutir significado, lacunas metodológicas, relação com a literatura, implicações para uso do CabotageLens e limites para trabalho futuro, sem alterar a classificação conservadora apresentada aqui.

## 8. Discussão

### 8.1 Pergunta interpretativa e fronteiras de leitura

O Capítulo 8 responde a uma pergunta diferente daquela tratada no Capítulo 7: qual é o significado da evidência sob as fronteiras adotadas? O capítulo anterior registrou resultados, categorias de uso e valores observados; a discussão interpreta o alcance desses achados sem acrescentar novas linhas, recalcular cenários ou promover classificações além daquelas já rastreadas.

A leitura defensável é deliberadamente estreita. As sensibilidades executadas, o benchmark Gustavo/Costa, o rerun Supabase/cache e a reconciliação rodoviária tornam a evidência mais interpretável, mas não mudam sua natureza. O conjunto atual sustenta discussão direcional, metodológica e condicionada; não sustenta validação calibrada, conclusão comercial, disponibilidade operacional real ou superioridade universal da cabotagem. Nenhum resultado corrente deve ser tratado como `headline_candidate`.

Essa separação é importante para a arquitetura do relatório. O Capítulo 7 mostra o que foi observado; o Capítulo 8 discute por que esses achados importam; o Capítulo 9 detalha as limitações que impedem leituras mais fortes; e o Capítulo 10 poderá concluir sem transformar evidência condicionada em afirmação universal.

### 8.2 Por que a comparação rota-a-rota e porta a porta importa

A principal implicação metodológica do CabotageLens é que a comparação modal não pode ser reduzida a caminhão contra navio em trechos isolados. A alternativa multimodal combina acesso rodoviário ao porto, perna marítima, operações portuárias quando modeladas e acesso rodoviário final. Assim, o resultado de custo modelado e CO2e operacional TTW emerge da cadeia porta a porta, não de uma propriedade abstrata da cabotagem.

Essa leitura é coerente com a literatura de short sea shipping e mudança modal, que trata a vantagem marítima como dependente de corredor, acesso terrestre, utilização, serviço, frequência, confiabilidade e custo total [shortsea2019] [modalshiftreview2020]. O papel da literatura aqui é interpretativo: ela ajuda a explicar por que uma comparação rota-a-rota é necessária, mas não substitui as categorias de validação do projeto nem valida numericamente qualquer corredor brasileiro específico.

O valor analítico da fronteira porta a porta está em impedir duas simplificações. A primeira seria favorecer artificialmente a cabotagem ao ignorar acessos terrestres e portos. A segunda seria descartar a cabotagem por comparar apenas médias nacionais ou trechos genéricos. O CabotageLens se posiciona entre esses extremos: compara cenários completos sob premissas explícitas e obriga cada interpretação a carregar suas escolhas de rota, porto, distância, custo e emissão.

### 8.3 Corredores, portos e proveniência da distância marítima

Os resultados precisam ser lidos por corredor porque porto e distância marítima mudam o significado da comparação. Alterar um porto não muda apenas um rótulo; muda as pernas rodoviárias de acesso, a perna marítima, a coerência operacional da cadeia e a relação entre o cenário modelado e o caso que se deseja discutir. Por isso, sensibilidades com Pecém ou Suape podem ser úteis para entender comportamento sob hipótese alternativa, mas não validam silenciosamente Porto de Fortaleza ou Porto do Recife.

A proveniência da distância marítima cumpre função semelhante. Uma distância com referência rastreada permite uma leitura mais forte do que uma distância de triagem, enquanto `haversine_fallback` preserva histórico e diagnóstico, mas não deve ser tratado como evidência robusta de rota navegável. O caso `same-port` também tem valor interpretativo porque mostra uma fronteira da lógica de seleção: quando origem e destino marítimos coincidem, o registro pode documentar aviso, exclusão ou limitação de rota, mas não desempenho normal da cabotagem.

Essa disciplina muda a pergunta da discussão. Em vez de perguntar se "a cabotagem" foi superior em sentido geral, o relatório deve perguntar o que acontece quando uma cadeia específica, com portos específicos e distância de proveniência conhecida, é comparada com a rota rodoviária direta sob a mesma unidade funcional. A resposta continua condicional, mas é tecnicamente mais defensável.

### 8.4 Benchmark Gustavo/Costa: apoio direcional, não calibração

O benchmark Gustavo/Costa é uma camada importante para o TF porque introduz uma referência externa ao próprio CabotageLens. No relatório final, ele pode receber tratamento mais amplo do que no artigo técnico, pois ajuda a explicar ao leitor da banca como o modelo se comporta diante de um comparador familiar ao contexto da pesquisa. Ainda assim, seu papel deve permanecer subordinado à contribuição principal do trabalho: o framework auditável, não a reprodução do workbook.

O significado seguro do Batch 002 é apoio direcional com lacunas de magnitude. Nos pares comparáveis, o workbook e o CabotageLens apontam na mesma direção modal de emissões, mas a classificação `same_direction_large_gap` preserva que a magnitude não foi calibrada. Isso não é uma falha a esconder nem uma prova de que o workbook seja verdade absoluta. É evidência de que os dois artefatos compartilham um sinal interpretativo, enquanto permanecem separados por fronteiras, premissas e métodos ainda não reconciliados.

| Camada de evidência | Significado para a discussão | Leitura que deve ser evitada |
| --- | --- | --- |
| Benchmark Gustavo/Costa | Acrescenta contraste externo e apoio direcional nas linhas comparáveis. | Tratar o workbook como ground truth ou reprodução calibrada. |
| Rerun Supabase/cache | Reduz a plausibilidade de instabilidade computacional como explicação principal da lacuna. | Converter estabilidade de cache em validação de rota, serviço ou magnitude. |
| Reconciliação rodoviária | Mostra que premissas rodoviárias explicam parte relevante da lacuna road-only. | Substituir o baseline do CabotageLens pelo fator diagnóstico. |
| Lacunas remanescentes | Tornam visíveis diferenças de distância, veículo, carga, alocação, porto, serviço, port-ops/hoteling e fronteira ambiental. | Fechar a validação como se as diferenças já estivessem reconciliadas. |

A discussão deve explicar essas lacunas de forma causal, mas sem inventar precisão. No lado rodoviário, a diferença pode estar associada a base de distância, consumo, fator de emissão, veículo, carga e alocação. No lado multimodal, pode envolver distância marítima, seleção de portos, lógica de serviço, port-ops/hoteling, alocação por contêiner e fronteira ambiental. A reconciliação rodoviária torna parte do desvio mais inteligível, mas não resolve a comparação completa nem autoriza recalibrar o aplicativo.

### 8.5 Fronteiras econômica, ambiental e portuária na interpretação

As fronteiras de custo e emissão não são apenas ressalvas defensivas; elas definem o tipo de significado que os resultados podem ter. Custos modelados permitem comparar componentes representados sob a mesma lógica de cenário, mas não são fretes comerciais, tarifas contratadas ou evidência de preço de mercado. A literatura de competitividade e super-rede ajuda a mostrar que a decisão real inclui frequência, inventário, confiabilidade, margens e estrutura de serviço [competitiveness2024], mas esses elementos não entram como validação automática dos custos do CabotageLens.

No mesmo sentido, CO2e operacional TTW não deve ser lido como WTW ou LCA. Quando aplicado à cadeia multimodal, o rótulo operacional TTW deve ser entendido de forma modalmente específica: Tank-to-Wheel nas pernas rodoviárias e Tank-to-Wake na perna marítima. Fontes que discutem WTW, LCA, combustíveis alternativos ou CO2-only são relevantes para enquadrar a fronteira e trabalhos futuros [decarb2024] [maritimelca2024], mas não corrigem nem substituem os resultados operacionais atuais sem reconciliação explícita de unidade, gases e escopo.

As operações portuárias reforçam essa leitura de fronteira. Hoteling e componentes portuários importam porque a cadeia multimodal não termina na distância marítima; há consumo associado à permanência e operação do navio no porto [berth2009] [shipops2022]. Ao mesmo tempo, incluir esses componentes como aproximações modeladas não transforma o estudo em inventário terminal-específico nem em análise completa de qualidade do ar. A interpretação segura é reconhecer que portos e berços afetam a comparação, mantendo-os como componentes condicionais dentro da fronteira declarada.

### 8.6 Valor prático do CabotageLens como triagem

O valor prático do CabotageLens está em estruturar uma triagem técnica, não em decidir uma contratação. A ferramenta permite comparar cenários, observar como escolhas de porto e distância alteram o resultado, identificar dependência de premissas frágeis e separar resultados executados, sensibilidades, diagnósticos, bloqueios e exemplos de limitação. Isso ajuda a formular perguntas melhores antes de buscar evidência comercial ou operacional externa.

Essa utilidade é mais forte quando o resultado é lido junto com seus metadados. Um cenário com distância marítima de referência comunica algo diferente de um cenário com `haversine_fallback`; uma sensibilidade com porto alternativo comunica algo diferente de um baseline validado; um benchmark direcional com lacuna de magnitude comunica algo diferente de uma calibração. A contribuição prática está justamente em preservar essas diferenças, não em esconder a incerteza atrás de um número final.

Assim, o CabotageLens pode apoiar triagem de corredores, comparação técnica entre alternativas, exposição de premissas e identificação de lacunas para validação futura com operadores, terminais ou bases comerciais. Ele não deve ser apresentado como cotador de frete, motor de booking, otimizador nacional de super-rede ou prova de disponibilidade de serviço. A passagem de um cenário favorável para uma decisão logística real exige evidência externa que este TF não pretende substituir.

### 8.7 Contribuição metodológica do framework auditável

A contribuição metodológica do trabalho está na combinação de cálculo, rastreabilidade e controle de inferência. O CabotageLens não entrega apenas um valor de custo ou emissão; ele organiza uma cadeia de evidências que inclui construção de rota, seleção de portos, fonte de distância marítima, fronteira de custo, fronteira de emissão, avisos de qualidade, classificação de validação, sensibilidades e benchmark externo.

Essa estrutura torna a discussão mais forte porque transforma incertezas em objetos explícitos de análise. Um resultado favorável pode ser reconhecido como favorável sem ser promovido indevidamente; uma lacuna de magnitude pode ser discutida como diferença metodológica sem ser tratada como erro opaco; uma sensibilidade pode informar comportamento do modelo sem substituir o caso-base; e uma referência externa pode apoiar direção sem virar verdade absoluta.

Com isso, o Capítulo 8 deve encerrar em uma posição analítica, não conclusiva em excesso: a evidência atual mostra que o framework permite comparar cenários de forma auditável e interpretar resultados sob fronteiras controladas. O Capítulo 9 detalha as limitações que ainda impedem transformar essa estrutura em validação operacional, comercial ou universal.

## 9. Limitações

### 9.1 Função das limitações e condições de uso

As limitações deste trabalho delimitam as condições de interpretação dos resultados. Elas não reduzem o valor do CabotageLens; ao contrário, reforçam sua contribuição principal: um framework auditável para comparar cenários rodoviários e rodoviário-cabotagem-rodoviário sob fronteiras explícitas de rota, custo, emissões, proveniência e validação.

O Capítulo 9 deve ser lido como controle de sobreafirmação. Ele separa o que o protótipo sustenta, o que permanece condicionado e o que ainda exige evidência externa. A interpretação segura dos resultados atuais é cenário-dependente, direcional e diagnóstica: sensibilidades mostram comportamento do modelo sob hipóteses rastreadas; o benchmark Gustavo/Costa apoia consistência direcional, mas não valida magnitude calibrada; e diagnósticos explicam lacunas sem substituir a linha de base.

| Fronteira | Condição de uso no TF |
| --- | --- |
| Ambiental | Emissões como TTW CO2e operacional, sem inferir WTW, LCA, CO2-only ou inventário completo de poluentes. |
| Econômica | Custos como estimativas modeladas, não como fretes comerciais, tarifas, contratos ou recomendação de compra. |
| Operacional | Rotas como cenários de comparação, não como prova de serviço, frequência, slot, terminal, agenda ou booking. |
| Rota e porto | Portos selecionados, portos forçados, portos alternativos, distância marítima e casos same-port condicionam a força da evidência. |
| Validação | Sensibilidade, benchmark, rerun e reconciliação têm papéis distintos e não devem ser convertidos em validação única. |
| Fontes | Literatura e artefatos externos podem contextualizar limites e trabalhos futuros, mas não substituem parâmetros ou resultados rastreados. |

Com essas fronteiras, o Capítulo 9 prepara a passagem para o Capítulo 10. As conclusões podem afirmar a contribuição metodológica do CabotageLens sem transformar evidência parcial em validação comercial, operacional ou universal.

### 9.2 Fronteira ambiental: TTW operacional, CO2e e limites de ciclo de vida

A fronteira ambiental corrente é operacional. Salvo indicação explícita em contrário, o CabotageLens reporta emissões TTW CO2e associadas às pernas e aos componentes modelados no cenário. Para as pernas rodoviárias, essa leitura corresponde às emissões diretas do uso de combustível no veículo; para a perna marítima, corresponde às emissões diretas da combustão a bordo e aos componentes operacionais explicitamente incluídos.

Essa fronteira deixa fora etapas a montante e de ciclo de vida. Produção, refino, transporte e distribuição de combustíveis, fabricação e manutenção de veículos ou navios, construção de infraestrutura, fim de vida dos ativos, combustíveis alternativos, emissões locais completas em porto e avaliação de qualidade do ar pertencem a fronteiras mais amplas, como WTT, WTW ou LCA. Esses temas podem contextualizar a discussão e orientar trabalhos futuros, mas não substituem a linha de base operacional atual.

Também há uma limitação de rastreabilidade da métrica CO2e quando o resultado é comparado a fontes externas. CO2e depende dos gases incluídos, dos fatores de emissão, da regra de equivalência climática e da fronteira adotada. Assim, literatura ou benchmarks que reportam CO2 isolado, CO2e sob outro escopo, WTW ou LCA não podem calibrar ou validar diretamente os resultados TTW CO2e do CabotageLens sem reconciliação explícita de unidade funcional, base de carga, gases incluídos, fatores e fronteira ambiental.

As operações portuárias e o *hoteling* seguem a mesma disciplina. Quando esses componentes aparecem no cenário, eles são parcelas operacionais modeladas, não inventário terminal-específico completo. A interpretação deve evitar dois extremos: ignorar que operações em porto podem alterar a comparação ou tratá-las como medição completa de produtividade, energia auxiliar, permanência em berço, dispersão atmosférica ou impacto local à saúde.

### 9.3 Fronteira econômica: custo modelado, alocação e ausência de frete comercial

A fronteira econômica do CabotageLens é de custo modelado. Os valores em BRL são saídas de cenários definidos por rota, portos, carga, componentes habilitados, parâmetros e regras de alocação. Eles servem para comparação metodológica entre alternativas sob o mesmo enquadramento, mas não representam cotação de mercado, tarifa praticada, contrato negociado, proposta de armador, booking ou recomendação de contratação.

Essa limitação é especialmente importante na alternativa multimodal. A perna marítima pode distribuir custo, combustível e emissões por capacidade compartilhada, enquanto a alternativa rodoviária direta representa o veículo dedicado à remessa modelada. Essa diferença de alocação é parte do método e ajuda a explicar por que custos ou emissões multimodais podem parecer muito baixos em alguns cenários. Ela não deve ser interpretada como erro automático do modelo, nem como prova de frete comercial mais barato.

O custo modelado também não incorpora, de forma completa, margem comercial, negociação, seguro, demurrage, detention, inventário em trânsito, confiabilidade, variação de prazo, risco operacional, taxas locais, tarifas terminal-específicas, disponibilidade de slot ou aceitação de carga. Esses elementos pertencem a uma avaliação comercial ou operacional posterior. Portanto, um resultado favorável em custo modelado pode indicar uma hipótese que merece investigação, mas não encerra a análise econômica de mercado.

### 9.4 Fronteira operacional: serviço, agenda, terminais e super-rede

O CabotageLens constrói cenários determinísticos e auditáveis; ele não constrói um plano operacional de transporte. Um porto selecionado ou forçado funciona como nó metodológico do experimento, não como prova de que existe linha de cabotagem disponível, janela de navio, aceitação terminal, cutoff documental, pátio, capacidade, slot ou operador disposto a executar a cadeia.

A decisão real de mudança modal depende de serviço, frequência, horários, confiabilidade, transit time, coordenação entre operadores, risco de atraso, capacidade disponível, aceitação de carga, integração entre trechos terrestres e marítimos e condições contratuais. Esses fatores são reconhecidos como relevantes, mas não são validados pelo protótipo atual. Por isso, uma rota favorável no modelo deve ser lida como comparação condicionada, não como autorização operacional.

O modelo também não resolve uma super-rede multimodal nacional. Ele não escolhe simultaneamente entre múltiplas linhas, operadores, transbordos, frequências, capacidades, conexões, tempos de espera e custos comerciais concorrentes. Essa fronteira preserva a utilidade do CabotageLens como instrumento de triagem e auditoria de cenários, sem transformá-lo em otimizador de rede, plataforma de cotação ou sistema de contratação logística.

### 9.5 Fronteira de rota: portos, distâncias, fallback e same-port

A interpretação dos resultados depende da rota construída. A alternativa rodoviário-cabotagem-rodoviário combina acesso terrestre, portos, distância marítima, componentes portuários e acesso final. Quando a distância marítima tem referência exata para o par de portos do cenário, a leitura é mais forte; quando depende de `haversine_fallback`, referência indireta ou ausência de evidência exata, o caso deve permanecer como lacuna, diagnóstico ou sensibilidade.

As lacunas selecionadas continuam relevantes: Manaus -> Porto de Fortaleza e Porto do Rio Grande -> Porto do Recife permanecem sem evidência suficiente de distância marítima exata nos artefatos rastreados atuais. Pecém pode ser discutido como sensibilidade de porto alternativo para a região de Fortaleza, mas não valida Porto de Fortaleza. Suape pode ser discutido como sensibilidade de porto alternativo para a região de Recife, mas não valida Porto do Recife. A troca de porto altera acessos, terminal, distância marítima, fronteira de cenário e leitura operacional.

Casos same-port, como Santos/Santos, não representam desempenho normal de cabotagem, porque não há perna marítima substantiva entre portos distintos. Eles são úteis como controle interpretativo, aviso de qualidade ou exemplo de exclusão, mas não sustentam comparação modal principal. Do mesmo modo, casos excluídos ou bloqueados, como a cadeia conteinerizada com Angra dos Reis ou decisões de porto ainda não documentadas, não devem ser reaproveitados como resultado numérico.

Essa fronteira de rota controla a leitura das sensibilidades. Uma sensibilidade executada mostra o comportamento do modelo sob uma hipótese rastreada de distância ou porto; ela não elimina a lacuna do caso selecionado original, não transforma fallback em referência robusta e não comprova serviço, terminal, slot, booking ou frete contratado.

### 9.6 Fronteira de validação: sensibilidades, Gustavo/Costa e reconciliação

A validação atual é composta por camadas, não por um veredito único. Batch 001 preserva diagnóstico histórico; Batch 001B organiza decisões metodológicas e sensibilidades; Batch 002 acrescenta benchmark externo Gustavo/Costa; o rerun Supabase/cache verifica estabilidade computacional; e a reconciliação rodoviária explica parte da lacuna de magnitude. Cada camada aumenta a rastreabilidade, mas nenhuma transforma os resultados atuais em `headline_candidate` robusto.

As sensibilidades executadas mostram comportamento sob hipóteses documentadas. Elas podem apoiar discussão sobre direção e sensibilidade de rota, mas não substituem baseline validado, não validam os portos originalmente selecionados e não provam disponibilidade operacional ou comercial. Seu papel é manter visível como distância marítima, porto alternativo e fronteira de cenário afetam a interpretação.

O benchmark Gustavo/Costa é valioso porque confronta o CabotageLens com uma referência externa familiar ao mesmo problema amplo de comparação entre rodovia e cabotagem. Contudo, o workbook/paper não foi reconstruído integralmente em sua lógica interna de distância, rota, serviço, porto, alocação de carga, tratamento de operações portuárias e fronteira ambiental. A concordância direcional observada nos pares comparáveis apoia consistência qualitativa, mas não valida magnitude calibrada nem reprodução exata.

A classificação `same_direction_large_gap` deve continuar visível porque comunica a diferença entre direção e magnitude. As células puladas ou não comparáveis do workbook também não são falha automática do modelo; elas indicam limites de comparabilidade entre artefatos. O rerun com Supabase/cache reduz a hipótese de instabilidade computacional como explicação principal da lacuna, mas não valida serviço, rota comercial, preço, terminal ou magnitude.

A reconciliação rodoviária com `0.8602944 kgCO2e/km` permanece diagnóstico de alinhamento com o benchmark, não recalibração do CabotageLens. Ela ajuda a explicar parte do mismatch rodoviário, mas não substitui o modelo rodoviário de linha de base, não altera os resultados do aplicativo e não autoriza misturar TTW, WTW, LCA, CO2 e CO2e. A lacuna residual continua metodologicamente relevante e deve ser atribuída a diferenças ainda não reconciliadas, não a validação fechada.

### 9.7 Fontes, literatura e generalização

A literatura usada no TF fortalece o enquadramento acadêmico, mas tem função controlada. Ela pode contextualizar a cabotagem brasileira, explicar barreiras de mudança modal, contrastar fronteiras ambientais, justificar cautela com custo comercial, orientar port ops e *hoteling*, ou apontar caminhos de trabalho futuro. Ela não deve ser convertida automaticamente em parâmetro, coeficiente, calibração, rota, porto, fator de emissão ou validação numérica do CabotageLens.

Essa regra evita substituições silenciosas. Valores WTW/LCA, HVO, fatores regionais de outro estudo, emissões CO2-only, margens comerciais, taxas, intensidades de navio, tempos de porto ou resultados de super-rede só poderiam entrar no modelo depois de uma decisão metodológica explícita, com unidade funcional, fronteira, base de carga, fonte, compatibilidade e implementação rastreadas. Sem essa cadeia, a literatura permanece como contexto, limitação, comparação ou agenda futura.

Por fim, os resultados do TF não devem ser generalizados para todos os corredores brasileiros. As conclusões são específicas por rota, cenário, carga, porto, distância, proveniência, fronteira econômica, fronteira ambiental e classificação de evidência. O trabalho pode concluir que o CabotageLens oferece uma estrutura auditável e academicamente útil para comparação de cenários; não pode concluir que a cabotagem seja universalmente superior, que custos modelados sejam fretes comerciais, que o benchmark Gustavo/Costa seja verdade de referência, ou que sensibilidades e literatura resolvam todas as lacunas de rota, validação, custo, emissões e operação.

## 10. Conclusões e trabalhos futuros

### 10.1 Conclusão principal

Este trabalho desenvolveu e documentou o CabotageLens como um framework computacional auditável, reprodutível e orientado por rota para comparar alternativas de transporte rodoviário direto e rodoviário-cabotagem-rodoviário em corredores brasileiros. A conclusão principal não é uma afirmação universal de superioridade da cabotagem. A contribuição central é mostrar que a comparação modal pode ser construída com unidade funcional explícita, cadeia porta a porta, proveniência de dados, fronteiras metodológicas declaradas e classificação conservadora da força da evidência.

Sob essa formulação, os resultados do CabotageLens devem ser lidos como estimativas de cenário. Custos permanecem custos modelados, não fretes comerciais, tarifas ou cotações. Emissões permanecem CO2e operacional TTW, não WTW nem LCA. A seleção de portos, a distância marítima, os acessos terrestres, os componentes portuários, os parâmetros de carga e a classificação de validação condicionam o alcance de cada conclusão.

Assim, o resultado mais defensável do TF é metodológico e computacional: o CabotageLens torna visíveis as hipóteses que normalmente ficam implícitas em uma comparação entre rodovia e cabotagem. A ferramenta não substitui validação comercial ou operacional, mas organiza uma base rastreável para discutir quando uma alternativa multimodal aparece promissora, quando a evidência é apenas sensível ou diagnóstica, e quais lacunas precisam ser fechadas antes de afirmações mais fortes.

### 10.2 Contribuição metodológica e computacional do CabotageLens

A contribuição do CabotageLens está na integração entre construção explícita de rotas, cálculo de custo modelado, estimativa de emissões operacionais TTW CO2e, preservação de proveniência e classificação de evidência. O framework separa a alternativa rodoviária direta da cadeia rodoviária-cabotagem-rodoviária, registra portos selecionados ou forçados, mantém a origem das distâncias e associa cada resultado ao cenário e aos parâmetros que o produziram.

Essa integração é importante porque a comparação modal depende de escolhas técnicas que alteram a interpretação. Distâncias marítimas com referência externa, matriz rastreada ou `haversine_fallback` não têm a mesma força. Portos alternativos, como Pecém ou Suape, podem ser úteis para sensibilidade, mas não validam silenciosamente Porto de Fortaleza ou Porto do Recife. Casos same-port, linhas bloqueadas, registros excluídos e resultados sensíveis têm valor acadêmico quando preservados como controles interpretativos, não como conclusões principais.

O valor do framework, portanto, não está apenas em gerar números de BRL e CO2e. Está em vincular esses números a uma trilha de auditoria: rota, porto, distância, fonte, parâmetro, aviso, categoria de uso e artefato de validação. Essa disciplina permite defender o trabalho sem transformar resultados condicionais em prova de viabilidade comercial, superioridade modal universal ou reprodução calibrada de um benchmark externo.

### 10.3 Alcance das evidências e interpretação segura

A evidência consolidada neste TF sustenta uma interpretação cautelosa, específica por corredor e dependente da fronteira adotada. As linhas históricas do Batch 001 permanecem como diagnóstico de evolução metodológica. O Batch 001B organiza decisões, bloqueios, lacunas e sensibilidades. As sensibilidades executadas mostram comportamento do modelo sob hipóteses rastreadas, mas não substituem baselines validados e não criam `headline_candidate`.

O Batch 002 acrescenta uma camada externa importante ao confrontar o CabotageLens com o workbook/paper Gustavo/Costa nos pares comparáveis. Esse benchmark é útil para a defesa acadêmica porque testa se o framework aponta a mesma direção modal em uma referência externa familiar ao tema. A leitura segura, porém, é direcional: Gustavo/Costa não é verdade absoluta, não foi reconstruído integralmente em suas premissas internas e não valida magnitude calibrada de emissões, custos, rotas, serviços, portos ou alocação.

O rerun Supabase/cache reforça a reprodutibilidade computacional ao reduzir a hipótese de instabilidade de provedor ou cache como causa principal das lacunas observadas. A reconciliação de fator rodoviário explica parte relevante da diferença no lado road-only, mas permanece diagnóstico de alinhamento com o benchmark. Ela não recalibra o CabotageLens, não substitui o modelo rodoviário de linha de base e não altera a fronteira operacional TTW do trabalho.

As limitações apresentadas no Capítulo 9, portanto, não enfraquecem a conclusão; elas definem seu uso correto. O TF pode concluir que o CabotageLens produz comparações rastreáveis, auditáveis e academicamente defensáveis sob fronteiras explícitas. Não pode concluir que a cabotagem seja universalmente superior, que custos modelados sejam fretes comerciais, que emissões TTW CO2e sejam WTW/LCA, que sensibilidades sejam resultados robustos de baseline ou que Gustavo/Costa tenha sido plenamente reproduzido.

### 10.4 Agenda prioritária de trabalhos futuros

Os trabalhos futuros devem ampliar o CabotageLens sem apagar a disciplina de fronteira que tornou o TF defensável. No eixo ambiental, a prioridade é separar claramente qualquer expansão WTW, WTT, LCA, CO2-only, CO2e ampliado, combustível alternativo, emissões locais em porto ou qualidade do ar da linha de base operacional atual. Esses temas só devem entrar como nova fronteira metodológica, com fatores, gases, unidades, energia, alocação e documentação próprios.

No eixo de rota e operação, a agenda deve fechar lacunas de distância marítima e seleção de portos antes de promover novos corredores a conclusões mais fortes. Isso inclui obter referências exatas para pares selecionados, manter portos alternativos como cenários próprios, melhorar a proveniência das rotas marítimas e incorporar, quando houver dados, serviço, frequência, janela operacional, capacidade, terminal, slot, tempo de trânsito e confiabilidade. Uma evolução de maior fidelidade seria uma super-rede multimodal, mas ela deve ser tratada como etapa futura, não como capacidade implícita do protótipo atual.

No eixo econômico, a próxima camada deve distinguir custo modelado, custo operacional alocado e frete comercial. Para avançar em viabilidade econômica, seria necessário incorporar tarifas, margens, contratos, demurrage, detention, seguro, inventário, confiabilidade, risco, disponibilidade de serviço e condições reais de contratação. Até lá, o CabotageLens continua útil como triagem técnica e acadêmica, não como cotador ou ferramenta de compra.

No eixo de validação e benchmark, o avanço deve priorizar a reconciliação explícita de carga, TEU, fator de carga, alocação, distância, rota, porto, serviço, operações portuárias e fronteira ambiental. Gustavo/Costa pode continuar como benchmark relevante no TF, mas deve permanecer como evidência externa de apoio, não como centro da contribuição. Trabalhos futuros também devem buscar benchmarks independentes para reduzir dependência de uma única família de referência.

Por fim, a agenda de publicação deve separar o relatório final do artigo técnico. O relatório pode preservar maior detalhe de Gustavo/Costa por sua função de defesa acadêmica e rastreabilidade. O artigo técnico deve apresentar esse benchmark de modo compacto, mantendo o CabotageLens como contribuição principal: um framework auditável, route-aware e boundary-explicit para comparação entre rodovia e cabotagem.

### 10.5 Fechamento

O CabotageLens não encerra a pergunta sobre a superioridade da cabotagem no Brasil, nem pretende substituir dados comerciais, operacionais ou ambientais mais completos. Sua contribuição é criar uma forma mais rigorosa de formular essa pergunta. Ao tornar explícitas as rotas, portos, distâncias, custos modelados, emissões operacionais, avisos e categorias de evidência, o framework permite comparar cenários com rastreabilidade e evitar conclusões mais fortes do que os dados sustentam.

Essa é a principal contribuição do TF: transformar uma comparação modal potencialmente opaca em uma análise auditável, conservadora e extensível. O trabalho mostra que a utilidade acadêmica do CabotageLens está tanto nos resultados que ele calcula quanto nos limites que ele preserva. A partir dessa base, trabalhos futuros podem ampliar fronteiras ambientais, operacionais, econômicas e de validação sem perder a condição essencial de defensibilidade: cada nova afirmação deve permanecer vinculada a fonte, método, unidade, cenário e evidência rastreados.
