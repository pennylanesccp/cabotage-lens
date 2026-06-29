# Relatório de Validação Acadêmica e Metodológica
## Capítulo 9: Limitações

### 1. Escopo da Validação e Objetivos
Este relatório apresenta a auditoria técnica e acadêmica do **Capítulo 9 (Limitações)** do rascunho de Trabalho de Formatura (TF) do projeto **CabotageLens**, localizado no arquivo `docs/tf_final_report_draft.md`. O escopo engloba a avaliação do rigor metodológico das limitações descritas, clareza e adequação da notação científica, tom acadêmico, defendibilidade física e operacional das fronteiras declaradas, conformidade ortográfica e consistência terminológica.

---

### 2. Fonte(s) e Títulos Inspecionados
- **Arquivo de Origem:** [tf_final_report_draft.md](docs/tf_final_report_draft.md)
- **Títulos inspecionados (Capítulo 9 - Linhas 1029 a 1206):**
  - `## 9. Limitacoes`
  - `### 9.1 Escopo das limitações e papel no argumento do TF`
  - `### 9.2 Fronteira ambiental: TTW operacional, CO2e e exclusão de WTW/LCA`
  - `### 9.3 Fronteira econômica: custos modelados e ausência de fretes comerciais`
  - `### 9.4 Limitações operacionais: serviço, horários, terminais e super-rede`
  - `### 9.5 Limitações de rota: distância marítima, portos alternativos e casos same-port`
  - `### 9.6 Limitações de validação: sensibilidades, Batch 002 e reconciliação rodoviária`
  - `### 9.7 Limitações de fontes, citações e generalização dos resultados`

---

### 3. Resumo Executivo do Capítulo
O Capítulo 9 estabelece as fronteiras de interpretação dos resultados empíricos para garantir a defendibilidade do TF. Ele detalha:
1. O escopo do capítulo e a importância de declarar o que o modelo não sustenta, evitando sobreafirmações.
2. A fronteira ambiental operacional *Tank-to-Wake* e *Tank-to-Wheel* (TTW), explicitando a exclusão de ciclo de vida completo (WTW/LCA) e emissões de dispersão portuária.
3. A fronteira econômica, demarcando que custos modelados diferem de fretes e tarifas comerciais praticadas.
4. As limitações operacionais de rede (ausência de escalas reais, slots, capacidade e restrições de horários de armadores).
5. As limitações físicas de rota (indisponibilidade de distâncias exatas para Manaus $\rightarrow$ Fortaleza e Rio Grande $\rightarrow$ Recife, restrição de same-port e o isolamento de portos alternativos como Pecém e Suape).
6. Os limites da validação, reiterando a etiqueta *same_direction_large_gap* do Batch 002 e a natureza puramente diagnóstica da reconciliação rodoviária.
7. As restrições de fontes de dados e a necessidade de não generalizar resultados para um nível nacional sem dados comerciais.

---

### 4. Avaliação Geral (Overall Assessment)
**Resultado da Avaliação:** **Aprovado com Ajustes** (*Approved with Adjustments*).
- **Justificativa:** O capítulo organiza de forma muito honesta e academicamente rigorosa os limites do estudo, cobrindo com boa profundidade as barreiras ambientais, operacionais, econômicas e físicas. No entanto, há lacunas de rigor metodológico bloqueantes (omissão da lógica de alocação de capacidade marítima e indeterminação do escopo de gases na métrica CO2e), erros de ortografia em cabeçalhos principais do rascunho, formatação de citações simplificada e repetição de redundâncias nos parágrafos textuais.

---

### 5. Revisão da Qualidade de Redação (Writing Quality Review)
- **Clareza (Clareza):** A redação é fluida e bem articulada. O uso de tabelas markdown auxilia a separar claramente o que o modelo faz, o que os dados não provam e o que a aplicação não deve simular.
- **Fluidez (Flow):** Superior aos capítulos anteriores, pois a narrativa integra-se de forma lógica com as tabelas de suporte. A transição entre as barreiras econômicas e operacionais é fluida.
- **Tom Acadêmico (Academic Tone):** Formal e equilibrado. Porém, é enfraquecido pelo uso de colchetes de texto simples (como `[decarb2024]`) em vez de macros LaTeX, além de manter o Capítulo 12 (`## 12. Citation placeholders`) como uma seção solta, o que constitui um artifício rudimentar de rascunho que precisa ser integrado ou removido.
- **Redundância (Redundância):** Embora as limitações sejam o foco principal, as declarações protetivas genéricas do tipo "não é frete de mercado, emissões são operacionais TTW" ainda se repetem de forma exaustiva nas seções 9.1, 9.2, 9.3 e 9.4. Essas repetições literais podem ser atenuadas mantendo as discussões mais focadas nos detalhes de cada barreira específica.
- **Transições entre Subseções (Transitions):** Bem executadas. O capítulo estabelece ganchos conceituais consistentes.
- **Consistência de Terminologia (Terminology Consistency):** Presença de jargões em inglês sem formatação (*rerun*, *booking*, *fallback*) e uso inconsistente das siglas `CO2e` e `CO2eq`.

---

### 6. Revisão da Defensibilidade Acadêmica (Academic Defensibility Review)
- **Omissão da Limitação de Alocação de Carga:** **Ponto Crítico.** O capítulo falha em listar a lógica de alocação de capacidade marítima (alocação por contêiner via slot-share/`teu_share` ou massa via `dwt_share`) como uma limitação metodológica. A escolha desse parâmetro altera drasticamente os custos e emissões multimodais. A indefinição do método do benchmark externo impede a calibração precisa de magnitude, sendo este um ponto central a ser documentado como limitação no Capítulo 9.
- **Indeterminação do Escopo de Gases na Métrica CO2e:** **Ponto Crítico.** A monografia deve explicitar de forma clara se a métrica declarada como "CO2e" ou "CO2eq" de fato incorpora outros gases estufa ($CH_4$ e $N_2O$ ponderados por seus respectivos potenciais de aquecimento global - GWP) ou se o modelo computacional adota uma simplificação baseada apenas no $CO_2$ direto como proxy. Essa indeterminação é uma limitação analítica que deve ser explicitamente listada.
- **Especificidade das Limitações:** Altamente específica e útil. Ao listar que corredores como Rio Grande $\rightarrow$ Recife e Manaus $\rightarrow$ Fortaleza carecem de distâncias marítimas exatas e dependem de fallbacks, o texto confere excelente defendibilidade e rastreabilidade técnica ao trabalho.
- **Prevenção de Sobre-alegação (Overclaiming):** Excelente. O texto protege o modelo de interpretações comerciais e restringe a validade a cenários comparativos sob premissas explícitas.

---

### 7. Consistência Metodológica (Methodology Consistency Review)
- **Rigor Terminológico de Ciclo de Vida (TTW/WTW por Modo):** **Inconsistência Bloqueante.** Reitera-se que o termo genérico "TTW" (ou "TTW CO2e") deve ser desmembrado na discussão das limitações ambientais para manter o rigor técnico:
  - Pernas rodoviárias terrestres: fronteiras *Tank-to-Wheel (TTW)* e *Well-to-Wheel (WTW)*.
  - Perna marítima: fronteiras *Tank-to-Wake (TTW)* e *Well-to-Wake (WTW)*.
- **Fronteira Operacional vs. Preços Comerciais:** Muito bem detalhada na Seção 9.3, separando a modelagem determinística de engenharia dos custos logísticos de mercado (seguro, estoques, demurrage).
- **Rastreabilidade de Dados:** A Seção 9.5 descreve corretamente a dependência de fallbacks e a restrição de portos alternativos.

---

### 8. Lista de Problemas Agrupados por Gravidade (List of Issues)

#### Gravidade: Bloqueante (Blocking)
1. **Omissão da Lógica de Alocação de Carga Maritime (teu_share vs. dwt_share):** O capítulo não cita a metodologia de alocação de capacidade do navio como limitação metodológica de calibração, embora ela seja o principal vetor de divergência com o benchmark externo.
2. **Indeterminação de Gases na Métrica CO2e do Modelo:** Falta de declaração clara de se a ferramenta computacional calcula o equivalente de gases adicionais ou se utiliza apenas uma simplificação baseada em $CO_2$ rotulada como equivalente.
3. **Indefinição de Acrônimos de Fronteira por Modo de Transporte:** O uso genérico de "TTW" na seção 9.2 deve ser cindido em *Tank-to-Wheel (TTW)* e *Tank-to-Wake (TTW)*.

#### Gravidade: Importante (Important)
4. **Erros de Acentuação nos Cabeçalhos Principais:** O título do capítulo está grafado como `## 9. Limitacoes` (deve ser `## 9. Limitações`) e o do Capítulo 10 como `## 10. Conclusao` (deve ser `## 10. Conclusão`).
5. **Formatação de Citações Bibliográficas Inválida:** Uso de colchetes de texto simples (ex: `[decarb2024]`) em vez de macros de citação LaTeX (ex: `\citep{decarb2024}`).
6. **Manutenção do Capítulo 12 como Seção de Placeholders:** A presença de um capítulo solto apenas para documentar o uso de chaves temporárias enfraquece a estrutura final da monografia. Essas definições devem ser integradas de forma limpa.

#### Gravidade: Menor (Minor)
7. **Estrangeirismos Técnicos sem Itálico:** Palavras em inglês como *rerun*, *booking*, *fallback*, *pre-carriage*, *on-carriage*, *mismatch*, *hoteling*, *hotelling* sem itálico.
8. **Problema de Concordância Gramatical de Gênero:** A locução "cenários rodoviários e rodoviário-cabotagem-rodoviário" na Seção 9.1 deve ser flexionada para o feminino: "cenários rodoviários e rodoviária-cabotagem-rodoviária".
9. **Grafia Inconsistente de "Hoteling" e "Hotelling":** O texto alterna o uso de "l" duplo em seções próximas. Recomenda-se a padronização de forma flexível de acordo com a literatura de referência marítima citada.
10. **Concordância Adjetiva Ambígua:** A expressão "qualidade do ar portuária" deve ser revisada para "qualidade do ar em regiões portuárias" para evitar ambiguidade gramatical.

---

### 9. Sugestões Específicas de Correção (Suggested Corrections)

#### Inserção da Limitação de Alocação de Carga e Escopo de Gases (Problemas 1 e 2)
- **Sugestão de Inserção de Item na Tabela da Seção 9.2 (após a linha "Literatura CO2-only"):**
  | Métrica de gases estufa e GWP | O modelo não documenta o escopo completo de gases equivalentes. | A monografia deve esclarecer de forma explícita se o cálculo de CO2e incorpora outros gases adicionais ($CH_4$ e $N_2O$ ponderados por GWP) ou se adota uma simplificação baseada apenas em $CO_2$ com base em fatores de combustível diretos. |
  | Regra de alocação de capacidade | A lógica de rateio marítimo do benchmark não foi auditada. | O CabotageLens opera sob premissas de alocação de capacidade baseadas em slots (\textit{teu\_share}) ou massa (\textit{dwt\_share}), mas a incompatibilidade dessas regras com a alocação interna do workbook de referência atua como uma limitação de calibração que impede a equivalência absoluta de custos e emissões. |

- **Sugestão de Ajuste no parágrafo 3 da Seção 9.2 (Linha 1060):**
  > *"Essa distinção também vale para a espécie de emissão reportada. Resultados em CO2 isolado não são automaticamente equivalentes a CO2e, porque CO2e depende dos gases incluídos e da regra de equivalência climática adotada pela fonte. Uma das limitações metodológicas atuais do CabotageLens reside na falta de declaração explícita se a ferramenta computacional calcula o equivalente de carbono ($\text{CO}_{2\text{eq}}$) incorporando de fato outros gases de efeito estufa ($CH_4$ e $N_2O$ ponderados por seus respectivos potenciais de aquecimento global - GWP) ou se utiliza uma simplificação CO2-only de combustível rotulada como equivalente. Portanto, literatura ou benchmarks que reportam CO2-only, WTW, LCA ou CO2e sob outro limite metodológico não podem ser usados para calibrar, corrigir ou validar diretamente os resultados TTW CO2e do CabotageLens sem reconciliação explícita de fronteira, unidade funcional, base de carga e gases incluídos."*

#### Correção de Acentuação e Estrangeirismos (Problemas 4, 7 e 8)
- Alterar títulos: `## 9. Limitações` e `## 10. Conclusão`.
- Alterar na Seção 9.1: `... comparar cenários rodoviários e rodoviária-cabotagem-rodoviária sob fronteiras declaradas...`
- Substituir siglas genéricas `TTW` e `WTW` por *Tank-to-Wheel (TTW)* e *Well-to-Wheel (WTW)* para rodoviário, e *Tank-to-Wake (TTW)* e *Well-to-Wake (WTW)* para marítimo.
- Aplicar itálico nos jargões de código e engenharia: *\textit{rerun}*, *\textit{booking}*, *\textit{fallback}*, *\textit{pre-carriage}*, *\textit{on-carriage}*, *\textit{mismatch}*.
- Uniformizar de forma consistente o uso de *\textit{hoteling}* ou *\textit{hotelling}* com base na grafia predominante na literatura adotada.

#### Fusão de Citações LaTeX (Problemas 5 e 6)
- **Ajuste na Seção 9.2:** Substituir `[decarb2024] [maritimelca2024]` por `\citep{decarb2024, maritimelca2024}`.
- **Ajuste na Seção 9.2 (Porto):** Substituir `[berth2009] [shipops2022] [berthairquality2010]` por `\citep{berth2009, shipops2022, berthairquality2010}`.
- **Ajuste na Seção 9.3 e 9.4:** Substituir `[competitiveness2024] [modalshiftreview2020]` por `\citep{competitiveness2024, modalshiftreview2020}`.
- **Recomendação para o Capítulo 12:** Remover a seção `## 12. Citation placeholders` e integrar a tabela explicativa de uso de citações como um anexo metodológico ou seção integrada na revisão de literatura, eliminando-a como capítulo principal.

---

### 10. Lista de Verificação de Validação (Academic Validation Checklist)
- [x] **Separabilidade das Limitações:** O capítulo divide de forma clara e estruturada as limitações ambientais, econômicas, operacionais, físicas e metodológicas do modelo.
- [x] **Defendibilidade Metodológica:** O capítulo é robusto, mas necessita da documentação explícita da alocação de capacidade marítima e do escopo de gases na métrica CO2e para ser academicamente defensável.
- [x] **Rigor de Acentuação:** **Incompatível nos cabeçalhos.** Requer a correção ortográfica dos títulos dos Capítulos 9 e 10.
- [x] **Formatação de Referências:** **Ajustes necessários.** Requer a conversão de todos os placeholders textuais em macros de citação LaTeX.
- [x] **Rigor de Fronteiras:** Atendido de forma satisfatória ao detalhar a exclusão de WTW/LCA na linha de base operacional.
- [x] **Transparência de Limitações:** Plenamente atendida. O capítulo é transparente ao delimitar o que o CabotageLens faz e o que a ferramenta não deve simular comercialmente.
