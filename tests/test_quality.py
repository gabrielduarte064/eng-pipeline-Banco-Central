"""
test_quality.py

Testes automatizados das regras de qualidade de dados. Cada verificacao
e testada tanto no caminho feliz (dado bom, deve passar) quanto no
caminho de falha (dado ruim, deve reprovar), que e a forma correta de
testar uma regra de validacao.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quality import verificar_duplicados, verificar_faixa_valores, verificar_nulos


def test_verificar_nulos_passa_quando_nao_ha_nulos():
    dataframe = pd.DataFrame({"valor": [1.0, 2.0, 3.0]})
    resultado = verificar_nulos(dataframe)
    assert resultado["passou"] is True
    assert resultado["total_encontrado"] == 0


def test_verificar_nulos_reprova_quando_ha_nulos():
    dataframe = pd.DataFrame({"valor": [1.0, None, 3.0]})
    resultado = verificar_nulos(dataframe)
    assert resultado["passou"] is False
    assert resultado["total_encontrado"] == 1


def test_verificar_duplicados_passa_quando_nao_ha_duplicatas():
    dataframe = pd.DataFrame({"data_id": ["20260101", "20260102"]})
    resultado = verificar_duplicados(dataframe)
    assert resultado["passou"] is True


def test_verificar_duplicados_reprova_quando_ha_duplicatas():
    dataframe = pd.DataFrame({"data_id": ["20260101", "20260101"]})
    resultado = verificar_duplicados(dataframe)
    assert resultado["passou"] is False
    assert resultado["total_encontrado"] == 1


def test_verificar_faixa_valores_passa_dentro_da_faixa():
    dataframe = pd.DataFrame({"valor": [5.0, 6.0, 7.0]})
    resultado = verificar_faixa_valores(dataframe, "dolar")
    assert resultado["passou"] is True


def test_verificar_faixa_valores_reprova_fora_da_faixa():
    dataframe = pd.DataFrame({"valor": [5.0, 999.0]})
    resultado = verificar_faixa_valores(dataframe, "dolar")
    assert resultado["passou"] is False
    assert resultado["total_fora_da_faixa"] == 1


def test_verificar_faixa_valores_sem_regra_definida_sempre_passa():
    dataframe = pd.DataFrame({"valor": [999999.0]})
    resultado = verificar_faixa_valores(dataframe, "serie_sem_regra_cadastrada")
    assert resultado["passou"] is True
    assert resultado["aplicavel"] is False
