"""Cliente da Open Food Facts + normalizacao do payload sujo.

Este e o modulo que satisfaz o requisito do enunciado: os dados da OFF sao
"consumidos e tratados dentro da aplicacao". Toda a sujeira medida na pesquisa
(nome so em product_name_pt, energy_100g que e kJ, macros ausentes, precisao
absurda, corpo 503 em HTML) e domada aqui, e o resto da API so ve DTOs limpos.

Duas integracoes distintas, dois hosts:
- produto por barcode -> world.openfoodfacts.org/api/v2/product/{code}.json
- busca por texto     -> search.openfoodfacts.org/search
"""
from __future__ import annotations

import requests

from .config import Config

# Campos recortados para nao baixar 32 KB / 233 chaves por produto.
_PRODUCT_FIELDS = (
    "code,product_name,product_name_pt,product_name_en,generic_name_pt,"
    "brands,quantity,serving_quantity,nutrition_data_per,nutriments,"
    "image_front_small_url,image_small_url,completeness,countries_tags,lang"
)


class OFFUnavailable(Exception):
    """A OFF respondeu 503, timeout, ou corpo nao-JSON."""


class ProductNotFound(Exception):
    """Barcode nao existe no catalogo da OFF (status 404 / status:0)."""


def _headers() -> dict:
    return {"User-Agent": Config.OFF_USER_AGENT}


def _get_json(url: str, params: dict | None = None) -> dict:
    """GET defensivo: checa status e Content-Type antes de parsear.

    O corpo do 503 global da OFF e uma pagina HTML; response.json() cego
    levantaria excecao de parse. Aqui isso vira OFFUnavailable tratavel.
    """
    try:
        resp = requests.get(
            url, params=params, headers=_headers(), timeout=Config.OFF_TIMEOUT
        )
    except requests.RequestException as exc:  # timeout, DNS, conexao...
        raise OFFUnavailable(str(exc)) from exc

    if resp.status_code == 404:
        raise ProductNotFound(url)
    if resp.status_code >= 500:
        raise OFFUnavailable(f"HTTP {resp.status_code}")

    content_type = resp.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        # 200 com corpo HTML tambem cai aqui (pagina de erro mascarada).
        raise OFFUnavailable(f"Content-Type inesperado: {content_type!r}")

    try:
        return resp.json()
    except ValueError as exc:
        raise OFFUnavailable("corpo nao e JSON valido") from exc


# --------------------------------------------------------------------------- #
# Normalizacao
# --------------------------------------------------------------------------- #
def _round_macro(value) -> float | None:
    """Arredonda macro para 1 casa; None se ausente/invalido."""
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _round_kcal(value) -> float | None:
    """Arredonda kcal para inteiro; None se ausente/invalido."""
    try:
        return float(round(float(value)))
    except (TypeError, ValueError):
        return None


def _first_name(*candidates) -> str:
    """Primeiro nome nao-vazio da cadeia de fallback."""
    for candidate in candidates:
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return "Produto sem nome"


def _brands_to_str(brands) -> str | None:
    """brands e string no endpoint de produto e lista no de busca."""
    if isinstance(brands, list):
        return ", ".join(str(b) for b in brands if b) or None
    if brands:
        return str(brands)
    return None


def normalize_product(raw: dict) -> dict:
    """DTO limpo a partir do objeto `product` da v2 (endpoint de barcode)."""
    nutr = raw.get("nutriments") or {}
    brands = _brands_to_str(raw.get("brands"))
    quantity = raw.get("quantity")
    return {
        "barcode": str(raw.get("code", "")),
        "name": _first_name(
            raw.get("product_name_pt"),
            raw.get("product_name"),
            raw.get("product_name_en"),
            raw.get("generic_name_pt"),
            f"{brands} {quantity}".strip() if (brands or quantity) else None,
        ),
        "brands": brands,
        "quantity": quantity,
        "image_url": raw.get("image_front_small_url") or raw.get("image_small_url"),
        # 100g vs 100ml so muda o rotulo da unidade na tela.
        "nutrition_basis": raw.get("nutrition_data_per") or "100g",
        # ATENCAO: usar energy-kcal_100g (kcal). energy_100g e kJ.
        "energy_kcal_100g": _round_kcal(nutr.get("energy-kcal_100g")),
        "proteins_100g": _round_macro(nutr.get("proteins_100g")),
        "carbohydrates_100g": _round_macro(nutr.get("carbohydrates_100g")),
        "fat_100g": _round_macro(nutr.get("fat_100g")),
        "completeness": raw.get("completeness"),
    }


def normalize_hit(hit: dict) -> dict:
    """DTO limpo a partir de um hit do Search-a-licious.

    O indice de busca tem formato diferente do endpoint de produto: nao traz
    `product_name` generico com frequencia, `brands` e lista, e nao carrega
    `nutrition_data_per`/`serving_size`.
    """
    nutr = hit.get("nutriments") or {}
    brands = _brands_to_str(hit.get("brands"))
    quantity = hit.get("quantity")
    return {
        "barcode": str(hit.get("code", "")),
        "name": _first_name(
            hit.get("product_name_pt"),
            hit.get("product_name"),
            hit.get("generic_name_pt"),
            f"{brands} {quantity}".strip() if (brands or quantity) else None,
        ),
        "brands": brands,
        "quantity": quantity,
        "image_url": hit.get("image_front_small_url") or hit.get("image_small_url"),
        "nutrition_basis": "100g",
        "energy_kcal_100g": _round_kcal(nutr.get("energy-kcal_100g")),
        "proteins_100g": _round_macro(nutr.get("proteins_100g")),
        "carbohydrates_100g": _round_macro(nutr.get("carbohydrates_100g")),
        "fat_100g": _round_macro(nutr.get("fat_100g")),
        "completeness": hit.get("completeness"),
    }


# --------------------------------------------------------------------------- #
# Chamadas publicas
# --------------------------------------------------------------------------- #
def fetch_product(barcode: str) -> dict:
    """Busca um produto por barcode e devolve o DTO normalizado.

    Levanta ProductNotFound (404) ou OFFUnavailable (503/timeout/HTML).
    """
    url = f"{Config.OFF_PRODUCT_BASE_URL}/api/v2/product/{barcode}.json"
    data = _get_json(url, params={"fields": _PRODUCT_FIELDS})
    if data.get("status") == 0 or "product" not in data:
        raise ProductNotFound(barcode)
    return normalize_product(data["product"])


def search_products(query: str, page: int, page_size: int) -> dict:
    """Busca por texto no Search-a-licious. Envelope paginado normalizado.

    Ordena por completeness/popularidade para trazer primeiro o que tem dado.
    """
    url = f"{Config.OFF_SEARCH_BASE_URL}/search"
    params = {
        "q": query,
        "langs": "pt,en",
        "page": page,
        "page_size": page_size,
        "sort_by": "-completeness",
        "fields": (
            "code,product_name,product_name_pt,generic_name_pt,brands,quantity,"
            "nutriments,image_front_small_url,image_small_url,completeness"
        ),
    }
    data = _get_json(url, params=params)
    hits = data.get("hits") or []
    items = [normalize_hit(h) for h in hits if h.get("code")]
    return {
        "items": items,
        "total": data.get("count", len(items)),
        "page": data.get("page", page),
        "page_size": data.get("page_size", page_size),
        "pages": data.get("page_count", 1),
    }
