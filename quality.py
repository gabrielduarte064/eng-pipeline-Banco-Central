"""
quality.py

Camada de qualidade de dados. Roda um conjunto de verificacoes
automaticas sobre o banco gold (nulos, duplicados, atualizacao recente e
faixas de valores plausiveis) e gera um relatorio em JSON.

Verificacoes automatizadas de qualidade sao uma pratica padrao em
pipelines de dados profissionais: elas detectam problemas de dados antes
que cheguem a um dashboard ou a uma decisao de negocio.
"""

import json
from datetime import datetime

import pandas as pd

from config import CAMINHO_RELATORIO_QUALIDADE, CATALOGO_SERIES, REGRAS_QUALIDADE
from load import obter_conexao
from logger import obter_logger

logger = obter_logger("quality")


def verificar_nulos(dataframe):
    total_nulos = int(dataframe["valor"].isna().sum())
    limite = REGRAS_QUALIDADE["maximo_valores_nulos_permitido"]
    return {
        "verificacao": "valores_nulos",
        "total_encontrado": total_nulos,
        "limite_permitido": limite,
        "passou": total_nulos <= limite,
    }


def verificar_duplicados(dataframe):
    total_duplicados = int(dataframe.duplicated(subset=["data_id"]).sum())
    limite = REGRAS_QUALIDADE["maximo_duplicados_permitido"]
    return {
        "verificacao": "registros_duplicados",
        "total_encontrado": total_duplicados,
        "limite_permitido": limite,
        "passou": total_duplicados <= limite,
    }


def verificar_atualizacao(dataframe):
    if dataframe.empty:
        return {
            "verificacao": "atualizacao_recente",
            "dias_desde_ultimo_dado": None,
            "limite_permitido_dias": REGRAS_QUALIDADE["maximo_dias_desatualizado"],
            "passou": False,
        }

    ultima_data = pd.to_datetime(dataframe["data"]).max()
    dias_desde_ultimo_dado = (datetime.now() - ultima_data).days
    limite = REGRAS_QUALIDADE["maximo_dias_desatualizado"]

    return {
        "verificacao": "atualizacao_recente",
        "dias_desde_ultimo_dado": int(dias_desde_ultimo_dado),
        "limite_permitido_dias": limite,
        "passou": dias_desde_ultimo_dado <= limite,
    }


def verificar_faixa_valores(dataframe, chave_serie):
    faixa = REGRAS_QUALIDADE["faixas_valores_validos"].get(chave_serie)
    if faixa is None:
        return {"verificacao": "faixa_valores_validos", "aplicavel": False, "passou": True}

    minimo, maximo = faixa
    fora_da_faixa = dataframe[(dataframe["valor"] < minimo) | (dataframe["valor"] > maximo)]

    return {
        "verificacao": "faixa_valores_validos",
        "aplicavel": True,
        "faixa_esperada": [minimo, maximo],
        "total_fora_da_faixa": int(len(fora_da_faixa)),
        "passou": len(fora_da_faixa) == 0,
    }


def avaliar_serie(conexao, chave_serie):
    dataframe = pd.read_sql(
        """
        SELECT f.data_id, d.data, f.valor
        FROM fato_indicador f
        JOIN dim_data d ON d.data_id = f.data_id
        WHERE f.serie_id = ?
        """,
        conexao,
        params=(chave_serie,),
    )

    verificacoes = [
        verificar_nulos(dataframe),
        verificar_duplicados(dataframe),
        verificar_atualizacao(dataframe),
        verificar_faixa_valores(dataframe, chave_serie),
    ]

    passou_em_tudo = all(verificacao["passou"] for verificacao in verificacoes)

    return {
        "serie": chave_serie,
        "total_registros": int(len(dataframe)),
        "passou_em_tudo": passou_em_tudo,
        "verificacoes": verificacoes,
    }


def rodar_verificacoes_de_qualidade():
    conexao = obter_conexao()
    try:
        resultado_por_serie = {
            chave_serie: avaliar_serie(conexao, chave_serie)
            for chave_serie in CATALOGO_SERIES
        }
    finally:
        conexao.close()

    relatorio = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "passou_em_tudo": all(item["passou_em_tudo"] for item in resultado_por_serie.values()),
        "series": resultado_por_serie,
    }

    CAMINHO_RELATORIO_QUALIDADE.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_RELATORIO_QUALIDADE, "w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)

    if relatorio["passou_em_tudo"]:
        logger.info("Todas as verificacoes de qualidade passaram")
    else:
        logger.warning("Uma ou mais verificacoes de qualidade falharam. Ver %s", CAMINHO_RELATORIO_QUALIDADE)

    return relatorio


if __name__ == "__main__":
    rodar_verificacoes_de_qualidade()
