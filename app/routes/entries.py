"""CRUD de Entry — a entidade central. Cobre GET/POST/PUT/DELETE.

O produto e garantido no cache antes de gravar o Entry: se o barcode ainda nao
foi cacheado, buscamos na OFF na hora. Os macros sao congelados no Entry por
regra de tres (valor_100 * quantidade / 100) no momento da gravacao.
"""
from datetime import date

from flask import jsonify
from flask_openapi3 import APIBlueprint, Tag

from ..database import SessionLocal
from ..models import Entry, Product
from ..off_client import OFFUnavailable, ProductNotFound, fetch_product
from ..routes.products import _cache_product
from ..schemas import EntryCreate, EntryListQuery, EntryPath, EntryUpdate

tag = Tag(name="Entries", description="Registros de consumo (diario alimentar)")
bp = APIBlueprint("entries", __name__, url_prefix="/api", abp_tags=[tag])


def _macro(value_100g, quantity_g) -> float | None:
    """Regra de tres. None se o produto nao tinha aquele macro."""
    if value_100g is None:
        return None
    return round(value_100g * quantity_g / 100.0, 1)


def _apply_macros(entry: Entry, product: Product) -> None:
    """Congela os macros do Entry a partir do produto e da quantidade."""
    q = entry.quantity_g
    entry.energy_kcal = (
        round(product.energy_kcal_100g * q / 100.0)
        if product.energy_kcal_100g is not None
        else None
    )
    entry.proteins = _macro(product.proteins_100g, q)
    entry.carbohydrates = _macro(product.carbohydrates_100g, q)
    entry.fat = _macro(product.fat_100g, q)


def _get_or_fetch_product(db, barcode: str) -> Product | None:
    """Devolve o produto do cache; se ausente, busca na OFF e cacheia."""
    product = db.get(Product, barcode)
    if product is not None:
        return product
    dto = fetch_product(barcode)  # pode levantar ProductNotFound / OFFUnavailable
    _cache_product(dto)
    return db.get(Product, barcode)


@bp.get("/entries", summary="Lista registros (paginado, com filtros)")
def list_entries(query: EntryListQuery):
    """Lista Entries com filtros por data e refeicao. Envelope paginado."""
    db = SessionLocal()
    q = db.query(Entry)
    if query.date is not None:
        q = q.filter(Entry.consumed_on == query.date)
    if query.meal is not None:
        q = q.filter(Entry.meal == query.meal)

    total = q.count()
    rows = (
        q.order_by(Entry.consumed_on.desc(), Entry.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
        .all()
    )
    pages = (total + query.page_size - 1) // query.page_size if total else 0
    return jsonify(
        {
            "items": [e.to_dict() for e in rows],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "pages": pages,
        }
    ), 200


@bp.post("/entries", summary="Cria um registro de consumo")
def create_entry(body: EntryCreate):
    """Cria um Entry, garantindo o produto no cache e congelando os macros."""
    db = SessionLocal()
    try:
        product = _get_or_fetch_product(db, body.barcode)
    except ProductNotFound:
        return jsonify({"error": "produto nao encontrado na Open Food Facts"}), 404
    except OFFUnavailable:
        return jsonify({"error": "Open Food Facts indisponivel"}), 502

    entry = Entry(
        product_barcode=product.barcode,
        product_name=product.name,
        quantity_g=body.quantity_g,
        meal=body.meal,
        consumed_on=body.consumed_on or date.today(),
    )
    _apply_macros(entry, product)
    db.add(entry)
    db.commit()
    return jsonify(entry.to_dict()), 201


@bp.put("/entries/<int:entry_id>", summary="Edita quantidade/refeicao de um registro")
def update_entry(path: EntryPath, body: EntryUpdate):
    """Atualiza um Entry. Se a quantidade muda, recalcula os macros."""
    db = SessionLocal()
    entry = db.get(Entry, path.entry_id)
    if entry is None:
        return jsonify({"error": "registro nao encontrado"}), 404

    if body.meal is not None:
        entry.meal = body.meal
    if body.consumed_on is not None:
        entry.consumed_on = body.consumed_on
    if body.quantity_g is not None:
        entry.quantity_g = body.quantity_g
        product = db.get(Product, entry.product_barcode)
        if product is not None:
            _apply_macros(entry, product)

    db.commit()
    return jsonify(entry.to_dict()), 200


@bp.delete("/entries/<int:entry_id>", summary="Remove um registro")
def delete_entry(path: EntryPath):
    """Remove um Entry pelo id."""
    db = SessionLocal()
    entry = db.get(Entry, path.entry_id)
    if entry is None:
        return jsonify({"error": "registro nao encontrado"}), 404
    db.delete(entry)
    db.commit()
    return "", 204
