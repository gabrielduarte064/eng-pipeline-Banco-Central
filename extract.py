"""
extract.py

Camada de extracao (bronze). Busca os dados na API publica do Banco
Central e grava exatamente o que a fonte retornou, sem nenhuma limpeza,
junto com metadados da extracao (quando foi extraido, de onde veio, com
quais parametros). Essa camada e a fonte da verdade caso seja preciso
reprocessar tudo do zero no futuro.
"""

import json
import time
from datetime import date, datetime, timedelta

import requests

from config import BASE_URL_BCB, CATALOGO_SERIES, DIR_BRONZE, LIMITE_DIAS_JANELA_API
from logger import obter_logger

logger = obter_logger("extract")

MAXIMO_TENTATIVAS = 3
ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = 2


def _formatar_data(data_python):
    return data_python.strftime("%d/%m/%Y")


def _calcular_janela(dias_historico):
    hoje = date.today()
    dias = min(dias_historico, LIMITE_DIAS_JANELA_API)
    return hoje - timedelta(days=dias), hoje


def _requisitar_com_retentativa(url):
    ultimo_erro = None
    for tentativa in range(1, MAXIMO_TENTATIVAS + 1):
        try:
            resposta = requests.get(url, timeout=25, headers={"User-Agent": "pipeline-dados-bcb/1.0"})
            resposta.raise_for_status()
            return resposta.json()
        except Exception as erro:
            ultimo_erro = erro
            logger.warning("Tentativa %s de %s falhou: %s", tentativa, MAXIMO_TENTATIVAS, erro)
            if tentativa < MAXIMO_TENTATIVAS:
                time.sleep(ESPERA_ENTRE_TENTATIVAS_SEGUNDOS * tentativa)
    raise ultimo_erro


def extrair_serie(chave_serie, data_referencia=None):
    """Extrai uma serie do catalogo e grava o resultado bruto na camada
    bronze. Retorna o caminho do arquivo gravado.

    O arquivo e nomeado com a data de referencia da extracao, o que torna
    o processo idempotente: rodar a extracao mais de uma vez no mesmo dia
    sobrescreve o mesmo arquivo, em vez de acumular copias duplicadas.
    """
    info = CATALOGO_SERIES[chave_serie]
    data_referencia = data_referencia or date.today()

    data_inicial, data_final = _calcular_janela(info["dias_historico"])
    url = BASE_URL_BCB.format(
        codigo=info["codigo"],
        data_inicial=_formatar_data(data_inicial),
        data_final=_formatar_data(data_final),
    )

    logger.info("Extraindo serie '%s' (codigo %s)", chave_serie, info["codigo"])
    dados_brutos = _requisitar_com_retentativa(url)

    pacote = {
        "metadados": {
            "serie": chave_serie,
            "codigo_bcb": info["codigo"],
            "fonte": url,
            "extraido_em": datetime.now().isoformat(timespec="seconds"),
            "total_registros": len(dados_brutos),
        },
        "registros": dados_brutos,
    }

    pasta_serie = DIR_BRONZE / chave_serie
    pasta_serie.mkdir(parents=True, exist_ok=True)
    caminho_arquivo = pasta_serie / f"{chave_serie}_{data_referencia.isoformat()}.json"

    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(pacote, arquivo, ensure_ascii=False, indent=2)

    logger.info(
        "Serie '%s' gravada em %s (%s registros)",
        chave_serie, caminho_arquivo, len(dados_brutos),
    )
    return caminho_arquivo


def extrair_todas_as_series():
    """Executa a extracao de todas as series do catalogo. Series que
    falharem sao registradas no log, sem interromper as demais."""
    resultados = {}
    for chave_serie in CATALOGO_SERIES:
        try:
            caminho = extrair_serie(chave_serie)
            resultados[chave_serie] = {"sucesso": True, "caminho": str(caminho)}
        except Exception as erro:
            logger.error("Falha ao extrair a serie '%s': %s", chave_serie, erro)
            resultados[chave_serie] = {"sucesso": False, "erro": str(erro)}
    return resultados


if __name__ == "__main__":
    extrair_todas_as_series()
