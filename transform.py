"""
transform.py

Camada de transformacao (silver). Le o dado bruto gravado pela camada
bronze, aplica limpeza, tipagem e deduplicacao, e grava o resultado em
formato Parquet, que e o formato binario colunar mais usado em pipelines
de dados reais (Spark, Databricks, Pandas).

As funcoes de limpeza sao escritas de forma pura (recebem dados e
devolvem dados, sem ler ou escrever arquivos), o que facilita testar cada
regra de negocio isoladamente em tests/test_transform.py.
"""

import json
from pathlib import Path

import pandas as pd

from config import CATALOGO_SERIES, DIR_BRONZE, DIR_SILVER
from logger import obter_logger

logger = obter_logger("transform")


def converter_valor(valor_bruto):
    """Converte o valor textual retornado pela API para float. Aceita
    tanto separador decimal com ponto quanto com virgula. Retorna None
    quando o valor nao pode ser convertido, para que o registro seja
    descartado na limpeza em vez de quebrar o pipeline."""
    if valor_bruto is None:
        return None
    texto = str(valor_bruto).strip().replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def registros_para_dataframe(registros, chave_serie):
    """Converte a lista de registros brutos (dicionarios com 'data' e
    'valor') em um DataFrame tipado, com uma coluna adicional indicando a
    serie de origem."""
    linhas = []
    for registro in registros:
        valor = converter_valor(registro.get("valor"))
        data_texto = registro.get("data")
        if valor is None or not data_texto:
            continue
        linhas.append({"data_texto": data_texto, "valor": valor, "serie": chave_serie})

    dataframe = pd.DataFrame(linhas)
    if dataframe.empty:
        return dataframe

    dataframe["data"] = pd.to_datetime(dataframe["data_texto"], format="%d/%m/%Y", errors="coerce")
    dataframe = dataframe.dropna(subset=["data"])
    dataframe = dataframe.drop(columns=["data_texto"])
    return dataframe


def limpar_dataframe(dataframe):
    """Aplica as regras de limpeza: remove duplicatas (mesma serie e
    mesma data) mantendo o registro mais recente, ordena por data e
    reseta o indice."""
    if dataframe.empty:
        return dataframe

    dataframe = dataframe.drop_duplicates(subset=["serie", "data"], keep="last")
    dataframe = dataframe.sort_values("data").reset_index(drop=True)
    return dataframe


def enriquecer_dataframe(dataframe):
    """Adiciona colunas derivadas da data (ano, mes, trimestre) que serao
    uteis na camada gold para agregacoes por periodo."""
    if dataframe.empty:
        return dataframe

    dataframe = dataframe.copy()
    dataframe["ano"] = dataframe["data"].dt.year
    dataframe["mes"] = dataframe["data"].dt.month
    dataframe["trimestre"] = dataframe["data"].dt.quarter
    return dataframe


def _ultimo_arquivo_bronze(chave_serie):
    pasta_serie = DIR_BRONZE / chave_serie
    if not pasta_serie.exists():
        return None
    arquivos = sorted(pasta_serie.glob(f"{chave_serie}_*.json"))
    return arquivos[-1] if arquivos else None


def transformar_serie(chave_serie):
    """Le o arquivo bronze mais recente da serie informada, aplica as
    regras de limpeza e enriquecimento, e grava o resultado em Parquet na
    camada silver. Retorna o caminho do arquivo gravado, ou None se nao
    houver dado bronze disponivel para a serie."""
    caminho_bronze = _ultimo_arquivo_bronze(chave_serie)
    if caminho_bronze is None:
        logger.warning("Nenhum arquivo bronze encontrado para a serie '%s'", chave_serie)
        return None

    with open(caminho_bronze, encoding="utf-8") as arquivo:
        pacote = json.load(arquivo)

    registros = pacote.get("registros", [])
    dataframe = registros_para_dataframe(registros, chave_serie)
    dataframe = limpar_dataframe(dataframe)
    dataframe = enriquecer_dataframe(dataframe)

    DIR_SILVER.mkdir(parents=True, exist_ok=True)
    caminho_silver = DIR_SILVER / f"{chave_serie}.parquet"

    if dataframe.empty:
        logger.warning("Serie '%s' ficou vazia apos a limpeza", chave_serie)
        return None

    dataframe.to_parquet(caminho_silver, index=False)
    logger.info(
        "Serie '%s' transformada: %s registros gravados em %s",
        chave_serie, len(dataframe), caminho_silver,
    )
    return caminho_silver


def transformar_todas_as_series():
    """Executa a transformacao de todas as series do catalogo."""
    resultados = {}
    for chave_serie in CATALOGO_SERIES:
        try:
            caminho = transformar_serie(chave_serie)
            resultados[chave_serie] = {"sucesso": caminho is not None, "caminho": str(caminho) if caminho else None}
        except Exception as erro:
            logger.error("Falha ao transformar a serie '%s': %s", chave_serie, erro)
            resultados[chave_serie] = {"sucesso": False, "erro": str(erro)}
    return resultados


if __name__ == "__main__":
    transformar_todas_as_series()
