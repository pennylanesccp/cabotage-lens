# Resumo do cálculo de consumo de combustível — fluxo principal

## 1. Estrutura da comparação

O modelo compara a mesma carga, origem e destino em duas alternativas:

```text
Rodoviária:
origem -> caminhão -> destino

Multimodal:
origem -> caminhão -> porto de origem -> navio
       -> porto de destino -> caminhão -> destino
```

A alternativa multimodal soma:

1. primeiro trecho rodoviário (*first mile*);
2. navegação;
3. operações portuárias;
4. último trecho rodoviário (*last mile*).

No fluxo principal, o *hoteling* não é somado separadamente porque a
intensidade marítima MRV já representa o consumo operacional agregado.
A exclusão evita dupla contagem.

---

## 2. Trechos rodoviários

A mesma metodologia é aplicada à rota rodoviária direta, ao *first mile*
e ao *last mile*.

### Dados de entrada

- distância rodoviária calculada pelo roteador, em km;
- massa total da carga, em t;
- capacidade do caminhão, em t;
- eficiência básica, em km/L;
- peso de referência do preset;
- quantidade de eixos.

### Presets principais

| Caminhão | Capacidade | Eficiência básica |
| --- | --- | --- |
| Semirreboque de 5 eixos | 27 t | 2,3 km/L |
| Carreta de 6 eixos | 30 t | 2,0 km/L |
| Bitrem de 7 eixos | 36 t | 2,0 km/L |
| Rodotrem de 9 eixos | 48 t | 2,0 km/L |

### Número de viagens

```text
numero_de_viagens = teto(massa_da_carga / capacidade_do_caminhao)
```

### Ajuste da eficiência

```text
delta_peso =
    (capacidade_do_caminhao - peso_de_referencia)
    / peso_de_referencia

eficiencia_ajustada =
    eficiencia_basica * (1 - elasticidade * delta_peso)
```

A elasticidade usada é 1. A eficiência final é limitada entre
0,6 e 8,0 km/L.

### Consumo rodoviário

```text
combustivel_rodoviario_L =
    distancia_km / eficiencia_ajustada_km_L
    * numero_de_viagens
```

No fluxo principal não é acrescentado retorno vazio.

### Emissões rodoviárias

```text
emissoes_rodoviarias_kgCO2e =
    combustivel_rodoviario_L * 2,68
```

---

## 3. Navegação

A navegação utiliza uma intensidade observada por trabalho de transporte:

```text
intensidade_maritima =
    g de combustivel / (t transportada * milha nautica)
```

### Origem dos dados

#### **ANTAQ**

- viagens reais de cabotagem;
- navio e número IMO;
- sequência de escalas;
- portos de origem e destino;
- carga movimentada em cada escala.

#### **EU MRV**

- consumo de combustível dos navios;
- distância navegada;
- trabalho de transporte;
- intensidade de combustível;
- tipo e classe do navio.

O número IMO liga os registros da ANTAQ aos dados MRV.

### Carga a bordo em cada trecho

A carga a bordo é reconstruída seguindo a sequência de escalas:

```text
carga_a_bordo_depois_da_escala =
    carga_a_bordo_anterior
    + carga_liquida_movimentada_na_escala
```

A carga resultante é aplicada ao trecho seguinte.

### Trabalho de transporte

```text
trabalho_de_transporte_t_nm =
    carga_a_bordo_t * distancia_do_trecho_nm
```

### Intensidade média da rota

Quando existem várias observações no mesmo corredor:

```text
intensidade_da_rota =
    soma(intensidade_do_navio * trabalho_de_transporte)
    / soma(trabalho_de_transporte)
```

É uma média ponderada pelo trabalho efetivamente realizado, não uma
média aritmética simples.

### Conversão de distância

```text
distancia_nm = distancia_km / 1,852
```

### Consumo marítimo atribuído à carga

```text
combustivel_maritimo_kg =
    intensidade_da_rota_g_t_nm
    * massa_da_carga_t
    * distancia_maritima_nm
    / 1000
```

O fator `/ 1000` converte gramas em quilogramas.

### Emissões marítimas

O combustível marítimo principal considerado é VLSFO:

```text
emissoes_maritimas_kgCO2e =
    combustivel_maritimo_kg * 3,114
```

---

## 4. Hoteling

*Hoteling* é o consumo do navio atracado, principalmente pelos motores
auxiliares, para geração elétrica, refrigeração, ventilação e serviços de
bordo.

No fluxo principal:

```text
combustivel_hoteling_separado = 0
```

Isso não significa que o navio não consome no porto. Significa que o
modelo não acrescenta outra parcela porque ela poderia já estar incluída
na intensidade agregada MRV usada na navegação.

Frase segura para a apresentação:

> O hoteling não é somado separadamente quando usamos a intensidade
> MRV por trabalho de transporte, para evitar dupla contagem.

---

## 5. Operações portuárias

As operações portuárias são calculadas separadamente do consumo do navio.

### Conversão da carga para TEU

Quando o usuário não informa TEU:

```text
TEU_da_carga = teto(massa_da_carga_t / 14)
```

O valor adotado é 14 t por TEU.

### Movimentos considerados

No cenário padrão:

| Equipamento | Movimentos por contêiner | Diesel por movimento |
| --- | --- | --- |
| RTG | 4 | 0,355148 L |
| Caminhão interno do terminal | 2 | 0,494671 L |
| STS | 1 | fator energético ainda indisponível |

Para cada equipamento:

```text
movimentos_do_equipamento =
    numero_de_chamadas
    * TEU_da_carga
    * movimentos_por_conteiner
```

```text
diesel_do_equipamento_L =
    movimentos_do_equipamento
    * litros_por_movimento
```

São consideradas duas chamadas: porto de origem e porto de destino.

Para 1 TEU, o total quantificado nos dois portos é aproximadamente:

```text
diesel_portuario = 4,82 L
```

### Conversão para emissões

```text
massa_diesel_kg = diesel_portuario_L * 0,85
```

```text
emissoes_portuarias_kgCO2e =
    massa_diesel_kg * 3,15
```

O cenário portuário padrão é um proxy baseado em dados de Santos.
Ele não representa automaticamente as características específicas de
todos os terminais brasileiros.

---

## 6. Soma final

### Alternativa rodoviária

```text
emissoes_rodoviarias_totais =
    emissoes_da_rota_direta
```

### Alternativa multimodal

```text
emissoes_multimodais =
    emissoes_first_mile
    + emissoes_navegacao
    + emissoes_operacoes_portuarias
    + emissoes_last_mile
```

No fluxo principal, o *hoteling* separado não entra na soma.

---

## 7. Resumo oral

> O modelo compara a mesma carga em duas cadeias porta a porta. Nos
> trechos rodoviários, calculamos o número de viagens pela capacidade do
> caminhão e o consumo pela distância dividida pela eficiência em km/L.
> Na navegação, cruzamos viagens observadas da ANTAQ com dados de
> eficiência do EU MRV pelo número IMO e obtemos uma intensidade
> direcional em gramas de combustível por tonelada-milha náutica. Essa
> intensidade é multiplicada pela massa da carga e pela distância marítima.
> O hoteling não é acrescentado separadamente para evitar dupla contagem.
> As operações portuárias são calculadas pelos movimentos de RTGs e
> caminhões internos. Finalmente, todos os consumos são convertidos para
> kg de CO2 equivalente e somados em cada alternativa.
