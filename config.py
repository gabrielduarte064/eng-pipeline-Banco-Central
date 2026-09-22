"""
config.py

Configuracao central do pipeline: catalogo de series extraidas, caminhos
das camadas de dados (bronze, silver, gold) e parametros gerais.

O pipeline segue a arquitetura em camadas (medallion architecture),
comum em plataformas de dados modernas (Databricks, Delta Lake, etc.):

    bronze  -> dado bruto, exatamente como veio da fonte, sem alteracao
    silver  -> dado limpo, tipado e validado
    gold    -> dado agregado em modelo dimensional, pronto para consumo
"""

from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent

DIR_BRONZE = RAIZ_PROJETO / "data" / "bronze"
DIR_SILVER = RAIZ_PROJETO / "data" / "silver"
DIR_GOLD = RAIZ_PROJETO / "data" / "gold"
DIR_LOGS = RAIZ_PROJETO / "logs"

CAMINHO_BANCO_GOLD = DIR_GOLD / "warehouse.db"
CAMINHO_RELATORIO_QUALIDADE = DIR_GOLD / "relatorio_qualidade.json"

BASE_URL_BCB = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    "?formato=json&dataInicial={data_inicial}&dataFinal={data_final}"
)

CATALOGO_SERIES = {
    "selic": {
        "codigo": 4390,
        "nome": "Taxa Selic acumulada no mes, anualizada",
        "unidade": "% ao ano",
        "periodicidade": "mensal",
        "dias_historico": 1800,
    },
    "ipca": {
        "codigo": 433,
        "nome": "IPCA - variacao mensal",
        "unidade": "% ao mes",
        "periodicidade": "mensal",
        "dias_historico": 1800,
    },
    "dolar": {
        "codigo": 1,
        "nome": "Dolar comercial (venda)",
        "unidade": "R$",
        "periodicidade": "diaria",
        "dias_historico": 900,
    },
    "desemprego": {
        "codigo": 24369,
        "nome": "Taxa de desocupacao (PNAD Continua)",
        "unidade": "%",
        "periodicidade": "mensal",
        "dias_historico": 1800,
    },
}

LIMITE_DIAS_JANELA_API = 365 * 10 - 30

REGRAS_QUALIDADE = {
    "maximo_valores_nulos_permitido": 0,
    "maximo_duplicados_permitido": 0,
    "maximo_dias_desatualizado": 45,
    "faixas_valores_validos": {
        "selic": (0, 100),
        "ipca": (-10, 10),
        "dolar": (0, 20),
        "desemprego": (0, 40),
    },
}
