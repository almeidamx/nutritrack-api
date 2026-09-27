"""Configuracao central da API NutriTrack.

Todos os valores tem default sensato para rodar localmente sem Docker, e sao
sobreponiveis por variavel de ambiente (o docker-compose injeta as versoes de
container). As duas base URLs da OFF sao separadas de proposito: o endpoint de
produto (v2) e o de busca (Search-a-licious) vivem em hosts diferentes, com
formatos de resposta diferentes (ver research/open-food-facts.md).
"""
import os


class Config:
    # Persistencia. Local: arquivo relativo. Docker: /data em volume nomeado.
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nutritrack.db")

    # Open Food Facts — dois hosts distintos.
    OFF_PRODUCT_BASE_URL = os.getenv(
        "OFF_PRODUCT_BASE_URL", "https://world.openfoodfacts.org"
    )
    OFF_SEARCH_BASE_URL = os.getenv(
        "OFF_SEARCH_BASE_URL", "https://search.openfoodfacts.org"
    )

    # A doc da OFF pede User-Agent no formato AppName/Version (Email).
    OFF_USER_AGENT = os.getenv(
        "OFF_USER_AGENT", "NutriTrack/1.0 (almeida.mx@gmail.com)"
    )

    # Timeout de saida para a OFF, em segundos. Curto de proposito: a OFF ja
    # respondeu 503 em sessoes de pesquisa, e nao queremos travar a nossa rota.
    OFF_TIMEOUT = float(os.getenv("OFF_TIMEOUT", "8"))

    # Paginacao padrao.
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "10"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "50"))
