"""
logger.py

Configuracao unica de logging usada por todos os modulos do pipeline.
Cada execucao grava mensagens no console e em um arquivo de log, o que
facilita depurar falhas quando o pipeline roda de forma automatizada
(por exemplo, dentro de um workflow do GitHub Actions).
"""

import logging
from logging.handlers import RotatingFileHandler

from config import DIR_LOGS

DIR_LOGS.mkdir(parents=True, exist_ok=True)

FORMATO_LOG = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def obter_logger(nome_modulo):
    """Retorna um logger configurado para o modulo informado. Chamar esta
    funcao varias vezes com o mesmo nome nao duplica os handlers."""
    logger = logging.getLogger(nome_modulo)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatador = logging.Formatter(FORMATO_LOG)

    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formatador)
    logger.addHandler(handler_console)

    handler_arquivo = RotatingFileHandler(
        DIR_LOGS / "pipeline.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler_arquivo.setFormatter(formatador)
    logger.addHandler(handler_arquivo)

    return logger
