"""
load.py

Camada de carga (gold). Le os arquivos Parquet da camada silver e monta
um modelo dimensional simples (esquema estrela) dentro de um banco
SQLite, que funciona aqui como um pequeno data warehouse local:

    dim_serie      -> uma linha por indicador (selic, ipca, dolar, etc.)
    dim_data       -> uma linha por data, com ano, mes e trimestre
    fato_indicador -> uma linha por (serie, data), com o valor observado

A carga e feita com "upsert" (inserir ou atualizar): rodar a carga varias
vezes com os mesmos dados nao gera duplicatas, o que torna o pipeline
seguro para ser executado repetidamente, inclusive em um agendamento
automatico.
"""

import sqlite3

import pandas as pd

from config import CAMINHO_BANCO_GOLD, CATALOGO_SERIES, DIR_SILVER
from logger import obter_logger

logger = obter_logger("load")


DDL_DIM_SERIE = """
CREATE TABLE IF NOT EXISTS dim_serie (
    serie_id TEXT PRIMARY KEY,
    codigo_bcb INTEGER NOT NULL,
    nome TEXT NOT NULL,
    unidade TEXT NOT NULL,
    periodicidade TEXT NOT NULL
);
"""

DDL_DIM_DATA = """
CREATE TABLE IF NOT EXISTS dim_data (
    data_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    trimestre INTEGER NOT NULL
);
"""

DDL_FATO_INDICADOR = """
CREATE TABLE IF NOT EXISTS fato_indicador (
    serie_id TEXT NOT NULL,
    data_id TEXT NOT NULL,
    valor REAL NOT NULL,
    carregado_em TEXT NOT NULL,
    PRIMARY KEY (serie_id, data_id),
    FOREIGN KEY (serie_id) REFERENCES dim_serie (serie_id),
    FOREIGN KEY (data_id) REFERENCES dim_data (data_id)
);
"""


def obter_conexao():
    CAMINHO_BANCO_GOLD.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(CAMINHO_BANCO_GOLD)
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao


def criar_esquema(conexao):
    conexao.execute(DDL_DIM_SERIE)
    conexao.execute(DDL_DIM_DATA)
    conexao.execute(DDL_FATO_INDICADOR)
    conexao.commit()


def carregar_dim_serie(conexao):
    for chave_serie, info in CATALOGO_SERIES.items():
        conexao.execute(
            """
            INSERT INTO dim_serie (serie_id, codigo_bcb, nome, unidade, periodicidade)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(serie_id) DO UPDATE SET
                codigo_bcb = excluded.codigo_bcb,
                nome = excluded.nome,
                unidade = excluded.unidade,
                periodicidade = excluded.periodicidade;
            """,
            (chave_serie, info["codigo"], info["nome"], info["unidade"], info["periodicidade"]),
        )
    conexao.commit()


def _data_id(data_como_texto):
    return data_como_texto.replace("-", "")


def carregar_dim_data(conexao, dataframe):
    if dataframe.empty:
        return

    linhas = dataframe[["data", "ano", "mes", "trimestre"]].drop_duplicates()
    for _, linha in linhas.iterrows():
        data_texto = linha["data"].strftime("%Y-%m-%d")
        conexao.execute(
            """
            INSERT INTO dim_data (data_id, data, ano, mes, trimestre)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(data_id) DO NOTHING;
            """,
            (_data_id(data_texto), data_texto, int(linha["ano"]), int(linha["mes"]), int(linha["trimestre"])),
        )
    conexao.commit()


def carregar_fato_indicador(conexao, dataframe, chave_serie, carregado_em):
    if dataframe.empty:
        return 0

    total = 0
    for _, linha in dataframe.iterrows():
        data_texto = linha["data"].strftime("%Y-%m-%d")
        conexao.execute(
            """
            INSERT INTO fato_indicador (serie_id, data_id, valor, carregado_em)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(serie_id, data_id) DO UPDATE SET
                valor = excluded.valor,
                carregado_em = excluded.carregado_em;
            """,
            (chave_serie, _data_id(data_texto), float(linha["valor"]), carregado_em),
        )
        total += 1
    conexao.commit()
    return total


def carregar_serie(conexao, chave_serie, carregado_em):
    caminho_silver = DIR_SILVER / f"{chave_serie}.parquet"
    if not caminho_silver.exists():
        logger.warning("Nenhum arquivo silver encontrado para a serie '%s'", chave_serie)
        return 0

    dataframe = pd.read_parquet(caminho_silver)
    carregar_dim_data(conexao, dataframe)
    total = carregar_fato_indicador(conexao, dataframe, chave_serie, carregado_em)
    logger.info("Serie '%s' carregada no gold: %s registros", chave_serie, total)
    return total


def carregar_todas_as_series(carregado_em=None):
    from datetime import datetime

    carregado_em = carregado_em or datetime.now().isoformat(timespec="seconds")

    conexao = obter_conexao()
    try:
        criar_esquema(conexao)
        carregar_dim_serie(conexao)

        resultados = {}
        for chave_serie in CATALOGO_SERIES:
            try:
                total = carregar_serie(conexao, chave_serie, carregado_em)
                resultados[chave_serie] = {"sucesso": True, "registros_carregados": total}
            except Exception as erro:
                logger.error("Falha ao carregar a serie '%s': %s", chave_serie, erro)
                resultados[chave_serie] = {"sucesso": False, "erro": str(erro)}
        return resultados
    finally:
        conexao.close()


if __name__ == "__main__":
    carregar_todas_as_series()
