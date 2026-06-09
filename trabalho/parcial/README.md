# Trabalho parcial — roadmap de desenvolvimento

Este documento organiza o desenvolvimento do trabalho parcial em etapas práticas, desde a leitura do enunciado até a geração dos arquivos, resultados e relatório final.

A ideia é manter o projeto reproduzível: os cálculos, parâmetros, scripts, hipóteses e resultados devem ficar rastreáveis no repositório, evitando depender apenas de cliques manuais no Abaqus/CAE.

---

## 1. Objetivo do trabalho

Modelar a seção mestra de um navio cargueiro entre duas anteparas transversais usando elementos finitos no Abaqus e verificar o fator de segurança ao escoamento, considerando:

- carregamento hidrostático associado ao calado;
- pressão equivalente da carga;
- momentos fletores globais verticais;
- momento fletor horizontal;
- eventual parcela torcional, se adotada na modelagem;
- tensão de escoamento do material igual a `300 MPa`.

O resultado final deve permitir responder:

> A seção fornecida atende ao critério de escoamento para os carregamentos considerados?

Caso o fator de segurança seja menor que 1 em regiões estruturalmente representativas, devem ser propostas modificações nos escantilhões.

---

## 2. Entregáveis esperados

Ao final do desenvolvimento, a pasta do trabalho parcial deve conter ou referenciar:

- relatório final em PDF;
- script(s) Python usados para gerar o modelo Abaqus;
- tabela de parâmetros e pré-cálculos;
- arquivo `.cae` gerado, se for leve o suficiente para versionar ou entregar separadamente;
- arquivo `.inp` do(s) job(s), quando útil para rastreabilidade;
- imagens dos resultados principais;
- tabelas de fatores de segurança;
- descrição das hipóteses adotadas;
- lista de eventuais limitações do modelo;
- recomendações de reforço, caso necessário.

Arquivos grandes, como `.odb`, devem preferencialmente ficar fora do Git, salvo decisão explícita em contrário. O ideal é entregar esses arquivos por outro meio, se forem exigidos.

---

## 3. Estrutura sugerida da pasta

```text
trabalho/parcial/
│
├── README.md
├── data/
│   └── parametros_base.yml              # parâmetros principais do navio e do modelo
│
├── scripts/
│   ├── build_model.py                   # script principal para gerar o modelo Abaqus
│   ├── calculations.py                  # pré-cálculos: pressões, momentos, combinações
│   ├── geometry.py                      # construção geométrica da seção
│   ├── loads.py                         # aplicação de pressões e momentos
│   ├── mesh.py                          # estratégia de malha
│   └── postprocess.py                   # extração de resultados do ODB, se aplicável
│
├── abaqus/
│   ├── inp/                             # arquivos .inp gerados
│   ├── cae/                             # arquivos .cae, se forem versionados
│   └── odb/                             # não versionar por padrão
│
├── results/
│   ├── figures/                         # prints e imagens exportadas do Abaqus
│   ├── tables/                          # tabelas CSV/Markdown de resultados
│   └── notes/                           # observações de interpretação dos resultados
│
└── report/
    ├── relatorio.md                     # rascunho em Markdown
    ├── relatorio.pdf                    # versão final exportada
    └── assets/                          # imagens usadas no relatório
```

Essa estrutura pode ser simplificada no começo. Se o projeto ainda estiver pequeno, um único script `build_model.py` já é suficiente.

---

## 4. Roadmap de desenvolvimento

### Etapa 0 — Organizar as fontes do enunciado

**Objetivo:** garantir que todos os dados de entrada venham de uma fonte rastreável.

Tarefas:

- [ ] Guardar o enunciado original na pasta adequada do repositório.
- [ ] Identificar quais páginas contêm:
  - geometria da seção;
  - dimensões principais;
  - escantilhões;
  - fórmula dos momentos normativos;
  - critérios de entrega.
- [ ] Criar uma tabela com todos os dados de entrada.
- [ ] Marcar como `TODO` qualquer dado ainda não confirmado.

Saída esperada:

- tabela inicial de parâmetros;
- lista de dúvidas pendentes;
- confirmação do espaçamento entre cavernas a ser usado.

---

### Etapa 1 — Definir parâmetros principais

**Objetivo:** centralizar os parâmetros para evitar valores espalhados pelo código.

Parâmetros mínimos:

```text
L = 100 m
B = 16 m
D = 9.0 m
T = 7.5 m
Cb = 0.70
comprimento_modelado = 24 m
rho_agua = 1025 kg/m³
rho_carga = 750 kg/m³
sigma_yield = 300 MPa
E = 200 a 210 GPa
nu = 0.30
```

Também definir:

- espaçamento entre cavernas;
- espessura das chapas;
- dimensões dos perfis;
- número de vãos longitudinais;
- convenção de eixos;
- unidades padrão.

Decisão recomendada:

- usar SI no código: `m`, `N`, `Pa`, `kg`;
- converter para `MPa`, `kPa` e `MN.m` apenas em tabelas e relatório.

Saída esperada:

- `parametros_base.yml`, `parameters.py` ou bloco único de parâmetros no script principal.

---

### Etapa 2 — Fazer os pré-cálculos de carregamento

**Objetivo:** calcular os valores que serão aplicados no Abaqus.

Tarefas:

- [ ] Calcular pressão hidrostática máxima na quilha:

```text
p_hidro_max = rho_agua * g * T
```

- [ ] Definir distribuição no costado:

```text
p(z) = rho_agua * g * (T - z)
```

- [ ] Definir pressão uniforme no fundo externo, se adotada como simplificação.
- [ ] Calcular pressão equivalente da carga no duplo fundo.
- [ ] Calcular momentos verticais de onda:
  - caso de alquebramento/hogging;
  - caso de tosamento/sagging.
- [ ] Calcular momento horizontal.
- [ ] Avaliar se a parcela torcional será incluída na primeira versão.
- [ ] Documentar claramente sinais e eixos.

Saída esperada:

- tabela de carregamentos;
- funções de cálculo em Python;
- valores finais usados no modelo.

---

### Etapa 3 — Definir a estratégia de modelagem

**Objetivo:** transformar a seção do enunciado em uma geometria reproduzível.

Decisões necessárias:

- [ ] Modelar seção inteira ou meia seção.
- [ ] Adotar simetria no plano diametral, se compatível com as cargas.
- [ ] Representar chapas como elementos de casca.
- [ ] Representar reforçadores como:
  - cascas equivalentes; ou
  - vigas acopladas; ou
  - geometria shell detalhada.
- [ ] Definir se a primeira iteração será simplificada ou completa.

Recomendação para primeira versão:

- meia seção por simetria;
- chapas principais como shell;
- reforçadores principais modelados de forma simplificada;
- comprimento extrudado de 24 m;
- cavernas/hastilhas posicionadas conforme espaçamento adotado.

Saída esperada:

- desenho esquemático da geometria;
- lista de partes ou regiões estruturais;
- convenção de coordenadas.

---

### Etapa 4 — Criar o script base do Abaqus

**Objetivo:** gerar automaticamente o modelo CAE.

Tarefas:

- [ ] Criar `scripts/build_model.py`.
- [ ] Importar bibliotecas do Abaqus:

```python
from abaqus import *
from abaqusConstants import *
```

- [ ] Criar modelo com nome claro.
- [ ] Criar material de aço linear elástico.
- [ ] Criar seções shell com espessuras diferentes.
- [ ] Criar geometria da meia seção.
- [ ] Extrudar o trecho de 24 m.
- [ ] Atribuir seções às regiões.
- [ ] Criar assembly.
- [ ] Criar sets/surfaces para:
  - fundo externo;
  - costado externo;
  - duplo fundo;
  - convés;
  - extremidade de vante;
  - extremidade de ré;
  - plano de simetria;
  - regiões críticas para paths.

Saída esperada:

- script que abre no Abaqus e gera a geometria sem cargas.

Comando esperado:

```bash
abaqus cae noGUI=scripts/build_model.py
```

---

### Etapa 5 — Implementar material, seções e espessuras

**Objetivo:** garantir que o modelo represente os escantilhões fornecidos.

Tarefas:

- [ ] Criar material:

```text
E = 200 ou 210 GPa
nu = 0.30
sigma_yield = 300 MPa
```

- [ ] Criar seções shell para cada espessura relevante.
- [ ] Atribuir seções corretamente:
  - fundo;
  - duplo fundo;
  - costado;
  - convés;
  - anteparas;
  - hastilhas;
  - cavernas;
  - reforçadores.
- [ ] Validar visualmente as espessuras no Abaqus.

Saída esperada:

- tabela `região x espessura x seção Abaqus`.

---

### Etapa 6 — Implementar malha

**Objetivo:** gerar uma malha suficientemente boa para o relatório.

Tarefas:

- [ ] Usar elementos `S4R` para chapas.
- [ ] Definir tamanho global inicial de malha.
- [ ] Refinar regiões críticas:
  - bojo;
  - interseções fundo/costado;
  - cantos de escotilha, se existirem;
  - regiões de acoplamento;
  - encontro de reforçadores.
- [ ] Verificar qualidade dos elementos:
  - distorção;
  - razão de aspecto;
  - orientação das normais;
  - conectividade.
- [ ] Registrar número de elementos e nós.

Saída esperada:

- imagem da malha;
- tabela com tamanho de malha, número de elementos e número de nós;
- justificativa do critério de malha.

---

### Etapa 7 — Implementar condições de contorno

**Objetivo:** impedir modos de corpo rígido sem travar artificialmente a estrutura.

Tarefas:

- [ ] Aplicar simetria no plano diametral.
- [ ] Criar Reference Points nas extremidades.
- [ ] Acoplar RPs às seções de extremidade.
- [ ] Definir restrições mínimas para estabilidade do modelo.
- [ ] Evitar engastes excessivamente rígidos quando possível.
- [ ] Considerar `distributing coupling` em vez de `rigid body coupling`, se os picos próximos aos RPs ficarem artificiais.

Saída esperada:

- imagem das condições de contorno;
- descrição dos graus de liberdade restritos;
- justificativa das restrições.

---

### Etapa 8 — Implementar carregamentos

**Objetivo:** aplicar pressões locais e esforços globais conforme os pré-cálculos.

Tarefas:

- [ ] Aplicar pressão hidrostática variável no costado.
- [ ] Aplicar pressão no fundo externo.
- [ ] Aplicar pressão da carga no duplo fundo.
- [ ] Criar pelo menos dois load cases:
  - hogging;
  - sagging.
- [ ] Aplicar momento fletor vertical nos RPs.
- [ ] Aplicar momento fletor horizontal nos RPs.
- [ ] Aplicar momento torcional, se adotado.
- [ ] Conferir sinal dos momentos pela deformada esperada.

Saída esperada:

- imagem das cargas aplicadas;
- tabela de cargas por caso;
- descrição da convenção de sinais.

---

### Etapa 9 — Rodar os jobs

**Objetivo:** gerar resultados para os casos de carga.

Jobs mínimos:

```text
job_hogging
job_sagging
```

Tarefas:

- [ ] Criar jobs pelo script.
- [ ] Gerar arquivos `.inp`.
- [ ] Rodar no Abaqus disponível.
- [ ] Verificar se os jobs completam sem erro.
- [ ] Salvar `.odb` em pasta local adequada.
- [ ] Registrar eventuais warnings.

Saída esperada:

- `.inp` de cada caso;
- `.odb` de cada caso;
- log de execução;
- print do Job Manager mostrando sucesso, se útil.

---

### Etapa 10 — Pós-processar resultados

**Objetivo:** extrair resultados suficientes para análise e relatório.

Resultados mínimos:

- [ ] deslocamento máximo;
- [ ] tensão equivalente de von Mises;
- [ ] componente longitudinal `S11` no costado/convés;
- [ ] componente transversal ou relevante `S22` no fundo;
- [ ] localização dos picos de tensão;
- [ ] paths em regiões representativas;
- [ ] fator de segurança global pelo pico máximo;
- [ ] fator de segurança representativo fora de singularidades.

Imagens mínimas:

- [ ] geometria sem malha;
- [ ] malha;
- [ ] condições de contorno;
- [ ] carregamentos;
- [ ] von Mises para hogging;
- [ ] von Mises para sagging;
- [ ] deslocamentos;
- [ ] paths de tensão.

Saída esperada:

- pasta `results/figures/` preenchida;
- tabela `results/tables/fatores_seguranca.csv`;
- anotações de interpretação em `results/notes/`.

---

### Etapa 11 — Calcular fatores de segurança

**Objetivo:** comparar tensões obtidas com o escoamento do aço.

Fórmula:

```text
FS = sigma_yield / sigma_vm
```

Tarefas:

- [ ] Calcular FS pelo pico global de von Mises.
- [ ] Calcular FS por tensão representativa nos paths.
- [ ] Separar picos físicos de possíveis singularidades numéricas.
- [ ] Documentar se o FS usado para conclusão vem de:
  - pico absoluto;
  - região central representativa;
  - path específico;
  - valor nominal longe dos acoplamentos.

Critério:

```text
FS >= 1: atende ao escoamento
FS < 1: não atende ao escoamento e requer proposta de reforço
```

Saída esperada:

- tabela por caso de carga;
- decisão clara de aprovação/reprovação;
- justificativa técnica da interpretação.

---

### Etapa 12 — Interpretar singularidades e picos locais

**Objetivo:** evitar conclusão errada baseada apenas em artefatos numéricos.

Tarefas:

- [ ] Verificar se o pico máximo ocorre em:
  - RP;
  - acoplamento rígido;
  - canto agudo;
  - encontro de múltiplas chapas;
  - borda restrita.
- [ ] Comparar pico global com tensões em paths centrais.
- [ ] Fazer ao menos uma rodada de refinamento local, se possível.
- [ ] Observar se o pico converge ou cresce indefinidamente.

Interpretação recomendada:

- se o pico estiver junto ao acoplamento, discutir como possível singularidade;
- se o pico estiver em região estrutural crítica real e estabilizar com malha, tratar como concentração física;
- sempre reportar os dois: pico global e leitura representativa.

Saída esperada:

- parágrafo técnico pronto para o relatório;
- tabela comparando `sigma_vm_global` e `sigma_vm_representativa`.

---

### Etapa 13 — Propor reforços, se necessário

**Objetivo:** responder ao requisito de modificação dos escantilhões quando `FS < 1`.

Propostas possíveis:

- aumentar espessura do fundo;
- aumentar espessura do duplo fundo;
- reforçar a região do bojo;
- aumentar espessura do costado inferior;
- aumentar inércia dos longitudinais;
- reforçar cavernas e hastilhas;
- adicionar brackets nas ligações críticas;
- suavizar transições geométricas;
- substituir acoplamento rígido por acoplamento distribuído para reduzir concentração artificial;
- refinar malha em regiões críticas.

Tarefas:

- [ ] Escolher reforços coerentes com o local do problema.
- [ ] Justificar mecanicamente cada reforço.
- [ ] Estimar qualitativamente o efeito esperado.
- [ ] Se houver tempo, rodar uma segunda iteração no Abaqus.

Saída esperada:

- tabela `problema x proposta x justificativa`;
- conclusão sobre necessidade de nova iteração.

---

### Etapa 14 — Montar o relatório

**Objetivo:** transformar o trabalho técnico em entrega formal.

Estrutura recomendada:

```text
1. Introdução
2. Dados do problema
3. Metodologia
4. Modelo de elementos finitos
5. Carregamentos e condições de contorno
6. Resultados
7. Fatores de segurança
8. Propostas de modificação, se necessárias
9. Conclusões e recomendações
10. Apêndices
```

Conteúdo mínimo por seção:

#### 1. Introdução

- contexto da análise estrutural de seção mestra;
- importância de avaliar tensões globais e locais;
- objetivo do estudo.

#### 2. Dados do problema

- dimensões principais;
- material;
- escantilhões;
- carregamentos previstos;
- critério de escoamento.

#### 3. Metodologia

- uso de elementos finitos;
- hipóteses adotadas;
- simplificações;
- casos de carga.

#### 4. Modelo de elementos finitos

- geometria;
- número de partes;
- tipo de elemento;
- formulação do elemento;
- material;
- seções/espessuras;
- malha;
- quantidade de nós e elementos.

#### 5. Carregamentos e condições de contorno

- pressão hidrostática;
- pressão da carga;
- momentos globais;
- RPs e acoplamentos;
- simetria;
- restrições.

#### 6. Resultados

- deformada;
- von Mises;
- S11/S22;
- paths;
- localização dos picos.

#### 7. Fatores de segurança

- fórmula usada;
- tabela por caso;
- interpretação dos picos;
- decisão de atendimento ou não atendimento.

#### 8. Propostas de modificação

- obrigatório se `FS < 1`;
- incluir justificativa estrutural.

#### 9. Conclusões

- resumo do modelo;
- caso mais crítico;
- FS final;
- limitações;
- próximos passos.

#### 10. Apêndices

- pré-cálculos;
- tabela de cargas;
- parâmetros do script;
- imagens complementares;
- logs relevantes.

Saída esperada:

- `report/relatorio.md`;
- `report/relatorio.pdf`.

---

### Etapa 15 — Montar apresentação curta, se necessário

**Objetivo:** preparar uma versão oral do relatório.

Roteiro sugerido:

```text
Slide 1 — Título e objetivo
Slide 2 — Dados do navio e seção
Slide 3 — Modelo Abaqus e malha
Slide 4 — Condições de contorno e cargas
Slide 5 — Resultados hogging
Slide 6 — Resultados sagging
Slide 7 — Fatores de segurança e discussão dos picos
Slide 8 — Reforços propostos / conclusão
```

Saída esperada:

- apresentação com prints do Abaqus;
- notas de fala por slide.

---

## 5. Checklist de qualidade antes da entrega

### Modelo

- [ ] Unidades consistentes.
- [ ] Espessuras corretas.
- [ ] Material correto.
- [ ] Elementos de casca usados corretamente.
- [ ] Normais verificadas.
- [ ] Simetria aplicada corretamente.
- [ ] Cargas com sentido físico correto.
- [ ] Deformada coerente com o caso de carga.

### Resultados

- [ ] Tensão de von Mises extraída.
- [ ] Deslocamento máximo extraído.
- [ ] Paths definidos fora de regiões artificiais.
- [ ] FS calculado corretamente.
- [ ] Picos próximos a vínculos discutidos com cuidado.
- [ ] Caso mais crítico identificado.

### Relatório

- [ ] Introdução clara.
- [ ] Metodologia reproduzível.
- [ ] Modelo CAE bem descrito.
- [ ] Carregamentos com fórmulas e valores.
- [ ] Condições de contorno explícitas.
- [ ] Resultados com figuras legíveis.
- [ ] Conclusão responde ao objetivo.
- [ ] Reforços propostos se `FS < 1`.
- [ ] Apêndice com pré-cálculos.

### Repositório

- [ ] Scripts versionados.
- [ ] Parâmetros versionados.
- [ ] Resultados leves versionados.
- [ ] Arquivos grandes fora do Git.
- [ ] README atualizado.
- [ ] Caminho de execução documentado.

---

## 6. Convenções de execução

Rodar script principal:

```bash
abaqus cae noGUI=scripts/build_model.py
```

Gerar input sem rodar, se o script for preparado para isso:

```bash
abaqus cae noGUI=scripts/build_model.py -- --write-input-only
```

Rodar job por linha de comando:

```bash
abaqus job=job_hogging input=abaqus/inp/job_hogging.inp interactive
abaqus job=job_sagging input=abaqus/inp/job_sagging.inp interactive
```

Abrir resultado:

```bash
abaqus viewer database=abaqus/odb/job_hogging.odb
```

Os comandos podem variar conforme a instalação local do Abaqus.

---

## 7. Ordem recomendada para executar sem travar

1. Criar uma versão simplificada da geometria.
2. Rodar só material + malha, sem cargas.
3. Adicionar condições de contorno.
4. Rodar um caso com pressão hidrostática apenas.
5. Adicionar momentos verticais.
6. Separar jobs de hogging e sagging.
7. Extrair von Mises e deslocamentos.
8. Criar paths.
9. Calcular FS.
10. Escrever resultados.
11. Só depois refinar malha e discutir picos.
12. Propor reforços, se necessário.

A prioridade é gerar um modelo completo e defensável primeiro. Refinamentos entram depois.

---

## 8. Definition of Done

O trabalho parcial pode ser considerado pronto quando houver:

- modelo Abaqus reproduzível por script ou procedimento documentado;
- pelo menos dois casos de carga avaliados;
- campos de von Mises e deslocamento exportados;
- cálculo de FS para cada caso;
- discussão sobre picos locais e possíveis singularidades;
- proposta de reforço caso algum FS relevante fique abaixo de 1;
- relatório final revisado;
- arquivos principais organizados na pasta do projeto.
