"""
test_load.py

Testes automatizados da camada de carga (gold). Usa um banco SQLite
temporario e isolado por teste, garantindo que a suite nao interfira com
o banco real do projeto e possa rodar em paralelo com outros testes.
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from load import carregar_dim_data, carregar_dim_serie, carregar_fato_indicador, criar_esquema


@pytest.fixture
def conexao_em_memoria():
    conexao = sqlite3.connect(":memory:")
    conexao.execute("PRAGMA foreign_keys = ON;")
    criar_esquema(conexao)
    yield conexao
    conexao.close()


def test_carregar_dim_serie_insere_todas_as_series_do_catalogo(conexao_em_memoria):
    carregar_dim_serie(conexao_em_memoria)
    total = conexao_em_memoria.execute("SELECT COUNT(*) FROM dim_serie").fetchone()[0]
    assert total > 0


def test_carregar_dim_serie_e_idempotente(conexao_em_memoria):
    carregar_dim_serie(conexao_em_memoria)
    total_primeira_carga = conexao_em_memoria.execute("SELECT COUNT(*) FROM dim_serie").fetchone()[0]

    carregar_dim_serie(conexao_em_memoria)
    total_segunda_carga = conexao_em_memoria.execute("SELECT COUNT(*) FROM dim_serie").fetchone()[0]

    assert total_primeira_carga == total_segunda_carga


def test_carregar_fato_indicador_e_idempotente(conexao_em_memoria):
    carregar_dim_serie(conexao_em_memoria)

    dataframe = pd.DataFrame({
        "data": pd.to_datetime(["2026-01-01", "2026-01-02"]),
        "valor": [5.0, 5.1],
        "ano": [2026, 2026],
        "mes": [1, 1],
        "trimestre": [1, 1],
    })

    carregar_dim_data(conexao_em_memoria, dataframe)
    carregar_fato_indicador(conexao_em_memoria, dataframe, "dolar", "2026-01-02T10:00:00")
    total_primeira_carga = conexao_em_memoria.execute("SELECT COUNT(*) FROM fato_indicador").fetchone()[0]

    carregar_fato_indicador(conexao_em_memoria, dataframe, "dolar", "2026-01-02T11:00:00")
    total_segunda_carga = conexao_em_memoria.execute("SELECT COUNT(*) FROM fato_indicador").fetchone()[0]

    assert total_primeira_carga == 2
    assert total_segunda_carga == 2


def test_carregar_fato_indicador_atualiza_valor_existente(conexao_em_memoria):
    carregar_dim_serie(conexao_em_memoria)

    dataframe_original = pd.DataFrame({
        "data": pd.to_datetime(["2026-01-01"]),
        "valor": [5.0],
        "ano": [2026], "mes": [1], "trimestre": [1],
    })
    carregar_dim_data(conexao_em_memoria, dataframe_original)
    carregar_fato_indicador(conexao_em_memoria, dataframe_original, "dolar", "2026-01-01T10:00:00")

    dataframe_atualizado = pd.DataFrame({
        "data": pd.to_datetime(["2026-01-01"]),
        "valor": [5.5],
        "ano": [2026], "mes": [1], "trimestre": [1],
    })
    carregar_fato_indicador(conexao_em_memoria, dataframe_atualizado, "dolar", "2026-01-01T12:00:00")

    valor_final = conexao_em_memoria.execute("SELECT valor FROM fato_indicador").fetchone()[0]
    assert valor_final == 5.5
