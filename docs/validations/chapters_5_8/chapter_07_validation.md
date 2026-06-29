# Relatório de Validação Acadêmica e Metodológica
## Capítulo 7: Resultados

### 1. Escopo da Validação e Objetivos
Este relatório apresenta a auditoria técnica e acadêmica do **Capítulo 7 (Resultados)** do rascunho de Trabalho de Formatura (TF) do projeto **CabotageLens**, localizado no arquivo `docs/tf_final_report_draft.md`. O escopo abrange a avaliação do rigor metodológico dos dados numéricos apresentados, clareza e adequação da notação científica, tom acadêmico, defendibilidade das comparações de custos e emissões, consistência das tabelas matemáticas e rastreabilidade dos desvios (mismatches) em relação aos benchmarks externos.

---

### 2. Fonte(s) e Títulos Inspecionados
- **Arquivo de Origem:** [tf_final_report_draft.md](docs/tf_final_report_draft.md)
- **Títulos inspecionados (Capítulo 7 - Linhas 700 a 839):**
  - `## 7. Resultados`
  - `### 7.1 Inventário final de casos e categorias de uso no TF`
  - `### 7.2 Resultados das sensibilidades executadas`
  - `### 7.3 Resultados do Batch 002`
  - `### 7.4 Resultados do rerun Supabase/cache`
  - `### 7.5 Resultados da reconciliação rodoviária`
  - `### 7.6 Síntese da interpretação numérica segura`

---

### 3. Resumo Executivo do Capítulo
O Capítulo 7 consolida as saídas empíricas do CabotageLens sob o framework de classificação definido no Capítulo 6. Ele apresenta:
1. O inventário de categorias de uso, confirmando que atualmente **não há casos classificados como `headline_candidate`** devido a limitações metodológicas e de referências.
2. Os resultados numéricos de custo e emissões de 3 sensibilidades (Santos/Manaus, Manaus/Pecém e Rio Grande/Suape), apontando desempenho favorável ao multimodal em todos os casos testados.
3. Os resultados qualitativos e quantitativos do Batch 002, demonstrando acordo direcional de 100% (21/21) com o workbook Gustavo/Costa em emissões, acompanhado da classificação geral *same_direction_large_gap*.
4. A reexecução controlada (rerun) via cache provando a estabilidade dos cálculos terrestres e isolando o erro de magnitude.
5. O diagnóstico de reconciliação rodoviária, em que a adoção das premissas de fator do benchmark reduz a discrepância média das emissões rodoviárias de 199,8% para 43,9%.
6. Uma tabela síntese para interpretação numérica segura de todos os lotes e execuções operacionais.

---

### 4. Avaliação Geral (Overall Assessment)
**Resultado da Avaliação:** **Aprovado com Ajustes** (*Approved with Adjustments*).
- **Justificativa:** O capítulo cumpre a função de documentar os resultados empíricos do protótipo com transparência e honestidade intelectual, registrando explicitamente a ausência de conclusões absolutas. Contudo, há falhas de defendibilidade acadêmica críticas (tabela de custos exibe distorções imensas sem qualquer explicação teórica no texto), imprecisões terminológicas de fronteiras (TTW/WTW geral), ambiguidade nos rótulos de erros percentuais, excesso de disclaimers repetitivos e falta de referências cruzadas com a literatura bibliográfica de referência.

---

### 5. Revisão da Qualidade de Redação (Writing Quality Review)
- **Clareza (Clareza):** A redação das seções é inteligível e a descrição do rerun e da reconciliação está logicamente estruturada. No entanto, a falta de explicação de por que os custos multimodais são tão baixos prejudica seriamente a clareza metodológica do modelo econômico para o leitor.
- **Fluidez (Flow):** Prejudicada pelo uso exaustivo de tabelas markdown curtas e desconectadas ao fim de cada seção. Recomenda-se a unificação de algumas dessas tabelas para melhorar o fluxo narrativo.
- **Tom Acadêmico (Academic Tone):** Formal e técnico, mas prejudicado pelo uso de jargões técnicos em inglês e expressões de código sem formatação apropriada (ex: *rerun*, *cache hits*, *misses*, *same-port*, *booking*, *pre-carriage*, *on-carriage*, *mismatch*).
- **Redundância (Redundância):** **Extremamente alta.** A declaração de que "custos são estimativas modeladas, não são fretes de mercado, as emissões são operacionais TTW e a ferramenta não prova a disponibilidade real de serviços" é repetida de forma idêntica em todas as subseções (7.1, 7.2, 7.3, 7.4, 7.5 e 7.6). Esta insistência satura o texto.
- **Transições entre Subseções (Transitions):** abruptas. A transição entre os resultados numéricos brutos e as discussões metodológicas adjacentes carece de parágrafos de ligação mais suaves.
- **Consistência de Terminologia (Terminology Consistency):** Uso misto e inconsistente de `CO2e` e `CO2eq` na mesma seção. A unidade "kg TTW CO2e" constitui uma fusão inadequada de métrica física e fronteira operacional.

---

### 6. Revisão da Defensibilidade Acadêmica (Academic Defensibility Review)
- **Explicação de Discrepâncias de Custo:** **Ponto Crítico.** A Tabela 7.2 reporta custos de R$ 727,33 para Manaus $\rightarrow$ Pecém contra R$ 26.391,03 para a rota rodoviária (uma diferença de 36 vezes). O capítulo não fornece qualquer justificativa teórica para essa discrepância extrema. Para ser defensável frente a uma banca examinadora, o texto deve explicar que a perna marítima do CabotageLens adota uma alocação baseada em compartilhamento de capacidade (onde o custo operacional do navio é dividido por milhares de contêineres nas lógicas `teu_share` ou `dwt_share`), enquanto o modo rodoviário direto carrega a totalidade do custo fixo e variável de um veículo dedicado.
- **Uso de Citações e Fontes:** A discussão dos resultados do Batch 002 e da reconciliação rodoviária baseia-se na comparação com os trabalhos de Gustavo Costa, mas falha em citar formalmente os artigos do repositório (`\citep{competitiveness2024}` e `\citep{decarb2024}`).
- **Explicitação de Hipóteses e Limitações:** As limitações metodológicas de cada lote e os critérios de filtragem de células puladas estão muito bem documentados.
- **Prevenção de Sobre-alegação (Overclaiming):** Excelente. O texto deixa claro que as reduções calculadas são condicionadas às premissas e não autorizam a declaração de superioridade universal da cabotagem.

---

### 7. Consistência Metodológica (Methodology Consistency Review)
- **Rigor de Ciclo de Vida (TTW/WTW por Modo):** **Inconsistência Bloqueante.** Assim como nos capítulos anteriores, o termo "TTW" (ex: `TTW CO2e`) é aplicado indistintamente a todo o multimodal. Deve-se detalhar as fronteiras corretas por modo de transporte (*Tank-to-Wheel* para rodoviário e *Tank-to-Wake* para marítimo) e as espécies de gases inclusas ($CO_2$, $CH_4$, $N_2O$ com GWP correspondente).
- **Ambiguidade das Métricas de Mismatch:** O termo "Mismatch rodoviário antes/depois" é ambíguo, pois pode ser interpretado como um erro na quilometragem das rotas terrestres. O correto é rotular como "Divergência média/mediana de emissões rodoviárias ($\text{CO}_{2\text{eq}}$)".
- **Omissão da Lacuna Multimodal Residual:** O capítulo indica que o rerun computacional estabilizou as rotas, mas manteve um "Mismatch multimodal antes/depois" de cerca de 60,8% (média) em relação ao benchmark. O texto falha em apontar para o leitor que essa divergência marítima se deve a fatores metodológicos pendentes de alinhamento (tais como escolha de trajetos de navegação reais no workbook versus fallbacks de distância marítima, consumo auxiliar, hoteling ou regras de alocação de capacidade do navio).
- **Grafia Inadequada de Unidades Físicas:** A notação "kg TTW CO2e" deve ser corrigida para $\text{kg CO}_{2\text{eq}}$ e a fronteira deve ser identificada no cabeçalho ou texto de apoio.

---

### 8. Lista de Problemas Agrupados por Gravidade (List of Issues)

#### Gravidade: Bloqueante (Blocking)
1. **Distorção de Custos sem Justificativa Teórica (Efeito de Compartilhamento):** Exibição de custos multimodais excessivamente baixos (BRL 727,33) sem esclarecer que isso é decorrência direta do método de alocação de capacidade de navios de grande porte (onde custos do navio são distribuídos por milhares de contêineres na lógica `teu_share`), contra o custo de veículo dedicado no rodoviário. Sem essa explicação, as saídas econômicas parecem um erro de cálculo e invalidam a defesa.
2. **Indefinição de Acrônimos de Fronteira (TTW/WTW) por Modo de Transporte:** O uso universal de "TTW" para a cadeia multimodal deve ser desmembrado em *Tank-to-Wheel* (rodoviário) e *Tank-to-Wake* (marítimo).

#### Gravidade: Importante (Important)
3. **Ambiguidade dos Rótulos de Mismatch nas Tabelas:** O uso de "Mismatch rodoviário antes/depois" em porcentagem induz a erros de interpretação sobre erros de distâncias físicas.
4. **Omissão de Discussão sobre o Desvio Multimodal de Magnitude (60,8%):** O capítulo aponta o erro de magnitude marítima no benchmark, mas não teoriza sobre as origens dessa divergência metodológica residual.
5. **Ausência de Citação Bibliográfica nos Resultados de Benchmark:** Falta de inserção das chaves BibTeX de referência (`\citep{competitiveness2024}` e `\citep{decarb2024}`) ao confrontar os dados com o workbook de Gustavo Costa.
6. **Redundância Excessiva de Disclaimers Protetivos:** Repetição literal de disclaimers sobre "não ser tarifa comercial" e "estimativa de protótipo acadêmico" em todas as subseções.

#### Gravidade: Menor (Minor)
7. **Grafia Inadequada de Unidades de Carbono Equivalente:** Substituir notações informais como "kg TTW CO2e" e "kgCO2e/km" pela notação científica padrão $\text{kg CO}_{2\text{eq}}$ e $\text{kg CO}_{2\text{eq}}\text{/km}$.
8. **Estrangeirismos Técnicos sem Itálico:** Palavras em inglês como *rerun*, *cache hits*, *misses*, *same-port*, *booking*, *pre-carriage*, *on-carriage*, *mismatch* devem ser formatadas em itálico.
9. **Inconsistência entre Siglas de Dióxido de Carbono Equivalente:** Padronizar o texto em torno de `CO2eq` ou $\text{CO}_{2\text{eq}}$.

---

### 9. Sugestões Específicas de Correção (Suggested Corrections)

#### Justificativa da Divergência de Custos (Problema 1)
- **Sugestão de Reescrita de Parágrafo na Seção 7.2:**
  > *"Nos três cenários de sensibilidade executados, a alternativa multimodal apresentou um custo modelado significativamente menor do que o rodoviário direto. Essa discrepância (em que o custo multimodal modelado chega a ser até 35 vezes inferior ao rodoviário direto) decorre estritamente da lógica de alocação de capacidade adotada pelo modelo do CabotageLens. Na alternativa multimodal, o custo fixo e o consumo de combustível da perna marítima são distribuídos de forma proporcional entre toda a capacidade operacional do navio feeder (\textit{teu\_share}), alocando apenas uma fração dimensionalmente diminuta (cerca de $0{,}03\%$) ao contêiner unitário de 14 toneladas. Em contrapartida, na alternativa rodoviária direta, o contêiner assume $100\%$ dos custos fixos e variáveis associados ao veículo rodoviário dedicado (\textit{heavy goods vehicle} - HGV) ao longo de todo o trajeto terrestre. Esses valores representam estimativas operacionais de custo alocado sob hipóteses de engenharia, não correspondendo a tarifas comerciais de mercado, taxas portuárias locais integradas ou fretes de contratação de operadores logísticos reais."*

#### Correção de Mismatch e Desvio Multimodal (Problemas 3 e 4)
- **Sugestão de Ajuste de Nomenclatura nas Tabelas 7.4 e 7.6:** Alterar "Mismatch rodoviário antes/depois" para "Divergência de emissões rodoviárias ($\text{CO}_{2\text{eq}}$) antes/depois" e "Mismatch multimodal antes/depois" para "Divergência de emissões multimodais ($\text{CO}_{2\text{eq}}$) antes/depois".
- **Sugestão de Inserção de Parágrafo explicativo na Seção 7.4 (Fim do parágrafo de divergência multimodal):**
  > *"A divergência multimodal residual de $60{,}8\%$ de média observada no rerun indica que, mesmo com a estabilidade de cache rodoviário comprovada, persistem lacunas metodológicas na perna marítima em relação ao benchmark de referência. Tais lacunas decorrem de: (i) discrepâncias entre as rotas marítimas reais assumidas no workbook e as distâncias simplificadas por matriz ou fallback geométrico no CabotageLens; (ii) divergências na alocação de combustível da embarcação em trânsito; e (iii) diferenças na representação de emissões auxiliares de hoteling e manobra. Esses desvios identificam os pontos onde a calibração de magnitude do modelo de cabotagem ainda requer refino futuro."*

#### Correção de Citações e Redundâncias (Problemas 5 e 6)
- **Inserção de Citação na Seção 7.3:**
  > *"O Batch 002 apresenta o resultado observado do benchmark externo extraído do workbook de modelagem associado aos estudos de Gustavo Costa \citep{competitiveness2024, decarb2024}..."*
- **Consolidação de Disclaimers:** Manter os disclaimers detalhados na introdução (Seção 7.1) e na síntese final (Seção 7.6). Nos itens 7.2, 7.3, 7.4 e 7.5, remover as repetições literais das mesmas frases defensivas, mantendo apenas a remissão conceitual curta às restrições gerais do modelo.

#### Correção de Grafia e Unidades (Problema 7)
- Nas tabelas da Seção 7.2, alterar o cabeçalho das emissões para "Emissões rodoviárias ($\text{kg CO}_{2\text{eq}}$)" e "Emissões multimodais ($\text{kg CO}_{2\text{eq}}$)", apresentando os valores apenas de forma numérica e sem o sufixo "kg TTW CO2e".
- Na subseção 7.5 (Tabela e Texto), alterar o fator resultante de `0.8602944 kgCO2e/km` para $0{,}8602944\text{ kg CO}_{2\text{eq}}\text{/km}$.

---

### 10. Lista de Verificação de Validação (Academic Validation Checklist)
- [x] **Separabilidade das Categorias de Dados:** O capítulo mapeia os resultados conforme o inventário de uso de dados e categorias de evidência definido anteriormente.
- [x] **Defendibilidade Metodológica:** A comparação de custos exige a inclusão do parágrafo explicativo sugerido sobre compartilhamento de capacidade marítima versus veículo rodoviário dedicado para ser academicamente aceitável.
- [x] **Rigor de Emissões:** **Ajustes necessários.** Requer a especificação de limites TTW (Tank-to-Wheel / Tank-to-Wake) por modo e a padronização das unidades científicas em $\text{CO}_{2\text{eq}}$.
- [x] **Rastreabilidade de Desvios (Mismatches):** O rerun computacional e a reconciliação foram mapeados matematicamente, mas requerem a eliminação da ambiguidade no rótulo de "Mismatch rodoviário".
- [x] **Transparência de Limitações:** Plenamente atendida. As limitações numéricas e qualitativas estão claras e devidamente enquadradas no texto.
