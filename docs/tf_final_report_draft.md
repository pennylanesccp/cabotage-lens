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

Do ponto de vista de arquitetura, o protótipo separa a interação com o usuário, a lógica de domínio e a persistência dos registros. A interface Streamlit organiza o fluxo de entrada e apresentação dos resultados; a lógica reutilizável de roteamento, avaliação multimodal, custos, emissões, proveniência e avisos permanece em módulos de domínio; e o Supabase/Postgres atua como backend durável para caches e registros reaproveitáveis. Essa separação reduz o risco de misturar apresentação, cálculo e evidência, além de facilitar a revisão posterior dos resultados.

| Camada do protótipo | Papel computacional | Função no TF |
| --- | --- | --- |
| Interface de uso | Coleta entradas, organiza sessão e apresenta cartões, tabelas, avisos e detalhes. | Demonstra a aplicação prática da metodologia sem substituir a análise crítica. |
| Núcleo de domínio | Constrói rotas, aplica parâmetros, calcula custos e emissões, registra proveniência e avisos. | Materializa as regras metodológicas em lógica auditável. |
| Persistência e cache | Preserva lugares, rotas, cenários e resultados reutilizáveis em Supabase/Postgres. | Apoia reprodutibilidade e reduz dependência de chamadas repetidas a provedores. |
| Artefatos reprodutíveis | Mantêm fluxos de execução, exportação e validação quando disponíveis. | Permitem revisar entradas, saídas, bloqueios, sensibilidades e classificações. |
| Documentação técnica e acadêmica | Registra fronteiras, premissas, sínteses de validação e limitações. | Conecta o protótipo à interpretação conservadora adotada no relatório. |

Essa arquitetura deve ser lida como a implementação de um método de comparação condicionada. Ela não resolve uma super-rede multimodal nacional, não verifica horários, frequência, slots, aceitação terminal, contratos ou tarifas, e não transforma estimativas em preços de mercado. A contribuição computacional está em permitir que cada número apresentado seja acompanhado por sua fronteira de cenário, origem de dados, decomposição de rota e cautelas de interpretação.

### 5.2 Fluxo de uso e entradas do usuário

O fluxo de uso começa pela definição de um cenário de comparação. O usuário informa origem, destino, base de carga e parâmetros operacionais ou de modelo que delimitam a análise. Esses campos não representam uma solicitação de cotação ou reserva; eles definem quais locais, volumes, componentes, fontes de distância e hipóteses entram no cálculo comparativo.

As entradas geográficas são resolvidas em localizações utilizadas pela construção de rota. A partir delas, a ferramenta monta uma alternativa rodoviária direta e uma cadeia multimodal composta por acesso rodoviário ao porto de origem, perna marítima e acesso rodoviário final a partir do porto de destino. Em cenários ordinários, os portos decorrem da regra de seleção do cenário; em fluxos de validação ou sensibilidade, portos forçados ou alternativos podem ser registrados como hipóteses explícitas, sem substituir silenciosamente o caso-base.

| Grupo de entrada | Como parametriza o método | Saída ou metadado afetado |
| --- | --- | --- |
| Origem e destino | Definem os pontos da unidade funcional e os acessos terrestres. | Distâncias rodoviárias, portos candidatos e pernas da rota. |
| Base de carga | Define massa, TEU e alocação dos resultados por remessa. | Custos modelados, emissões TTW CO2e e comparabilidade entre alternativas. |
| Controle de portos | Define porto selecionado, elegível, forçado ou alternativo conforme o cenário. | Nós marítimos, acessos terrestres, avisos e classificação de uso. |
| Fonte de distância | Determina se a distância vem de provedor/cache, matriz, referência, substituição documentada ou `haversine_fallback`. | Confiança metodológica, proveniência e avisos de qualidade de rota. |
| Componentes operacionais | Habilita ou exclui parcelas como operações portuárias e *hoteling*. | Fronteira de custo e emissões efetivamente calculada. |
| Parâmetros de custo e emissões | Aplicam a fronteira operacional definida no Capítulo 4. | Estimativas em `BRL` e emissões operacionais TTW CO2e. |

O cenário resultante deve ser lido como conjunto. Uma diferença aparente de custo ou emissão pode depender da distância marítima usada, da escolha de portos, da presença de aviso `same-port`, de uma distância por `fallback`, de componentes habilitados ou de uma classificação de validação. Por isso, o fluxo de uso preserva não apenas os totais finais, mas também os metadados que explicam como o resultado foi produzido.

### 5.3 Construção das alternativas de rota

A construção das alternativas de rota é a etapa em que as entradas do cenário se tornam duas cadeias comparáveis. Na alternativa rodoviária direta, o CabotageLens representa o transporte da origem ao destino por uma única perna terrestre, usada como referência para consumo, custo modelado e emissões operacionais TTW CO2e. Na cadeia rodoviária-cabotagem-rodoviária, a ferramenta separa a análise em *pre-carriage*, perna marítima e *on-carriage*, mantendo visíveis os acessos terrestres que podem alterar materialmente a interpretação do multimodal.

O fluxo computacional pode ser resumido em cinco movimentos. Primeiro, origem e destino são resolvidos como pontos de rota. Segundo, a alternativa rodoviária direta é construída como referência comparativa. Terceiro, a lógica de cenário seleciona ou recebe os portos marítimos aplicáveis, distinguindo portos selecionados, elegíveis, forçados ou alternativos. Quarto, a ferramenta monta as pernas da cadeia multimodal e associa a cada uma sua distância, fonte e papel no cenário. Quinto, avisos de qualidade sinalizam casos que exigem leitura restrita, como `same-port`, distância marítima ausente, distância marítima muito pequena, uso de `haversine_fallback` ou domínio dos acessos rodoviários em uma cadeia marítima local.

Essa construção não busca simular todas as opções logísticas possíveis no território nacional. Ela fornece uma representação rastreável das alternativas necessárias para a comparação definida na unidade funcional. Um porto selecionado ou forçado é uma premissa do cenário, não prova de escala, frequência, slot, aceitação terminal, contrato ou viabilidade comercial. Do mesmo modo, uma distância marítima por referência forte, matriz interna, substituição manual ou `fallback` não deve receber o mesmo peso metodológico.

A disciplina de interpretação decorre dessa decomposição. A perna marítima não deve ser analisada isoladamente como se representasse toda a alternativa multimodal, e casos frágeis não devem ser promovidos a conclusões principais. Registros `same-port`, cenários de porto alternativo, linhas históricas, casos bloqueados, excluídos ou marcados como `reference_needed` podem apoiar diagnóstico, limitação, sensibilidade ou trabalho futuro, mas não sustentam, por si sós, afirmações robustas de superioridade modal.

### 5.4 Cálculo de distância, custo modelado e emissões operacionais

Após a construção das rotas, o CabotageLens consolida distâncias, custos modelados e emissões operacionais em saídas de cenário. As fórmulas, fatores, unidades e fronteiras substantivas pertencem ao Capítulo 4; neste capítulo, o foco é explicar como a ferramenta preserva a ligação entre essas definições metodológicas e os resultados apresentados ao usuário.

As distâncias são mantidas por perna antes de qualquer leitura agregada. A alternativa rodoviária direta possui a distância origem-destino; a cadeia multimodal combina os acessos terrestres e a perna marítima. O total modelado não elimina a necessidade de observar portos usados, fonte da distância marítima, avisos e componentes habilitados. Essa decomposição evita que uma comparação de totais esconda a origem da diferença entre alternativas.

O custo reportado em `BRL` é uma estimativa modelada dos componentes incluídos na fronteira do cenário. Ele não representa frete cotado, tarifa de transportador, preço de armador, contrato, *booking* ou custo logístico total de mercado. Da mesma forma, as emissões reportadas permanecem emissões operacionais TTW CO2e dos componentes representados, salvo indicação explícita de outra fronteira. Elas não devem ser lidas como WTW, LCA ou evidência CO2-only.

Operações portuárias e *hoteling* são tratados como componentes condicionais. Quando habilitados e compatíveis com a fronteira do cenário, podem ampliar a representação operacional do cálculo. Quando uma intensidade agregada já incorpora consumo operacional, a implementação pode registrar a exclusão do *hoteling* separado para reduzir risco de dupla contagem. O ponto metodológico é que a saída deve mostrar se esses componentes foram incluídos, excluídos ou tratados como já incorporados, pois isso altera a fronteira efetivamente calculada.

Assim, a comparação de custo e emissões não define automaticamente um vencedor. Ela fornece dimensões separadas de avaliação, condicionadas à rota construída, aos portos escolhidos, à proveniência das distâncias, aos componentes habilitados e aos parâmetros do cenário. Benchmarks e diagnósticos pertencem às etapas de validação e discussão; eles podem contextualizar lacunas, mas não recalibram silenciosamente a linha de base do protótipo.

### 5.5 Persistência, cache e proveniência dos dados

A persistência tem papel metodológico porque preserva a memória técnica das execuções. O Supabase/Postgres é usado como backend durável para registros reutilizáveis, incluindo lugares resolvidos, rotas, cenários e resultados. Essa camada melhora a repetibilidade do processo e reduz a dependência de novas consultas a provedores externos, especialmente quando a mesma consulta pode ser reaproveitada por cache.

Um `cache hit`, entretanto, deve ser interpretado com cautela. Ele indica que o protótipo reutilizou uma evidência computacional anterior compatível com aquela consulta. Não indica que a rota seja comercialmente disponível, operacionalmente ótima, contratável ou validada em magnitude. Em termos acadêmicos, o cache ajuda a separar instabilidade de provedor de diferenças metodológicas, mas não transforma estabilidade de execução em validação de custo, emissão ou viabilidade logística.

A proveniência de distância cumpre função semelhante. O protótipo distingue fontes como matriz ou serviço marítimo, referência externa, substituição manual documentada, `haversine_fallback`, registro histórico ou lacuna marcada como `reference_needed`. Essas categorias não têm o mesmo peso. Uma distância com referência documentada sustenta interpretação mais forte do que uma distância usada apenas para triagem; um caso `same-port` ou sustentado por `fallback` deve continuar limitado mesmo que esteja persistido ou exportado.

A utilidade acadêmica dessa camada está na auditabilidade. Registros persistidos e artefatos de exportação permitem recuperar o que foi calculado, com quais entradas, portos, distâncias, fontes, parâmetros, avisos e classificações. Eles não corrigem automaticamente lacunas de fonte, seleção de porto, fronteira de custo, fronteira de emissões ou compatibilidade operacional.

### 5.6 Saídas, avisos e registros de exportação

As saídas do CabotageLens devem ser entendidas como um conjunto interpretativo, não como totais finais isolados. A interface apresenta cartões de síntese para custo modelado, emissões TTW CO2e e distância, mas a leitura acadêmica depende dos detalhes associados: pernas de rota, portos, fonte de distância, avisos, componentes incluídos e fronteira do cenário.

| Superfície de saída | Informação exposta | Função de auditabilidade |
| --- | --- | --- |
| Cartões de síntese | Custos modelados, emissões operacionais TTW CO2e e distâncias comparadas. | Mostram a comparação principal sem esconder que ela é condicionada. |
| Detalhes de rota e premissas | Pernas, portos, componentes habilitados, fronteira de emissões e fronteira de custo. | Permitem reconstruir a composição do cenário. |
| Proveniência de distância | Fonte, tipo de fonte, substituição, `fallback` ou lacuna. | Indica a confiança atribuível à rota e à perna marítima. |
| Avisos de qualidade | Alertas como `same-port`, distância ausente, distância pequena ou acesso terrestre dominante. | Sinalizam quando o resultado deve ser usado como cautela, diagnóstico ou sensibilidade. |
| Exportações e registros de validação | Entradas, saídas, portos, distâncias, avisos, status e classificações quando disponíveis. | Preservam trilha de revisão sem converter o cenário em validação operacional. |

Os avisos são controles interpretativos. A presença de aviso não prova impossibilidade operacional; ela indica que o resultado não deve ser tratado como evidência robusta sem suporte adicional. A ausência de aviso também não comprova serviço real, escala, frequência, disponibilidade de slot, aceitação terminal, contrato ou tarifa. Ela apenas informa que, dentro das regras implementadas, não foi identificado um problema daquela classe.

Os registros de exportação e validação apoiam a passagem do resultado numérico para evidência classificada. Campos de status como `record_only_warning`, `reference_needed`, `sensitivity_only` ou `sensitive` preservam o uso permitido de cada linha no TF. Sua função é impedir que uma saída frágil seja promovida a conclusão principal, não criar uma validação automática. A discussão detalhada dessas evidências pertence aos capítulos de validação e resultados.

### 5.7 Limitações computacionais e uso correto da ferramenta

O uso correto do CabotageLens é analítico e acadêmico. A ferramenta apoia comparação transparente entre a alternativa rodoviária direta e a cadeia rodoviária-cabotagem-rodoviária, análise de sensibilidade, rastreabilidade, reprodutibilidade e identificação de lacunas metodológicas. Ela não automatiza decisão comercial, contratação de transporte, validação operacional ou conclusão universal sobre a cabotagem.

As principais fronteiras de uso são três. Primeiro, a fronteira econômica: custos modelados não são fretes, cotações, tarifas, contratos ou custos logísticos totais de mercado. Segundo, a fronteira ambiental: emissões reportadas permanecem operacionais TTW CO2e, não WTW, LCA ou evidência CO2-only. Terceiro, a fronteira operacional: seleção de portos, cache, ausência de aviso ou exportação completa não comprovam disponibilidade real de serviço, escala, frequência, slot, aceitação terminal ou viabilidade comercial.

Consequentemente, os estudos de caso do Capítulo 6 devem herdar essas cautelas. Cada resultado precisa ser interpretado junto com entradas, portos, distâncias, proveniência, cache, componentes habilitados, avisos e classificação conservadora. O fechamento deste capítulo é, portanto, uma regra de leitura: o CabotageLens torna a implementação metodológica visível e auditável, mas a força de cada conclusão depende da qualidade da evidência associada ao cenário.

## 6. Estudos de caso e validacao

### 6.1 Estratégia de validação e classificação de evidências

A validação adotada neste TF não é tratada como um resultado binário de aprovação ou reprovação do modelo. Ela é uma estratégia em camadas para classificar evidências, preservar rastreabilidade e controlar a força das afirmações feitas a partir de cada linha. O objetivo é avaliar plausibilidade, consistência, proveniência, estabilidade computacional e disciplina de fronteira, sem transformar automaticamente uma execução numérica em validação operacional ou comercial.

Essa abordagem é necessária porque as saídas do CabotageLens combinam distâncias modeladas, seleção de portos, fontes marítimas de qualidade desigual, parâmetros de custo e emissões e evidências externas com fronteiras nem sempre equivalentes. Um resultado executado, portanto, não é automaticamente um resultado válido para conclusão principal. A classificação define se a linha pode ser usada como diagnóstico histórico, sensibilidade, limitação, exclusão, bloqueio metodológico, lacuna de referência ou apoio direcional de benchmark.

| Camada de evidência | Papel no Capítulo 6 | Interpretação segura |
| --- | --- | --- |
| Batch 001 histórico | Preserva a primeira camada diagnóstica de casos OD. | Evidência histórica e motivação para correções; não resultado final validado. |
| Batch 001B metodológico | Classifica decisões, exclusões, bloqueios, lacunas de referência, avisos e sensibilidades. | Camada de auditabilidade que controla o uso permitido de cada caso. |
| Sensibilidades executadas | Testa hipóteses documentadas sob portos, distâncias ou referências específicas. | Discussão condicional; não conclusão robusta nem `headline_candidate`. |
| Batch 002 externo | Compara o modelo com o workbook Gustavo/Costa. | Apoio direcional de benchmark; não validação calibrada de magnitude. |
| Rerun Supabase/cache | Verifica se instabilidade de provedor/cache explica a lacuna rodoviária. | Evidência de estabilidade computacional; não prova operacional ou comercial. |
| Reconciliação rodoviária | Testa premissas rodoviárias como explicação diagnóstica da lacuna road-only. | Explica parte do desalinhamento; não recalibra nem substitui a linha de base. |
| Classificação final de uso | Define o que cada linha pode sustentar no TF. | Controle de afirmação que deve ser herdado pelo Capítulo 7. |

O Batch 001 é mantido como evidência histórica diagnóstica. O Batch 001B acrescenta a camada de decisão metodológica que separa casos excluídos, bloqueados, `reference_needed`, `record_only_warning` e `sensitivity_only` ou `sensitive`. As sensibilidades executadas ajudam a discutir comportamento do modelo sob hipóteses explícitas, mas não são resultados de linha de base e não devem ser promovidas a conclusões principais robustas.

O Batch 002 acrescenta um benchmark externo, mas o workbook Gustavo/Costa é tratado como referência comparativa, não como verdade de referência. A concordância em direção entre benchmark e CabotageLens não implica validação calibrada de magnitude. Do mesmo modo, o rerun Supabase/cache testa estabilidade de processo, enquanto a reconciliação de fator rodoviário é um diagnóstico para explicar parte da lacuna road-only; esse diagnóstico não atualiza, recalibra nem substitui o modelo de linha de base do CabotageLens.

As classificações também preservam as fronteiras substantivas do trabalho. Nenhuma classificação prova disponibilidade de serviço, aceitação por transportador, disponibilidade de slot, viabilidade comercial, frete contratado ou execução operacional real. Custos continuam sendo estimativas modeladas, não fretes comerciais, e emissões continuam sendo operacionais TTW CO2e, salvo indicação explícita em contrário. No estado atual dos artefatos rastreados, nenhum resultado deve ser promovido a `headline_candidate` sem suporte explícito adicional.

### 6.2 Batch 001 como diagnóstico histórico

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

### 6.4 Sensibilidades executadas

Três casos foram executados como sensibilidades do Batch 001B: Santos/Manaus com distância marítima de referência documentada, Manaus/Pecém como sensibilidade de porto alternativo para a região de Fortaleza e Rio Grande/Suape como sensibilidade de porto alternativo para a região de Recife. Esses casos foram selecionados porque cada um testava uma hipótese metodológica rastreada nos artefatos: correção de proveniência de distância, uso explícito de porto alternativo ou separação entre porto regionalmente próximo e porto originalmente selecionado.

O ponto central desta subseção é a classificação, não a magnitude numérica. As três linhas executadas permanecem classificadas como `sensitive`. Elas podem ser usadas para discutir como a escolha de rota, porto e distância marítima afeta custo modelado e emissões operacionais TTW CO2e, mas não substituem validação robusta, não criam casos `headline_candidate` e não encerram as lacunas dos casos-base ainda dependentes de referência exata.

| Sensibilidade | Hipótese testada | Interpretação segura | Limitação |
| --- | --- | --- | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Santos/Manaus com distância marítima de referência documentada. | Mostra o comportamento do modelo quando a distância marítima histórica de fallback é tratada como hipótese de sensibilidade. | Não valida todos os casos com `haversine_fallback` nem transforma a linha em conclusão robusta. |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Manaus/Pecém como porto alternativo para a região de Fortaleza. | Permite discutir sensibilidade a porto alternativo, acesso rodoviário e distância marítima. | Pecém não valida Porto de Fortaleza e não substitui a linha-base selecionada. |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Rio Grande/Suape como porto alternativo para a região de Recife. | Permite discutir sensibilidade a porto alternativo, acesso rodoviário e distância marítima. | Suape não valida Porto do Recife e não substitui a linha-base selecionada. |

A sensibilidade Santos/Manaus é útil porque ilustra o efeito de substituir uma distância marítima histórica de fallback por uma referência documentada no mesmo corredor. Esse resultado, porém, não autoriza extrapolar a conclusão para qualquer caso com `haversine_fallback`. Cada linha com fallback continua exigindo análise própria de porto, proveniência, fronteira e uso permitido antes de sustentar qualquer afirmação forte.

As sensibilidades Manaus/Pecém e Rio Grande/Suape têm outra função: mostrar como a mudança de porto pode alterar a interpretação do cenário. Pecém e Suape podem ser discutidos como portos alternativos explicitamente rotulados, mas não validam silenciosamente Porto de Fortaleza ou Porto do Recife. Portanto, os casos-base Manaus/Fortaleza e Rio Grande/Recife permanecem dependentes de referências exatas para os portos selecionados, ou de decisão metodológica posterior igualmente rastreada.

Mesmo quando uma sensibilidade apresenta menor custo modelado ou menor TTW CO2e operacional para a alternativa multimodal, essa direção não prova superioridade universal da cabotagem. O resultado continua condicionado à hipótese testada, à cadeia de portos, à distância marítima adotada e aos componentes incluídos. Além disso, custos permanecem estimativas modeladas, não fretes comerciais, e emissões permanecem operacionais TTW CO2e, não WTW nem LCA. As sensibilidades também não demonstram disponibilidade de serviço, viabilidade comercial, frequência de escala ou preço praticado no mercado.

### 6.5 Batch 002 como benchmark externo Gustavo/Costa

O Batch 002 acrescentou uma camada de benchmark externo baseada no workbook Gustavo/Costa. Esse benchmark pertence ao mesmo contexto amplo de comparação entre transporte rodoviário e cabotagem ou alternativa multimodal no Brasil, por isso é útil para confrontar o CabotageLens com uma referência externa ao próprio protótipo. Seu papel, entretanto, é estritamente metodológico: verificar consistência direcional e expor lacunas de comparabilidade, não reproduzir exatamente o workbook nem tratá-lo como verdade absoluta.

A leitura segura do Batch 002 começa pela diferença entre direção e magnitude. A pergunta defensável é se, nos pares OD positivos e suportados, o workbook e o CabotageLens apontam para o mesmo lado da comparação de emissões: cabotagem/multimodal abaixo do rodoviário direto. A pergunta que o Batch 002 ainda não responde é se as magnitudes são calibradas, se a metodologia do workbook foi reconstruída integralmente ou se cada rota representa uma operação comercial disponível.

| Item Batch 002 | Valor consolidado | Interpretação segura |
| --- | ---: | --- |
| Células de matriz do workbook parseadas | 36 | Inventário inicial do benchmark; nem todas são comparáveis ou executáveis. |
| Pares OD positivos e suportados benchmarkados | 21 | Escopo efetivo da comparação direcional. |
| Linhas executadas com sucesso | 21 | Execução completa dos pares suportados; não implica validação calibrada. |
| Células puladas antes da execução do modelo | 15 | Inclui self-pairs e linhas rodoviárias zero ou não positivas, portanto não deve ser tratado como falha do modelo. |
| Pares com acordo direcional | 21 de 21 | Workbook e CabotageLens favorecem cabotagem/multimodal em emissões frente ao road-only. |
| Classificação rastreada atual | 21 `same_direction_large_gap` | Apoia interpretação direcional cautelosa, mas preserva lacunas relevantes de magnitude. |

As 15 células puladas correspondem a seis self-pairs e nove linhas rodoviárias zero ou não positivas. Essa filtragem é parte da disciplina de benchmark: nem todo par presente na matriz do workbook é automaticamente um corredor comparável para execução no CabotageLens. Assim, o denominador relevante para a leitura do Batch 002 é o conjunto de 21 pares OD positivos e suportados, não a matriz inteira sem qualificação.

Para esses 21 pares, o resultado é consistente em direção: tanto o workbook quanto o CabotageLens indicam emissões de cabotagem/multimodal abaixo das emissões road-only. Esse alinhamento fortalece a defesa metodológica porque mostra que o sinal modal geral não é produzido apenas internamente pelo protótipo. Ainda assim, todas as linhas permanecem classificadas como `same_direction_large_gap`, o que significa que a diferença de magnitude continua material e deve ficar visível na interpretação.

O workbook, portanto, é benchmark e não verdade de referência. Diferenças de distância, seleção de portos, lógica de serviço, carga, alocação, tratamento de port-ops/hoteling e fronteira ambiental podem explicar parte das lacunas. A concordância direcional não valida magnitude exata, não demonstra reprodução do workbook, não confirma disponibilidade de serviço, não prova viabilidade comercial e não transforma custos modelados em fretes ou tarifas de mercado. As emissões do CabotageLens permanecem operacionais TTW CO2e, salvo indicação explícita em contrário, e não devem ser misturadas com WTW ou LCA.

Consequentemente, o Batch 002 não cria um `headline_candidate`. Seu uso adequado no Capítulo 6 é mostrar que há apoio externo direcional, acompanhado de limites de comparabilidade suficientemente importantes para impedir uma afirmação de validação calibrada. A conclusão conservadora é que o benchmark sustenta discussão metodológica e confiança direcional limitada, enquanto a validação de magnitude, custo comercial, serviço e rota permanece fora do alcance do lote.

### 6.6 Rerun Supabase/cache como verificação de estabilidade

O rerun Supabase/cache foi usado para testar uma hipótese operacional específica do Batch 002: se a diferença de magnitude entre o workbook Gustavo/Costa e o CabotageLens, especialmente no lado rodoviário, poderia ser explicada por instabilidade de provedor de rota, leitura de cache ou escrita de cache. Essa verificação não buscou recalibrar o modelo nem forçar aproximação numérica ao benchmark; seu objetivo foi separar instabilidade computacional de diferenças metodológicas mais profundas.

No rerun, as distâncias rodoviárias vieram apenas de cache. O artefato consolidado registra que a conexão e a leitura/escrita de cache Supabase funcionaram, que as pernas rodoviárias necessárias foram atendidas por registros existentes e que não houve necessidade de novas escritas de distância por provedor. Isso torna o rerun uma evidência de rastreabilidade do processo, não uma evidência de operação logística real.

| Verificação do rerun | Resultado observado | Interpretação |
| --- | --- | --- |
| Fonte de distância rodoviária | Distâncias rodoviárias em cache | Reduz a hipótese de instabilidade por chamada em tempo real ao provedor. |
| `route-cache hits` | 63 | As 21 pernas diretas, 21 pernas de acesso inicial e 21 pernas de acesso final foram atendidas por cache. |
| `route-cache misses` | 0 | Não houve lacuna de cache rodoviário no rerun. |
| Escritas de distância por provedor | 0 | O rerun não dependeu de novas distâncias de provedor. |
| Falhas de leitura/escrita de cache | 0 | Não houve evidência de falha operacional de cache no lote. |
| Diferença rodoviária média/mediana | 201,0%/150,5% -> 199,8%/149,3% | A mudança agregada foi pequena; a lacuna permanece. |

Essa estabilidade reduz a probabilidade de que a grande lacuna rodoviária do Batch 002 seja explicada principalmente por ruído de provedor, falha de cache ou variação de rota entre execuções. A evidência aponta para uma interpretação mais conservadora: a diferença deve ser investigada sobretudo como diferença de método, fronteira, parâmetro, carga, alocação ou base de distância, e não como simples instabilidade computacional.

Ao mesmo tempo, a estabilidade do cache não valida magnitudes exatas. Cache hits indicam que o processo reaproveitou entradas rastreáveis, mas não provam que a rota representa disponibilidade comercial, serviço contratado, tarifa praticada, frequência de escala ou viabilidade operacional. Também não transformam os custos em fretes comerciais nem alteram a fronteira das emissões, que continuam sendo operacionais TTW CO2e no CabotageLens.

Portanto, o rerun Supabase/cache fortalece a auditabilidade e a reprodutibilidade computacional do Batch 002, mas não resolve sozinho os desencontros com Gustavo/Costa. Ele permite descartar uma explicação fraca, baseada apenas em instabilidade de cache/provedor, e prepara a discussão metodológica seguinte sobre fatores rodoviários e demais fronteiras de comparação.

### 6.7 Reconciliação rodoviária como diagnóstico de alinhamento

A reconciliação rodoviária do Batch 002 deve ser lida como diagnóstico de alinhamento com benchmark, não como atualização do modelo de linha de base do CabotageLens. Depois que o rerun Supabase/cache reduziu a hipótese de instabilidade de rota, esta etapa testou uma pergunta mais específica: quanto da lacuna de magnitude no lado rodoviário poderia ser explicado por diferenças de premissas de consumo de combustível e fator de emissão em relação à família Gustavo/Costa.

O diagnóstico manteve fixas as mesmas distâncias rodoviárias em cache do Batch 002 e aplicou, apenas para comparação, as premissas rodoviárias rastreadas no benchmark: `FDc = 0.28 L/km`, `FDe = 35.52 MJ/L` e `FDf = 86.5 gCO2eq/MJ`. A combinação desses valores gera o fator diagnóstico:

```text
0.28 L/km * 35.52 MJ/L * 86.5 gCO2eq/MJ / 1000 = 0.8602944 kgCO2e/km
```

| Item diagnóstico | Valor ou observação | Limite de interpretação |
| --- | --- | --- |
| Premissa de consumo rodoviário | `FDc = 0.28 L/km` | Usada apenas no diagnóstico de alinhamento; não substitui o preset rodoviário da ferramenta. |
| Conteúdo energético do diesel | `FDe = 35.52 MJ/L` | Mantém o teste vinculado ao benchmark, não a uma nova calibração geral. |
| Fator de emissão | `FDf = 86.5 gCO2eq/MJ` | Não autoriza misturar TTW, WTW, LCA, CO2 e CO2e sem reconciliação explícita de fronteira. |
| Fator diagnóstico resultante | `0.8602944 kgCO2e/km` | Sensibilidade de alinhamento, não fator de linha de base do CabotageLens. |
| Diferença rodoviária média | `199,8%` -> `43,9%` | Redução substancial, mas não eliminação da lacuna. |
| Diferença rodoviária mediana | `149,3%` -> `19,6%` | Indica que premissas rodoviárias explicam grande parte do desalinhamento. |

O efeito do teste é forte: aplicar o fator diagnóstico às mesmas distâncias rodoviárias em cache reduziu substancialmente a diferença média e mediana do lado road-only. Essa evidência sugere que uma parte importante da divergência com o workbook está associada a premissas rodoviárias de consumo e emissão, e não apenas à rota ou ao cache. Ela também ajuda a explicar por que a comparação direcional pode ser coerente enquanto a magnitude permanece distante.

Essa redução, porém, não resolve todo o problema. Permanecem lacunas associadas à base de distância rodoviária, construção de rota, carga por contêiner, alocação, fronteira TTW versus WTW/LCA, gases incluídos, escolhas do workbook e demais parâmetros ainda não reconciliados. Por isso, o resultado deve ser apresentado como diagnóstico de sensibilidade a premissas rodoviárias, não como validação calibrada de magnitude.

O teste também não altera a fronteira econômica ou operacional do trabalho. Ele não valida fretes comerciais, tarifas, disponibilidade de serviço, viabilidade de rota ou preços praticados no mercado. Custos do CabotageLens continuam sendo estimativas modeladas, e emissões continuam sendo operacionais TTW CO2e, salvo indicação explícita em contrário. O fator diagnóstico pode explicar parte do desalinhamento com o benchmark, mas não autoriza misturar TTW, WTW, LCA, CO2 e CO2e como se fossem equivalentes.

Assim, a conclusão metodológica é limitada e útil: a reconciliação rodoviária mostra que as premissas de consumo e fator de emissão explicam muito da lacuna road-only, mas não substitui o modelo rodoviário de linha de base do CabotageLens, não recalibra a aplicação e não transforma o Batch 002 em validação exata. Seu valor no TF é tornar explícita uma causa provável da diferença de magnitude, preservando a classificação conservadora do benchmark.

### 6.8 Categorias finais de uso no TF e controles de afirmação

O fechamento do Capítulo 6 transforma as camadas anteriores em uma regra prática de uso da evidência. Um resultado executado não é automaticamente um resultado utilizável como conclusão principal do TF. A classificação atribuída a cada linha controla a forma de citação, a força da afirmação permitida e o tipo de ressalva exigida antes que o Capítulo 7 apresente números, tabelas ou sínteses.

Essa classificação não é cosmética. Ela separa registros históricos, sensibilidades, bloqueios, exclusões, lacunas de referência e evidência externa de benchmark. Sem essa separação, casos frágeis poderiam ser promovidos indevidamente a conclusões de desempenho modal. No estado atual dos artefatos rastreados, nenhum caso é um `headline_candidate` robusto: as sensibilidades apoiam discussão condicionada, o Batch 002 apoia interpretação direcional com lacunas de magnitude, e a reconciliação rodoviária explica parte do desalinhamento sem substituir a linha de base.

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
| `benchmark_methodology_gap` | Diferenças de método permanecem relevantes. | Explicar lacunas de rota, carga, alocação, serviço e parâmetros. | Tratar o benchmark como verdade de referência plenamente reconciliada. |
| `benchmark_boundary_mismatch` | Fronteiras ambientais ou funcionais não coincidem totalmente. | Preservar cautela entre TTW, WTW, LCA, CO2 e CO2e. | Misturar fronteiras ou unidades como equivalentes. |
| `not_comparable` | Linha ou evidência sem comparabilidade suficiente na fronteira atual. | Usar como limitação ou justificativa de não execução. | Transformar em evidência numérica ou conclusão de desempenho. |

Esses controles também delimitam o que o trabalho não demonstra. Nenhuma linha atual prova superioridade universal da cabotagem, viabilidade comercial, disponibilidade de serviço, aceitação por transportador, disponibilidade de slot, frequência de escala ou frete contratado. Mesmo quando a direção modelada favorece a alternativa multimodal, a afirmação permanece condicionada ao corredor, aos portos, às distâncias, à fronteira de custo, aos parâmetros de emissão e à classificação da linha.

O mesmo vale para as fronteiras de custo e emissões. Custos continuam sendo estimativas modeladas, não tarifas, cotações ou fretes comerciais. Emissões continuam sendo operacionais TTW CO2e, salvo indicação explícita em contrário. Evidências WTW, LCA, CO2 isolado ou CO2e sob outra fronteira não podem ser misturadas aos resultados do CabotageLens sem reconciliação metodológica explícita.

Assim, o Capítulo 7 deve herdar integralmente esses limites. A apresentação dos resultados pode mostrar sensibilidades executadas, apoio direcional do Batch 002, estabilidade computacional do cache e diagnóstico de premissas rodoviárias, mas deve manter cada evidência dentro da categoria que a sustenta. A contribuição defendida é a rastreabilidade metodológica e a interpretação conservadora dos cenários, não uma validação universal, comercial ou calibrada de todas as magnitudes.

## 7. Resultados

### 7.1 Inventário final de casos e categorias de uso no TF

Este capítulo apresenta os resultados observados sob os controles de evidência definidos no Capítulo 6. A primeira função desta seção não é interpretar a relevância logística dos corredores, mas registrar quais linhas existem no inventário final, qual é a classificação de uso de cada camada de evidência e quais limites impedem sua promoção a conclusão principal. Com a síntese atualmente rastreada, nenhum caso Batch 001/001B e nenhuma linha Batch 002 deve ser apresentado como `headline_candidate` robusto.

O inventário final separa evidência executada, evidência planejada, lacunas de referência, bloqueios metodológicos, exemplos de limitação e camadas de benchmark. Essa separação é necessária porque uma linha executada não é automaticamente uma linha validada: execução apenas indica que a ferramenta produziu uma saída sob uma configuração documentada. Do mesmo modo, linhas de sensibilidade continuam sendo resultados de sensibilidade, não conclusões de linha de base.

Nos casos Batch 001 e Batch 001B, os registros originais permanecem como `historical_diagnostic`, os casos de rota inadequada ou fora da fronteira são tratados como `limitation_example` ou `excluded`, e as lacunas de distância ou decisão de porto permanecem como `reference_needed` ou `methodology_blocked`. As sensibilidades executadas e planejadas ficam em `sensitivity_discussion`, pois servem para mostrar comportamento do modelo sob hipóteses nomeadas, sem validar automaticamente o corredor original, o porto selecionado ou a magnitude final.

| Categoria | Significado | Evidência associada | Uso seguro no Capítulo 7 |
| --- | --- | --- | --- |
| `headline_candidate` | Resultado candidato a conclusão principal robusta após validação e sensibilidade suficientes. | Nenhum caso atual. | Registrar a ausência de resultado principal robusto. |
| `sensitivity_discussion` | Evidência planejada ou executada sob hipótese documentada. | Sensibilidades Batch 001B de distância de referência ou porto alternativo. | Apresentar como resultado de sensibilidade, não como linha de base validada. |
| `limitation_example` | Caso útil para mostrar limite de rota, seleção de porto ou interpretação. | Registro same-port e casos de aviso. | Usar como exemplo de limitação metodológica. |
| `excluded` | Caso inválido ou fora da fronteira atual de comparação. | Cadeias excluídas do benchmark vigente. | Justificar exclusão, sem conclusão numérica. |
| `reference_needed` | Caso com referência exata ainda ausente. | Pares selecionados sem distância marítima exata rastreada. | Registrar lacuna de evidência e requisito futuro. |
| `methodology_blocked` | Caso bloqueado por decisão metodológica ainda não definida. | Linhas sem porto alternativo ou regra defensável suficiente. | Registrar bloqueio, sem execução ou inferência numérica. |
| `historical_diagnostic` | Resultado histórico preservado para rastreabilidade. | Saídas originais Batch 001. | Mostrar evolução do método, não resultado corrigido. |
| `benchmark_supports_direction` | Benchmark externo apoia a mesma direção modal de emissões sob fronteiras próprias. | Pares OD positivos e suportados do Batch 002. | Usar como apoio direcional, não validação calibrada. |
| `benchmark_supports_road_factor_explanation` | Diagnóstico rodoviário explica parte relevante da lacuna road-only. | Reconciliação de fator rodoviário do Batch 002. | Tratar como diagnóstico de premissas, não recalibração da linha de base. |
| `benchmark_methodology_gap` | Diferenças de método permanecem relevantes para a magnitude. | Rerun com cache e diferenças remanescentes do Batch 002. | Descrever lacunas metodológicas sem tratar o workbook como verdade absoluta. |
| `benchmark_boundary_mismatch` | Fronteiras funcionais ou ambientais não estão plenamente reconciliadas. | Diferenças de TTW, WTW, LCA, CO2, CO2e, alocação, rota, porto, serviço e port-ops/hoteling. | Preservar cautela de fronteira e unidade. |
| `not_comparable` | Linha ou camada sem comparabilidade suficiente na fronteira atual. | Células puladas do workbook e evidências sem base comparável. | Usar como limitação, sem resultado numérico. |

O Batch 002 entra neste inventário como benchmark externo direcional. Ele sustenta a interpretação de que, nas linhas comparáveis na unidade reportada, o workbook Gustavo/Costa e o CabotageLens apontam a mesma direção modal de emissões, mas não fornece validação calibrada de magnitude, reprodução exata do workbook, validação de escolhas de serviço ou equivalência de custo comercial. O workbook é uma camada externa de comparação, não uma verdade de referência que resolva automaticamente as fronteiras internas do modelo.

A reconciliação de fator rodoviário também deve ser lida como resultado observado de diagnóstico. Ela indica que premissas de consumo e fator de emissão rodoviários explicam parcela relevante da lacuna road-only do Batch 002, mas não substitui o modelo rodoviário de linha de base, não recalibra o aplicativo e não elimina as diferenças remanescentes de distância, veículo, carregamento, alocação, fronteira ambiental ou premissas do workbook.

Por fim, este inventário preserva as fronteiras materiais dos resultados. Custos permanecem estimativas modeladas, não tarifas ou fretes comerciais; emissões permanecem CO2e operacional TTW, salvo indicação explícita em contrário; e nenhum resultado desta seção prova superioridade universal da cabotagem, viabilidade comercial ou disponibilidade de serviço. A função do Capítulo 7 é apresentar o que foi observado e classificado; a interpretação mais profunda dessas implicações pertence ao Capítulo 8.

### 7.2 Resultados das sensibilidades executadas

Foram executadas três linhas de sensibilidade do Batch 001B: `TF-VAL-001B-SENS-002-REFDIST`, `TF-VAL-001B-SENS-003B-ALTPECEM` e `TF-VAL-001B-SENS-005B-ALTSUAPE`. A tabela a seguir apresenta apenas os valores já rastreados nos artefatos de validação e mantém a classificação de cada linha como `sensitive`. Os custos são estimativas modeladas por remessa, não fretes comerciais; as emissões são CO2e operacional TTW, não WTW nem LCA.

| Caso | Papel da sensibilidade | Portos | Custo modelado rodoviário | Custo modelado multimodal | TTW CO2e rodoviário | TTW CO2e multimodal | Classificação |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Distância de referência Santos/Manaus | Santos -> Manaus | BRL 18456,45 | BRL 1263,50 | 6961,76 kg TTW CO2e | 1104,67 kg TTW CO2e | `sensitive` |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Porto alternativo Pecém | Manaus -> Pecém | BRL 26391,03 | BRL 727,33 | 9989,83 kg TTW CO2e | 573,48 kg TTW CO2e | `sensitive` |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Porto alternativo Suape | Rio Grande -> Suape | BRL 18121,99 | BRL 2122,38 | 7013,27 kg TTW CO2e | 1127,46 kg TTW CO2e | `sensitive` |

Nos três cenários nomeados, a alternativa multimodal apresentou menor custo modelado e menor TTW CO2e operacional do que a alternativa rodoviária direta. Esse resultado é observado dentro das premissas documentadas de cada sensibilidade, e não deve ser lido como conclusão robusta de linha de base. Nenhuma dessas linhas é `headline_candidate`.

O caso Santos/Manaus é uma sensibilidade de distância de referência. Ele mostra o comportamento do modelo quando a distância marítima de referência rastreada é usada para esse par específico, mas não valida automaticamente todos os casos que dependem de `haversine_fallback`, nem transforma distâncias de triagem em evidência final de rota.

As linhas Manaus/Pecém e Rio Grande/Suape são sensibilidades de porto alternativo. Pecém não valida Porto de Fortaleza, e Suape não valida Porto do Recife. A mudança de porto altera o cenário avaliado e deve permanecer visível na leitura dos resultados, sem substituição silenciosa do porto originalmente selecionado.

Portanto, os valores desta subseção devem ser usados como resultados observados de sensibilidade: úteis para mostrar a direção do modelo sob hipóteses documentadas, mas insuficientes para afirmar superioridade universal da cabotagem, disponibilidade de serviço, viabilidade comercial ou validação plena do modelo. A discussão das implicações permanece reservada ao Capítulo 8.

### 7.3 Resultados do Batch 002

O Batch 002 apresenta o resultado observado do benchmark externo Gustavo/Costa. A função desta subseção é registrar o inventário e a classificação do lote, não discutir em profundidade as causas das diferenças de magnitude. O workbook é tratado como camada de benchmark, não como verdade de referência, e o resultado do CabotageLens não deve ser lido como reprodução exata do workbook.

Foram parseadas 36 células da matriz do workbook. Desse conjunto, 21 pares OD positivos e suportados foram benchmarkados e executados com sucesso no CabotageLens. As 15 células restantes foram puladas antes da execução do modelo; esse grupo inclui 6 self-pairs e 9 linhas com valor rodoviário zero ou não positivo. Portanto, as células puladas não devem ser tratadas como falhas do modelo sem esse contexto de filtragem.

| Métrica | Valor observado | Interpretação |
| --- | ---: | --- |
| Células da matriz do workbook parseadas | 36 | Inventário completo da matriz 6 x 6 lida para o benchmark. |
| Pares OD positivos e suportados | 21 | Linhas elegíveis para comparação na base reportada do workbook. |
| Execuções bem-sucedidas | 21 | Todos os pares positivos suportados foram processados. |
| Células puladas antes da execução | 15 | 6 self-pairs e 9 linhas rodoviárias zero ou não positivas; não são falhas de execução. |
| Alinhamento direcional | 21/21 | Workbook e CabotageLens indicam cabotagem/multimodal abaixo do rodoviário direto em emissões. |
| Classificação atual | 21 x `same_direction_large_gap` | Há concordância de direção, mas lacuna material de magnitude. |
| Validação de magnitude | 0 linhas plenamente calibradas | O lote não sustenta validação calibrada nem reprodução exata do workbook. |

O resultado central do Batch 002 é a consistência direcional externa: nos 21 pares OD positivos e suportados, tanto o workbook quanto o CabotageLens indicam emissões menores para a alternativa de cabotagem/multimodal do que para o rodoviário direto. Essa concordância é útil para a apresentação de resultados, mas não valida as magnitudes exatas de emissões.

A classificação rastreada de todas as 21 linhas é `same_direction_large_gap`. Assim, o lote deve ser apresentado como apoio direcional com lacuna de magnitude, não como calibração, reprodução exata, validação plena de rota ou validação de premissas internas do workbook. As diferenças de magnitude permanecem um resultado observado relevante e são retomadas como questão metodológica no Capítulo 8.

As fronteiras do TF continuam válidas nesta subseção. Custos permanecem estimativas modeladas, não tarifas, cotações ou fretes comerciais. Emissões permanecem CO2e operacional TTW, salvo indicação explícita em contrário, e não devem ser misturadas com WTW ou LCA. O Batch 002 também não valida disponibilidade real de serviço, viabilidade comercial, frequência, capacidade, preço praticado ou superioridade universal da cabotagem.

Por esses motivos, o Batch 002 não cria um `headline_candidate`. O uso seguro no Capítulo 7 é registrar que há apoio externo de direção para os pares comparáveis, preservando a ressalva de que a magnitude ainda não está calibrada e que parte do workbook permaneceu fora da execução por critérios explícitos de comparabilidade.

### 7.4 Resultados do rerun Supabase/cache

O rerun Supabase/cache foi usado para testar uma hipótese limitada: se a instabilidade de provedor de rota, leitura de cache ou escrita de cache poderia explicar a lacuna de magnitude observada no Batch 002. A execução não teve o objetivo de recalibrar o modelo, substituir premissas nem validar magnitude absoluta. Seu papel é documentar a rastreabilidade computacional das distâncias rodoviárias usadas no benchmark externo Gustavo/Costa.

No rerun, as distâncias rodoviárias vieram apenas de registros já armazenados em cache. A evidência consolidada registra leitura de cache funcional, sonda de escrita com rollback bem-sucedida antes da execução, 63 route-cache hits, 0 misses, 0 escritas de distância pelo provedor e 0 falhas de leitura/escrita. Esses hits cobrem as pernas rodoviárias do lote executado, mas devem ser lidos como evidência computacional de reutilização de dados, não como prova de disponibilidade comercial de rota, serviço, frequência, capacidade ou preço.

| Métrica do rerun | Valor observado | Interpretação segura |
| --- | ---: | --- |
| Route-cache hits | 63 | Todas as pernas rodoviárias consultadas no rerun foram atendidas por cache. |
| Route-cache misses | 0 | Nenhuma distância rodoviária exigiu nova chamada viva ao provedor. |
| Escritas de distância pelo provedor | 0 | O rerun não gerou novas distâncias de provedor para o lote. |
| Falhas de leitura/escrita do cache | 0 | Não há falha registrada de persistência no rerun. |
| Linhas parseadas/executadas | 21 / 21 | Todos os pares OD positivos e suportados foram processados com sucesso. |
| Células puladas antes da execução | 15 | 6 self-pairs e 9 linhas rodoviárias zero ou não positivas permaneceram fora da comparação. |
| Mismatch rodoviário antes/depois | 201.0% / 150.5% -> 199.8% / 149.3% | A média/mediana mudou pouco; cache/provedor é improvável como causa principal da lacuna road-only. |
| Mismatch multimodal antes/depois | 53.5% / 52.9% -> 60.8% / 63.7% | A média/mediana não melhorou materialmente; a lacuna permanece metodológica e de fronteira. |

O resultado rodoviário agregado ficou praticamente estável entre a execução original e o rerun. A diferença média absoluta caiu de 201.0% para 199.8%, e a mediana caiu de 150.5% para 149.3%. Essa mudança pequena reduz a plausibilidade de que a lacuna road-only seja explicada principalmente por instabilidade de cache ou provedor, mas não valida a magnitude exata das emissões rodoviárias calculadas.

No lado cabotagem/multimodal, o rerun também não resolveu o desvio em relação ao workbook. A diferença média absoluta aumentou de 53.5% para 60.8%, e a mediana aumentou de 52.9% para 63.7%. Portanto, o rerun preserva a conclusão de que o Batch 002 oferece apoio direcional, mas não reprodução calibrada do workbook nem reconciliação plena das premissas de distância, alocação, serviço, porto, port-ops/hoteling e fronteira ambiental.

A interpretação segura é que os registros Supabase/cache fortalecem a rastreabilidade e a reprodutibilidade computacional do rerun. Eles não são dados de mercado, não provam disponibilidade operacional ou viabilidade comercial e não transformam custos modelados em fretes comerciais. As emissões continuam sendo CO2e operacional TTW, salvo indicação explícita em contrário, e não WTW ou LCA. Assim, nenhum resultado do rerun prova superioridade universal da cabotagem, valida escolhas comerciais de serviço ou cria um `headline_candidate`.

### 7.5 Resultados da reconciliação rodoviária

A reconciliação rodoviária foi executada como diagnóstico de alinhamento com o benchmark Gustavo/Costa, mantendo fixas as mesmas distâncias rodoviárias cacheadas do rerun Supabase/cache. A pergunta testada foi restrita: quanto da lacuna road-only seria reduzida se as premissas rodoviárias do workbook fossem aplicadas apenas ao cálculo diagnóstico das emissões rodoviárias? Esse procedimento não substitui o modelo rodoviário de linha de base do CabotageLens, não altera fórmulas da aplicação e não sobrescreve os resultados do Batch 002.

O diagnóstico usou as premissas rastreadas `FDc = 0.28 L/km`, `FDe = 35.52 MJ/L` e `FDf = 86.5 gCO2eq/MJ`. A combinação documentada dessas premissas resulta no fator diagnóstico `0.8602944 kgCO2e/km`, aplicado às distâncias rodoviárias cacheadas já usadas no rerun. Como o próprio fator vem de uma fronteira de benchmark distinta, ele deve ser tratado como sensibilidade de alinhamento, não como fator operacional TTW substituto.

| Métrica diagnóstica | Valor baseline/rerun | Valor diagnóstico | Interpretação segura |
| --- | ---: | ---: | --- |
| Fator aplicado | Modelo rodoviário baseline do CabotageLens | 0.8602944 kgCO2e/km | Fator Gustavo/Costa usado apenas para diagnóstico de alinhamento. |
| Mismatch rodoviário médio absoluto | 199.8% | 43.9% | Redução material da lacuna road-only ao trocar apenas a premissa de fator rodoviário. |
| Mismatch rodoviário mediano absoluto | 149.3% | 19.6% | A mediana também cai fortemente, indicando sensibilidade sistemática às premissas rodoviárias. |
| Lacuna residual | Presente no rerun | Ainda presente | O diagnóstico reduz, mas não elimina, o desvio em relação ao workbook. |
| Limite de interpretação | Linha de base operacional TTW | Sensibilidade de benchmark | Não é recalibração, validação de magnitude ou substituição do baseline. |

O efeito numérico observado é expressivo. A diferença média absoluta do lado rodoviário caiu de 199.8% para 43.9%, enquanto a mediana caiu de 149.3% para 19.6%. Como as distâncias rodoviárias foram mantidas constantes, essa redução sustenta a leitura de que premissas de consumo de combustível e fator de emissão explicam grande parte da lacuna de magnitude road-only do Batch 002.

Essa redução, entretanto, não resolve integralmente o mismatch. A evidência rastreada ainda registra lacunas residuais, atribuíveis a diferenças de base de distância rodoviária, construção de rota, premissas de veículo e carregamento, alocação por contêiner, fronteira WTW versus TTW/operacional e hipóteses internas do workbook que não foram completamente extraídas. Portanto, o resultado deve permanecer como evidência diagnóstica, não como validação calibrada de magnitudes.

Também não se deve interpretar o diagnóstico como confirmação de que o workbook é verdade de referência. O workbook continua sendo uma camada externa de benchmark, útil para testar sensibilidade e coerência direcional, mas insuficiente para definir sozinho a fronteira correta do CabotageLens. O uso do fator Gustavo/Costa não autoriza misturar TTW, WTW, LCA, CO2 e CO2e como se fossem equivalentes, nem altera a leitura das emissões do relatório, que permanecem CO2e operacional TTW salvo indicação explícita em contrário.

Por fim, a reconciliação rodoviária não altera a fronteira econômica nem operacional do trabalho. Custos continuam sendo estimativas modeladas, não fretes comerciais, tarifas ou cotações de mercado. O diagnóstico não prova disponibilidade de serviço, viabilidade comercial, execução operacional real ou superioridade universal da cabotagem, e não cria um `headline_candidate`. Sua contribuição no Capítulo 7 é registrar o efeito numérico observado de uma hipótese rodoviária específica; a discussão das implicações metodológicas permanece para o Capítulo 8.

### 7.6 Síntese da interpretação numérica segura

A leitura conjunta do Capítulo 7 permite uma conclusão numérica conservadora, mas útil. As sensibilidades executadas, o Batch 002, o rerun Supabase/cache e a reconciliação rodoviária apontam para uma direção metodológica coerente: sob as hipóteses nomeadas e dentro das fronteiras rastreadas, a alternativa multimodal tende a aparecer favorável em emissões frente ao rodoviário direto. Essa conclusão, porém, é direcional e metodológica, não uma validação calibrada, universal ou comercial.

| Grupo de evidência | Observação numérica | Conclusão segura | O que não sustenta |
| --- | --- | --- | --- |
| Sensibilidades executadas | Três linhas executadas, todas classificadas como `sensitive`. | A direção modelada favorece o multimodal sob hipóteses nomeadas de distância ou porto alternativo. | Conclusões robustas de linha de base, validação do porto original ou viabilidade comercial. |
| Batch 002 direcional | 21/21 pares OD positivos e suportados alinhados em direção, com 21 x `same_direction_large_gap`. | O benchmark externo apoia consistência direcional de emissões. | Reprodução exata do workbook, validação calibrada de magnitude ou workbook como verdade absoluta. |
| Rerun Supabase/cache | 63 route-cache hits, 0 misses e distâncias rodoviárias cacheadas; mismatch rodoviário praticamente estável em 199.8% / 149.3%. | A instabilidade de cache/provedor é improvável como principal causa da lacuna road-only. | Validação de magnitude, disponibilidade comercial de rota ou prova de serviço contratado. |
| Reconciliação rodoviária | Mismatch rodoviário médio/mediano reduzido de 199.8% / 149.3% para 43.9% / 19.6%. | Premissas rodoviárias explicam parte substancial da lacuna de magnitude road-only. | Recalibração do CabotageLens, substituição do baseline ou eliminação total do mismatch. |
| Status final de resultado principal | 0 `headline_candidate`. | O uso seguro é apresentar evidência direcional, diagnóstica e condicionada. | Afirmação robusta de superioridade universal da cabotagem. |

As sensibilidades do Batch 001B são importantes porque mostram comportamento do modelo sob hipóteses explícitas. Nos três cenários executados, o multimodal permanece menor em custo modelado e em CO2e operacional TTW, mas cada linha continua `sensitive`. Elas não validam automaticamente Santos/Manaus como linha de base robusta, não transformam Pecém em Porto de Fortaleza, não transformam Suape em Porto do Recife e não provam aceitação operacional por transportador.

O Batch 002 amplia a evidência por meio de um benchmark externo, mas seu resultado seguro também é limitado. O alinhamento 21/21 indica que workbook e CabotageLens apontam a mesma direção modal para os pares comparáveis, enquanto a classificação `same_direction_large_gap` mantém visível que a magnitude ainda diverge. Portanto, o lote apoia consistência direcional, não calibração contra Gustavo/Costa, reprodução exata de rotas, validação de serviços ou confirmação de fretes.

O rerun Supabase/cache e a reconciliação rodoviária ajudam a separar duas explicações. O rerun reduz a hipótese de que a lacuna road-only seja causada principalmente por instabilidade computacional de cache ou provedor. A reconciliação rodoviária, por sua vez, mostra que premissas de consumo e fator de emissão explicam muito da diferença de magnitude no lado rodoviário. Ainda assim, cache estável não valida magnitude, e fator diagnóstico não recalibra nem substitui o modelo de linha de base.

Assim, a síntese numérica segura é que os resultados atuais sustentam uma interpretação direcional e metodológica: há evidência de comportamento favorável ao multimodal em cenários específicos e evidência de que parte relevante do desalinhamento com o benchmark decorre de premissas rodoviárias e fronteiras não reconciliadas. Não há evidência suficiente para promover qualquer caso a `headline_candidate`, declarar superioridade universal da cabotagem, provar disponibilidade de serviço, viabilidade comercial, aceitação por transportador, disponibilidade de slot ou frete contratado.

As fronteiras materiais permanecem inalteradas ao fechar o capítulo. Custos são estimativas modeladas, não tarifas, cotações ou fretes comerciais. Emissões são CO2e operacional TTW, salvo indicação explícita em contrário. TTW, WTW, LCA, CO2 e CO2e não devem ser misturados sem reconciliação metodológica explícita. Com esses limites, o Capítulo 7 apresenta resultados numericamente úteis, mas preserva para o Capítulo 8 a discussão mais ampla sobre implicações, limitações e trabalho futuro.

## 8. Discussao

### 8.1 Alcance das evidências e leitura conservadora

O Capítulo 8 interpreta a evidência apresentada no Capítulo 7, sem acrescentar novos resultados numéricos nem alterar a classificação das linhas já rastreadas. A passagem dos resultados para a discussão exige uma leitura conservadora: a evidência atual é útil para explicar direção, comportamento do método e limites de interpretação, mas não para sustentar uma conclusão universal, calibrada ou comercial sobre a cabotagem.

A leitura mais segura é direcional e metodológica. As sensibilidades executadas mostram comportamento modelado favorável às alternativas multimodais sob hipóteses nomeadas, mas continuam sendo sensibilidades. Elas não substituem conclusões de linha de base, não validam automaticamente os corredores originais e não demonstram, por si só, disponibilidade real de serviço, aceitação por transportadores, disponibilidade de slot, viabilidade comercial ou fretes contratados.

O Batch 002 amplia a discussão por introduzir um benchmark externo Gustavo/Costa, porém seu papel também é limitado. O resultado apoia consistência direcional entre o workbook e o CabotageLens nas linhas comparáveis, enquanto a classificação rastreada permanece `same_direction_large_gap`. Portanto, concordância direcional não deve ser escrita como validação calibrada de magnitude, reprodução exata do workbook ou prova de que o CabotageLens foi calibrado contra Gustavo/Costa.

| Grupo de evidência | O que sustenta | O que não sustenta |
| --- | --- | --- |
| Sensibilidades executadas | Comportamento favorável do multimodal sob hipóteses documentadas. | Conclusões de linha de base, validação externa ou superioridade universal da cabotagem. |
| Batch 002 benchmark | Apoio externo direcional, com linhas comparáveis classificadas como `same_direction_large_gap`. | Calibração de magnitude, reprodução exata do workbook ou equivalência a fretes comerciais. |
| Rerun Supabase/cache | Estabilidade computacional, rastreabilidade e menor plausibilidade de instabilidade de provedor/cache como causa principal da lacuna. | Validação de magnitude, disponibilidade operacional, disponibilidade de serviço ou preço contratado. |
| Reconciliação de fator rodoviário | Explicação diagnóstica de parte da lacuna road-only por premissas rodoviárias. | Recalibração do modelo, substituição do baseline ou validação plena do benchmark. |
| Classificação final para uso no TF | Interpretação direcional, diagnóstica e condicionada. | Promoção de qualquer resultado atual a `headline_candidate`. |

O rerun Supabase/cache e a reconciliação rodoviária ajudam a separar explicações, mas não eliminam as cautelas centrais. A evidência de cache apoia estabilidade e rastreabilidade computacional; ela não transforma uma rota modelada em serviço contratado nem valida magnitude absoluta. A reconciliação de fator rodoviário explica parte relevante da diferença no lado rodoviário, mas é um diagnóstico de alinhamento, não uma recalibração do modelo de linha de base nem uma autorização para substituir premissas do CabotageLens.

As fronteiras econômica e ambiental permanecem inalteradas nesta discussão. Custos são estimativas modeladas, não tarifas, cotações, fretes comerciais ou preços praticados. Emissões são CO2e operacional TTW, salvo indicação explícita em contrário. TTW, WTW, LCA, CO2 e CO2e não devem ser misturados como se fossem equivalentes, nem usados para validar resultados sem uma reconciliação metodológica explícita de fronteira, unidade e métrica.

Desse modo, o Capítulo 8 deve partir de uma conclusão deliberadamente estreita: os resultados atuais indicam comportamento multimodal favorável em cenários específicos e apoio externo direcional, mas não provam superioridade universal da cabotagem, viabilidade comercial, disponibilidade de serviço, aceitação por transportadores, disponibilidade de slot ou fretes contratados. Nenhum resultado corrente qualifica-se como `headline_candidate`; a contribuição defensável do trabalho está na estrutura auditável, na explicitação de fronteiras e na disciplina de classificar o que cada evidência pode e não pode sustentar.

### 8.2 Dependência por corredor, porto e distância marítima

A interpretação dos resultados do CabotageLens depende do corredor analisado, da cadeia de portos adotada e da fronteira de rota usada para construir a alternativa multimodal. A direção ambiental e econômica de uma configuração rodoviário-cabotagem-rodoviário não é uma propriedade abstrata da cabotagem; ela nasce da combinação entre acesso rodoviário ao porto de origem, perna marítima, acesso rodoviário final, componentes portuários modelados e premissas de distância. Por isso, os resultados do Capítulo 7 devem ser lidos como cenários condicionais, não como achados universais de rota.

A escolha do porto não é um parâmetro cosmético. Alterar o porto de origem ou destino muda as pernas rodoviárias de acesso, a distância marítima, a coerência operacional da cadeia e a interpretação do resultado. Um porto alternativo pode ser útil para testar uma hipótese explícita, mas passa a representar outro cenário. Assim, Pecém não valida Porto de Fortaleza, e Suape não valida Porto do Recife; as sensibilidades com esses portos devem permanecer identificadas como cenários alternativos, sem substituição silenciosa dos portos originalmente selecionados.

A proveniência da distância marítima é igualmente decisiva. Distâncias classificadas como `haversine_fallback` ou apoiadas em evidência fraca funcionam como estimativas de triagem e podem preservar rastreabilidade histórica, mas não bastam para sustentar validação robusta de rota. A sensibilidade Santos/Manaus com distância marítima documentada mostra como uma referência mais forte pode alterar a leitura de um caso específico, mas continua sendo uma sensibilidade nomeada; ela não prova que todos os casos baseados em fallback sejam válidos, nem transforma sensibilidade em resultado de linha de base.

| Questão de rota/porto | Por que importa | Interpretação segura |
| --- | --- | --- |
| Caso same-port | A perna marítima deixa de representar uma cadeia normal de cabotagem. | Santos/Santos é exemplo de limitação ou exclusão, não desempenho normal da cabotagem. |
| Distância marítima por fallback | A estimativa geométrica não documenta plenamente a rota marítima. | `haversine_fallback` preserva diagnóstico, mas não sustenta conclusão robusta sozinho. |
| Sensibilidade de distância de referência | Testa uma distância documentada para um par de portos específico. | Santos/Manaus é resultado de sensibilidade, não validação geral de casos fallback. |
| Sensibilidade Pecém | Altera o porto de destino e a cadeia de acesso. | Pecém é cenário alternativo e não valida Porto de Fortaleza. |
| Sensibilidade Suape | Altera o porto de destino e a cadeia de acesso. | Suape é cenário alternativo e não valida Porto do Recife. |
| Pernas rodoviárias de acesso | Pré-carriage e on-carriage mudam distância, custo modelado e TTW CO2e. | O resultado deve ser lido porta a porta, não como comparação marítima isolada. |

O caso same-port Santos/Santos ilustra o limite mais evidente da construção de rota. Quando origem e destino marítimos recaem no mesmo porto, a cadeia deixa de representar uma alternativa normal de cabotagem entre portos distintos. Esse tipo de registro pode ser útil para documentar aviso, exclusão ou comportamento de seleção de portos, mas não deve ser usado como evidência de desempenho modal da cabotagem.

Também é necessário separar construção de rota de disponibilidade operacional. Uma rota modelada, mesmo quando rastreável e coerente como cenário acadêmico, não prova que exista serviço de cabotagem disponível, frequência adequada, aceitação por armador, slot contratado, terminal disponível, prazo competitivo ou viabilidade comercial. O CabotageLens organiza uma comparação auditável sob fronteiras explícitas; ele não substitui uma análise de rede de serviços nem uma cotação de mercado.

Por fim, as fronteiras de interpretação permanecem as mesmas da seção anterior. Custos continuam sendo estimativas modeladas, não fretes comerciais, tarifas ou cotações contratadas. Emissões continuam sendo CO2e operacional TTW, salvo mudança explícita de fronteira. Portanto, uma sensibilidade favorável em custo modelado e TTW CO2e deve ser discutida como comportamento condicionado por corredor, porto, distância e fronteira de rota, e não como prova de superioridade universal da cabotagem ou como resultado robusto de linha de base.

### 8.3 Interpretação do Batch 002 e das lacunas de magnitude

O Batch 002 fortalece o relatório porque desloca parte da discussão para fora das saídas internas do próprio CabotageLens. Ao comparar o modelo com o workbook Gustavo/Costa, o trabalho passa a ter uma camada externa de benchmark para testar se a direção modal observada internamente aparece também em uma referência independente. Esse ganho, porém, deve ser interpretado com rigor: o benchmark é útil como contraste externo, não como verdade absoluta nem como calibração automática do modelo.

O resultado direcional é claro dentro do conjunto comparável: os 21 pares OD positivos e suportados indicam menor emissão para a alternativa de cabotagem/multimodal tanto no workbook quanto no CabotageLens. Essa concordância sustenta uma afirmação limitada, mas relevante, de consistência direcional em emissões. Ela não autoriza afirmar que o CabotageLens reproduziu Gustavo/Costa, que as magnitudes foram validadas exatamente ou que a cabotagem é universalmente superior.

Ao mesmo tempo, a classificação de todas as linhas comparáveis permanece `same_direction_large_gap`. Essa classificação é central para a discussão e não deve ser suavizada. Ela significa que o sinal modal é coerente, mas que as diferenças de magnitude continuam grandes o suficiente para impedir validação calibrada. Tratar essas lacunas como detalhe menor apagaria justamente uma das contribuições metodológicas do Batch 002: tornar visíveis as fronteiras, premissas e incompatibilidades que ainda precisam ser reconciliadas.

| Achado do Batch 002 | Significado na discussão | Limite de interpretação |
| --- | --- | --- |
| 21/21 de alinhamento direcional | O benchmark externo e o CabotageLens apontam a mesma direção modal nas linhas comparáveis. | Direção não equivale a validação calibrada. |
| 21 linhas `same_direction_large_gap` | A concordância convive com lacunas materiais de magnitude. | Não há reprodução exata do workbook nem `headline_candidate`. |
| Células puladas do workbook | Nem toda a matriz era comparável ou executável no modelo atual. | Não se deve tratar todos os dados do workbook como evidência de comparação. |
| Lacuna no lado rodoviário | Premissas de distância, consumo, fator de emissão, veículo, carga e alocação podem explicar parte do desvio. | A reconciliação rodoviária é diagnóstica, não recalibração do baseline. |
| Lacuna no lado multimodal | Portos, lógica de serviço, rota marítima, port-ops/hoteling, alocação e fronteira ambiental podem divergir. | O desvio multimodal não fica resolvido pelo alinhamento direcional. |
| Papel do benchmark | Fornece contraste externo e disciplina de comparação. | O workbook não é verdade de referência (`ground truth`) e não valida preços, fretes, rotas ou serviços. |

As lacunas de magnitude podem ter várias origens plausíveis e cumulativas. No lado rodoviário, podem refletir diferenças de base de distância, premissas de consumo, fator de emissão, veículo, carregamento e alocação por contêiner. No lado multimodal, podem decorrer de distância marítima, seleção de portos, lógica de serviço, tratamento de operações portuárias e hoteling, premissas de embarcação, regra de alocação e fronteira ambiental. Essas possibilidades não devem ser usadas para desqualificar o benchmark, mas para enquadrá-lo corretamente como evidência metodológica com fronteiras ainda não reconciliadas.

O rerun Supabase/cache e a reconciliação rodoviária ajudam a organizar essa leitura. O rerun reduz a hipótese de que a divergência seja principalmente instabilidade de provedor ou cache; a reconciliação rodoviária mostra que premissas rodoviárias explicam parte relevante da lacuna no lado road-only. Nenhum dos dois passos, entretanto, resolve integralmente a diferença de magnitude, substitui o modelo de linha de base ou transforma o workbook em referência normativa.

Portanto, o uso seguro do Batch 002 no TF é afirmar apoio direcional externo com lacunas de magnitude explícitas. O lote não prova viabilidade comercial, disponibilidade de serviço, escolha real de rotas, frequência, preços praticados ou fretes contratados. Custos continuam sendo estimativas modeladas, e emissões continuam sendo CO2e operacional TTW, salvo indicação explícita em contrário. Com esses limites, o Batch 002 contribui para uma defesa acadêmica mais forte justamente porque combina evidência externa favorável em direção com transparência sobre aquilo que ainda não está calibrado.

### 8.4 Papel do cache, da rastreabilidade e da reconciliação rodoviária

O rerun com Supabase/cache e a reconciliação rodoviária não acrescentam uma nova conclusão de desempenho modal; eles qualificam a interpretação do Batch 002. Seu papel principal é separar hipóteses de erro operacional, como instabilidade de cache ou de provedor, de diferenças metodológicas mais profundas entre o CabotageLens e o benchmark externo. Essa distinção é importante porque uma lacuna de magnitude pode ter origens muito diferentes: pode decorrer de execução instável, de premissas incompatíveis ou de fronteiras analíticas distintas.

No caso do cache, a estabilidade dos registros rodoviários e a repetição rastreável das distâncias tornam improvável que a instabilidade de provedor ou cache seja a principal explicação para a lacuna no lado rodoviário. Isso fortalece a auditabilidade do resultado, pois mostra que a comparação pode ser reproduzida dentro da infraestrutura de dados usada pelo projeto. Essa estabilidade, porém, não valida magnitude exata, não transforma o benchmark em calibração e não prova disponibilidade comercial. Registros de cache são evidência computacional, não evidência de mercado; do mesmo modo, acertos de route-cache não demonstram existência de serviço contratado, frequência, capacidade, aceite por transportador, slot ou rota comercial efetivamente disponível.

A reconciliação rodoviária deve ser lida com a mesma cautela. O exercício indica que premissas de fator rodoviário, consumo e fronteira ambiental explicam parte relevante da diferença de magnitude no componente road-only. Ao reduzir a lacuna, ele torna a discussão mais específica: a divergência não precisa ser tratada como um desvio opaco, pois há indícios de que parte dela está associada ao lado rodoviário da comparação. Ainda assim, a reconciliação é diagnóstica, não normativa. O fator diagnóstico não substitui o modelo de linha de base do CabotageLens, o aplicativo não foi recalibrado, e as saídas de baseline permanecem as apresentadas no Capítulo 7.

| Verificação | O que reduz ou descarta | O que permanece em aberto |
| --- | --- | --- |
| Supabase/cache rerun | Reduz a hipótese de que a lacuna seja explicada principalmente por instabilidade de cache, provedor ou repetição computacional. | Não valida magnitude exata, serviço disponível, rota comercial, preço ou frete contratado. |
| Reconciliação rodoviária | Mostra que premissas rodoviárias explicam parte importante do desvio no lado road-only. | É diagnóstico apenas; não recalibra o aplicativo nem substitui o baseline. |
| Lacuna rodoviária residual | Torna a explicação mais estreita e mais rastreável. | Diferenças residuais de distância, fronteira, alocação, veículo ou carga ainda podem permanecer. |
| Lacuna multimodal | Evita atribuir toda a divergência ao componente rodoviário. | Permanecem diferenças potenciais de porto, rota marítima, operação portuária, alocação e lógica de serviço. |
| Contribuição de auditabilidade | Documenta o que foi reexecutado, comparado e diagnosticado. | Auditabilidade não equivale a validação calibrada nem a evidência comercial. |

Essas verificações, portanto, estreitam o espaço de explicações prováveis sem fechar a questão. O cache reduz a suspeita de instabilidade computacional; a reconciliação rodoviária reduz parte da incerteza sobre o lado road-only; mas lacunas residuais continuam presentes, inclusive no componente multimodal. O resultado metodologicamente seguro é reconhecer que os desvios são mais interpretáveis do que seriam sem esses testes, mas continuam insuficientes para sustentar validação calibrada ou reprodução exata do workbook.

A contribuição mais importante dessas etapas é a transparência. Elas mostram que o trabalho não apenas observou uma divergência, mas também testou hipóteses plausíveis sobre sua origem e preservou a trilha de execução. Isso reforça a reprodutibilidade do estudo e torna mais claro o que pode ser defendido: apoio direcional externo, estabilidade computacional e diagnóstico parcial da lacuna rodoviária. Não autoriza, entretanto, afirmar que o modelo foi ajustado para coincidir com Gustavo/Costa, que o Batch 002 valida magnitudes exatas ou que os resultados possam ser usados como evidência comercial de contratação logística.

Por fim, as mesmas fronteiras do relatório continuam válidas. Custos continuam sendo estimativas modeladas, não fretes de mercado, tarifas ou cotações contratadas. Emissões continuam sendo CO2e operacional TTW, salvo indicação explícita em contrário; TTW, WTW, LCA, CO2 e CO2e não devem ser misturados na interpretação. Com esses limites, cache, rastreabilidade e reconciliação rodoviária funcionam como instrumentos de defesa metodológica, não como recalibração do CabotageLens nem como solução completa das lacunas de magnitude.

### 8.5 Relação com a literatura de short sea shipping e mudança modal

Os resultados discutidos neste capítulo são coerentes com uma leitura recorrente da literatura de short sea shipping e cabotagem: o transporte marítimo costeiro pode reduzir emissões em certos contextos, especialmente quando a comparação considera cadeias porta a porta, mas essa vantagem não é automática nem universal [shortsea2019] [modalshiftreview2020]. Essa relação com a literatura deve ser usada como enquadramento interpretativo, não como validação substituta das classificações dos Capítulos 6 e 7. As categorias `sensitive`, `same_direction_large_gap`, `benchmark_boundary_mismatch` e a ausência de `headline_candidate` continuam sendo definidas pelos artefatos de validação do próprio projeto, não por afirmações gerais encontradas em estudos externos.

A literatura ajuda a explicar por que os resultados do CabotageLens precisam ser lidos por corredor. Estudos de short sea shipping ressaltam que distância, acessos terrestres, utilização da embarcação, tipo de serviço, operações portuárias e hipóteses de roteamento afetam a direção e a magnitude da comparação [shortsea2019]. Esse ponto converge com os resultados do Capítulo 7 e com a discussão das seções anteriores: sensibilidades favoráveis sob portos, distâncias e fronteiras nomeadas não se transformam em uma regra geral para todas as rotas, nem validam automaticamente casos com distância marítima fraca, porto alternativo ou cadeia same-port.

O mesmo vale para a literatura de mudança modal. Revisões sobre transferência de carga da rodovia para o transporte marítimo costeiro mostram que a decisão real envolve dimensões econômicas, ambientais e de qualidade de serviço, incluindo frequência, confiabilidade, integração terrestre, tempo de trânsito, disponibilidade e organização institucional [modalshiftreview2020]. O CabotageLens contribui para essa discussão ao tornar explícita uma camada de custo modelado e CO2e operacional TTW, mas não resolve sozinho a decisão modal completa. Uma rota modelada não prova serviço disponível, aceitação por armador ou transportador, slot operacional, frequência contratável ou viabilidade comercial.

No contexto brasileiro, a literatura sobre cabotagem reforça tanto o potencial ambiental e logístico quanto os gargalos operacionais, regulatórios, de infraestrutura e de rede [icct2022] [competitiveness2024]. Esse enquadramento é compatível com a contribuição do trabalho: oferecer uma estrutura transparente para comparar alternativas rodoviárias e rodoviário-cabotagem-rodoviário em cenários específicos. O resultado não é uma demonstração de que a cabotagem brasileira seja comercialmente viável para todos os pares OD, nem uma solução do problema nacional de otimização multimodal. Ele é uma ferramenta de comparação rastreável, sujeita às fronteiras e classificações já documentadas.

| Tema da literatura | Relação com os achados do CabotageLens | Limite para este TF |
| --- | --- | --- |
| Potencial ambiental do short sea shipping | Ajuda a contextualizar por que alternativas multimodais podem ser favoráveis em alguns corredores [shortsea2019]. | Não prova que as rotas testadas sejam validadas, nem que a cabotagem seja sempre mais limpa. |
| Competitividade específica por corredor | Reforça que distância, acesso portuário, utilização e roteamento afetam o resultado [shortsea2019] [competitiveness2024]. | Não substitui a classificação de sensibilidade, fallback ou limitação dos casos do Capítulo 7. |
| Barreiras de mudança modal | Mostra que custo e emissões são apenas parte da decisão logística [modalshiftreview2020]. | Não demonstra disponibilidade de serviço, frequência, slot, aceitação de transportador ou frete contratado. |
| Descarbonização da cabotagem brasileira | Situa a cabotagem como tema relevante para política e transição energética no Brasil [icct2022] [decarb2024]. | Valores WTW, LCA, CO2 ou CO2e de fronteira distinta não validam a saída operacional TTW CO2e do CabotageLens. |
| Abordagens de super-rede multimodal | Oferece contraste com modelos que incorporam serviços, frequência, custos comerciais e rede completa [competitiveness2024]. | O CabotageLens não resolve a otimização nacional multimodal nem funciona como cotador de frete. |
| Ferramentas físico-emissivas de comparação | Inspira leituras espaciais e futuras visualizações de sensibilidade [isoemission2019]. | Não implica que o CabotageLens já implemente mapa de iso-emissão nem valida magnitudes por literatura. |

Essa leitura também protege a fronteira ambiental. Parte da literatura usa CO2, CO2e, WTW ou LCA em contextos diferentes dos adotados aqui [decarb2024] [maritimelca2024]. Esses trabalhos são relevantes para situar limitações e futuras expansões, mas não devem ser misturados com o resultado atual como se fossem a mesma métrica. Neste TF, a saída ambiental continua sendo CO2e operacional TTW, salvo indicação explícita de outra fronteira; portanto, uma conclusão WTW, LCA ou CO2-only da literatura não valida, corrige ou substitui a métrica TTW CO2e do CabotageLens.

A fronteira econômica exige cuidado semelhante. Estudos de competitividade podem tratar fretes comerciais, margens, inventário, confiabilidade, frequência e estrutura de rede [competitiveness2024], enquanto o CabotageLens reporta custos modelados sob uma fronteira operacional mais restrita. Assim, a literatura pode explicar por que a viabilidade comercial depende de mais elementos que o custo calculado, mas não transforma os resultados em tarifas, cotações ou fretes contratados. Declarações externas sobre custo ou competitividade também não validam os custos estimados pelo modelo para uma rota específica.

Com esses limites, a relação com a literatura é positiva, mas conservadora. Os resultados do CabotageLens se alinham à ideia de que a cabotagem pode ser ambientalmente promissora em situações específicas e que a mudança modal exige análise porta a porta, sensibilidade a corredor e atenção a serviço e custo total. A contribuição do TF, entretanto, não é provar superioridade universal da cabotagem, nem substituir estudos de super-rede ou validação comercial. É oferecer uma estrutura computacional transparente para comparação rota a rota, capaz de mostrar onde a evidência é favorável, onde é apenas sensível e onde ainda permanece limitada.

### 8.6 Hotelling, operações portuárias e fronteiras ambientais

A comparação entre alternativa rodoviária direta e alternativa rodoviário-cabotagem-rodoviário não termina na distância marítima. A etapa portuária importa porque navios continuam consumindo energia enquanto permanecem atracados ou em operação associada à carga, seja para serviços de bordo, sistemas auxiliares, espera, carregamento ou descarga [berth2009] [shipops2022]. Por isso, hoteling e operações portuárias podem alterar a comparação ambiental total entre cadeias modais, especialmente quando a análise busca uma leitura porta a porta e não apenas uma comparação entre caminhão e trecho marítimo.

No CabotageLens, esses componentes devem ser interpretados como contribuição operacional modelada dentro da fronteira do estudo, não como inventário completo de emissões portuárias. A presença de hoteling ou de componentes portuários modelados melhora a visibilidade de uma parte relevante da cadeia multimodal, mas não substitui dados específicos de terminal, escala, navio, produtividade, energia auxiliar ou operação real. O resultado continua sendo uma aproximação rastreável para comparação de cenários, e não uma medição terminal-específica.

| Fator porto/berço | Por que importa | Fronteira neste TF |
| --- | --- | --- |
| Tempo de hotelling | Afeta o período em que o navio consome energia enquanto está atracado ou aguardando operação. | Componente operacional modelado quando explicitamente incluído; não valida tempos reais de escala. |
| Energia auxiliar no berço | Alimenta serviços de bordo e sistemas necessários durante a estadia no porto. | Emissão operacional TTW CO2e; não substitui dados de motor auxiliar, combustível real ou eletrificação local. |
| Produtividade de carga/descarga | Influencia duração de berço e intensidade operacional associada à movimentação. | Parâmetro de cenário ou limitação; não prova produtividade terminal-específica. |
| Disponibilidade de terminal/serviço | Condiciona a viabilidade operacional da cadeia multimodal. | Fora do escopo de validação comercial; rota modelada não comprova serviço, frequência ou slot. |
| Poluentes atmosféricos locais | NOx, SOx, PM, CO e VOC podem ser relevantes para qualidade do ar local [berthairquality2010]. | Não há modelagem de dispersão, concentração, exposição ou impacto à saúde. |
| Descarbonização WTW/LCA de combustíveis | Ajuda a discutir combustíveis e trajetórias futuras [decarb2024] [maritimelca2024]. | Contexto e trabalho futuro; não substitui a linha de base operacional TTW CO2e. |

As variáveis que controlam emissões em berço são mais amplas que as variáveis necessárias para uma estimativa simplificada. Tempo de permanência, potência auxiliar, tipo de embarcação, combustível, regime de operação, produtividade de carregamento e descarga, disponibilidade de energia em terra e práticas do terminal podem modificar o resultado [shipops2022]. O presente TF não valida esses elementos para terminais específicos e não incorpora dados AIS, janelas de escala, programação de navios, medições de motor auxiliar ou registros operacionais de terminal como base calibrada.

Também é importante separar a contabilização de CO2e operacional de uma avaliação de qualidade do ar. Fontes sobre emissões em porto e impactos locais ajudam a lembrar que a operação atracada pode ter consequências além do carbono [berthairquality2010]. Ainda assim, este relatório não realiza modelagem de dispersão atmosférica, concentração local, exposição populacional ou impactos à saúde, nem estima inventário completo de poluentes como NOx, SOx, material particulado, CO ou VOC. Esses temas pertencem a uma análise ambiental portuária mais específica do que a fronteira atual do CabotageLens.

A disciplina de fronteira ambiental é, portanto, central para interpretar os resultados. A métrica do relatório é CO2e operacional TTW, salvo indicação explícita em contrário. Literatura de descarbonização marítima, combustíveis alternativos, WTW ou LCA é relevante para contextualizar futuras extensões, mas não deve ser misturada com a saída atual como se fosse a mesma métrica [decarb2024] [maritimelca2024]. Do mesmo modo, resultados CO2-only de fontes externas não devem ser tratados como equivalentes a CO2e sem reconciliação explícita de gases, unidade funcional e fronteira.

Essas cautelas não reduzem a importância de incluir o tema portuário na discussão; ao contrário, mostram por que ele deve aparecer de forma limitada e transparente. Se hoteling e operações portuárias forem ignorados, a alternativa multimodal pode parecer mais simples do que realmente é. Se forem superinterpretados, o modelo passa a sugerir uma precisão terminal-específica que não possui. A interpretação segura está entre esses extremos: reconhecer que emissões de berço e operação portuária podem afetar a comparação, mas tratá-las como componentes modelados e condicionais.

Por fim, a presença de custos portuários ou operacionais modelados não transforma o resultado em frete comercial. Custos continuam sendo estimativas modeladas, não tarifas portuárias completas, cotações, contratos ou fretes praticados. A inclusão de hotelling ou operações portuárias tampouco comprova disponibilidade de terminal, janela de atracação, frequência de serviço, escala real ou aceitação comercial. Assim, a contribuição da seção é reforçar a leitura de fronteira: portos e berços importam para a comparação, mas a evidência atual permanece operacional, modelada e não calibrada para inventário portuário completo.

### 8.7 Implicações para uso do CabotageLens como apoio à decisão

O CabotageLens pode ser usado de forma responsável como um protótipo acadêmico de apoio à decisão, desde que o termo "apoio" seja interpretado com rigor. A ferramenta organiza uma comparação transparente entre alternativa rodoviária direta e alternativa rodoviário-cabotagem-rodoviário, expondo rotas, portos, fontes de distância, custos modelados, CO2e operacional TTW e classificações de evidência. Seu valor principal está em tornar a discussão técnica mais rastreável, não em automatizar uma decisão logística final.

O uso mais forte do protótipo é exploratório, metodológico e educacional. Ele permite comparar cenários, testar a sensibilidade de escolhas de porto e distância, identificar quando uma rota depende de premissas frágeis e mostrar como fronteiras de custo e emissões alteram a leitura do resultado. Nesse sentido, o número final não deve ser separado dos avisos, classificações e metadados de proveniência. Um resultado com `haversine_fallback`, status `sensitive`, lacuna de benchmark ou ressalva de serviço comunica algo diferente de um resultado com fonte mais forte e fronteira mais bem documentada.

| Uso responsável | O que a ferramenta sustenta | O que ainda requer validação externa |
| --- | --- | --- |
| Triagem de cenários | Comparar, sob premissas explícitas, cadeias road-only e road-cabotage-road. | Decisão final de contratação, prazo, risco operacional e disponibilidade real. |
| Comparação de rota/porto | Mostrar como seleção de portos, acessos terrestres e distância marítima afetam o resultado. | Consulta a operadores, terminais, armadores e serviços efetivamente ofertados. |
| Consciência de fronteira | Evidenciar que custos são modelados e emissões são CO2e operacional TTW. | Fretes comerciais, tarifas negociadas, WTW, LCA ou escopos ambientais ampliados. |
| Análise de sensibilidade | Explorar hipóteses documentadas sem confundi-las com baseline validado. | Calibração operacional, validação externa de magnitude e dados comerciais. |
| Relato acadêmico | Preservar rastreabilidade, classificação e limites de interpretação. | Generalizações universais ou promoção de resultados a decisão de negócio. |
| Decisão comercial | Estruturar perguntas para validação posterior. | Reserva de frete, agenda, slot, aceite de terminal, aceite de transportador e viabilidade contratual. |

Essa distinção é essencial porque a ferramenta não reserva frete, não consulta disponibilidade de linha e não confirma janela operacional. Ela não prova disponibilidade de serviço de cabotagem, agenda, slot, aceitação de terminal, aceitação de armador ou transportador, nem viabilidade comercial de uma cadeia específica. Também não produz cotações de frete de mercado, tarifas negociadas ou taxas contratadas. Esses elementos exigem consulta externa a operadores, terminais, transportadores, armadores, agentes de carga e dados comerciais atualizados.

O CabotageLens também não deve ser lido como um otimizador nacional completo. A seleção de portos e a construção de rotas fornecem cenários determinísticos e auditáveis, mas não resolvem uma super-rede multimodal com múltiplas linhas, frequências, capacidades, transbordos, tempos de espera, estoques, restrições comerciais e alternativas concorrentes. Pelo mesmo motivo, o protótipo não é um sistema calibrado de despacho operacional. Ele não decide qual veículo, navio, terminal, janela ou operador deve ser usado em uma operação real.

Para uso acadêmico e técnico, a implicação prática é que cada saída deve ser lida como condicional. A confiabilidade da interpretação depende das entradas fornecidas, da proveniência das distâncias, da escolha de portos, da fronteira econômica, da fronteira ambiental e da classificação de validação. Custos permanecem estimativas modeladas, não fretes comerciais. Emissões permanecem CO2e operacional TTW, salvo indicação explícita em contrário; WTW, LCA, CO2 e CO2e não devem ser misturados sem reconciliação metodológica.

Com esses limites, o protótipo é útil justamente porque estrutura perguntas melhores para etapas posteriores. Ele ajuda a identificar quais rotas merecem investigação comercial, quais premissas precisam de fonte mais forte, quais resultados dependem de sensibilidade e quais lacunas devem ser levadas a operadores, terminais ou bases comerciais. Assim, o CabotageLens apoia triagem, comparação técnica e argumentação acadêmica, mas a passagem de um cenário favorável para uma decisão logística real requer validação externa de serviço, preço, capacidade, contrato e operação.

### 8.8 Contribuição metodológica do framework auditável

A contribuição central deste trabalho não é um ranking modal universal entre rodovia e cabotagem. Ela é metodológica: construir e documentar um framework auditável, conservador e orientado por cenários para comparar alternativas rodoviárias diretas e alternativas rodoviário-cabotagem-rodoviário sob fronteiras explícitas. Essa formulação é importante porque evita transformar resultados favoráveis em prova geral de superioridade da cabotagem e mantém visível que cada conclusão depende de rota, porto, distância, premissas de custo, fronteira ambiental e qualidade da evidência disponível.

O CabotageLens combina, em um mesmo fluxo, construção de rota, estimativa de custo modelado, estimativa de CO2e operacional TTW, avisos de qualidade, proveniência de distância, classificação de validação, sensibilidades e comparação com benchmark externo. O valor dessa combinação está em tratar o resultado como um conjunto rastreável de evidências, não como uma resposta única e opaca. Quando uma distância é frágil, quando um porto é alternativo, quando uma linha é apenas sensibilidade ou quando uma lacuna de benchmark permanece grande, essa fragilidade aparece como parte da interpretação.

| Elemento metodológico | Contribuição | Limitação remanescente |
| --- | --- | --- |
| Construção de rota | Organiza cadeias road-only e road-cabotage-road de forma explícita e comparável. | Não comprova operação real, disponibilidade de serviço, agenda ou aceitação comercial. |
| Fronteira de custo e emissões | Mantém custos como estimativas modeladas e emissões como CO2e operacional TTW. | Não produz fretes comerciais, WTW, LCA ou inventário ambiental completo. |
| Proveniência e cache | Preserva fontes, reuso computacional e rastreabilidade de distâncias e cenários. | Estabilidade computacional não valida magnitude nem disponibilidade de mercado. |
| Classificação de validação | Impede que resultados sensíveis, bloqueados ou diagnósticos sejam promovidos indevidamente. | Nenhum resultado atual é um `headline_candidate` robusto. |
| Casos de sensibilidade | Mostram como hipóteses documentadas alteram a leitura do modelo. | Não substituem baselines validados nem provam corredores originais. |
| Benchmark externo | Acrescenta apoio direcional e disciplina de comparação fora do próprio modelo. | Não é validação calibrada, reprodução exata ou verdade de referência. |
| Reconciliação diagnóstica | Ajuda a explicar parte das lacunas, especialmente no lado rodoviário. | Não recalibra o aplicativo, não resolve todas as magnitudes e não substitui o baseline. |

Essa estrutura contribui para a qualidade acadêmica do trabalho porque transforma incertezas em objetos explícitos de análise. Em vez de ocultar premissas frágeis atrás de um valor final de custo ou emissão, o framework separa o que é resultado executado, o que é sensibilidade, o que é diagnóstico, o que é limitação e o que ainda depende de referência externa. A classificação de evidência, portanto, não é um detalhe administrativo; ela é parte da contribuição metodológica e reduz o risco de sobreinterpretação.

O benchmark externo e as verificações diagnósticas reforçam essa leitura sem mudar sua natureza. O Batch 002 fortalece a interpretação ao mostrar apoio direcional externo, mas não transforma o CabotageLens em modelo calibrado contra Gustavo/Costa. O rerun com cache melhora a confiança na estabilidade computacional, mas não valida magnitude exata. A reconciliação rodoviária torna parte da lacuna mais explicável, mas não substitui o modelo de linha de base nem elimina todos os desvios. O ganho está na transparência metodológica, não em uma validação comercial ou universal.

Como consequência, os resultados atuais permanecem condicionais. Nenhum resultado atual deve ser tratado como `headline_candidate` robusto. Eles dependem das premissas modeladas, das referências disponíveis, da construção de rota, da seleção de portos, da fronteira de custo e da fronteira ambiental adotada. Custos continuam sendo estimativas modeladas, não fretes comerciais, tarifas ou cotações negociadas. Emissões continuam sendo CO2e operacional TTW, salvo indicação explícita em contrário. O framework não substitui dados de operadores, terminais, agendas de armadores, disponibilidade de slots, cotações de mercado ou validação operacional de campo.

Ao mesmo tempo, essa limitação define um caminho de evolução claro. O mesmo framework pode apoiar trabalhos futuros com referências marítimas mais completas, dados operacionais de operadores e terminais, agendas e frequências de transportadores, expansão WTW/LCA, custos comerciais e taxas negociadas, desde que cada nova camada seja incorporada com fronteira, unidade e proveniência explícitas. Assim, o Capítulo 8 se encerra com uma conclusão deliberadamente conservadora: o valor do CabotageLens está na estrutura auditável que permite comparar cenários e controlar afirmações. O Capítulo 9 detalha justamente as limitações que ainda impedem converter essa estrutura em validação operacional, comercial ou universal.

## 9. Limitacoes

### 9.1 Escopo das limitações e papel no argumento do TF

As limitações deste trabalho não são tratadas como fragilidades a serem ocultadas, mas como parte explícita do argumento acadêmico do TF. Depois dos capítulos de validação, resultados e discussão, o papel do Capítulo 9 é delimitar o que os resultados podem sustentar e, com a mesma importância, o que eles não podem sustentar. Essa delimitação controla a leitura dos Capítulos 6, 7 e 8 e evita que evidências úteis, porém condicionais, sejam convertidas em conclusões mais fortes do que os artefatos rastreados permitem.

Essa postura não invalida o protótipo CabotageLens. Ao contrário, reforça sua contribuição mais segura: uma estrutura metodológica e computacional auditável para comparar cenários rodoviários e rodoviário-cabotagem-rodoviário sob fronteiras declaradas. O objetivo atual não é produzir um ranking universal entre cabotagem e transporte rodoviário, nem comprovar a viabilidade comercial de uma cadeia logística real. O valor do trabalho está em tornar visíveis as hipóteses de rota, porto, distância, custo, emissões, proveniência e classificação de evidência.

A interpretação mais defensável, no estado atual do projeto, é cenário-dependente, direcional e diagnóstica. As linhas de sensibilidade mostram comportamento do modelo sob hipóteses documentadas; o benchmark externo apoia leitura direcional, mas não valida magnitude calibrada; e as verificações diagnósticas ajudam a explicar lacunas sem substituir o modelo de linha de base. Por isso, nenhum resultado atual deve ser promovido a `headline_candidate` robusto, e nenhuma evidência atual prova superioridade universal da cabotagem.

Também é necessário separar as fronteiras econômicas, ambientais e operacionais. Os custos permanecem estimativas modeladas, não fretes comerciais, tarifas, cotações, contratos negociados ou comprovação de viabilidade econômica de mercado. As emissões permanecem operacionais TTW CO2e, salvo indicação explícita em contrário, e não devem ser misturadas com WTW, LCA, CO2 isolado ou outros limites de CO2e sem reconciliação metodológica. Da mesma forma, os resultados não comprovam disponibilidade de serviço, aceitação por armadores, aceitação por terminais, disponibilidade de slots, frequência operacional ou contratação real de frete.

| Grupo de limitação | Por que importa | Onde afeta a interpretação |
| --- | --- | --- |
| Fronteira ambiental | Evita misturar TTW CO2e com WTW, LCA, CO2 isolado ou fatores de literatura ainda não adotados pelo método. | Capítulos 6, 7 e 8, especialmente nas comparações de emissões. |
| Fronteira econômica | Mantém custos como estimativas modeladas, sem transformá-los em fretes comerciais ou viabilidade contratual. | Resultados de custo, discussão de apoio à decisão e conclusões. |
| Fronteira operacional e de serviço | Impede inferir disponibilidade real de linhas, frequência, slots, aceitação de carga ou execução comercial. | Discussão logística, limitações e trabalhos futuros. |
| Proveniência de rota e distância | Mantém visíveis lacunas de distância marítima, seleção de portos, casos same-port e cenários de porto alternativo. | Validação, classificação de casos e leitura por corredor. |
| Limites de validação e benchmark | Preserva sensibilidades como sensibilidades, benchmark como apoio direcional e diagnósticos como diagnósticos. | Capítulos 6, 7 e 8, sem conversão em `headline_candidate`. |
| Maturidade de fontes e citações | Evita usar literatura ou fontes pendentes como coeficientes, calibração ou validação sem adoção metodológica rastreada. | Revisão bibliográfica, metodologia e agenda de pesquisa futura. |

A tabela acima resume a função organizadora do capítulo, sem esgotar cada limitação específica. As subseções seguintes podem detalhar grupos particulares de restrições, mas a regra de leitura já fica estabelecida aqui: limitações existem para impedir sobreafirmações, não para negar o valor do protótipo. Elas preservam a diferença entre resultado executado, sensibilidade, benchmark, diagnóstico, exclusão e trabalho futuro.

Com essa estrutura, o Capítulo 9 prepara a transição para as conclusões e os trabalhos futuros. O Capítulo 10 pode afirmar a contribuição metodológica do CabotageLens sem extrapolar para validação comercial, operacional ou universal. O Capítulo 11, por sua vez, pode transformar as limitações em uma agenda de evolução: ampliar fronteiras ambientais, refinar custos, incorporar evidência operacional, reconciliar benchmarks e fortalecer a base de validação sem apagar as incertezas que tornam o argumento acadêmico defensável.

### 9.2 Fronteira ambiental: TTW operacional, CO2e e exclusão de WTW/LCA

A primeira limitação ambiental do TF é a fronteira de contabilização adotada para os resultados de emissões. Salvo indicação explícita em contrário, o CabotageLens reporta emissões operacionais TTW CO2e associadas às pernas e componentes modelados no cenário. Essa escolha permite comparar alternativas sob uma fronteira comum e auditável, mas não deve ser confundida com uma avaliação climática completa da cadeia logística.

Na prática, a fronteira TTW operacional considera emissões associadas ao uso de combustível nas etapas representadas, enquanto deixa fora etapas a montante e de ciclo de vida. Assim, a linha de base atual não inclui produção, refino, transporte ou distribuição dos combustíveis; construção e manutenção de infraestrutura; fabricação de caminhões, navios ou equipamentos; nem fim de vida dos ativos. Esses elementos pertencem a fronteiras WTT, WTW ou LCA, que são relevantes para contextualização e trabalhos futuros, mas não substituem os resultados operacionais do modelo corrente [decarb2024] [maritimelca2024].

Essa distinção também vale para a espécie de emissão reportada. Resultados em CO2 isolado não são automaticamente equivalentes a CO2e, porque CO2e depende dos gases incluídos e da regra de equivalência climática adotada pela fonte. Portanto, literatura ou benchmarks que reportam CO2-only, WTW, LCA ou CO2e sob outro limite metodológico não podem ser usados para calibrar, corrigir ou validar diretamente os resultados TTW CO2e do CabotageLens sem reconciliação explícita de fronteira, unidade funcional, base de carga e gases incluídos.

| Escopo ambiental | Incluído no TF atual? | Limite de interpretação |
| --- | --- | --- |
| TTW CO2e operacional | Sim, como fronteira ambiental da linha de base quando o cenário reporta emissões. | Apoia comparação operacional entre cenários modelados, não conclusão WTW/LCA. |
| WTT e produção de combustível | Não, salvo futura expansão explícita de fronteira. | Não deve ser inferido a partir dos resultados TTW. |
| WTW/LCA | Não executado como resultado de linha de base. | Literatura WTW/LCA é contexto ou trabalho futuro, não substituição do modelo atual. |
| Literatura CO2-only | Não como equivalente direto. | Exige reconciliação antes de qualquer comparação com CO2e. |
| Poluentes locais | Não como resultado principal. | NOx, SOx, PM, CO e VOC ficam fora da fronteira de resultado, salvo discussão bibliográfica. |
| Dispersão e qualidade do ar portuária | Não. | O TF não estima concentração, exposição ou impacto local à saúde. |
| Combustíveis alternativos e HVO | Não na linha de base. | Permanecem como contexto ou trabalho futuro se não forem modelados separadamente. |

As operações portuárias e o *hoteling* reforçam a importância dessa separação. O fato de o modelo poder representar componentes operacionais associados à estadia ou operação em porto não transforma o CabotageLens em inventário completo de emissões portuárias, nem em estudo de qualidade do ar local. Fontes sobre consumo de navios atracados e impactos locais de emissões portuárias ajudam a justificar a relevância metodológica do tema [berth2009] [shipops2022] [berthairquality2010], mas o TF atual não modela dispersão atmosférica, concentração, exposição populacional, terminal específico, produtividade real ou inventário completo de poluentes.

Também não se deve usar discussões sobre combustíveis alternativos, HVO ou trajetórias de descarbonização como se fossem resultados da linha de base. Esses temas são úteis para posicionar a agenda de pesquisa e para orientar trabalhos futuros, mas exigiriam cenários separados, fatores compatíveis, fronteira ambiental documentada e rastreabilidade própria antes de serem comparados aos resultados TTW CO2e atuais. Sem essa etapa, a literatura de descarbonização permanece contextual, não uma fonte de recalibração silenciosa.

A reconciliação rodoviária do Batch 002 segue a mesma regra. Ela é uma verificação diagnóstica de alinhamento com o benchmark externo, não uma autorização para alterar a fronteira ambiental da linha de base nem para substituir fatores do modelo. O próprio valor metodológico desse diagnóstico está em mostrar que diferenças de fronteira e premissas podem explicar lacunas de magnitude; ele não transforma uma hipótese WTW ou externa em resultado operacional TTW CO2e do CabotageLens.

Portanto, a limitação ambiental não invalida o modelo, mas define o alcance das afirmações que ele pode sustentar. Os resultados atuais podem apoiar interpretação operacional, cenário-dependente e comparativa sob TTW CO2e. Eles não podem sustentar conclusões WTW, WTT, LCA, CO2-only, inventário completo de poluentes, impacto de qualidade do ar portuária ou superioridade ambiental universal sem uma expansão metodológica explícita e rastreada.

### 9.3 Fronteira econômica: custos modelados e ausência de fretes comerciais

A segunda limitação central do Capítulo 9 é econômica. O CabotageLens reporta custos modelados dentro de uma fronteira definida, não fretes comerciais. Portanto, os valores em BRL devem ser lidos como saídas de um cenário de comparação construído com rotas, portos, componentes e hipóteses explícitas. Eles ajudam a comparar alternativas sob o mesmo enquadramento metodológico, mas não representam cotação de mercado, tarifa praticada, proposta de armador, contrato negociado ou recomendação de contratação.

Essa distinção é importante porque a decisão logística real envolve elementos que o protótipo atual não captura integralmente. Além dos componentes operacionais representados no modelo, uma contratação real depende de frequência de serviço, confiabilidade, prazo, estoque em trânsito, seguro, risco operacional, demurrage, detention, janelas de terminal, disponibilidade de slot, condições contratuais, negociação comercial e tolerância do embarcador a variabilidade. A literatura sobre competitividade da cabotagem e mudança modal ajuda a contextualizar essas dimensões [competitiveness2024] [modalshiftreview2020], mas não valida automaticamente os custos calculados pelo CabotageLens.

Assim, uma diferença favorável de custo modelado não deve ser narrada como prova de menor frete contratado. Ela indica apenas que, sob a fronteira atual e sob as premissas daquele cenário, a soma dos componentes representados foi menor para uma alternativa do que para outra. A interpretação continua condicionada à rota, à seleção de portos, aos componentes habilitados, à base de carga, à disponibilidade das distâncias e às regras de fronteira econômica. Se qualquer uma dessas dimensões muda, a leitura do resultado também pode mudar.

| Dimensão de custo | Tratamento no TF atual | Limitação |
| --- | --- | --- |
| Custo de rota modelado | Calculado como saída do cenário dentro da fronteira implementada. | Não equivale a preço de mercado nem a custo logístico total. |
| Cotação de frete | Fora da fronteira atual. | Exige consulta comercial a transportadores, armadores, agentes ou operadores. |
| Contrato negociado | Fora da fronteira atual. | Não é inferido a partir do custo modelado. |
| Tarifas portuárias e manuseio | Representadas apenas quando e como o cenário modela componentes portuários. | Não cobre tabelas completas, encargos locais ou condições terminal-específicas. |
| Estoque, tempo e confiabilidade | Reconhecidos como dimensões logísticas relevantes. | Não são modelados como custo total de inventário, atraso ou variabilidade operacional. |
| Seguro, risco e demurrage | Fora da fronteira corrente salvo componente explicitamente modelado. | Não sustentam conclusão de custo comercial completo. |
| Viabilidade comercial integral | Não avaliada pelo protótipo. | Requer serviço disponível, preço contratado, capacidade, prazo e risco operacional verificados. |

A fronteira econômica também impede que custo e disponibilidade sejam confundidos. O fato de uma alternativa apresentar menor custo modelado não prova que exista serviço de cabotagem disponível no corredor, que um terminal aceite a carga, que haja slot operacional, que um armador ofereça frequência adequada ou que o preço final negociado seja menor. O CabotageLens organiza uma comparação acadêmica auditável; ele não é motor de cotação, plataforma de booking, sistema de precificação comercial nem modelo completo de custo logístico.

Essa limitação não reduz a utilidade do resultado. Pelo contrário, torna mais clara sua função: o custo modelado serve para testar coerência de cenário, sensibilidade de rota, efeito da seleção de portos e impacto dos componentes incluídos. Ele pode indicar onde uma investigação comercial posterior faria sentido, mas a passagem de um resultado favorável para uma decisão de mercado exige evidência externa de preço, serviço, prazo, risco e contrato. Sem essa verificação, a conclusão defensável permanece metodológica, não comercial.

Por fim, a literatura de competitividade e de mudança modal deve ser usada com o mesmo cuidado. Estudos que discutem tarifas, frequência, confiabilidade ou estrutura de rede ajudam a explicar por que a decisão real é mais ampla do que o custo calculado, mas não substituem cotações reais nem transformam o CabotageLens em modelo comercial calibrado. No estado atual do TF, a afirmação segura é que os custos são estimativas modeladas, condicionadas à fronteira adotada; não são fretes comerciais, não provam viabilidade comercial e não demonstram superioridade econômica universal da cabotagem.

### 9.4 Limitações operacionais: serviço, horários, terminais e super-rede

A terceira limitação central do Capítulo 9 é operacional. O CabotageLens constrói cenários determinísticos e auditáveis para comparar uma alternativa rodoviária direta com uma alternativa rodoviário-cabotagem-rodoviário, mas não transforma esse encadeamento em plano operacional de transporte. A rota modelada é uma representação metodológica sob fronteiras explícitas; ela não prova que exista serviço disponível, agenda compatível, vaga de embarque, aceitação de carga ou execução comercial possível naquele corredor.

Essa distinção é especialmente importante na interpretação da cadeia portuária. Um porto selecionado pelo modelo, ou forçado em um cenário de sensibilidade, funciona como nó de comparação dentro do experimento. Isso não equivale a validação de terminal, aceitação de carga, janela de operação, cutoff documental, disponibilidade de pátio, slot de navio ou viabilidade de booking. Portanto, uma cadeia de portos modelada não deve ser narrada como confirmação de que o terminal ou o operador aceitariam a operação real.

A decisão efetiva de mudança modal depende de dimensões que ficam fora da fronteira operacional atual: frequência de serviço, horários, confiabilidade, tempo de espera, coordenação entre operadores, qualidade de atendimento, risco de atraso, capacidade disponível e integração entre trechos terrestres e marítimos. A literatura de competitividade e mudança modal ajuda a contextualizar por que esses fatores são decisivos [competitiveness2024] [modalshiftreview2020], mas não transforma o CabotageLens em validador de serviço, agenda ou operação.

| Dimensão operacional | Tratamento no TF atual | Limitação |
| --- | --- | --- |
| Disponibilidade de serviço | Não consultada como condição operacional real. | Uma rota modelada não comprova linha de cabotagem disponível no corredor. |
| Horários e frequência | Fora da fronteira de cálculo. | O modelo não confirma escalas, janelas, transit time contratado ou regularidade de serviço. |
| Aceitação por terminal | Não validada no nível terminal-carga. | Uma cadeia portuária modelada não prova aceitação operacional, documental ou comercial. |
| Slot e capacidade | Não modelados como restrição de oferta. | Resultado favorável não prova vaga, capacidade de navio, pátio ou booking disponível. |
| Espera e confiabilidade | Reconhecidas como fatores relevantes, mas não estimadas como resultado. | O TF não calcula variabilidade, fila, risco de atraso ou nível de serviço. |
| Super-rede multimodal | Não otimizada como rede nacional completa. | O modelo não resolve múltiplas linhas, operadores, transbordos, frequências e capacidades. |
| Coordenação de operadores | Depende de evidência externa. | O uso prático exigiria consulta a armadores, terminais, agentes, transportadores ou operadores logísticos. |

Também não se deve interpretar o protótipo como otimizador de uma super-rede nacional. O modelo atual compara cenários construídos e rastreáveis; ele não escolhe simultaneamente entre múltiplas linhas de cabotagem, operadores, portos alternativos, transbordos, frequências, restrições de capacidade e conexões terrestres. Uma super-rede completa exigiria outro nível de dados, formulação e validação, incluindo oferta real de serviço, restrições temporais e capacidade operacional.

Essa limitação não invalida a comparação de cenários. Ela define o alcance correto da interpretação: o CabotageLens pode indicar como custo modelado e emissões operacionais TTW CO2e se comportam sob uma rota e uma fronteira declaradas, mas não substitui consulta a armador, terminal, agente de carga, transportador rodoviário, operador logístico ou autoridade portuária. A passagem de um resultado acadêmico favorável para uma decisão operacional exigiria validação externa de serviço, horário, terminal, capacidade, aceitação, preço e risco.

Assim, a afirmação defensável para o TF é que o CabotageLens organiza uma comparação metodológica e auditável, não um plano logístico final. Uma rota favorável no modelo pode orientar investigação posterior, mas não confirma disponibilidade de serviço, aceitação por transportador, slot, booking, operação terminal ou viabilidade comercial. Essa fronteira preserva a utilidade do protótipo sem transformar resultados condicionais em prova operacional.

### 9.5 Limitações de rota: distância marítima, portos alternativos e casos same-port

A quarta limitação do Capítulo 9 está na própria construção das rotas usadas para comparação. No CabotageLens, a rota rodoviário-cabotagem-rodoviário depende da seleção de portos, da distância marítima entre esses portos, dos acessos rodoviários de entrada e saída e da classificação de qualidade do cenário. Esses elementos tornam a comparação auditável, mas também delimitam o que pode ser afirmado: uma cadeia modelada não é, por si só, evidência de rota marítima robusta, serviço disponível ou viabilidade comercial.

A proveniência da distância marítima continua sendo uma restrição central. Quando há referência exata para o par de portos do cenário, a interpretação é mais forte; quando a distância depende de fallback, fonte fraca ou ausência de referência exata, a linha não deve sustentar conclusão numérica robusta. Em especial, Manaus -> Porto de Fortaleza permanece sem evidência suficiente de distância marítima exata nos artefatos rastreados atuais, e Porto do Rio Grande -> Porto do Recife também permanece sem evidência suficiente de distância marítima exata. Essas lacunas devem aparecer como limitações, não como problemas já resolvidos.

Os portos alternativos precisam permanecer separados dos portos originalmente selecionados. Pecém pode ser discutido apenas como sensibilidade de porto alternativo para a região de Fortaleza; Pecém não valida Porto de Fortaleza. Do mesmo modo, Suape pode ser discutido apenas como sensibilidade de porto alternativo para a região de Recife; Suape não valida Porto do Recife. A troca de porto altera a perna marítima, os acessos rodoviários, o terminal considerado, a interpretação operacional e a fronteira do cenário. Portanto, uma sensibilidade com porto alternativo é um cenário diferente, não uma substituição silenciosa do caso-base.

| Limitação de rota | Exemplo afetado | Tratamento seguro no TF |
| --- | --- | --- |
| Distância marítima exata ausente | Manaus -> Porto de Fortaleza; Porto do Rio Grande -> Porto do Recife | Manter como lacuna de referência até que artefatos rastreados documentem a distância exata do par selecionado. |
| Sensibilidade com Pecém | Manaus -> Pecém como porto alternativo | Discutir apenas como cenário alternativo; não usar como validação de Porto de Fortaleza. |
| Sensibilidade com Suape | Rio Grande -> Suape como porto alternativo | Discutir apenas como cenário alternativo; não usar como validação de Porto do Recife. |
| Caso same-port | Santos -> Santos | Tratar como exemplo de limitação, aviso de qualidade ou exclusão, não como desempenho normal de cabotagem. |
| Cadeia Angra dos Reis | Brasília/Salvador com Angra dos Reis | Manter excluída para a cadeia conteinerizada atual. |
| Caso metodologia-bloqueado | Brasília/Salvador com porto alternativo ainda não documentado | Não converter em resultado até que a decisão metodológica e a evidência de rota estejam rastreadas. |
| Distância marítima por fallback | Linhas sem referência marítima robusta | Usar como diagnóstico, histórico ou lacuna; não como validação final de rota. |

Os casos same-port exigem cuidado adicional. Uma linha Santos/Santos não representa desempenho normal de cabotagem, porque não há uma perna marítima substantiva entre portos distintos. Esse tipo de caso pode ser útil para mostrar como a lógica de seleção de portos deve emitir avisos, preservar exclusões ou bloquear interpretações indevidas, mas não deve sustentar comparação modal entre rodovia e cabotagem.

Os casos excluídos ou bloqueados também não podem ser reaproveitados como resultado numérico. A cadeia conteinerizada envolvendo Angra dos Reis permanece excluída no estado atual do TF. O caso Brasília/Salvador com alternativa de porto ainda permanece metodologia-bloqueado enquanto os artefatos rastreados não documentarem uma decisão defensável de porto alternativo e sua distância marítima. Esses registros têm valor como evidência de limitação e agenda de melhoria, não como base para conclusão de custo, emissões ou desempenho de rota.

Essa limitação de rota controla especialmente a leitura das sensibilidades. As linhas executadas como sensibilidade continuam sendo sensibilidade: elas mostram como o modelo se comporta sob uma hipótese documentada de distância ou porto alternativo, mas não se tornam conclusões robustas de baseline. Um resultado favorável em sensibilidade não elimina a lacuna do caso selecionado original, não transforma fallback em referência robusta e não resolve automaticamente a diferença entre porto regional alternativo e porto originalmente escolhido.

Por fim, a construção de rota permanece separada da validação operacional e comercial. Mesmo uma distância marítima bem documentada ou uma sensibilidade coerente não prova disponibilidade de serviço, frequência, slot, aceitação terminal, aceite de transportador, booking ou frete contratado. A afirmação segura é metodológica: o CabotageLens torna visíveis as hipóteses de rota, distância e porto para que elas possam ser auditadas. Ele não converte, no estado atual, essas hipóteses em prova de operação real.

### 9.6 Limitações de validação: sensibilidades, Batch 002 e reconciliação rodoviária

A quinta limitação do Capítulo 9 está na força das evidências de validação disponíveis. O TF já possui uma camada de sensibilidade interna, um benchmark externo Gustavo/Costa, um rerun com Supabase/cache e uma reconciliação rodoviária diagnóstica. Esses elementos melhoram a rastreabilidade da defesa, mas não têm o mesmo papel metodológico que uma calibração completa contra dados observados. A leitura correta é classificada: sensibilidade permanece sensibilidade, benchmark permanece benchmark, diagnóstico permanece diagnóstico e baseline permanece baseline.

As linhas de sensibilidade do Batch 001B mostram comportamento do modelo sob hipóteses documentadas de distância marítima ou porto alternativo. Elas são úteis porque testam se a direção do resultado muda quando uma premissa rastreada é alterada. Contudo, essas linhas não são conclusões robustas de baseline, não validam os portos originalmente selecionados e não podem ser promovidas a `headline_candidate`. Seu papel é apoiar discussão de sensibilidade, não substituir validação de rota, custo, emissões ou serviço.

O Batch 002 acrescenta uma camada externa importante, mas limitada. O workbook Gustavo/Costa é um benchmark, não uma verdade de referência. O fato de o benchmark e o CabotageLens apontarem na mesma direção para as linhas comparáveis sustenta interpretação direcional de emissões, mas acordo direcional não é validação calibrada de magnitude. Após o rerun rastreado, todas as linhas comparáveis do Batch 002 permanecem classificadas como `same_direction_large_gap`; essa etiqueta deve continuar visível porque ela comunica exatamente a lacuna entre direção e magnitude.

| Camada de validação | O que sustenta | Limitação de validação |
| --- | --- | --- |
| Sensibilidades Batch 001B | Comportamento do modelo sob hipóteses documentadas. | Não são baseline robusto nem `headline_candidate`. |
| Benchmark direcional Batch 002 | Apoio externo à direção modal das emissões em linhas comparáveis. | Não valida magnitude exata, serviço, rota, preço, frete ou viabilidade comercial. |
| `same_direction_large_gap` | Transparência sobre acordo direcional com lacuna de magnitude. | Não deve ser suavizado como calibração ou reprodução exata. |
| Rerun Supabase/cache | Estabilidade computacional da camada de cache/rota no benchmark. | Não valida disponibilidade operacional, disponibilidade comercial ou magnitude calibrada. |
| Reconciliação rodoviária | Diagnóstico de alinhamento para premissas rodoviárias. | Não substitui o modelo rodoviário de linha de base e não recalibra o aplicativo. |
| Lacuna residual | Evidência de que diferenças metodológicas permanecem. | O mismatch não está totalmente resolvido e não deve ser tratado como fechado. |

As células puladas do workbook também precisam de interpretação cautelosa. Linhas não comparáveis, pares sem valor útil ou casos fora do escopo de comparação não devem ser transformados automaticamente em falha do modelo. Elas indicam limites de comparabilidade entre artefatos, especialmente quando a estrutura interna do workbook, as premissas de rota, a alocação por contêiner, os serviços assumidos e a fronteira de emissões não foram totalmente reconstruídos.

O rerun Supabase/cache tem uma função diferente. Ele reduz a hipótese de que a lacuna de magnitude do Batch 002 seja explicada principalmente por instabilidade de provedor, leitura de cache ou escrita de rota. Isso melhora a confiança na reprodutibilidade computacional do benchmark, mas não valida rota comercial, disponibilidade de serviço, terminal, agenda, slot, frete, preço ou aceitação por operador. Estabilidade de cache é evidência de execução, não evidência operacional ou comercial.

A reconciliação rodoviária com `0.8602944 kgCO2e/km` deve permanecer ainda mais claramente separada da linha de base. Esse valor é usado como fator diagnóstico de alinhamento com o benchmark externo e ajuda a explicar uma parte relevante do mismatch rodoviário. Ele não substitui o modelo rodoviário operacional TTW CO2e do CabotageLens, não recalibra o aplicativo, não altera os resultados de baseline e não autoriza misturar TTW, WTW, LCA, CO2 e CO2e. Se for citado, deve ser identificado como diagnóstico, não como novo coeficiente de linha de base.

Mesmo depois da reconciliação, permanece mismatch residual. Essa lacuna pode estar associada a distância rodoviária, construção de rota, veículo, carregamento, alocação por contêiner, escolhas de porto e serviço, tratamento de operações portuárias e diferenças de fronteira ambiental entre TTW, WTW, LCA, CO2 e CO2e. Portanto, a reconciliação melhora a explicação da diferença, mas não fecha a validação. Ela torna a limitação mais inteligível, não resolvida.

Por consequência, a validação atual sustenta uma conclusão acadêmica conservadora: o CabotageLens é auditável, reproduzível em suas trilhas de execução e coerente para comparação de cenários sob fronteiras explícitas. Ela não sustenta que o modelo esteja calibrado contra Gustavo/Costa, que o workbook seja uma verdade de referência, que o Batch 002 valide magnitudes exatas ou que custos modelados sejam fretes comerciais. A contribuição permanece metodológica e diagnóstica, com emissões operacionais TTW CO2e e custos como estimativas modeladas, até que uma futura camada de validação expanda explicitamente dados, fronteiras e evidências.

### 9.7 Limitações de fontes, citações e generalização dos resultados

A limitação final do Capítulo 9 diz respeito à maturidade das fontes, ao uso das citações e ao grau de generalização permitido pelos resultados. A literatura usada no TF não tem uma única função: algumas fontes contextualizam a cabotagem brasileira, outras delimitam fronteiras ambientais, outras explicam barreiras de mudança modal, operações portuárias, *hotelling*, LCA, WTW, HVO ou visualização futura. Essa literatura fortalece o enquadramento acadêmico, mas não deve ser convertida automaticamente em calibração numérica do CabotageLens.

As chaves de citação presentes no rascunho ainda funcionam como *placeholders* de redação. Elas precisam ser formatadas e verificadas em uma etapa posterior de referências, sem inventar metadados bibliográficos, autores, títulos, anos, periódicos, páginas ou identificadores que não estejam disponíveis nos artefatos rastreados. Até essa etapa, a regra de uso deve ser conservadora: citar para contexto, fronteira, limitação ou trabalho futuro; não citar como se a fonte validasse diretamente uma rota, um porto, um coeficiente ou um resultado específico do modelo.

| Limitação de fonte ou evidência | Uso seguro | Uso proibido |
| --- | --- | --- |
| *Placeholders* de citação | Marcar fontes a formatar e verificar em etapa bibliográfica posterior. | Não tratar chaves como referências finais nem inventar metadados. |
| Literatura de mapas de iso-emissão | Motivar visualização e pesquisa futura. | Não afirmar que o CabotageLens já implementa ou valida mapas desse tipo. |
| Literatura WTW/LCA/HVO | Contextualizar expansão ambiental futura e diferenças de fronteira. | Não recalibrar a linha de base TTW CO2e nem transferir fatores sem adoção metodológica. |
| Literatura de porto e *hotelling* | Informar limites de inventário portuário e operações atracadas. | Não transformar o modelo em inventário completo de emissões portuárias ou validação terminal-específica. |
| Literatura de competitividade e mudança modal | Explicar barreiras logísticas, rede, serviço, custo e decisão operacional. | Não provar disponibilidade de serviço, viabilidade comercial ou superioridade geral da cabotagem. |
| Benchmark Batch 002 | Apoiar interpretação direcional e identificar lacunas metodológicas. | Não tratar o workbook como verdade de referência ou calibração rota a rota. |
| Saídas de sensibilidade | Mostrar comportamento do modelo sob hipóteses documentadas. | Não promover sensibilidades a baseline robusto ou `headline_candidate`. |

Também há uma limitação de transferência metodológica. Valores, fatores, taxas, intensidades, premissas de combustível, parâmetros de frota ou resultados de artigos externos não podem ser inseridos no modelo apenas porque aparecem na literatura. Para que um valor externo seja usado como parâmetro, seria necessário adotá-lo explicitamente na metodologia, registrar sua proveniência, compatibilizar unidade funcional, fronteira ambiental, espécie de emissão, base de carga, rota e papel do resultado. Sem essa cadeia, a fonte permanece como contexto ou motivação de trabalho futuro.

Essa cautela vale especialmente para emissões. O relatório atual permanece, salvo indicação explícita em contrário, na fronteira operacional TTW CO2e. Literatura WTW, LCA, CO2-only ou CO2e sob outra fronteira pode explicar por que a agenda ambiental é mais ampla, mas não altera a linha de base atual. Da mesma forma, discussões de HVO, combustíveis alternativos, emissões locais em porto ou impactos de qualidade do ar precisam de cenários próprios antes de serem comparadas aos resultados do CabotageLens.

O mesmo raciocínio se aplica à generalização dos resultados. As conclusões do TF são específicas por rota, cenário, fronteira, premissa, seleção de portos, proveniência de distância, classificação de evidência e artefato rastreado. A literatura sobre potencial brasileiro de cabotagem, competitividade, short sea shipping ou mudança modal ajuda a posicionar o problema, mas não valida todos os corredores brasileiros nem transforma resultados sensíveis ou diagnósticos em conclusões nacionais. Nenhum resultado atual prova superioridade universal da cabotagem, e nenhum resultado atual deve ser tratado como `headline_candidate` robusto.

Por isso, as fontes devem ser lidas junto com as classificações de evidência. O Batch 002 é benchmark direcional, não verdade de referência; as sensibilidades mostram comportamento sob hipóteses documentadas, não baseline robusto; as citações ambientais contextualizam fronteiras e trabalhos futuros, não recalibram emissões; e a literatura econômica ou operacional explica dimensões ausentes, não converte custos modelados em fretes comerciais. Custos permanecem estimativas modeladas, e emissões permanecem operacionais TTW CO2e salvo indicação explícita em contrário.

Essa limitação encerra o Capítulo 9 porque define como o leitor deve atravessar a transição para as conclusões. O trabalho pode concluir que o CabotageLens oferece uma estrutura auditável e academicamente útil para comparação de cenários, mas não que a literatura, o benchmark ou as sensibilidades resolvam todas as lacunas de rota, validação, custo, emissões e operação. As limitações, portanto, não reduzem a contribuição do TF; elas estabelecem as condições sob as quais a contribuição pode ser defendida e indicam o que trabalhos futuros precisam fechar antes de afirmações mais gerais.

## 10. Conclusões e trabalhos futuros

### 10.1 Conclusão principal

Este trabalho desenvolveu e documentou o CabotageLens como um framework computacional reprodutível e auditável para comparar alternativas de transporte rodoviário direto e rodoviário-cabotagem-rodoviário em corredores brasileiros. A conclusão principal não é que a cabotagem seja superior em termos universais. A contribuição central é que o framework torna a comparação rastreável, dependente de rota e defensável sob fronteiras explicitamente declaradas.

A comparação adotada é porta a porta: a alternativa rodoviária direta liga origem e destino por caminhão, enquanto a alternativa multimodal combina pré-carriage rodoviário, perna marítima de cabotagem e on-carriage rodoviário. Os resultados são interpretados dentro de duas fronteiras principais: custo como estimativa modelada, não frete comercial, e emissões como CO2e operacional TTW, não WTW nem LCA. A análise também preserva a proveniência de distâncias, portos, parâmetros e artefatos de validação, além de classificar a força da evidência de forma conservadora.

Assim, o resultado mais defensável do TF é metodológico: o CabotageLens permite comparar cenários rodoviários e multimodais de forma explícita, com trilha de auditoria, avisos de qualidade e disciplina sobre o que pode ou não ser afirmado. Quando uma alternativa multimodal aparece favorável em um cenário específico, essa leitura deve continuar condicionada ao corredor, à seleção de portos, à distância marítima, aos parâmetros usados e à classificação do caso.

### 10.2 Contribuição metodológica e computacional

A contribuição do CabotageLens está na integração entre construção explícita de rotas, cálculo de custo modelado, cálculo de emissões operacionais TTW CO2e e preservação da proveniência dos dados. O protótipo separa a alternativa rodoviária direta da cadeia rodoviário-cabotagem-rodoviário, registra portos selecionados ou forçados, distingue distâncias marítimas de maior ou menor confiabilidade e mantém o vínculo entre resultado numérico, cenário, parâmetros e artefatos de validação.

Essa estrutura é particularmente importante porque a comparação entre rodovia e cabotagem depende de escolhas que não são neutras. A distância marítima pode vir de SeaMatrix, de fallback haversine, de referência manual ou de referência externa rastreada. Portos alternativos, como Pecém ou Suape, podem ser úteis em sensibilidades, mas não substituem silenciosamente Porto de Fortaleza ou Porto do Recife. Por isso, o framework inclui avisos de qualidade de rota, status de fallback, identificação de casos bloqueados ou excluídos e separação entre baseline, sensibilidade, benchmark externo e diagnóstico.

O valor do trabalho, portanto, não está apenas na geração de números de custo e emissões. Está também na camada de auditoria e classificação: o relatório pode diferenciar resultado histórico, caso sensível, lacuna de referência, comparação externa, rerun de cache e reconciliação diagnóstica. Essa disciplina evita que saídas do modelo sejam transformadas em afirmações mais fortes do que a evidência permite, especialmente em relação a custos comerciais, fronteiras TTW/WTW/LCA, seleção de portos e reprodução de benchmarks externos.

### 10.3 Síntese das evidências obtidas

O Batch 001 permanece como evidência diagnóstica histórica. Ele registrou resultados iniciais e ajudou a revelar problemas de interpretação, especialmente a dependência de distâncias marítimas por fallback e a necessidade de separar casos same-port, lacunas de referência e casos inadequados para conclusão numérica. Esses resultados não foram reescritos como evidência final robusta.

O Batch 001B passou a funcionar como camada de decisão metodológica. Ele reorganizou os casos por status de uso no TF, preservou portos, fontes de distância, unidades, conversões e classificações, e delimitou quais linhas poderiam ser usadas apenas como sensibilidade ou limitação. As sensibilidades executadas no issue #16 indicaram que, nos três cenários nomeados, a alternativa multimodal permaneceu menor que a rodoviária direta em custo modelado e TTW CO2e operacional. Entretanto, essas linhas foram classificadas como `sensitive`, não como `robust`, e nenhuma deve ser promovida a `headline_candidate` irrestrito.

O Batch 002 acrescentou uma camada externa relevante por comparar o CabotageLens ao workbook/paper Gustavo/Costa em pares OD suportados. Esse benchmark tem importância acadêmica para a defesa porque confronta o framework com uma referência externa familiar ao problema estudado. Ao mesmo tempo, ele deve ser interpretado com cautela: os 21 pares OD positivos e suportados ficaram alinhados na direção modal das emissões, mas classificados como `same_direction_large_gap` após o rerun rastreado. Portanto, o Batch 002 apoia consistência direcional, não reprodução calibrada de magnitude, nem reconstrução completa da lógica de carga, alocação, rota, serviço e fronteira do workbook.

O rerun Supabase/cache, presente nos artefatos rastreados, reduziu a hipótese de que a lacuna de magnitude fosse causada principalmente por instabilidade de cache ou provedor de rota. A execução cache-enabled manteve as diferenças agregadas em patamar semelhante e indicou que as lacunas remanescentes são mais provavelmente metodológicas. A reconciliação de fator rodoviário também explicou parte importante da lacuna do lado road-only ao aplicar, apenas como diagnóstico, premissas rodoviárias compatíveis com a família Gustavo/Costa. Essa reconciliação permanece diagnóstica: ela não substitui o modelo rodoviário de linha de base do CabotageLens e não altera a fronteira operacional TTW do trabalho.

Em síntese, as evidências atuais sustentam uma leitura cautelosa e específica por corredor. Elas mostram que o framework produz comparações rastreáveis, que as sensibilidades internas preservam direção favorável sob hipóteses documentadas, que o benchmark Gustavo/Costa apoia consistência direcional externa e que a lacuna rodoviária tem explicação metodológica plausível. Elas não sustentam afirmação universal sobre cabotagem, validação calibrada de magnitude ou equivalência entre custo modelado e frete comercial.

### 10.4 Implicações para interpretação dos resultados

Os resultados permitem usar o CabotageLens como uma ferramenta reprodutível de triagem e comparação de cenários. O modelo pode mostrar se uma alternativa multimodal é direcionalmente favorável sob uma combinação explícita de rota, porto, distância, carga, parâmetros de custo e fronteira ambiental. A camada de benchmark e sensibilidade aumenta a confiança no comportamento direcional do framework e, ao mesmo tempo, evidencia as lacunas que precisam ser resolvidas antes de conclusões mais fortes.

Essa leitura deve permanecer específica por corredor. Um resultado favorável em custo modelado e TTW CO2e operacional pode justificar investigação adicional, comparação de hipóteses ou discussão acadêmica, mas não encerra a análise logística. A decisão real dependeria de preço contratado, disponibilidade de serviço, frequência, tempo de trânsito, confiabilidade, capacidade, aceitação da carga, risco operacional e demais componentes fora da fronteira atual.

Por consequência, o relatório não deve afirmar que:

- a cabotagem é universalmente superior ao transporte rodoviário;
- o custo modelado equivale a frete comercial ou cotação de mercado;
- CO2e operacional TTW equivale a WTW ou LCA;
- o workbook/paper Gustavo/Costa foi plenamente reproduzido;
- as linhas de sensibilidade são substitutas validadas de baseline;
- Pecém equivale a Porto de Fortaleza;
- Suape equivale a Porto do Recife;
- o fator rodoviário diagnóstico deve substituir o modelo rodoviário de linha de base.

Essas restrições não diminuem a contribuição do trabalho; elas definem o uso correto dos resultados. A principal força do CabotageLens está em tornar claras as condições sob as quais cada comparação foi produzida e em impedir que evidências sensíveis, diagnósticas ou parcialmente comparáveis sejam tratadas como validação final.

### 10.5 Limitações finais

As limitações finais decorrem diretamente das fronteiras adotadas. A fronteira ambiental é operacional TTW CO2e, sem incorporação completa de WTW, LCA, infraestrutura, fabricação de veículos, manutenção ou demais etapas de ciclo de vida. A fronteira econômica é de estimativa modelada de custos operacionais, sem fretes comerciais, tarifas completas, margens, inventário, demurrage, contratos, disponibilidade de serviço ou formação real de preço.

A construção das rotas também permanece simplificada. A seleção de portos é uma heurística ou uma decisão forçada de cenário, não uma otimização operacional completa. O modelo ainda não representa uma super-rede multimodal com serviços, frequência, horários, capacidade, conexões, confiabilidade e disponibilidade comercial. Além disso, algumas linhas continuam com evidência incompleta de distância marítima para o par de portos selecionado, especialmente quando o resultado depende de fallback, referência indireta ou sensibilidade com porto alternativo.

As evidências de validação precisam ser lidas como classificação, não como veredito único de passa/falha. Casos same-port, excluídos, bloqueados, sensitivity-only ou not-comparable não devem ser usados para conclusão numérica principal. As sensibilidades executadas ajudam a entender comportamento do modelo, mas não substituem baseline robusto. O workbook Gustavo/Costa é evidência externa importante, mas sua lógica interna de carga, alocação, rota, serviço, distância, porto e fronteira ambiental não foi completamente reconstruída. A reconciliação rodoviária é útil para explicar a lacuna de magnitude, mas permanece diagnóstico de alinhamento, não recalibração do CabotageLens.

Essas limitações não invalidam o framework. Elas indicam que a contribuição do TF está em produzir uma comparação auditável e metodologicamente disciplinada, com incertezas visíveis. A maturidade acadêmica do resultado depende justamente de preservar essas fronteiras, em vez de converter evidência parcial em afirmação geral.

### 10.6 Trabalhos futuros

Os próximos desenvolvimentos devem expandir a fronteira ambiental somente com fatores, unidades e documentação compatíveis. Uma extensão para WTW ou LCA exigiria separar explicitamente emissões upstream, combustíveis, infraestrutura, fabricação, manutenção, operações portuárias adicionais e possíveis cenários de combustíveis alternativos. Essa expansão não deve ser feita por substituição direta de fatores na linha de base TTW, mas por uma nova fronteira metodológica documentada.

Também é necessário melhorar a validação de distâncias marítimas e de portos selecionados. Isso inclui obter evidência exata para pares ainda pendentes, separar portos alternativos de portos originalmente selecionados, ampliar referências independentes de distância e registrar a proveniência de cada rota usada em conclusão. Em paralelo, a modelagem de operações portuárias e hoteling deve incorporar dados mais específicos de terminal, equipamento, produtividade, energia elétrica, combustível, tempo de atracação e tratamento de dupla contagem.

No eixo econômico e operacional, trabalhos futuros devem incorporar fretes comerciais, tarifas, tempo de trânsito, frequência, confiabilidade, demurrage, inventário, disponibilidade de serviço, capacidade e aceitação operacional. Uma evolução natural seria transformar a comparação atual em uma super-rede multimodal, com alternativas de porto, serviços marítimos, conexões, restrições de frequência e critérios explícitos de escolha. Essa expansão permitiria diferenciar melhor vantagem modelada, viabilidade operacional e competitividade comercial.

Outra frente é aprofundar a reconciliação com o workbook/paper Gustavo/Costa. O objetivo não deve ser tratar o benchmark como verdade absoluta, mas reconstruir com mais precisão sua lógica de carga, alocação, distância, rota, porto, serviço e fronteira ambiental. O mesmo esforço deve ser ampliado para outros benchmarks independentes, de modo que a avaliação deixe de depender de uma única família de referência externa.

Por fim, o trabalho deve avançar em sensibilidades de carga, alocação por contêiner, fator de carga, consumo rodoviário, intensidade marítima e parâmetros portuários, sempre com valores rastreados e defensáveis. A versão orientada à publicação do artigo técnico deve refletir a decisão de escopo registrada para o TF: o relatório final pode discutir Gustavo/Costa com maior detalhe por sua relevância para a defesa, mas o artigo deve reposicionar esse benchmark como evidência externa compacta, mantendo o CabotageLens como a contribuição central.
