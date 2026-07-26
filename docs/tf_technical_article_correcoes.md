# Propostas de correção do artigo técnico

Este arquivo reúne alterações identificadas durante a revisão completa de `tf_technical_article_draft.md` que não foram aplicadas automaticamente. Os itens abaixo alteram conteúdo, estrutura, numeração, interpretação ou nível de detalhamento e, por isso, dependem de aprovação.

## COR01 — Atualizar os números e o exemplo do EU MRV

**Local:** Seções 4.3.4.2.2 a 4.3.4.2.4.

**Problema:** o texto ainda usa uma versão anterior da base MRV. O artefato atual registra 268 navios do tipo *container ship*, P95 de 13,409 g/(t·nm), retirada de dois valores em cada extremidade, 264 valores mantidos e média aparada de 6,624583 g/(t·nm). O texto apresenta 243 navios, P95 de 24,073 g/(t·nm), 239 valores mantidos e média de 9,322050 g/(t·nm).

Além disso, a viagem `voyage_9974486_00001` não serve mais como exemplo de ausência no EU MRV: o IMO 9974486 possui correspondência individual na publicação de 2025, com intensidade de 3,24 g/(t·nm).

**Proposta:** atualizar os números e substituir o exemplo por uma viagem que efetivamente use a estimativa pelo tipo na matriz atual. Uma possibilidade é `voyage_9612777_00005`, pertencente ao conjunto Santos–Manaus e atualmente classificada como estimativa pelo tipo.

## COR02 — Definir como apresentar a estimativa pela classe do navio

**Local:** Seções 4.3.4.2.3 e 4.3.4.2.4.

**Problema:** a hierarquia menciona estimativa pela classe antes da estimativa pelo tipo, mas a matriz Santos–Manaus atual não contém recortes resolvidos pela classe. Os 70 *fallbacks* desse par foram resolvidos pelo tipo, e os 268 registros da referência coletiva usam o campo baseado em massa, não DWT.

**Proposta:** escolher entre:

1. manter a classe apenas como regra metodológica, sem exemplo numérico; ou
2. acrescentar um exemplo externo ao conjunto Santos–Manaus, identificado explicitamente como demonstração da regra e não como caso usado no cenário.

## COR03 — Incluir resumo e palavras-chave

**Local:** início do artigo, antes do Sumário.

**Problema:** o documento começa diretamente pelo Sumário. Para o formato de artigo técnico ou acadêmico, um resumo permite apresentar objetivo, método, principal resultado e limitações em um único bloco.

**Proposta:** incluir um resumo conciso e de três a cinco palavras-chave, sem antecipar conclusões além do cenário São Paulo–Rio Branco.

## COR04 — Consolidar as limitações em uma subseção própria

**Local:** Capítulo 7.

**Problema:** as limitações estão distribuídas pelo texto, mas não há uma síntese ao final.

**Proposta:** criar a Seção 7.3, reunindo pelo menos: fronteira TTW; custo restrito ao combustível; uso de parâmetros históricos; hipótese de VLSFO; seleção dos portos por proximidade; representação simplificada das operações portuárias; ausência de garantia comercial; uso de estimativas coletivas do EU MRV; e subtrechos marítimos aproximados.

## COR05 — Numerar a tabela do exemplo de carga a bordo

**Local:** Seção 4.3.4.1.3.2.

**Problema:** a tabela “Detalhamento do saldo de carga por escala” não possui número, enquanto as demais tabelas do artigo são numeradas.

**Proposta:** incorporá-la à sequência de tabelas e atualizar todas as numerações e referências posteriores. A alteração deve ser feita em conjunto no Markdown e no LaTeX.

## COR06 — Padronizar a numeração dos fluxogramas da implementação

**Local:** Seções 5.2.4, 5.3.1, 5.3.4 e 5.4.2.5.

**Problema:** esses fluxogramas aparecem sem legenda e numeração, enquanto outros diagramas são tratados como figuras.

**Proposta:** numerá-los como figuras, acrescentar legendas e atualizar a numeração das Figuras 8 a 17. Como alternativa, declarar no padrão editorial que fluxogramas internos não serão numerados e aplicar essa decisão de forma uniforme.

## COR07 — Corrigir a representação simplificada do JSON

**Local:** Bloco de código 1, na Seção 5.4.2.5.

**Problema:** o bloco é marcado como `json`, mas contém reticências e uma estrutura de chaves que não forma um JSON válido.

**Proposta:** substituir o conteúdo por um recorte JSON válido e mínimo ou mudar a identificação para pseudocódigo, deixando explícito que se trata apenas de uma representação conceitual.

## COR08 — Rever a referência do fator de emissão do VLSFO

**Local:** Tabela 7 e Seção 4.3.5.

**Problema:** a fonte aparece como “Costa et al. (2025): Resolução IMO MEPC.391(81)”, o que combina uma fonte secundária e uma resolução primária sem uma referência bibliográfica própria para a resolução.

**Proposta:** decidir se o fator será atribuído somente a Costa et al. (2025) ou se a resolução da IMO será citada diretamente e incluída nas Referências. A revisão deve preservar a distinção entre CO₂ e CO₂e adotada no artigo.

## COR09 — Explicar quais arquivos da ANP são armazenados

**Local:** Seção 5.3.2.

**Problema:** o texto informa que a rotina “salva os dois arquivos” no Supabase Storage, mas não identifica quais são esses arquivos.

**Proposta:** nomear o arquivo XLSX original e o artefato derivado ou reformular a frase para descrever exatamente o que a implementação persiste.

## COR10 — Ampliar o dicionário de termos técnicos

**Local:** Dicionário de termos.

**Problema:** siglas e termos recorrentes na implementação não estão definidos no dicionário, como ORS, RTG, UF, BCE, *pipeline* e *fallback*.

**Proposta:** incluir apenas os termos indispensáveis à leitura do artigo ou substituir os estrangeirismos por equivalentes em português no primeiro uso.

## COR11 — Tornar mais neutra a interpretação das comparações externas

**Local:** Seções 6.2 e 6.3.

**Problema:** expressões como “essa proximidade é positiva” e “sinal de coerência de ordem de grandeza” podem sugerir validação do modelo, embora as ferramentas usem fronteiras, rotas e componentes diferentes.

**Proposta:** descrever apenas a proximidade ou a diferença observada e reforçar que a comparação é contextual, não uma validação independente.

## COR12 — Identificar o recorte temporal das informações operacionais

**Local:** Seções 5.1, 5.8 e referências a preços e cobertura da aplicação.

**Problema:** afirmações sobre modalidades gratuitas, disponibilidade pública, quantidade de municípios e dados “mais recentes” podem mudar com o tempo.

**Proposta:** associar essas informações à versão ou à data da execução apresentada no artigo, evitando que sejam interpretadas como garantias permanentes.

## COR13 — Evitar a sobreposição do símbolo de distância com o desembarque

**Local:** Quadro 2 e Seção 4.3.4.1.3.1.

**Problema:** o símbolo $D$ representa distância no quadro geral, mas $D_k$ representa massa desembarcada no balanço de carga.

**Proposta:** adotar outro símbolo para o desembarque ou registrar explicitamente essa exceção no Quadro 2. A mudança exigirá atualização conjunta das fórmulas, da tabela do exemplo e do LaTeX.

## COR14 — Reduzir a densidade da explicação da hierarquia de intensidade

**Local:** Seções 4.3.4.2 a 4.3.4.2.3.

**Problema:** a sequência IMO → verificação pelo P95 → classe → tipo está correta, mas aparece distribuída em parágrafos longos e pode dificultar a identificação da ordem de decisão.

**Proposta:** acrescentar uma lista curta ou um fluxograma da hierarquia depois da explicação conceitual, sem repetir as definições desenvolvidas nas subseções.

## COR15 — Informar o período coberto pela matriz marítima

**Local:** Seções 5.4.2.5, Tabelas 13 e 14 e Seção 5.5.1.

**Problema:** o texto informa a data de atualização da matriz, mas não explicita, junto às tabelas, os anos de ANTAQ e EU MRV que compõem o artefato.

**Proposta:** acrescentar o período de cobertura e a versão ou data de geração da matriz, facilitando a reprodução dos valores apresentados.
