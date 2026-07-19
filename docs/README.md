# Documentação do CabotageLens

## Artigo técnico ativo

- [`tf_technical_article_draft.md`](tf_technical_article_draft.md): fonte de validação textual e único arquivo a ser editado durante a revisão de conteúdo.
- [`tf_technical_article.tex`](tf_technical_article.tex): fonte LaTeX preparada a partir do Markdown para a futura compilação com XeLaTeX.
- [`references.bib`](references.bib): base bibliográfica que será normalizada quando as chaves de citação do artigo forem aprovadas.

Enquanto a validação textual estiver aberta, o Markdown é a referência. O arquivo LaTeX deve acompanhá-lo, mas não deve receber revisões de conteúdo isoladas.

## Estrutura de apoio

| Local | Conteúdo |
| :-- | :-- |
| [`images/`](images/) | Figuras e capturas usadas no artigo. |
| [`comparacao_externa/`](comparacao_externa/) | Capturas e exportações das ferramentas comparadas na Seção 5.2. |
| [`apresentacao_preliminar/`](apresentacao_preliminar/) | Arquivos da apresentação preliminar. |
| [`validation/`](validation/) | Resultados e evidências de validação usados pelo projeto. |
| [`literature_audit/`](literature_audit/) | Auditoria de referências e notas de leitura. |
| [`tf_support/`](tf_support/) | Notas metodológicas, de auditoria e de rastreabilidade que apoiam o artigo. |
| Arquivos Markdown na raiz | Documentação específica de intensidade marítima, operações portuárias, hoteling, alocação e Supabase. |

Os antigos relatórios modulares e suas fontes LaTeX foram retirados desta pasta. A estrutura atual mantém apenas a fonte LaTeX do artigo técnico.
