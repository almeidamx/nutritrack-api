"""Rotas de proxy para a Open Food Facts (busca e detalhe por barcode).

Estas rotas nunca expoem o payload cru da OFF: sempre devolvem o DTO
normalizado por off_client. O detalhe por barcode tambem grava o produto no
cache local (protege o rate limit compartilhado).
"""
from flask import jsonify
from flask_openapi3 import APIBlueprint, Tag

from ..database import SessionLocal
from ..models import Product
from ..off_client import OFFUnavailable, ProductNotFound, fetch_product, search_products
from ..schemas import BarcodePath, SearchQuery

tag = Tag(name="Produtos", description="Busca e leitura de produtos na Open Food Facts")
bp = APIBlueprint("products", __name__, url_prefix="/api", abp_tags=[tag])


def _cache_product(dto: dict) -> None:
    """Grava/atualiza o produto no cache local (upsert por barcode)."""
    db = SessionLocal()
    product = db.get(Product, dto["barcode"])
    if product is None:
        product = Product(barcode=dto["barcode"])
        db.add(product)
    product.name = dto["name"]
    product.brands = dto["brands"]
    product.quantity = dto["quantity"]
    product.image_url = dto["image_url"]
    product.nutrition_basis = dto["nutrition_basis"]
    product.energy_kcal_100g = dto["energy_kcal_100g"]
    product.proteins_100g = dto["proteins_100g"]
    product.carbohydrates_100g = dto["carbohydrates_100g"]
    product.fat_100g = dto["fat_100g"]
    product.completeness = dto["completeness"]
    db.commit()


@bp.get("/products/search", summary="Busca produtos por texto")
def search(query: SearchQuery):
    """Proxy para o Search-a-licious. Devolve envelope paginado normalizado."""
    try:
        result = search_products(query.q, query.page, query.page_size)
    except OFFUnavailable:
        # Degrada com elegancia: lista vazia + flag, o front avisa o usuario.
        return jsonify(
            {"items": [], "total": 0, "page": query.page,
             "page_size": query.page_size, "pages": 0, "off_unavailable": True}
        ), 200
    return jsonify(result), 200


@bp.get("/products/<barcode>", summary="Detalhe de um produto por barcode")
def get_product(path: BarcodePath):
    """Le um produto por barcode na OFF, normaliza e cacheia localmente."""
    try:
        dto = fetch_product(path.barcode)
    except ProductNotFound:
        return jsonify({"error": "produto nao encontrado na Open Food Facts"}), 404
    except OFFUnavailable:
        return jsonify({"error": "Open Food Facts indisponivel"}), 502
    _cache_product(dto)
    return jsonify(dto), 200
