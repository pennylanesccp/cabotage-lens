# Relatório de Validação Acadêmica e Metodológica
## Capítulo 6: Estudos de Caso e Validação

### 1. Escopo da Validação e Objetivos
Este relatório apresenta a auditoria técnica e acadêmica do **Capítulo 6 (Estudos de caso e validação)** do rascunho de Trabalho de Formatura (TF) do projeto **CabotageLens**, localizado no arquivo `docs/tf_final_report_draft.md`. O escopo abrange a avaliação do rigor metodológico, clareza e correção textual, tom acadêmico, defensibilidade científica, aderência aos padrões de emissões (distinção TTW/WTW e notações de carbono equivalente por modo de transporte), consistência matemática das reconciliações com benchmarks externos e validade da classificação das evidências empíricas apresentadas.

---

### 2. Fonte(s) e Títulos Inspecionados
- **Arquivo de Origem:** [tf_final_report_draft.md](file:///C:/Users/Cliente/Documents/workspaces/personal/skills-cabotage-lens/cabotage-lens/docs/tf_final_report_draft.md)
- **Títulos inspecionados (Capítulo 6 - Linhas 523 a 699):**
  - `## 6. Estudos de caso e validacao`
  - `### 6.1 Estratégia de validação e classificação de evidências`
  - `### 6.2 Batch 001 como diagnóstico histórico`
  - `### 6.3 Batch 001B como camada de decisão metodológica`
  - `### 6.4 Sensibilidades executadas`
  - `### 6.5 Batch 002 como benchmark externo Gustavo/Costa`
  - `### 6.6 Rerun Supabase/cache como verificação de estabilidade`
  - `### 6.7 Reconciliação rodoviária como diagnóstico de alinhamento`
  - `### 6.8 Categorias finais de uso no TF e controles de afirmação`

---

### 3. Resumo Executivo do Capítulo
O Capítulo 6 estrutura a validação empírica do modelo CabotageLens. Ele define um framework de classificação de evidências em camadas (diagnóstico histórico, sensibilidades, benchmarks externos e reconciliações rodoviárias) para assegurar o uso metodologicamente correto das saídas numéricas no TF. O capítulo relata:
1. O diagnóstico histórico de 5 pares origem-destino (Batch 001), apontando a limitação inicial de distâncias por fallback geométrico.
2. A organização do Batch 001B, definindo regras para a triagem e restrição de uso de casos bloqueados ou excluídos.
3. A execução de 3 cenários de sensibilidade (Santos/Manaus com distância de referência, Manaus/Pecém e Rio Grande/Suape com portos alternativos).
4. A comparação direcional de emissões (Batch 002) com o workbook de referência de Gustavo Costa, apontando acordo direcional de 100% nas 21 linhas suportadas, apesar de lacunas de magnitude relevantes (*same_direction_large_gap*).
5. A reexecução controlada (rerun) via cache para testar e comprovar a estabilidade do processo computacional rodoviário.
6. A reconciliação rodoviária diagnosticando que a diferença nas premissas de consumo e fatores de combustível explica a maior parte da divergência na perna terrestre do benchmark.
7. As regras operacionais finais que limitam a força das afirmações no TF, proibindo sobre-alegações (*overclaiming*) comerciais ou de superioridade universal.

---

### 4. Avaliação Geral (Overall Assessment)
**Resultado da Avaliação:** **Aprovado com Ajustes** (*Approved with Adjustments*).
- **Justificativa:** O capítulo apresenta um excelente e robusto arcabouço lógico de controle de qualidade para a validação empírica do modelo, separando consistentemente as tendências qualitativas direcionalmente corretas das magnitudes quantitativas absolutas. Contudo, há uma pendência de redação crítica na Seção 6.2 (completa ausência de acentos ortográficos em português), imprecisões terminológicas na definição de ciclo de vida (TTW/WTW sem distinção por modo de transporte), ambiguidade na apresentação das tabelas de métricas de erro rodoviário, redundância defensiva excessiva e falta de citações acadêmicas explícitas para os trabalhos de referência.

---

### 5. Revisão da Qualidade de Redação (Writing Quality Review)
- **Clareza (Clareza):** A argumentação lógica e a separação de resultados são claras e compreensíveis. Contudo, a apresentação de percentuais de discrepância (como `199.8%` ou `43.9%`) sob a denominação "Diferença rodoviária média" é ambígua, pois pode ser confundida com distâncias e não com emissões de $CO_2$.
- **Fluidez (Flow):** A fluidez de leitura é severamente prejudicada pelo mesmo padrão observado no capítulo anterior: a inserção rígida de tabelas markdown longas e repetitivas em todas as subseções (especialmente a tabela 6.8, que replica conceitos das tabelas 6.1 e 6.3).
- **Tom Acadêmico (Academic Tone):** Geralmente formal e científico. Entretanto, é enfraquecido pelo uso abundante de termos e acrônimos em inglês sem formatação (itálico) ou definição prévia (ex: *rerun*, *misses*, *cache hits*, *same-port*, *booking*, *heavy goods vehicle*, *haversine_fallback*, *pre-carriage*, *on-carriage*).
- **Redundância (Redundância):** **Muito alta.** O aviso protetivo afirmando que "custos são modelados, não são fretes de mercado, as emissões são operacionais TTW e a ferramenta não prova a disponibilidade real de serviços de cabotagem" é repetido literalmente em todas as oito subseções (de 6.1 a 6.8). A consolidação desses disclaimers em parágrafos de transição tornaria a leitura muito menos cansativa.
- **Transições entre Subseções (Transitions):** Aceitáveis, mas a transição de tabelas para novos blocos de texto continua muito fragmentada e necessita de ganchos textuais mais fluidos.
- **Consistência de Terminologia (Terminology Consistency):** Uso misto de siglas como `CO2e` e `CO2eq` na mesma subseção (como na 6.7), e do acrônimo híbrido de unidade "kg TTW CO2e" na Seção 6.4.

---

### 6. Revisão da Defensibilidade Acadêmica (Academic Defensibility Review)
- **Uso de Citações e Fontes:** **Crítico.** O capítulo baseia metade do seu conteúdo (lotes Batch 002, reruns e reconciliações) nos trabalhos da "família Gustavo/Costa" ou "workbook Gustavo/Costa". No entanto, não há **nenhuma** citação formal a essas publicações. O texto precisa incorporar referências diretas usando as chaves BibTeX já presentes no repositório (`\citep{competitiveness2024}` e `\citep{decarb2024}`).
- **Explicitação de Premissas e Hipóteses:** As premissas físicas do diagnóstico rodoviário (`FDc`, `FDe` e `FDf`) estão explicitamente declaradas na Seção 6.7, o que confere boa transparência matemática ao diagnóstico.
- **Divulgação de Limitações:** Altamente defensiva e transparente. As fraquezas e inconsistências de fronteira do modelo comparativo estão completamente divulgadas.
- **Prevenção de Sobre-alegação (Overclaiming):** Excelente. As saídas empíricas do Batch 002 e das sensibilidades não são tratadas como provas universais de viabilidade comercial, restringindo-se à concordância qualitativa em determinadas pernas.

---

### 7. Consistência Metodológica (Methodology Consistency Review)
- **Rigor Terminológico de Ciclo de Vida (TTW/WTW):** **Inconsistência Bloqueante.** O texto usa a sigla "TTW" (ou "TTW CO2e") de forma universal para o multimodal. Para rigor científico de engenharia naval, o capítulo deve deixar claro que as fronteiras operacionais diferem:
  - Para pernas marítimas: **Tank-to-Wake (TTW)** para emissões de combustão direta do navio e **Well-to-Wake (WTW)** para ciclo de vida.
  - Para pernas terrestres (rodoviárias): **Tank-to-Wheel (TTW)** para emissões de combustão direta do motor do caminhão e **Well-to-Wheel (WTW)** para ciclo de vida.
- **Fator e Unidade de Carbono Equivalente ($\text{CO}_{2\text{eq}}$):** O capítulo utiliza a expressão de unidade "kg TTW CO2e" (Seção 6.4) ou "kgCO2e/km" (Seção 6.7). Academicamente, a unidade deve refletir a dimensão física ($\text{kg CO}_{2\text{eq}}$ ou $\text{kg CO}_{2\text{eq}}\text{/km}$) e a fronteira deve ser descrita separadamente para evitar confusão entre unidade e escopo.
- **Dimensionalidade da Reconciliação Rodoviária:** A equação da Seção 6.7 é matematicamente precisa:
  $$0{,}28 \text{ L/km} \times 35{,}52 \text{ MJ/L} \times 86{,}5 \text{ g }\text{CO}_{2\text{eq}}\text{/MJ} \div 1000 = 0{,}8602944 \text{ kg }\text{CO}_{2\text{eq}}\text{/km}$$
  Os valores e conversões de L para MJ e MJ para g estão corretos, necessitando apenas da correção da grafia da unidade de saída.

---

### 8. Lista de Problemas Agrupados por Gravidade (List of Issues)

#### Gravidade: Bloqueante (Blocking)
1. **Ausência Completa de Acentuação Ortográfica na Seção 6.2:** A subseção `### 6.2 Batch 001 como diagnóstico histórico` foi integralmente digitada sem acentos ou caracteres especiais em português (ex: *historica*, *avaliacao*, *validacao*, *numericos*, *referencia*, *revisao*, *limitacao*, *maritimas*, *navegacao*, *servico*, *Sao Paulo*, *Brasilia*, *excluida*, *nao*, *sao*, *selecao*, *exclusao*). Isto representa uma falha acadêmica grave e deve ser corrigido imediatamente.
2. **Indefinição dos Limites de Ciclo de Vida (TTW/WTW) por Modo de Transporte:** O uso indiscriminado da sigla "TTW" para ambas as operações rodoviária e marítima precisa ser formalmente diferenciado no texto (adotando *Tank-to-Wheel* para rodoviário e *Tank-to-Wake* para marítimo).

#### Gravidade: Importante (Important)
3. **Falta de Citação Bibliográfica de Referência (Gustavo/Costa):** O capítulo refere-se exaustivamente ao benchmark "Gustavo/Costa", mas falha em incluir as citações aos artigos correspondentes (`\citep{competitiveness2024}` e `\citep{decarb2024}`).
4. **Redundância Sistemática de Disclaimers Operacionais:** A repetição quase idêntica de disclaimers sobre "não ser frete comercial", "não provar disponibilidade de serviço" e "estimativa modelada" em cada uma das subseções satura o texto.
5. **Ambiguidade de Nomenclatura nas Tabelas (Métricas de Discrepância):** As tabelas das seções 6.6 e 6.7 denominam a divergência de emissões rodoviárias como "Diferença rodoviária média" e "Diferença rodoviária mediana", o que induz o leitor a pensar que se trata de uma discrepância na quilometragem (distância) rodoviária calculada.

#### Gravidade: Menor (Minor)
6. **Grafia Inadequada de Unidades de Emissões:** O uso das expressões "kg TTW CO2e" e "kgCO2e/km" deve ser substituído pela notação padrão com subscrito em LaTeX: $\text{kg CO}_{2\text{eq}}$ e $\text{kg CO}_{2\text{eq}}\text{/km}$.
7. **Estrangeirismos Técnicos sem Itálico:** Termos em inglês como *rerun*, *route-cache hits*, *misses*, *same-port*, *booking*, *heavy goods vehicle*, *fallback* devem ser grafados em itálico para manter o rigor gramatical acadêmico.
8. **Inconsistência entre Siglas de Dióxido de Carbono Equivalente:** O texto oscila entre `CO2e` e `CO2eq` de forma desordenada no mesmo capítulo. Recomenda-se a padronização para `CO2eq`.

---

### 9. Sugestões Específicas de Correção (Suggested Corrections)

#### Correção Ortográfica da Seção 6.2 (Problema 1)
- **Sugestão de Reescrita de Todo o Bloco da Seção 6.2 (com acentuação completa):**
  > *"O Batch 001 foi a primeira camada **histórica** de **avaliação** dos casos de **validação**. Ele preserva resultados **numéricos** para cinco pares origem-destino, mas todos os casos ficaram associados **à** necessidade de **referência** ou **revisão** posterior. A principal **limitação** diagnosticada foi o uso de distâncias **marítimas** com a abordagem \textit{haversine\_fallback} em casos onde a distância de **navegação** e a plausibilidade de **serviço** exigem evidência mais forte.*
  > 
  > *Os cinco casos **históricos** foram:*
  > - *\texttt{TF-VAL-001}: **São** Paulo, SP $\rightarrow$ Santos, SP (Santos $\rightarrow$ Santos) $\rightarrow$ **Diagnóstico** de caso \textit{same-port} e limite de rota.*
  > - *\texttt{TF-VAL-002}: **São** Paulo, SP $\rightarrow$ Manaus, AM (Santos $\rightarrow$ Manaus) $\rightarrow$ **Diagnóstico** **histórico**; base para sensibilidade de **distância** de **referência**.*
  > - *\texttt{TF-VAL-003}: Manaus, AM $\rightarrow$ Fortaleza, CE (Manaus $\rightarrow$ Fortaleza) $\rightarrow$ **Diagnóstico** **histórico**; **referência** exata de Fortaleza permanece faltante.*
  > - *\texttt{TF-VAL-004}: **Brasília**, DF $\rightarrow$ Salvador, BA (Angra dos Reis $\rightarrow$ Salvador) $\rightarrow$ **Diagnóstico** **histórico**; cadeia de Angra dos Reis depois **excluída** para o benchmark **conteinerizado**.*
  > - *\texttt{TF-VAL-005}: Porto Alegre, RS $\rightarrow$ Recife, PE (Rio Grande $\rightarrow$ Recife) $\rightarrow$ **Diagnóstico** **histórico**; **referência** exata de Recife permanece faltante.*
  > 
  > *Essas linhas **não** devem ser tratadas como resultados corrigidos. Elas **são** importantes porque mostram onde a metodologia precisava separar \textit{fallback}, **seleção** de porto, sensibilidade e **exclusão**."*

#### Correção de Ciclo de Vida e Notações de CO2eq (Problemas 2 e 6)
- **Sugestão de Reescrita para o Parágrafo da Tabela da Seção 6.4:**
  > *"Nas três linhas executadas, as emissões calculadas correspondem a emissões operacionais de dióxido de carbono equivalente ($\text{CO}_{2\text{eq}}$) sob as fronteiras Tank-to-Wheel (TTW) para pernas terrestres e Tank-to-Wake (TTW) para pernas marítimas, não devendo ser confundidas com as métricas de ciclo de vida completo Well-to-Wheel (WTW) ou Well-to-Wake (WTW), respectivamente. Os resultados continuam expressos em $\text{kg CO}_{2\text{eq}}$ por remessa, dentro da fronteira definida."*
- **Ajuste na Tabela 6.4:** Alterar os títulos das colunas de "TTW CO2e rodoviário" para "Emissões rodoviárias ($\text{kg CO}_{2\text{eq}}$)" e "TTW CO2e multimodal" para "Emissões multimodais ($\text{kg CO}_{2\text{eq}}$)", removendo o sufixo "kg TTW CO2e" dos valores numéricos.

#### Correção de Citações (Problema 3)
- **Inserção de Citações na Seção 6.5:**
  > *"O Batch 002 acrescentou uma camada de benchmark externo baseada no workbook operacional dos trabalhos de Gustavo Costa \citep{competitiveness2024, decarb2024}. Esse benchmark pertence ao mesmo contexto amplo de comparação..."*

#### Correção de Ambiguidade de Nomenclatura (Problema 5)
- **Ajuste nas Tabelas 6.6 e 6.7:** Alterar o rótulo "Diferença rodoviária média/mediana" para "Diferença média/mediana de emissões rodoviárias ($\text{CO}_{2\text{eq}}$)".
- **Ajuste na Tabela 6.7 (Linha 660):** Corrigir a unidade do fator de emissão no texto e tabela para $\text{g }\text{CO}_{2\text{eq}}\text{/MJ}$, e o fator resultante para $0{,}8602944 \text{ kg }\text{CO}_{2\text{eq}}\text{/km}$.

---

### 10. Lista de Verificação de Validação (Academic Validation Checklist)
- [x] **Separabilidade das Categorias de Dados:** O capítulo categoriza adequadamente as evidências em termos de relevância metodológica (diagnóstico, sensibilidade, benchmark e reconciliação).
- [x] **Defendibilidade Metodológica:** O capítulo valida qualitativamente a consistência direcional do modelo com a literatura local. No entanto, é necessária a inclusão das citações BibTeX recomendadas.
- [x] **Classificações de Emissão:** **Necessita de ajuste crítico.** Há necessidade de formalizar a divisão de fronteiras (Tank-to-Wake vs. Tank-to-Wheel) no texto do relatório e padronizar o uso de $\text{CO}_{2\text{eq}}$.
- [x] **Conformidade Gramatical e Ortográfica:** **Incompatível na Seção 6.2.** A Seção 6.2 inteira carece de acentuação no português e precisa ser reescrita de acordo com as diretrizes propostas.
- [x] **Rastreabilidade Físico-Matemática:** A derivação das equações e o uso de caches estão bem justificados, comprovando a estabilidade computacional da ferramenta.
- [x] **Transparência de Limitações:** Plenamente atendida. O capítulo explicita as barreiras de comparação e proíbe interpretações de otimização comercial das rotas ou tarifas.
