"""
test_transform.py

Testes automatizados das regras de limpeza da camada silver. Nenhum
teste aqui depende de rede: os dados de entrada sao criados diretamente
no proprio teste, o que torna a suite rapida e confiavel para rodar em
um pipeline de integracao continua (CI).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transform import converter_valor, enriquecer_dataframe, limpar_dataframe, registros_para_dataframe


def test_converter_valor_aceita_ponto():
    assert converter_valor("5.32") == 5.32


def test_converter_valor_aceita_virgula():
    assert converter_valor("5,32") == 5.32


def test_converter_valor_invalido_retorna_none():
    assert converter_valor("abc") is None


def test_converter_valor_none_retorna_none():
    assert converter_valor(None) is None


def test_registros_para_dataframe_descarta_valores_invalidos():
    registros = [
        {"data": "01/01/2026", "valor": "5.0"},
        {"data": "02/01/2026", "valor": "abc"},
        {"data": "03/01/2026", "valor": "5.5"},
    ]
    dataframe = registros_para_dataframe(registros, "dolar")
    assert len(dataframe) == 2
    assert set(dataframe["valor"]) == {5.0, 5.5}


def test_registros_para_dataframe_marca_a_serie_de_origem():
    registros = [{"data": "01/01/2026", "valor": "5.0"}]
    dataframe = registros_para_dataframe(registros, "dolar")
    assert dataframe.iloc[0]["serie"] == "dolar"


def test_limpar_dataframe_remove_duplicatas_mantendo_o_ultimo():
    registros = [
        {"data": "01/01/2026", "valor": "5.0"},
        {"data": "01/01/2026", "valor": "5.9"},
    ]
    dataframe = registros_para_dataframe(registros, "dolar")
    dataframe_limpo = limpar_dataframe(dataframe)
    assert len(dataframe_limpo) == 1
    assert dataframe_limpo.iloc[0]["valor"] == 5.9


def test_limpar_dataframe_ordena_por_data():
    registros = [
        {"data": "03/01/2026", "valor": "5.0"},
        {"data": "01/01/2026", "valor": "5.5"},
        {"data": "02/01/2026", "valor": "5.2"},
    ]
    dataframe = registros_para_dataframe(registros, "dolar")
    dataframe_limpo = limpar_dataframe(dataframe)
    datas_ordenadas = list(dataframe_limpo["data"])
    assert datas_ordenadas == sorted(datas_ordenadas)


def test_enriquecer_dataframe_adiciona_colunas_de_data():
    registros = [{"data": "15/06/2026", "valor": "5.0"}]
    dataframe = registros_para_dataframe(registros, "dolar")
    dataframe_enriquecido = enriquecer_dataframe(dataframe)
    linha = dataframe_enriquecido.iloc[0]
    assert linha["ano"] == 2026
    assert linha["mes"] == 6
    assert linha["trimestre"] == 2


def test_dataframe_vazio_nao_quebra_o_pipeline():
    dataframe_vazio = registros_para_dataframe([], "dolar")
    assert dataframe_vazio.empty
    assert limpar_dataframe(dataframe_vazio).empty
    assert enriquecer_dataframe(dataframe_vazio).empty
