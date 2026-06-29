# Relatório de Validação Acadêmica e Metodológica
## Capítulo 4: Metodologia

### 1. Escopo da Validação e Objetivos
Este relatório apresenta a auditoria técnica e acadêmica do **Capítulo 4 (Metodologia)** do rascunho de Trabalho de Formatura (TF) do projeto **CabotageLens**, localizado no arquivo `docs/tf_final_report_draft.md`. O escopo engloba a avaliação do rigor metodológico das definições e premissas (incluindo unidade funcional, alternativas de rotas, distâncias, custos, emissões e classificação de validação), a clareza e fluidez do texto, a defendibilidade acadêmica sob a ótica da engenharia naval, a consistência terminológica e a identificação de lacunas técnicas.

---

### 2. Fonte(s) e Títulos Inspecionados
- **Arquivo de Origem:** [tf_final_report_draft.md](docs/tf_final_report_draft.md)
- **Títulos inspecionados (Capítulo 4 - Linhas 78 a 338):**
  - `## 4. Metodologia`
  - `### 4.1 Unidade funcional e base de carga`
  - `### 4.2 Alternativa rodoviária direta`
  - `### 4.3 Alternativa rodoviário-cabotagem-rodoviário`
  - `### 4.4 Seleção de portos e construção de rota`
  - `### 4.5 Proveniência da distância rodoviária e lógica de roteamento/cache`
  - `### 4.6 Proveniência da distância marítima e hierarquia de fallback`
  - `### 4.7 Avisos same-port e qualidade de rota`
  - `### 4.8 Fronteira de emissões`
  - `### 4.9 Fronteira de custo`
  - `### 4.10 Validação e classificação conservadora`

---

### 3. Resumo Executivo do Capítulo
O Capítulo 4 formaliza a estrutura metodológica adotada no CabotageLens para comparar o transporte rodoviário direto e a cadeia rodoviária-cabotagem-rodoviária no Brasil. Ele estabelece:
1. A unidade funcional do estudo baseada em remessa conteinerizada de carga porta a porta.
2. A formulação conceitual da perna rodoviária direta e da cadeia multimodal (composta por pre-carriage, perna marítima, componentes portuários/hoteling e on-carriage).
3. A lógica determinística de seleção e imposição de portos para construção de rotas.
4. A proveniência das distâncias terrestres (via cache e provedor OpenRouteService) e marítimas (SeaMatrix, referências externas e fallback geométrico por Haversine).
5. Os avisos de qualidade operacional de rotas, com ênfase no tratamento de casos same-port.
6. A delimitação das fronteiras de emissão operacional (Tank-to-Wheel / Tank-to-Wake CO2e) e de custos modelados (em contraste com fretes comerciais).
7. O sistema de classificação de qualidade e robustez dos resultados de validação (Batch 001/001B/002).

---

### 4. Avaliação Geral (Overall Assessment)
**Resultado da Avaliação:** **Aprovado com Ajustes** (*Approved with Adjustments*).
- **Justificativa:** O capítulo descreve com excelente rigor lógico e prudência acadêmica as premissas estruturais do CabotageLens. A definição das fronteiras operacionais (TTW e custos modelados) é correta e impede o sobreafirmamento de superioridade modal. No entanto, há lacunas de rigor técnico e redação que precisam ser corrigidas antes do texto final:
  1. **Ausência de Equações Matemáticas:** Um trabalho de engenharia naval exige a formalização algébrica dos cálculos de consumo, emissões e custos. A descrição puramente qualitativa é insuficiente.
  2. **Indeterminação do Escopo de Gases e GWP:** Falta explicitar se a métrica $CO_{2e}$ incorpora $CH_4$ e $N_2O$ (e quais fatores de aquecimento global) ou se é baseada apenas em $CO_2$ direto.
  3. **Falta de Especificação dos Fatores de Circuidade e Limiares de Alertas:** A metodologia não revela os fatores de desvio e os limiares numéricos usados para os avisos de qualidade de rota.
  4. **Inconsistência Severa de Acentuação:** A subseção 4.1 está totalmente sem acentos, em contraste direto com o restante do capítulo.
  5. **Inclusão Precoce de Resultados:** Estatísticas de execução do Batch 002 foram incorporadas inapropriadamente nas seções de metodologia.
  6. **Redundância Crítica:** O aviso protetivo sobre limites de custos e ciclo de emissões é repetido exaustivamente em quase todas as dez subseções.

---

### 5. Revisão da Qualidade de Redação (Writing Quality Review)
- **Clareza (Clareza):** A exposição dos conceitos logísticos é clara, e as tabelas resumem bem os limites de interpretação de cada componente.
- **Fluidez (Flow):** A estrutura lógica das subseções é excelente, partindo da definição básica (unidade funcional) até o sistema de classificação de validação.
- **Tom Acadêmico (Academic Tone):** Formal e condizente com um TF. Contudo, é enfraquecido pela falta de formalização matemática e pela grafia de jargões técnicos em inglês sem formatação em itálico.
- **Redundância (Redundância):** **Crítica.** O capítulo sofre de uma repetição sistemática de salvaguardas (*disclaimers*). A afirmação de que "custos são estimativas modeladas e não fretes comerciais" e que "emissões são operacionais TTW e não WTW/LCA" aparece em quase todas as dez seções, tornando a leitura desnecessariamente repetitiva. Recomenda-se consolidar esses avisos de forma centralizada.
- **Transições entre Subseções (Transitions):** Fluem de forma orgânica, preparando o leitor para o detalhamento da ferramenta computacional no Capítulo 5.
- **Consistência de Terminologia (Terminology Consistency):**
  - **Mapeamento de Acentuação:** Há uma quebra drástica na Seção 4.1, que não possui acentos ortográficos (ex: *nao*, *e*, *referencia*, *alocacao*, *condicao*, *so*, *sao*), enquanto a Seção 4.2 e seguintes possuem acentuação correta.
  - **Classificação TTW:** Uso generalizado do termo "TTW" sem a necessária distinção de modo: *Tank-to-Wheel* para transporte rodoviário e *Tank-to-Wake* para transporte marítimo.

---

### 6. Revisão da Defensibilidade Acadêmica (Academic Defensibility Review)
- **Especificidade Metodológica para Engenharia Naval:** **Insuficiente em termos de formalização matemática.** Um Trabalho de Formatura em Engenharia Naval não pode se limitar a descrever fluxos de cálculo em formato de texto. É indispensável apresentar formalmente as equações que regem o modelo computacional.
- **Separação de Metodologia e Resultados:** **Ponto Crítico.** A discussão sobre a estabilidade do cache e os dados do rerun do Batch 002 (como "63 route-cache hits, 0 misses, 0 escritas" nas seções 4.2 e 4.5) representa a apresentação de dados empíricos observados e deve ser realocada para os capítulos de resultados e validação (Capítulos 7 e 8). A metodologia deve focar exclusivamente na modelagem da lógica do cache e do roteamento.
- **Transparência e Divulgação de Limitações:** Excelente. O texto aborda honestamente as limitações geométricas de *haversine_fallback*, casos *same-port* e o isolamento de portos alternativos como Pecém e Suape para rotas vizinhas.
- **Prevenção de Sobre-afirmações (Overclaiming):** Muito bem executada. O rascunho protege o CabotageLens de interpretações comerciais e deixa evidente que a superioridade da cabotagem é condicional e route-aware.

---

### 7. Consistência Metodológica (Methodology Consistency Review)
- **Equivalência da Unidade Funcional:** As alternativas rodoviária direta e multimodal são comparadas de forma equitativa em limites de origem-destino (porta a porta). O trecho marítimo não é tratado como substituto sem acesso terrestre.
- **Fatores de Desvio e Circuidade:** **Omissão.** O modelo menciona o uso de distâncias de triagem por Haversine, mas não descreve os fatores de circuidade rodoviária ou desvio marítimo (maritime detour) aplicados para aproximar as distâncias reais de navegação. A metodologia deve declarar esses fatores de forma explícita.
- **Escopo e Classificação de Emissões:** O texto declara o escopo operacional TTW, mas falha em especificar se a métrica $CO_{2e}$ de fato incorpora outros gases estufa ($CH_4$ e $N_2O$ ponderados por potenciais de aquecimento global - GWP) ou se utiliza apenas uma aproximação baseada em $CO_2$ direto. A metodologia deve declarar explicitamente o escopo de gases e os fatores GWP associados.
- **Terminologia de Ciclo de Vida por Modo:** Para evitar imprecisões acadêmicas, o termo genérico TTW deve ser detalhado como *Tank-to-Wheel (TTW)* para o modo rodoviário e *Tank-to-Wake (TTW)* para o modo marítimo.
- **Limiares Quantitativos de Alerta:** A metodologia cita alertas de qualidade de rota como "perna marítima muito curta" e "acesso rodoviário dominante", mas não especifica os limites numéricos que ativam esses avisos no motor do modelo.

---

### 8. Lista de Problemas Agrupados por Gravidade (List of Issues)

#### Gravidade: Bloqueante (Blocking)
1. **Ausência de Equações e Formalização Matemática:** O capítulo não apresenta nenhuma fórmula matemática. É obrigatório formalizar algebricamente os cálculos de consumo de combustível, emissões e agregação de custos.
2. **Indeterminação do Escopo de Gases e Potenciais GWP:** O rascunho utiliza a métrica $CO_{2e}$ sem esclarecer se o modelo de fato calcula emissões equivalentes com base em $CH_4$ e $N_2O$ (e sob qual horizonte de GWP) ou se opera de forma simplificada com fatores de combustível baseados apenas em $CO_2$.
3. **Omissão dos Fatores de Desvio/Circuidade:** A metodologia não descreve como as distâncias de triagem geométrica (*haversine*) são adaptadas às restrições físicas de rota.

#### Gravidade: Importante (Important)
4. **Inconsistência Ortográfica de Acentuação na Seção 4.1:** A subseção 4.1 contém severas falhas de acentuação em português ("adotada e o", "comparacoes", "so sao defensaveis", "alocacao", "nao", "condicao", "metodologica", "consequencia").
5. **Inclusão Precoce de Estatísticas de Execução (Rerun Batch 002):** A menção a "63 route-cache hits, 0 misses" nas seções 4.2 e 4.5 deve ser removida da metodologia e transferida para a seção de validação de resultados.
6. **Uso Indiferenciado de Siglas TTW/WTW:** A monografia deve cindir o termo TTW/WTW genérico em *Tank-to-Wheel* / *Well-to-Wheel* para transporte rodoviário, e *Tank-to-Wake* / *Well-to-Wake* para perna marítima.
7. **Falta de Parametrização Numérica para Alertas de Qualidade:** Não são especificados os limiares quantitativos para o acionamento dos alertas de perna marítima curta ou dominância rodoviária.

#### Gravidade: Menor (Minor)
8. **Redundância Excessiva de Salvaguardas (Disclaimers):** O capítulo repete de forma idêntica as restrições de custo (não ser frete comercial) e emissão (não ser WTW/LCA) em quase todas as seções (4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 4.9, 4.10).
9. **Estrangeirismos Técnicos sem Formatação:** Termos como *pre-carriage*, *on-carriage*, *hoteling*, *same-port*, *routing*, *cache*, *rerun*, *driving-hgv*, *fallback* aparecem em texto comum, sem itálico.
10. **Indefinição de Parâmetros de Combustível e Veículo:** O texto menciona preset de veículo e combustível, mas não especifica qual tipo de diesel (S10/S500), biodiesel ou fatores de emissão de referência foram modelados na linha de base.

---

### 9. Sugestões Específicas de Correção (Suggested Corrections)

#### 9.1 Inclusão de Equações Matemáticas e Escopo de Gases (Problemas 1, 2 e 3)
Recomenda-se a inserção de um bloco de formulação algébrica nas seções de cálculo correspondentes.

- **Equação de Emissões Rodoviárias TTW (Seção 4.2):**
  $$E_{\text{rod, TTW}} = d_{\text{rod}} \times FC_{\text{rod}} \times EF_{\text{diesel, TTW}}$$
  Onde $d_{\text{rod}}$ é a distância rodoviária modelada ($\text{km}$), $FC_{\text{rod}}$ é o consumo específico do veículo representativo ($\text{l/km}$ ou $\text{kg/km}$) e $EF_{\text{diesel, TTW}}$ é o fator de emissão do combustível utilizado ($\text{kg CO}_{2\text{e}}\text{/l}$ ou $\text{kg CO}_{2\text{e}}\text{/kg}$).

- **Equação de Emissões Multimodais Porta a Porta (Seção 4.3):**
  $$E_{\text{multi, TTW}} = E_{\text{pre, TTW}} + E_{\text{mar, TTW}} + E_{\text{port, TTW}} + E_{\text{on, TTW}}$$
  Onde as parcelas representam pre-carriage, perna marítima, componentes portuários/hoteling (se aplicáveis) e on-carriage rodoviário.

- **Esclarecimento sobre a métrica $CO_{2e}$ e GWP na Seção 4.8:**
  > *"As emissões são expressas em $\text{kg CO}_{2\text{eq}}$ por remessa. A modelagem adota fatores de emissão diretos baseados em [Necessita citação de fonte] que representam [Esclarecer se é apenas CO2 como proxy ou se inclui CH4 e N2O com seus potenciais GWP-100 do IPCC, ex: GWP = 28 para CH4 e 265 para N2O]. Essa definição deve ser explicitada para evitar a equiparação incorreta com fatores puramente de dióxido de carbono ($CO_2$-only)."*

- **Especificação de Circuidade / Desvio (Seção 4.6):**
  > *"Quando a distância marítima provém de Haversine fallback ($d_{\text{hav}}$), uma estimativa física é obtida aplicando um fator de desvio marítimo (detour factor) de $f_{\text{detour}}$ [Necessita especificação de valor], de forma a aproximar a rota geométrica da trajetória real de navegação:*
  $$d_{\text{mar}} = d_{\text{hav}} \times f_{\text{detour}}$$
  *Caso contrário, a distância estimada por Haversine deve ser explicitamente descrita como o limite inferior absoluto (distância ortodrômica direta) de navegação marítima."*

#### 9.2 Correção de Redundâncias e Consolidação de Salvaguardas (Problema 8)
- Em vez de repetir em todas as subseções que o custo modelado não é frete comercial e que o ciclo é TTW, recomenda-se criar uma seção de "Fronteiras e Escopo Metodológico" unificada no início do capítulo (por exemplo, na Seção 4.1) ou simplesmente remover as sentenças repetitivas das seções 4.2 a 4.7 e 4.10, mantendo a discussão detalhada exclusivamente nas Seções 4.8 (Emissões) e 4.9 (Custo).
- *Exemplo de trecho redundante a ser suprimido nas seções intermediárias:*
  - Na Seção 4.3 (Linha 148): remover *"Custos multimodais são estimativas de custo do modelo, não fretes comerciais... Resultados TTW não devem ser misturados com evidências WTW, LCA..."*.
  - Na Seção 4.4 (Linha 175): remover *"Os custos calculados continuam sendo estimativas de custo do modelo... As emissões continuam sendo emissões operacionais TTW CO2e..."*.

#### 9.3 Correção Ortográfica e Normatização de Termos (Problemas 4, 9 e 10)
- **Seção 4.1:** Aplicar a acentuação correta no texto (substituir "adotada e o" por "adotada é o", "comparacoes" por "comparações", "so sao" por "só são", "alocacao" por "alocação", "nao" por "não", "metodologica" por "metodológica").
- **Estrangeirismos:** Formatar termos técnicos em inglês em itálico: *\textit{pre-carriage}*, *\textit{on-carriage}*, *\textit{hoteling}*, *\textit{same-port}*, *\textit{driving-hgv}*, *\textit{fallback}*, *\textit{cache}*, *\textit{rerun}*.
- **Cindir TTW/WTW:** Substituir referências genéricas a "TTW" por *"Tank-to-Wheel (TTW)"* para rodoviário e *"Tank-to-Wake (TTW)"* para marítimo.

---

### 10. Lista de Verificação de Validação (Academic Validation Checklist)
- [x] **Unidade Funcional Explícita:** O capítulo define a unidade funcional antes de descrever as alternativas.
- [ ] **Rigor de Formalização Matemática (Bloqueante):** **Pendente.** Necessita da inserção de fórmulas algébricas para os cálculos de emissões e custos por trecho.
- [ ] **Definição de Fronteiras de Carbono e Gases (Bloqueante):** **Pendente.** Necessita especificar o escopo exato de gases na métrica $CO_{2e}$ e os fatores GWP aplicados.
- [ ] **Uniformidade Ortográfica e Acentuação (Importante):** **Pendente.** A subseção 4.1 requer revisão ortográfica completa para acentuação em português.
- [ ] **Separação de Resultados e Metodologia (Importante):** **Pendente.** As estatísticas do rerun do Batch 002 devem ser movidas para os Capítulos 7/8.
- [x] **Hierarquia de Fallback Defensável:** A hierarquia de fontes de distância marítima está clara e as limitações de Haversine estão corretas.
- [x] **Prevenção de Sobre-afirmações:** O capítulo diferencia corretamente estimativas modeladas de custos operacionais frente a preços de mercado.
