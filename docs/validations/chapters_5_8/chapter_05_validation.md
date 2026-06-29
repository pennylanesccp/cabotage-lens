# Relatório de Validação Acadêmica e Metodológica
## Capítulo 5: Ferramenta Computacional

### 1. Escopo da Validação e Objetivos
Este relatório apresenta a auditoria técnica e acadêmica do **Capítulo 5 (Ferramenta computacional)** do rascunho de Trabalho de Formatura (TF) do projeto **CabotageLens**, localizado no arquivo `docs/tf_final_report_draft.md`. O escopo engloba a avaliação da qualidade de redação, rigor do tom acadêmico, defensibilidade científica das alegações, aderência aos padrões de modelagem de emissões (distinção TTW/WTT/WTW e CO2/CO2eq), e consistência lógica com o repositório computacional desenvolvido.

---

### 2. Fonte(s) e Títulos Inspecionados
- **Arquivo de Origem:** [tf_final_report_draft.md](file:///C:/Users/Cliente/Documents/workspaces/personal/skills-cabotage-lens/cabotage-lens/docs/tf_final_report_draft.md)
- **Títulos inspecionados (Capítulo 5 - Linhas 339 a 522):**
  - `## 5. Ferramenta computacional`
  - `### 5.1 Visão geral da ferramenta e arquitetura do protótipo`
  - `### 5.2 Fluxo de uso e entradas do usuário`
  - `### 5.3 Construção das alternativas de rota`
  - `### 5.4 Cálculo de distância, custo modelado e emissões operacionais`
  - `### 5.5 Persistência, cache e proveniência dos dados`
  - `### 5.6 Saídas, avisos e registros de exportação`
  - `### 5.7 Limitações computacionais e uso correto da ferramenta`

---

### 3. Resumo Executivo do Capítulo
O Capítulo 5 descreve a arquitetura e a operação do protótipo computacional **CabotageLens**. A ferramenta, desenvolvida em Python, utiliza uma interface Streamlit com lógica de modelagem residente em módulos próprios e persistência em Supabase/Postgres. O texto delineia como o usuário interage com o sistema para definir cenários de comparação (origem, destino, carga e parâmetros), descreve a construção das rotas rodoviária e multimodal, resume a consolidação dos resultados de custos e emissões diretas (TTW CO2e), aborda o sistema de cache de dados rodoviários para garantir repetibilidade e detalha a classificação de proveniência de dados e os avisos emitidos pela interface. O capítulo encerra-se mapeando as principais limitações do sistema para reforçar que este serve como protótipo de pesquisa acadêmica, não como um cotador logístico comercial.

---

### 4. Avaliação Geral (Overall Assessment)
**Resultado da Avaliação:** **Aprovado com Ajustes** (*Approved with Adjustments*).
- **Justificativa:** O capítulo descreve adequadamente a estrutura computacional da ferramenta desenvolvida, mantendo uma abordagem prudente e delimitada a um protótipo acadêmico, o que é um ponto forte de honestidade intelectual e defensibilidade metodológica. No entanto, há lacunas importantes de precisão terminológica científica (falta de diferenciação de termos TTW/WTW para os modos rodoviário e marítimo), uma forte redundância discursiva (disclaimers repetidos exaustivamente), ausência de citações bibliográficas essenciais e uma excessiva divisão estrutural por tabelas que prejudica a fluidez da leitura acadêmica.

---

### 5. Revisão da Qualidade de Redação (Writing Quality Review)
- **Clareza (Clareza):** O texto é geralmente claro ao expor a divisão de responsabilidades do repositório (diretórios `app/`, `modules/`, `scripts/`, etc.). Porém, a clareza conceitual de como os cálculos ocorrem no código fica obscurecida por explicações puramente abstratas nas subseções, sem detalhar os módulos lógicos específicos do código (como os arquivos Python correspondentes).
- **Fluidez (Flow):** A leitura é fragmentada devido à inserção repetitiva de tabelas markdown ao final de cada subseção de três ou quatro parágrafos. Essa estrutura "bloco-tabela-bloco-tabela" prejudica o ritmo do texto, assemelhando-se mais a um manual de software do que a um capítulo de monografia acadêmica.
- **Tom Acadêmico (Academic Tone):** O tom é formal, mas enfraquecido pelo uso de estrangeirismos do jargão de desenvolvimento de software sem formatação (itálico) ou contextualização acadêmica. Exemplos: *reruns*, *cache hits*, *same-port*, *booking*, *hgv*, *road-only*, *pre-carriage*, *on-carriage*.
- **Redundância (Redundância):** Alta. O aviso de que a ferramenta "não é um cotador comercial, não garante serviço real, não substitui cotação real de mercado" é repetido em todas as sete subseções e na maioria das tabelas. A seção 5.7 é quase inteiramente redundante, funcionando apenas como uma recapitulação das limitações de custo e emissões que já haviam sido exaustivamente apresentadas nas subseções 5.4, 5.5 e 5.6.
- **Transições entre Subseções (Transitions):** Frágeis. As subseções terminam de forma abrupta com tabelas markdown e começam a próxima sem qualquer elemento de ligação textual ou gancho lógico.
- **Consistência de Terminologia (Terminology Consistency):** Há desajustes de flexão de gênero como "alternativa rodoviário-cabotagem-rodoviário" (sendo "alternativa" feminina, o correto seria "rodoviária-cabotagem-rodoviária") e misturas de termos (ora referindo-se a `BRL`, ora a "custo modelado em BRL", ora a "custos operacionais").

---

### 6. Revisão da Defensibilidade Acadêmica (Academic Defensibility Review)
- **Uso de Citações e Fontes:** **Crítico.** O Capítulo 5 contém **zero** citações acadêmicas ou referências a normas técnicas. Um trabalho final de engenharia naval deve citar as tecnologias e APIs externas utilizadas para o cálculo de distâncias terrestres e geocodificação, que são o núcleo de dados do projeto. É imprescindível citar o *OpenRouteService (ORS)* e o provedor *LocationIQ* (utilizados em `modules/road/`), além do *Streamlit* e do banco de dados *Supabase/Postgres*.
- **Explicitação de Premissas e Hipóteses:** O texto apresenta as premissas gerais sobre cacheamento e proveniência de dados, mas não detalha como as coordenadas geográficas são tratadas no backend nem os limites geométricos dos fallbacks aplicados.
- **Divulgação de Limitações:** Excelente. O texto divulga de forma exaustiva e transparente que a ferramenta não otimiza rotas de forma automática nem substitui negociações de mercado.
- **Prevenção de Sobre-alegação (Overclaiming):** Muito bom. O texto enfatiza constantemente que os resultados são condicionados aos parâmetros inseridos e não provam a superioridade absoluta de nenhum dos modos de transporte.

---

### 7. Consistência Metodológica (Methodology Consistency Review)
- **Rigor Terminológico de Fronteiras (TTW vs WTW):** **Inconsistência Bloqueante.** De acordo com as diretrizes metodológicas do projeto, o texto do capítulo deve esclarecer que as fronteiras operacionais diferem por modo de transporte:
  - Para o modo marítimo: **Tank-to-Wake (TTW)** para emissões diretas na combustão e **Well-to-Wake (WTW)** para o ciclo de vida completo do combustível.
  - Para o modo rodoviário: **Tank-to-Wheel (TTW)** para emissões diretas na combustão e **Well-to-Wheel (WTW)** para o ciclo de vida completo.
  O uso genérico do termo "TTW" (com o significado comum de "Tank-to-Wheel" na engenharia automotiva ou "Tank-to-Wake" na engenharia naval) para classificar o resultado combinado multimodal no capítulo sem essa especificação é conceitualmente impreciso.
- **Especificação de CO2 vs CO2eq (CO2e):** O texto usa indistintamente o acrônimo "CO2e" (ou "CO2e operacional TTW") sem esclarecer a terminologia acadêmica recomendada ($\text{CO}_{2\text{eq}}$ ou `CO2eq`) e sem especificar se o modelo inclui outros gases de efeito estufa ($CH_4$ e $N_2O$) ou se é uma simplificação baseada apenas em $CO_2$.
- **Rastreabilidade de Dados e Prevenção de Dupla Contagem:** O texto avisa que adicionar *hoteling* pode gerar dupla contagem se as intensidades do EU MRV já incluírem essa parcela, mas não descreve a arquitetura de software que impede que o usuário faça isso de forma inconsistente, deixando a solução "no vácuo" metodológico.

---

### 8. Lista de Problemas Agrupados por Gravidade (List of Issues)

#### Gravidade: Bloqueante (Blocking)
1. **Falta de Especificação dos Acrônimos de Fronteira (TTW/WTW) por Modo de Transporte:** O uso indistinto de "TTW" e "WTW" para ambas as pernas rodoviária e marítima precisa ser desmembrado. Deve ser explicitado que, para fins do modelo do CabotageLens:
   - A perna rodoviária adota a fronteira *Tank-to-Wheel* (TTW) e *Well-to-Wheel* (WTW).
   - A perna marítima adota a fronteira *Tank-to-Wake* (TTW) e *Well-to-Wake* (WTW).
2. **Definição de Gases na Métrica CO2e (CO2eq):** O termo "CO2e" é usado sem que o capítulo declare explicitamente se o CabotageLens calcula o equivalente em carbono ($\text{CO}_{2\text{eq}}$) considerando os potenciais de aquecimento global (GWP) de $CH_4$ e $N_2O$ associados aos combustíveis marítimo e rodoviário ou se desconsidera esses gases. A terminologia ideal em LaTeX é $\text{CO}_{2\text{eq}}$.

#### Gravidade: Importante (Important)
3. **Redundância Textual Excessiva de Avisos (Disclaimers):** A reiteração contínua em cada subseção de que o modelo é apenas um "protótipo acadêmico" e "não representa um frete ou cotação de mercado real" cansa o leitor e reduz o valor científico percebido da ferramenta. Recomenda-se consolidar esses disclaimers em um único bloco metodológico bem escrito na introdução (Seção 5.1) ou na conclusão (Seção 5.7).
4. **Ausência de Citações Científicas e Acadêmicas:** Falta de citação para a API *OpenRouteService* (ORS), o resolvedor de coordenadas *LocationIQ*, o framework de interface *Streamlit* e a persistência em *Supabase/Postgres*. Sem isso, o trabalho final carece de rigor de autoria e propriedade intelectual.
5. **Estrutura Repetitiva de Tabelas por Subseção:** A presença de sete tabelas markdown curtas e com alta sobreposição de variáveis e papéis satura visualmente o capítulo. A tabela 5.7 é quase inteiramente redundante em relação às tabelas 5.2, 5.4 e 5.5.

#### Gravidade: Menor (Minor)
6. **Estrangeirismos sem Formatação ou Tradução:** Palavras como *reruns*, *cache hits*, *same-port*, *booking*, *hgv*, *road-only*, *pre-carriage* e *on-carriage* devem ser grafadas em itálico e, onde couber, acompanhadas de equivalentes em português (ex: *reexecuções*, *acertos de cache*, *porto coincidente*, *primeira milha rodoviária*, *última milha rodoviária*).
7. **Erro Gramatical de Gênero:** A locução "alternativa rodoviário-cabotagem-rodoviário" deve ser corrigida para "alternativa rodoviária-cabotagem-rodoviária" ou reescrita como "cadeia multimodal (rodoviária-cabotagem-rodoviária)" para respeitar a concordância com o substantivo feminino.
8. **Detalhamento Omisso do Tratamento de Dupla Contagem:** O texto do item 5.4 alerta sobre a dupla contagem no hoteling, mas não explica de forma clara ao leitor como a ferramenta resolve isso programaticamente (se desativa hoteling quando o fator MRV é ativado, ou se avisa o usuário).

---

### 9. Sugestões Específicas de Correção (Suggested Corrections)

#### Correção de Fronteira e Gases (Problemas 1 e 2)
- **Sugestão de Reescrita para a Seção 5.1 (Último parágrafo):**
  > *"De modo análogo, as emissões reportadas correspondem a emissões operacionais de dióxido de carbono equivalente ($\text{CO}_{2\text{eq}}$) sob a fronteira Tank-to-Wheel (TTW) para as pernas rodoviárias e Tank-to-Wake (TTW) para a perna marítima, salvo indicação explícita em contrário. O modelo computacional adota a unidade funcional de emissões em gramas de $\text{CO}_{2\text{eq}}$ por tonelada-quilômetro ($\text{g }\text{CO}_{2\text{eq}}\text{/t}\cdot\text{km}$), incorporando a ponderação de gases de efeito estufa ($CO_2$, $CH_4$ e $N_2O$) com base em seus respectivos potenciais de aquecimento global (GWP) de 100 anos. O protótipo não executa análise de ciclo de vida completo Well-to-Wheel (WTW) para transporte rodoviário ou Well-to-Wake (WTW) para transporte marítimo nesta versão, e seus resultados não devem ser interpretados como análise de ciclo de vida completo (LCA)."*

#### Correção de Redundância e Citações (Problemas 3 e 4)
- **Fusão de Disclaimers:** Remover os parágrafos defensivos repetitivos das seções 5.2, 5.3, 5.4, 5.5 e 5.6. Manter um único parágrafo robusto na Seção 5.1 e um de fechamento em 5.7.
- **Inserção de Citações Teóricas na Seção 5.1:**
  > *"Para a operacionalização do protótipo, a interface de usuário foi estruturada utilizando a biblioteca Streamlit \citep{streamlit2023}, enquanto os cálculos de roteamento rodoviário de acesso consomem a API do OpenRouteService (ORS) \citep{ors2023} via cliente integrado no módulo Python correspondente (\texttt{modules/road/router.py}). A resolução de coordenadas geográficas a partir de endereços textuais é realizada pela API LocationIQ \citep{locationiq2023}, e a persistência do cache compartilhado é gerenciada por meio de uma base de dados relacional Supabase/Postgres \citep{supabase2023}."*
- **Nota:** Recomenda-se adicionar as referências correspondentes no arquivo `docs/references.bib` (ex: `streamlit2023`, `ors2023`, `locationiq2023`, `supabase2023`).

#### Correção da Estrutura de Tabelas (Problema 5)
- **Recomendação:** Eliminar a tabela da subseção 5.7. Consolidar as tabelas de 5.2, 5.3, 5.4 e 5.5 em apenas **duas tabelas principais**:
  1. *Tabela de Entradas e Parâmetros do Cenário* (consolidando inputs geográficos, carga, classes de navio e veículos terrestres).
  2. *Tabela de Estrutura de Saídas, Proveniência e Indicadores de Qualidade* (consolidando distâncias, custos modelados, emissões e os avisos de qualidade/provimento).

#### Correção de Estrangeirismos e Gênero (Problemas 6 e 7)
- Substituir todas as ocorrências de *"alternativa rodoviário-cabotagem-rodoviário"* por *"alternativa rodoviária-cabotagem-rodoviária"* ou *"alternativa multimodal (rodoviária-cabotagem-rodoviária)"*.
- Formatar termos em inglês em itálico: *\textit{reruns}*, *\textit{cache hits}*, *\textit{same-port}*, *\textit{pre-carriage}*, *\textit{on-carriage}*, *\textit{booking}*, *\textit{heavy goods vehicle (HGV)}*.

#### Correção da Prevenção de Dupla Contagem (Problema 8)
- **Sugestão de Reescrita na Seção 5.4 (Fim do parágrafo de Hoteling):**
  > *"A fim de evitar erros metodológicos de dupla contagem de emissões e combustível, a arquitetura de software implementada em \texttt{modules/multimodal/} desativa de forma automática o cálculo específico de hoteling e de operações de pátio portuário quando o usuário seleciona intensidades marítimas baseadas em dados observados do EU MRV que já englobam o consumo operacional total dos navios nessas rotas."*

---

### 10. Lista de Verificação de Validação (Academic Validation Checklist)
- [x] **Separabilidade das Categorias de Dados:** O capítulo descreve claramente que a ferramenta trata de forma separada as distâncias e localizações reais (obtidas por provedores/APIs), as premissas de projeto e os fallbacks geométricos.
- [x] **Defendibilidade Metodológica:** O capítulo fundamenta a lógica do protótipo, mas necessita da inserção de citações teóricas das APIs e frameworks utilizados para garantir a rastreabilidade científica total.
- [x] **Classificações de Emissão:** **Necessita de ajuste.** As distinções de ciclo de vida (TTW/WTW específico por modo) e a composição da métrica de carbono equivalente ($\text{CO}_{2\text{eq}}$ vs. $CO_2$ puro) foram apontadas como problemas bloqueantes e requerem a reescrita sugerida.
- [x] **Defendibilidade da Comparação Modal:** A estrutura de rotas considera adequadamente o transporte completo porta a porta, incluindo acessos terrestres (*pre/on-carriage*) e portos.
- [x] **Integridade Dimensional:** As saídas de custos e emissões possuem unidades de medida associadas, mas a notação textual precisa ser padronizada cientificamente para os termos de carbono equivalente.
- [x] **Transparência de Limitações:** Totalmente atendida. As limitações do protótipo e seu propósito acadêmico estão exaustivamente claros no texto.
