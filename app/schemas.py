"""Schemas Pydantic (request/response) para o flask-openapi3.

Sao estes schemas que geram o Swagger interativo mostrado no video. Meal e
validado como Literal para casar com o enum de aplicacao dos models.
"""
from datetime import date as date_type
from typing import Literal, Optional

from pydantic import BaseModel, Field

Meal = Literal["breakfast", "lunch", "dinner", "snack"]


# --------------------------- Path / Query params --------------------------- #
class BarcodePath(BaseModel):
    barcode: str = Field(..., description="Codigo de barras (EAN) do produto")


class EntryPath(BaseModel):
    entry_id: int = Field(..., description="ID do Entry")


class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, description="Texto livre da busca")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)


class EntryListQuery(BaseModel):
    date: Optional[date_type] = Field(None, description="Filtra por dia (YYYY-MM-DD)")
    meal: Optional[Meal] = Field(None, description="Filtra por refeicao")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)


class SummaryQuery(BaseModel):
    date: Optional[date_type] = Field(None, description="Dia do resumo (default: hoje)")


# ------------------------------- Bodies ------------------------------------ #
class EntryCreate(BaseModel):
    barcode: str = Field(..., description="Barcode do produto a registrar")
    quantity_g: float = Field(..., gt=0, description="Quantidade consumida (g/ml)")
    meal: Meal = Field(...)
    consumed_on: Optional[date_type] = Field(
        None, description="Dia do consumo (default: hoje)"
    )


class EntryUpdate(BaseModel):
    quantity_g: Optional[float] = Field(None, gt=0)
    meal: Optional[Meal] = None
    consumed_on: Optional[date_type] = None


class GoalUpdate(BaseModel):
    energy_kcal: float = Field(..., ge=0)
    proteins: float = Field(..., ge=0)
    carbohydrates: float = Field(..., ge=0)
    fat: float = Field(..., ge=0)
