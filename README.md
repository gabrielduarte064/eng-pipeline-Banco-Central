# Pipeline de Dados Economicos - Banco Central

Pipeline de engenharia de dados que extrai indicadores economicos publicos
do Banco Central do Brasil, processa em camadas (bronze, silver, gold) e
disponibiliza os dados prontos para consumo em um pequeno data warehouse
local (SQLite), com verificacoes automatizadas de qualidade e testes
automatizados.

## Por que este projeto

A ideia nao e so "buscar dados de uma API", e mostrar, em escala pequena,
as praticas usadas em pipelines de dados reais:

- arquitetura em camadas (medallion architecture: bronze, silver, gold)
- modelagem dimensional (esquema estrela: dimensoes e fato)
- cargas idempotentes (rodar o pipeline varias vezes nao duplica dados)
- verificacoes automatizadas de qualidade de dados
- logging estruturado
- testes automatizados com pytest
- integracao continua com GitHub Actions

## Arquitetura

```
API do Banco Central
        |
        v
   [ extract.py ]  ->  data/bronze/   (json bruto, uma copia por dia)
        |
        v
   [ transform.py ] ->  data/silver/  (parquet limpo e tipado)
        |
        v
   [ load.py ]      ->  data/gold/warehouse.db  (esquema estrela em SQLite)
        |
        v
   [ quality.py ]   ->  data/gold/relatorio_qualidade.json
```

Cada camada tem uma responsabilidade unica:

- **bronze**: guarda o dado exatamente como a fonte enviou. Serve como
  copia de seguranca caso seja preciso reprocessar tudo do zero.
- **silver**: dado limpo, tipado e sem duplicatas, pronto para ser
  cruzado com outras fontes no futuro.
- **gold**: dado organizado em um modelo dimensional simples, pronto
  para ser consultado com SQL por qualquer ferramenta de BI.

## Modelo de dados (esquema estrela)

```
dim_serie                    dim_data
------------------------     ------------------------
serie_id (PK)                data_id (PK)
codigo_bcb                    data
nome                          ano
unidade                       mes
periodicidade                 trimestre

              fato_indicador
              ------------------------
              serie_id (FK)
              data_id (FK)
              valor
              carregado_em
```

## Indicadores incluidos

| Serie | Codigo no Banco Central | Periodicidade |
|---|---|---|
| Selic (acumulada no mes, anualizada) | 4390 | mensal |
| IPCA (variacao mensal) | 433 | mensal |
| Dolar comercial (venda) | 1 | diaria |
| Taxa de desocupacao (PNAD Continua) | 24369 | mensal |

Novos indicadores podem ser adicionados apenas incluindo uma nova entrada
em `CATALOGO_SERIES`, dentro de `config.py`. Nenhum outro arquivo precisa
ser alterado.

## Como rodar

```
pip install -r requirements.txt
python pipeline.py
```

Isso roda o pipeline completo (extract, transform, load e quality) e
gera o banco `data/gold/warehouse.db`.

Tambem e possivel rodar uma etapa isolada:

```
python pipeline.py --etapa extract
python pipeline.py --etapa transform
python pipeline.py --etapa load
python pipeline.py --etapa quality
```

## Consultando os dados gerados

O resultado final fica em um banco SQLite comum, que pode ser aberto com
qualquer cliente de SQL (incluindo o proprio Python):

```python
import sqlite3
import pandas as pd

conexao = sqlite3.connect("data/gold/warehouse.db")

pd.read_sql("""
    SELECT s.nome, d.data, f.valor
    FROM fato_indicador f
    JOIN dim_serie s ON s.serie_id = f.serie_id
    JOIN dim_data d ON d.data_id = f.data_id
    WHERE s.serie_id = 'dolar'
    ORDER BY d.data DESC
    LIMIT 10
""", conexao)
```

## Qualidade de dados

A cada execucao, o arquivo `data/gold/relatorio_qualidade.json` e gerado
com quatro verificacoes por indicador:

- **valores nulos**: nenhum valor pode estar vazio.
- **registros duplicados**: nenhuma combinacao de serie e data pode
  aparecer mais de uma vez.
- **atualizacao recente**: o dado mais recente nao pode estar defasado
  por mais de 45 dias.
- **faixa de valores plausiveis**: por exemplo, o dolar deve estar entre
  R$ 0 e R$ 20; a Selic, entre 0% e 100% ao ano.

Se alguma verificacao falhar, o pipeline registra um aviso no log e o
comando `python pipeline.py` termina com codigo de saida diferente de
zero, o que permite que um workflow de CI/CD detecte o problema
automaticamente.

## Testes automatizados

```
pytest tests/ -v
```

Os testes cobrem as regras de limpeza (`transform.py`), as regras de
qualidade (`quality.py`) e o comportamento idempotente da carga
(`load.py`). Nenhum teste depende de acesso a internet: os dados de
entrada sao criados diretamente em cada teste.

## Integracao continua

Este repositorio inclui dois workflows do GitHub Actions, em
`.github/workflows/`:

- **ci.yml**: roda a suite de testes automaticamente a cada push ou
  pull request.
- **pipeline_diario.yml**: roda o pipeline completo uma vez por dia,
  publicando o banco de dados e o relatorio de qualidade gerados como
  artefatos do workflow.

## Estrutura do projeto

```
pipeline_dados_bcb/
├── config.py               catalogo de series e configuracoes gerais
├── logger.py                configuracao de logging usada por todo o projeto
├── extract.py               camada bronze: extracao da API
├── transform.py             camada silver: limpeza e tipagem
├── load.py                  camada gold: carga no esquema estrela (SQLite)
├── quality.py                verificacoes automatizadas de qualidade
├── pipeline.py               orquestrador com interface de linha de comando
├── tests/
│   ├── test_transform.py
│   ├── test_quality.py
│   └── test_load.py
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── logs/
├── .github/workflows/
│   ├── ci.yml
│   └── pipeline_diario.yml
├── requirements.txt
└── README.md
```

## Possiveis evolucoes

Ideias para continuar evoluindo o projeto:

- trocar o SQLite por um banco gerenciado (Postgres, por exemplo) sem
  alterar a logica de `load.py`, apenas a conexao.
- adicionar novas fontes de dados (outra API publica) e cruzar com os
  indicadores existentes na camada gold.
- versionar o banco gold com um processo de "slowly changing dimension"
  para manter o historico de mudancas nos metadados das series.
- expor os dados atraves de uma API propria (FastAPI, por exemplo), em
  vez de depender apenas de leitura direta do SQLite.
