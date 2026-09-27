"""Popula o banco com dados de demonstracao para o video.

Insere produtos de exemplo (staples brasileiros, com macros por 100g/ml
realistas), alguns registros de consumo do dia de hoje distribuidos entre as
refeicoes, e uma meta diaria. Assim o dashboard aparece populado nos primeiros
segundos da gravacao, sem depender da OFF ao vivo (protege contra 503 e contra
o rate limit durante a demo).

Uso:
    python seed.py            # limpa e recria os dados de demo
"""
from datetime import date

from app.database import SessionLocal, init_db
from app.models import GOAL_SINGLETON_ID, Entry, Goal, Product

# barcode -> (nome, basis, kcal_100, prot_100, carb_100, fat_100, imagem)
# Valores ilustrativos de staples; o leite Tirol vem do payload real da pesquisa.
DEMO_PRODUCTS = {
    "7896256600223": ("Leite integral Tirol", "100ml", 58, 3.2, 4.5, 3.0,
                       "https://images.openfoodfacts.org/images/products/789/625/660/0223/front_en.15.200.jpg"),
    "0000000000017": ("Arroz branco cozido", "100g", 128, 2.5, 28.0, 0.2, None),
    "0000000000024": ("Feijao carioca cozido", "100g", 76, 4.8, 13.6, 0.5, None),
    "0000000000031": ("Peito de frango grelhado", "100g", 165, 31.0, 0.0, 3.6, None),
    "0000000000048": ("Banana prata", "100g", 89, 1.1, 22.8, 0.3, None),
    "0000000000055": ("Pao frances", "100g", 300, 8.0, 58.0, 3.1, None),
}

# (barcode, quantidade_g, refeicao)
DEMO_ENTRIES = [
    ("7896256600223", 200, "breakfast"),
    ("0000000000055", 100, "breakfast"),
    ("0000000000031", 150, "lunch"),
    ("0000000000017", 180, "lunch"),
    ("0000000000024", 120, "lunch"),
    ("0000000000048", 120, "snack"),
    ("0000000000031", 120, "dinner"),
    ("0000000000048", 100, "dinner"),
]


def _macro(v100, q):
    return None if v100 is None else round(v100 * q / 100.0, 1)


def run():
    init_db()
    db = SessionLocal()

    # Limpa dados anteriores (idempotente).
    db.query(Entry).delete()
    db.query(Product).delete()
    db.query(Goal).delete()
    db.commit()

    for barcode, (name, basis, kcal, prot, carb, fat, img) in DEMO_PRODUCTS.items():
        db.add(Product(
            barcode=barcode, name=name, nutrition_basis=basis,
            energy_kcal_100g=kcal, proteins_100g=prot,
            carbohydrates_100g=carb, fat_100g=fat, image_url=img,
            brands=None, quantity=None, completeness=1.0,
        ))
    db.commit()

    today = date.today()
    for barcode, qty, meal in DEMO_ENTRIES:
        p = db.get(Product, barcode)
        db.add(Entry(
            product_barcode=barcode, product_name=p.name, quantity_g=qty,
            meal=meal, consumed_on=today,
            energy_kcal=(round(p.energy_kcal_100g * qty / 100.0)
                         if p.energy_kcal_100g is not None else None),
            proteins=_macro(p.proteins_100g, qty),
            carbohydrates=_macro(p.carbohydrates_100g, qty),
            fat=_macro(p.fat_100g, qty),
        ))

    db.add(Goal(id=GOAL_SINGLETON_ID, energy_kcal=2200, proteins=130,
                carbohydrates=260, fat=70))
    db.commit()

    n_entries = db.query(Entry).count()
    print(f"Seed concluido: {len(DEMO_PRODUCTS)} produtos, {n_entries} registros "
          f"em {today.isoformat()}, meta definida.")


if __name__ == "__main__":
    run()
