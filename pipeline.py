"""
pipeline.py

Ponto de entrada do projeto. Orquestra as quatro etapas do pipeline na
ordem correta (extract -> transform -> load -> quality) e mede o tempo
de cada etapa.

Uso:
    python pipeline.py                 roda o pipeline completo
    python pipeline.py --etapa extract roda somente a extracao
    python pipeline.py --etapa transform
    python pipeline.py --etapa load
    python pipeline.py --etapa quality
"""

import argparse
import sys
import time

from logger import obter_logger

logger = obter_logger("pipeline")

ETAPAS_VALIDAS = ["extract", "transform", "load", "quality", "all"]


def _rodar_etapa(nome_etapa, funcao):
    logger.info("Iniciando etapa: %s", nome_etapa)
    inicio = time.time()
    resultado = funcao()
    duracao = round(time.time() - inicio, 2)
    logger.info("Etapa '%s' concluida em %s segundos", nome_etapa, duracao)
    return resultado


def rodar_extract():
    from extract import extrair_todas_as_series
    return _rodar_etapa("extract", extrair_todas_as_series)


def rodar_transform():
    from transform import transformar_todas_as_series
    return _rodar_etapa("transform", transformar_todas_as_series)


def rodar_load():
    from load import carregar_todas_as_series
    return _rodar_etapa("load", carregar_todas_as_series)


def rodar_quality():
    from quality import rodar_verificacoes_de_qualidade
    return _rodar_etapa("quality", rodar_verificacoes_de_qualidade)


def rodar_pipeline_completo():
    logger.info("Iniciando execucao completa do pipeline")
    resultado_extract = rodar_extract()
    resultado_transform = rodar_transform()
    resultado_load = rodar_load()
    resultado_quality = rodar_quality()
    logger.info("Pipeline completo finalizado")

    return {
        "extract": resultado_extract,
        "transform": resultado_transform,
        "load": resultado_load,
        "quality": resultado_quality,
    }


def main():
    parser = argparse.ArgumentParser(description="Pipeline de dados economicos do Banco Central")
    parser.add_argument(
        "--etapa",
        choices=ETAPAS_VALIDAS,
        default="all",
        help="Qual etapa executar. O padrao roda o pipeline completo.",
    )
    argumentos = parser.parse_args()

    mapa_etapas = {
        "extract": rodar_extract,
        "transform": rodar_transform,
        "load": rodar_load,
        "quality": rodar_quality,
        "all": rodar_pipeline_completo,
    }

    resultado = mapa_etapas[argumentos.etapa]()

    if argumentos.etapa in ("quality", "all"):
        relatorio_qualidade = resultado["quality"] if argumentos.etapa == "all" else resultado
        if not relatorio_qualidade.get("passou_em_tudo", True):
            logger.error("Pipeline concluido com falhas de qualidade de dados")
            sys.exit(1)

    logger.info("Execucao finalizada com sucesso")


if __name__ == "__main__":
    main()
