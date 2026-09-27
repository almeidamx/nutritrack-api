"""Modelo de dados do NutriTrack.

Tres entidades:

- Product: cache local do produto da Open Food Facts, chaveado pelo barcode.
  Gravado quando um Entry o referencia. No MVP o cache nunca expira — isso e o
  que protege o rate limit compartilhado de 15 req/min/IP da OFF.
- Entry: a ocorrencia de consumo. Entidade central (sofre CRUD completo). Os
  macros sao CONGELADOS no momento da gravacao (snapshot), calculados a partir
  do produto por regra de tres. Assim o historico nao muda se a OFF corrigir o
  produto depois, a leitura e trivial e o dashboard so soma colunas.
- Goal: alvo diario. Singleton (id fixo = 1), sem multiusuario.

Meal e enum na aplicacao (nao vira tabela), validado nos schemas Pydantic.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Refeicoes validas (enum de aplicacao). Chave estavel em ingles; o rotulo PT
# fica no front.
MEALS = ("breakfast", "lunch", "dinner", "snack")

GOAL_SINGLETON_ID = 1


class Product(Base):
    """Cache de um produto da OFF. Macros por 100g/100ml, ja normalizados."""

    __tablename__ = "products"

    barcode: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    brands: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # "100g" ou "100ml" — so muda o rotulo da unidade, nao a aritmetica.
    nutrition_basis: Mapped[str | None] = mapped_column(String, nullable=True)

    # Macros por 100g/ml. Nulo = a OFF nao tinha o dado (comum: ~50% da cauda).
    energy_kcal_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    proteins_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbohydrates_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_100g: Mapped[float | None] = mapped_column(Float, nullable=True)

    completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    entries: Mapped[list["Entry"]] = relationship(back_populates="product")


class Entry(Base):
    """Um registro de consumo: este produto, nesta quantidade, data e refeicao."""

    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_barcode: Mapped[str] = mapped_column(
        ForeignKey("products.barcode"), nullable=False
    )
    # Snapshot do nome no momento da gravacao (o produto pode mudar na OFF).
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)
    meal: Mapped[str] = mapped_column(String, nullable=False)
    consumed_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Macros CONGELADOS para esta quantidade (regra de tres na gravacao).
    # Nulo quando o produto nao tinha aquele macro — some do somatorio.
    energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    proteins: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbohydrates: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="entries")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_barcode": self.product_barcode,
            "product_name": self.product_name,
            "quantity_g": round(self.quantity_g, 1),
            "meal": self.meal,
            "consumed_on": self.consumed_on.isoformat(),
            "energy_kcal": self.energy_kcal,
            "proteins": self.proteins,
            "carbohydrates": self.carbohydrates,
            "fat": self.fat,
            "image_url": self.product.image_url if self.product else None,
        }


class Goal(Base):
    """Alvo diario de calorias e macros. Uma linha so (singleton)."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    energy_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=2000)
    proteins: Mapped[float] = mapped_column(Float, nullable=False, default=100)
    carbohydrates: Mapped[float] = mapped_column(Float, nullable=False, default=250)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=65)

    def to_dict(self) -> dict:
        return {
            "energy_kcal": self.energy_kcal,
            "proteins": self.proteins,
            "carbohydrates": self.carbohydrates,
            "fat": self.fat,
        }
