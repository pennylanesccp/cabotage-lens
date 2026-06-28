# CabotageLens: uma estrutura computacional auditável para comparação entre transporte rodoviário e cabotagem no Brasil

> **Status**: Rascunho do artigo técnico — narrativa-fonte para o relatório final de TF.
>
> **Última revisão**: 2025-06-27

---

## Resumo

O transporte de cargas no Brasil depende fortemente do modo rodoviário, mesmo em corredores de longa distância onde a navegação de cabotagem pode oferecer vantagens ambientais e logísticas. Comparações modais simplificadas entre caminhão e navio ignoram etapas terrestres de acesso, seleção de portos, proveniência de distâncias e fronteiras de emissão, comprometendo a interpretação dos resultados. Este artigo apresenta o CabotageLens, uma estrutura computacional auditável e orientada por rota para comparação entre alternativas rodoviárias diretas e alternativas rodoviário-cabotagem-rodoviário no Brasil. A ferramenta opera sob fronteiras explícitas de emissões operacionais TTW CO₂e e custo modelado, preservando a proveniência de cada distância, porto e parâmetro. A estratégia de validação combina sensibilidade interna com um benchmark externo baseado no workbook Gustavo/Costa. Nos 21 pares OD positivos e suportados do benchmark externo, ambas as fontes favorecem a cabotagem/multimodal em emissões frente ao rodoviário direto, indicando consistência direcional. A reconciliação de fator rodoviário mostra que premissas de consumo e fator de emissão explicam grande parte da diferença de magnitude no lado rodoviário. Os resultados sustentam interpretação direcional cautelosa, não validação calibrada de magnitude. A contribuição principal é metodológica e computacional: uma estrutura reprodutível que torna explícitas as hipóteses de rota, porto, distância, custo e emissões, apoiando uma expansão disciplinada para o relatório final de TF.

**Palavras-chave**: cabotagem; transporte rodoviário; transporte multimodal; emissões; CO₂e; logística; Brasil; ferramenta computacional.

---

## 1. Introdução

O transporte de cargas no Brasil é historicamente dominado pelo modo rodoviário. Essa configuração permite capilaridade e flexibilidade operacional, mas expõe corredores longos a custos elevados de combustível, maior intensidade de emissões por tonelada transportada e vulnerabilidades de infraestrutura [icct2022]. A navegação de cabotagem aparece como alternativa relevante para parte desses fluxos, especialmente quando origem e destino podem ser conectados por uma cadeia composta de acesso rodoviário, perna marítima e acesso rodoviário final.

Políticas recentes, como o BR do Mar [BR_DO_MAR], reforçam o interesse em expandir a cabotagem conteinerizada brasileira. No entanto, a competitividade real do transporte marítimo costeiro depende de distância, acesso terrestre, frequência de serviço, disponibilidade de navios, custos portuários, tempo de trânsito, confiabilidade e escala de carga [competitiveness2024] [modalshiftreview2020]. Afirmar simplesmente que "navio emite menos que caminhão" é insuficiente sem uma comparação porta a porta sob unidade funcional e fronteira de emissão explícitas.

A literatura internacional de short sea shipping confirma que a vantagem ambiental do transporte marítimo costeiro não é automática: resultados dependem de corredor, utilização da embarcação, tipo de navio, intensidade de combustível, acessos terrestres e operações portuárias [shortsea2019]. Revisões sobre mudança modal mostram que barreiras logísticas, qualidade do serviço e confiabilidade podem limitar a transferência efetiva de cargas da rodovia para o mar [modalshiftreview2020].

Este artigo apresenta o CabotageLens como contribuição a esse problema. O CabotageLens é uma estrutura computacional auditável para comparação entre alternativas rodoviárias diretas e alternativas rodoviário-cabotagem-rodoviário em corredores brasileiros, sob fronteiras explícitas de emissões operacionais TTW CO₂e e custo modelado. A ferramenta não é um motor de cotação de frete comercial, não implementa uma super-rede multimodal completa e não pretende demonstrar superioridade universal da cabotagem. Sua contribuição é oferecer um método reprodutível que torna explícitas as hipóteses de rota, porto, distância, custo e emissões, permitindo que cada resultado seja rastreado, classificado e interpretado de forma defensável.

---

## 2. Posicionamento na literatura

Esta seção posiciona o artigo em relação à literatura existente. Não se trata de uma revisão bibliográfica exaustiva; as fontes são usadas para contexto, definição de fronteira e identificação de limitações, não para substituir distâncias, fatores ou resultados calculados pelo CabotageLens, salvo quando explicitamente rastreados em artefatos de cálculo.

### 2.1 Cabotagem brasileira e BR do Mar

A cabotagem brasileira é frequentemente associada a oportunidades de descarbonização e redução da dependência rodoviária em corredores longos. O Brasil possui extenso litoral e centros urbanos costeiros que favorecem essa alternativa. O programa BR do Mar [BR_DO_MAR] e dados do setor [ANTAQ_ANUARIO] reforçam o contexto de política pública, mas valores nacionais de participação modal e emissões setoriais não validam diretamente resultados rota a rota [icct2022].

### 2.2 Short sea shipping e mudança modal

A literatura internacional mostra que short sea shipping pode ser ambientalmente favorável em determinados corredores, mas a conclusão não é universal [shortsea2019] [PAIXAO_MARLOW] [MEDDA_TRUJILLO]. Revisões sobre mudança modal indicam que custo, prazo, variabilidade, disponibilidade, integração terrestre e confiabilidade são determinantes da decisão real [modalshiftreview2020]. Esses trabalhos sustentam a cautela interpretativa adotada neste artigo.

### 2.3 Super-redes e estudos de competitividade

Estudos de competitividade da cabotagem conteinerizada brasileira mostram que a decisão modal real requer uma estrutura de rede mais rica: serviços disponíveis, frequência, tempo de espera, custos comerciais, inventário e alternativas de roteamento [competitiveness2024]. O CabotageLens não implementa uma super-rede comercial e essa limitação é explicitamente reconhecida.

### 2.4 Fronteiras TTW, WTW, LCA, CO₂ e CO₂e

Uma distinção central do trabalho é entre TTW (tank-to-wheel/tank-to-wake), WTW (well-to-wheel/well-to-wake) e LCA (avaliação de ciclo de vida). O CabotageLens reporta emissões operacionais TTW CO₂e. Fontes que reportam WTW, LCA, CO₂ isolado ou CO₂e com fronteira distinta são usadas para contraste e posicionamento, não para calibração do modelo corrente [decarb2024] [maritimelca2024] [IMO_GHG_STUDY]. Resultados CO₂ por tonelada-quilômetro não devem ser convertidos em TTW CO₂e sem ajuste explícito de fronteira.

### 2.5 Operações portuárias e hoteling

Operações portuárias e hoteling podem afetar o desempenho ambiental da cadeia multimodal. Fontes sobre consumo de combustível em navios atracados [berth2009] [shipops2022] e impacto local de emissões portuárias [berthairquality2010] informam o método e as limitações. No CabotageLens, essas emissões seguem a fronteira operacional TTW CO₂e; valores WTW, LCA ou regionais específicos permanecem como referência para trabalho futuro.

---

## 3. Metodologia

### 3.1 Unidade funcional e base de carga

A unidade funcional é o transporte de uma massa especificada de carga conteinerizada entre uma origem e um destino no Brasil. Nos artefatos de validação, a base recorrente de benchmark é **1 TEU / 14 t** por remessa. Resultados são expressos por remessa e podem ser normalizados por tonelada, TEU ou tonelada-quilômetro.

### 3.2 Alternativa rodoviária direta

A alternativa rodoviária representa o transporte por caminhão da origem ao destino. A distância rodoviária é obtida via provedor de roteamento (OpenRouteService, perfil driving-hgv), com cache em Supabase [ORS_API] [SUPABASE]. Consumo de diesel, custo modelado e emissões TTW CO₂e são calculados a partir da distância, do preset de veículo, da massa da carga, dos parâmetros de combustível e dos fatores de emissão implementados.

### 3.3 Alternativa rodoviário-cabotagem-rodoviário

A alternativa multimodal é composta por:

- **pré-carriage**: transporte rodoviário da origem ao porto de origem;
- **perna marítima**: cabotagem entre porto de origem e porto de destino;
- **on-carriage**: transporte rodoviário do porto de destino ao destino final.

Operações portuárias (manuseio de carga e hoteling) são incluídas em ambos os portos quando habilitadas, sob a mesma fronteira operacional TTW CO₂e.

### 3.4 Seleção de portos e construção de rota

A seleção de portos usa uma heurística de porto mais próximo (geodésica) com filtragem de portos elegíveis. Essa abordagem é determinística e auditável, mas não otimiza uma rede de serviços. Um porto geometricamente próximo pode não ser operacionalmente adequado; um porto alternativo forçado cria um cenário de sensibilidade, não uma validação do porto originalmente selecionado.

### 3.5 Proveniência de rotas e distâncias

A metodologia rastreia a proveniência de cada distância:

| Fonte | Uso | Tipo |
|-------|-----|------|
| OpenRouteService (ORS) | Distâncias rodoviárias (driving-hgv) | Cache/provedor |
| SeaMatrix | Distâncias marítimas (par de portos) | Lookup |
| Haversine fallback | Distâncias marítimas quando SeaMatrix indisponível | Fallback geométrico |
| Referência externa | Distância documentada para par de portos específico | Override rastreado |

Distâncias marítimas em milhas náuticas são convertidas por 1 nm = 1.852 km. Uma distância de fallback haversine é apenas uma estimativa de triagem e não sustenta conclusões numéricas fortes.

### 3.6 Modelo de emissões rodoviárias

As emissões rodoviárias seguem a cadeia: distância × consumo de combustível × fator de emissão TTW CO₂e. O modelo usa parâmetros de veículo pesado (caminhão combinado), consumo de diesel e fator de emissão implementados na ferramenta.

### 3.7 Modelo de emissões marítimas

As emissões marítimas dependem da distância marítima, da velocidade de serviço, do consumo de combustível da embarcação (classe representativa container feeder) e do fator de emissão TTW CO₂e. Quando disponível, uma intensidade de trabalho de transporte (transport-work intensity) derivada de KPI de rota SeaMatrix é utilizada; caso contrário, aplica-se intensidade por classe de embarcação.

### 3.8 Operações portuárias e hoteling

O modelo de operações portuárias inclui manuseio de carga (componentes fixo e por TEU) e hoteling da embarcação (potência auxiliar × tempo de atracação × consumo específico × fator de emissão). A alocação de hoteling por TEU usa divisão pela capacidade efetiva da embarcação. Os parâmetros são estimativas modeladas, não dados medidos de terminais específicos. Detalhes completos estão documentados no artefato `port_ops_model.md`.

### 3.9 Fronteira de emissões: TTW CO₂e operacional

As emissões reportadas são operacionais TTW CO₂e em kg CO₂e por remessa. A fronteira inclui combustão de combustível nas pernas representadas. Não inclui WTW, LCA, fabricação de veículos/navios, construção de infraestrutura, refrigeração (reefer) ou retorno vazio. A escolha por TTW é documentada para que futuras extensões possam migrar para WTW ou LCA com fatores compatíveis.

### 3.10 Fronteira de custo: estimativa modelada

Os custos são estimativas modeladas em BRL por remessa. Incluem combustível rodoviário, combustível marítimo, custos portuários modelados e pedágios quando aplicáveis. **Não são fretes comerciais.** Tarifas portuárias completas, margens, seguros, inventário, tempo de trânsito, confiabilidade, demurrage, frequência de serviço e custos administrativos estão fora da fronteira.

### 3.11 Classificação de qualidade de resultados

Cada resultado é classificado conservadoramente:

| Categoria | Uso no TF |
|-----------|-----------|
| `robust` | Seguro para afirmações principais (nenhum caso atual) |
| `same_direction_large_gap` | Direção alinhada, magnitudes divergentes |
| `sensitivity` | Exercício interno sem validação externa |
| `reference_needed` | Plausível, mas sem referência externa |
| `blocked` | Não utilizável |
| `excluded` | Não utilizável |
| `not_comparable` | Comparação inválida por fronteira/escopo |

---

## 4. Implementação computacional

O CabotageLens é implementado como aplicação Streamlit com módulos reutilizáveis e suporte a fluxos de linha de comando.

**Entradas**: origem, destino, carga (massa, TEU), parâmetros de rota e modelo (classe de embarcação, fator de carga, operações portuárias, cenário de porto).

**Saídas**: distâncias por perna (rodoviária, pré-carriage, marítima, on-carriage), custos modelados, emissões operacionais TTW CO₂e, portos selecionados, fonte de distância marítima, avisos de qualidade de rota e proveniência de dados.

A arquitetura separa responsabilidades:

- `app/` — interface Streamlit e orquestração de sessão;
- `modules/` — lógica de domínio: roteamento, avaliação multimodal, combustível, emissões, custos, persistência e proveniência;
- `scripts/` — fluxos reprodutíveis de execução e manutenção;
- `data/` — insumos estáticos e artefatos processados rastreados;
- `supabase/migrations/` — esquema do Supabase Postgres.

Distâncias rodoviárias são obtidas via OpenRouteService [ORS_API] com cache em Supabase Postgres [SUPABASE]. Distâncias marítimas usam SeaMatrix [SEAMATRIX] ou fallback haversine. A persistência garante reprodutibilidade: cenários, resultados, configurações e decisões metodológicas são preservados como artefatos rastreáveis.

A ferramenta não é um motor de cotação de frete, não resolve uma super-rede nacional e não confirma disponibilidade real de serviços de cabotagem.

---

## 5. Estratégia de validação e benchmark

A validação do CabotageLens não busca equivalência perfeita com uma operação real. Ela busca plausibilidade, consistência dimensional, proveniência de dados e classificação adequada da incerteza. A estratégia é composta por camadas complementares.

### 5.1 Batch 001: diagnóstico histórico

O Batch 001 foi a primeira camada de avaliação, preservando resultados numéricos para cinco pares OD. Todos os casos ficaram associados a necessidade de referência ou revisão. A principal limitação diagnosticada foi o uso de distâncias marítimas de fallback haversine onde evidência mais forte era necessária.

### 5.2 Batch 001B: camada de auditabilidade e classificação

O Batch 001B reorganizou a evidência em uma camada de auditabilidade: portos selecionados ou forçados, fonte de distância marítima, unidade, conversão, status metodológico e uso permitido no TF. Nenhum caso Batch 001B foi classificado como pronto para conclusão principal. O ganho foi metodológico: separação explícita de casos executáveis, sensíveis, bloqueados, excluídos e registros históricos.

### 5.3 Sensibilidades internas (issue #16)

Três sensibilidades foram executadas:

- Santos/Manaus com distância de referência (3.300 nm / 6.111,6 km);
- Manaus/Pecém como porto alternativo (1.569 nm / 2.905,788 km);
- Rio Grande/Suape como porto alternativo (1.844 nm / 3.415,088 km).

Essas linhas são `sensitive`, não `robust`. São exercícios internos do modelo e não validações externas.

### 5.4 Batch 002: benchmark externo Gustavo/Costa

O Batch 002 introduziu um benchmark externo baseado no workbook Gustavo/Costa [GUSTAVO_COSTA_2020]. O workbook contém uma matriz 6×6 de diferenças de emissões (multimodal menos rodoviário) para cidades brasileiras. O objetivo não foi reproduzir o workbook, mas verificar se o CabotageLens aponta para a mesma direção modal.

### 5.5 Rerun Supabase/cache

O rerun com cache Supabase testou se instabilidade de cache ou provedor de rota explicava a diferença workbook-vs-modelo. O resultado mostrou 63 cache hits, 0 misses e diferença agregada estável, indicando que a instabilidade de cache/provedor é improvável como causa principal da lacuna.

### 5.6 Reconciliação de fator rodoviário

A reconciliação de fator rodoviário testou uma explicação metodológica: se as premissas rodoviárias do workbook Gustavo/Costa fossem aplicadas diagnosticamente, quanto da lacuna road-only seria reduzida. Este é um exercício diagnóstico, não uma recalibração.

---

## 6. Resultados

### 6.1 Resultados de sensibilidade interna

As três sensibilidades executadas mostram que, sob a fronteira atual, a alternativa multimodal permanece menor que a rodoviária direta em custo modelado e TTW CO₂e operacional.

| Par OD | Emissões rodo (kg CO₂e) | Emissões multi (kg CO₂e) | Δ% emissões | Custo rodo (R$) | Custo multi (R$) | Δ% custo | Classificação |
|--------|------------------------:|-------------------------:|------------:|----------------:|-----------------:|---------:|---------------|
| Santos → Manaus | 3.329 | 677 | −79,7% | 8.613 | 4.543 | −47,3% | `sensitivity` |
| Manaus → Pecém | 4.897 | 840 | −82,8% | 12.687 | 5.133 | −59,5% | `sensitivity` |
| Rio Grande → Suape | 2.668 | 614 | −77,0% | 6.904 | 4.372 | −36,7% | `sensitivity` |

**Ressalvas obrigatórias**:

- Esses resultados são `sensitive`, não `robust`.
- Pecém não equivale a Porto de Fortaleza; Suape não equivale a Porto do Recife.
- São exercícios internos do modelo, não evidência externamente validada.
- A base de carga é 14 t / 1 TEU e a fronteira de custo é modelada.

### 6.2 Benchmark externo Gustavo/Costa

O Batch 002 benchmarkou o CabotageLens contra o workbook Gustavo/Costa [GUSTAVO_COSTA_2020].

| Métrica | Valor |
|---------|------:|
| Células da matriz do workbook parseadas | 36 |
| Pares OD positivos e suportados benchmarkados | 21 |
| Linhas executadas com sucesso | 21 |
| Células puladas antes da execução | 15 |
| Alinhamento direcional (cabotagem favorecida em ambos) | 21/21 (100%) |
| Classificação rastreada | 21 × `same_direction_large_gap` |

As 15 células puladas incluem 7 pares com mesma origem/destino, 4 com valor negativo ou zero e 4 com porto não suportado.

**Interpretação**: Todos os 21 pares OD positivos e suportados são direcionalmente alinhados — tanto o workbook quanto o CabotageLens favorecem cabotagem/multimodal em emissões frente ao rodoviário direto. Contudo, as magnitudes de linha de base diferem significativamente. A classificação atual é `same_direction_large_gap` para todas as 21 linhas. O benchmark sustenta consistência direcional, não reprodução exata nem validação calibrada de magnitude. O workbook não é tratado como verdade absoluta.

### 6.3 Reconciliação de fator rodoviário

A reconciliação diagnosticou a lacuna road-only usando as premissas rodoviárias do workbook:

| Parâmetro Gustavo/Costa | Valor | Unidade |
|-------------------------|------:|---------|
| Consumo rodoviário (FDc) | 0,28 | L/km |
| Densidade energética (FDe) | 35,52 | MJ/L |
| Fator de emissão (FDf) | 86,5 | gCO₂eq/MJ |
| **Fator diagnóstico** | **0,8602944** | **kgCO₂e/km** |

| Métrica de mismatch rodoviário | Linha de base | Fator diagnóstico |
|--------------------------------|--------------:|------------------:|
| Média | 199,8% | 43,9% |
| Mediana | 149,3% | 19,6% |

**Interpretação**: Premissas de consumo de combustível rodoviário e fator de emissão explicam uma parte grande da diferença de magnitude no lado road-only. A reconciliação é diagnóstica: não substitui o modelo rodoviário de linha de base do CabotageLens, não afirma que o fator diagnóstico é mais correto, e não valida o lado marítimo da comparação. A lacuna residual (~20-44%) é atribuível a diferenças de distância rodoviária, premissas de veículo/carregamento, alocação e fronteira WTW vs TTW.

---

## 7. Discussão

Os resultados reforçam que o desempenho da cabotagem é específico por corredor. Em corredores longos com acesso portuário coerente e distância marítima documentada, a alternativa multimodal pode apresentar forte redução modelada de emissões TTW CO₂e e custo operacional. No entanto, esse comportamento depende da qualidade da distância marítima, da escolha do porto, da disponibilidade real de serviço e da fronteira de custo. A literatura de short sea shipping confirma que a vantagem ambiental não é automática [shortsea2019] [modalshiftreview2020].

A consistência direcional do Batch 002 é significativa: 21/21 pares OD positivos apontam na mesma direção em ambas as fontes. Porém, a diferença de magnitude impede afirmação de validação calibrada. Essa diferença não deve ser narrada como falha do modelo nem como indicação de que o workbook é verdade absoluta. Ela deve ser apresentada como transparência metodológica sobre fronteiras, parâmetros e alocações não reconciliados.

A lacuna road-only tornou-se metodologicamente explicável. O rerun com cache mostrou que instabilidade de rota/provedor não é a causa principal. A reconciliação rodoviária reduziu fortemente a diferença quando aplicou o fator diagnóstico Gustavo/Costa. Permanecem lacunas associadas a distância rodoviária, construção de rota, premissas de veículo e carregamento, alocação por contêiner, seleção de portos, tratamento de port-ops/hoteling e diferenças TTW/WTW/LCA/CO₂/CO₂e.

A contribuição do artigo não é um ranking modal universal. É a estrutura auditável e a disciplina de classificação. A ferramenta torna explícitas as fronteiras de rota, porto, distância, custo e emissões, permitindo que cada resultado seja rastreado e interpretado de forma defensável. Essa abordagem apoia, sem exagerar, a defesa do TF final.

É necessário separar custo e emissões. Um resultado com menor custo modelado e menor TTW CO₂e em uma linha de sensibilidade é útil, mas se em outros cenários custo e emissões apontarem para modos diferentes, não há "vencedor" único sem uma regra de decisão explícita. O presente trabalho não define uma função objetivo que combine BRL e kg CO₂e.

---

## 8. Limitações

O trabalho possui limitações deliberadas e limitações não resolvidas:

1. **Fronteira ambiental**: as emissões são operacionais TTW CO₂e, não WTW nem LCA. Etapas upstream, infraestrutura e fabricação não estão incorporadas.

2. **Fronteira de custo**: os custos são estimativas modeladas, não fretes comerciais. Tarifas, margens, inventário, serviço, frequência, confiabilidade, demurrage e outros custos logísticos não estão incluídos.

3. **Sem super-rede completa**: o CabotageLens não modela horários, frequência de escalas, disponibilidade de serviço, capacidade de navio, tempo de espera ou conexões comerciais.

4. **Seleção de portos simplificada**: a heurística de porto mais próximo é determinística, mas pode não refletir o porto operacionalmente adequado.

5. **Linhas de sensibilidade, não robustas**: os resultados internos são classificados como `sensitivity` e não substituem validação externa.

6. **Workbook não totalmente reconstruído**: massa interna de carga, definição de TEU, fator de carga, alocação, base de distância e fronteira de emissões do workbook Gustavo/Costa não foram completamente reconciliados.

7. **Fator diagnóstico é apenas sensibilidade**: a reconciliação rodoviária de `0,8602944 kgCO₂e/km` não substitui o modelo rodoviário de linha de base e não autoriza misturar TTW, WTW, LCA, CO₂ e CO₂e.

8. **Sem afirmação de superioridade universal**: os resultados são específicos por corredor, hipótese e fronteira. O CabotageLens não demonstra que a cabotagem é universalmente superior ao transporte rodoviário.

---

## 9. Conclusões

O CabotageLens fornece um método reprodutível e auditável para comparação entre alternativas rodoviárias diretas e alternativas rodoviário-cabotagem-rodoviário em corredores brasileiros. A estrutura torna explícitas as hipóteses de rota, porto, distância, custo modelado, emissões operacionais TTW CO₂e e fronteiras de interpretação.

A evidência de sensibilidade interna e o benchmark externo Gustavo/Costa sustentam interpretação direcional cautelosa. Em todos os cenários executados — tanto sensibilidades internas quanto os 21 pares do benchmark externo — a alternativa multimodal apresenta menores emissões TTW CO₂e que a alternativa rodoviária direta. A reconciliação de fator rodoviário explica grande parte da diferença de magnitude no lado road-only por premissas de consumo de combustível e fator de emissão.

A contribuição principal é metodológica e computacional. O CabotageLens oferece uma estrutura que classifica e documenta cada resultado de forma conservadora, distinguindo consistência direcional de validação calibrada, sensibilidade interna de evidência externa, e exercício diagnóstico de recalibração. Essa disciplina apoia uma expansão fundamentada para o relatório final de TF.

---

## 10. Trabalhos futuros

- Expandir a fronteira ambiental para WTW/LCA com fatores, unidades e documentação compatíveis.
- Reconciliar mais completamente a lógica de carga, alocação, rota e serviço do workbook Gustavo/Costa.
- Melhorar a evidência de distância marítima e validação de portos selecionados.
- Incorporar frete comercial, tarifas, frequência, tempo, confiabilidade e custo de inventário.
- Evoluir para uma super-rede multimodal com serviços, frequências e operadores.
- Ampliar validação contra referências independentes de distância, custo e emissão.

---

## 11. Tabelas de apoio

### Tabela A — Resumo de proveniência e metodologia

| Componente | Fonte ou método | Fronteira | Rastreabilidade |
|------------|-----------------|-----------|-----------------|
| Distância rodoviária | ORS driving-hgv + cache Supabase | Rota modelada | Provedor e cache rastreados |
| Distância marítima | SeaMatrix / haversine fallback / referência externa | Estimativa de rota | Tipo de fonte registrado |
| Emissões rodoviárias | Modelo TTW CO₂e: distância × consumo × fator | Operacional TTW | Parâmetros implementados |
| Emissões marítimas | Modelo TTW CO₂e: classe de embarcação / KPI de rota | Operacional TTW | Classe e intensidade rastreadas |
| Operações portuárias | Modelo fixo + por-TEU + hoteling | Operacional TTW | Parâmetros documentados |
| Custo | Estimativa modelada: combustível + operacional | Custo operacional parcial | Não é frete comercial |

### Tabela B — Resultados de sensibilidade interna

| Par OD | Portos | Emissões rodo (kg CO₂e) | Emissões multi (kg CO₂e) | Δ% | Custo rodo (R$) | Custo multi (R$) | Δ% | Classificação |
|--------|--------|------------------------:|-------------------------:|---:|----------------:|-----------------:|---:|---------------|
| Santos → Manaus | Santos → Manaus | 3.329 | 677 | −79,7% | 8.613 | 4.543 | −47,3% | `sensitivity` |
| Manaus → Pecém | Manaus → Pecém | 4.897 | 840 | −82,8% | 12.687 | 5.133 | −59,5% | `sensitivity` |
| Rio Grande → Suape | Rio Grande → Suape | 2.668 | 614 | −77,0% | 6.904 | 4.372 | −36,7% | `sensitivity` |

### Tabela C — Resumo do benchmark externo Batch 002

| Métrica | Valor |
|---------|------:|
| Células da matriz parseadas | 36 |
| Células puladas (inválidas/não suportadas) | 15 |
| Pares OD positivos e suportados | 21 |
| Linhas executadas com sucesso | 21 |
| Alinhamento direcional | 21/21 (100%) |
| Classificação | 21 × `same_direction_large_gap` |
| Mismatch rodo médio (linha de base) | 199,8% |
| Mismatch rodo mediano (linha de base) | 149,3% |
| Mismatch rodo médio (diagnóstico) | 43,9% |
| Mismatch rodo mediano (diagnóstico) | 19,6% |

### Tabela D — Reconciliação de fator rodoviário

| Fator | Gustavo/Costa | Unidade |
|-------|-------------:|---------|
| FDc (consumo de combustível) | 0,28 | L/km |
| FDe (densidade energética) | 35,52 | MJ/L |
| FDf (fator de emissão) | 86,5 | gCO₂eq/MJ |
| Fator diagnóstico | 0,8602944 | kgCO₂e/km |

### Tabela E — Afirmações permitidas e não permitidas

| Afirmação permitida | Evidência | Ressalva |
|---------------------|-----------|----------|
| CabotageLens fornece estrutura auditável para comparação rodo vs cabotagem | Arquitetura e metodologia | — |
| Corredores longos mostram vantagem direcional da cabotagem em emissões | Sensibilidade #16 + Batch 002 | Sensibilidade interna + direcional externo |
| 100% de alinhamento direcional nos 21 pares OD do benchmark | Batch 002 | Direcional apenas; magnitudes divergem |
| Premissas rodoviárias explicam grande parte da lacuna road-only | Reconciliação de fator | Diagnóstico apenas; não substitui modelo de linha de base |

| **Afirmação NÃO permitida** | **Motivo** |
|------------------------------|------------|
| Cabotagem é universalmente superior | Resultados são corredor-específicos e fronteira-dependentes |
| CabotageLens reproduz o workbook Gustavo/Costa | Magnitudes divergem; metodologia não totalmente reconstruída |
| Custos do modelo são fretes comerciais | Custos são estimativas modeladas |
| Emissões TTW são equivalentes a WTW ou LCA | Fronteiras distintas |
| Resultados de sensibilidade são externamente validados | São exercícios internos |
| O fator diagnóstico deve substituir o modelo rodoviário | É análise diagnóstica apenas |
| Pecém equivale a Fortaleza | Portos diferentes |
| Suape equivale a Recife | Portos diferentes |

---

## 12. Referências (placeholders)

As chaves abaixo são placeholders de citação. A formatação ABNT final será compilada no relatório do TF. Metadados bibliográficos não devem ser inventados.

| Chave | Descrição resumida |
|-------|-------------------|
| `[icct2022]` | Cabotagem brasileira, BR do Mar, contexto de emissões e modal share |
| `[BR_DO_MAR]` | Programa BR do Mar (Lei 14.301/2022) |
| `[ANTAQ_ANUARIO]` | ANTAQ Anuário Estatístico da navegação de cabotagem |
| `[competitiveness2024]` | Competitividade da cabotagem conteinerizada brasileira e super-rede |
| `[shortsea2019]` | Eficiência comparativa CO₂ de short sea container transport |
| `[modalshiftreview2020]` | Revisão sistemática sobre mudança modal rodoviário-SSS |
| `[GUSTAVO_COSTA_2020]` | Gustavo & Costa (2020) — benchmark externo de emissões |
| `[decarb2024]` | Caminhos de descarbonização da cabotagem brasileira |
| `[maritimelca2024]` | Revisão de LCA de combustíveis marítimos |
| `[IMO_GHG_STUDY]` | Estudo IMO de GHG (3º ou 4º) |
| `[berth2009]` | Consumo de combustível de navios atracados |
| `[shipops2022]` | Emissões em hoteling e carga/descarga em portos |
| `[berthairquality2010]` | Impacto de emissões portuárias na qualidade do ar |
| `[ORS_API]` | OpenRouteService API |
| `[SEAMATRIX]` | SeaMatrix — distâncias marítimas |
| `[SUPABASE]` | Supabase — backend de persistência |
| `[PAIXAO_MARLOW]` | Paixão & Marlow — competitividade de SSS |
| `[MEDDA_TRUJILLO]` | Medda & Trujillo — análise de short sea shipping |
| `[CNT_PESQUISA]` | CNT Pesquisa Rodoviária |

---

*Este artigo é a narrativa-fonte concisa para o relatório final de TF. Ele não substitui o scaffold expandido em `tf_final_report_draft.md` e não é o relatório final.*
