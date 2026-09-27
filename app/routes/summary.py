"""Resumo diario: totais consumidos x meta. Alimenta o dashboard do front."""
from datetime import date

from flask import jsonify
from flask_openapi3 import APIBlueprint, Tag
from sqlalchemy import func

from ..database import SessionLocal
from ..models import GOAL_SINGLETON_ID, Entry, Goal
from ..schemas import SummaryQuery

tag = Tag(name="Resumo", description="Totais do dia contra a meta")
bp = APIBlueprint("summary", __name__, url_prefix="/api", abp_tags=[tag])


@bp.get("/summary", summary="Totais consumidos no dia x meta")
def get_summary(query: SummaryQuery):
    """Soma os macros do dia (nulos sao ignorados) e compara com a Goal."""
    db = SessionLocal()
    day = query.date or date.today()

    totals = (
        db.query(
            func.coalesce(func.sum(Entry.energy_kcal), 0.0),
            func.coalesce(func.sum(Entry.proteins), 0.0),
            func.coalesce(func.sum(Entry.carbohydrates), 0.0),
            func.coalesce(func.sum(Entry.fat), 0.0),
        )
        .filter(Entry.consumed_on == day)
        .one()
    )
    consumed = {
        "energy_kcal": round(totals[0]),
        "proteins": round(totals[1], 1),
        "carbohydrates": round(totals[2], 1),
        "fat": round(totals[3], 1),
    }

    goal = db.get(Goal, GOAL_SINGLETON_ID)
    goal_dict = goal.to_dict() if goal else Goal(id=GOAL_SINGLETON_ID).to_dict()

    entries_count = (
        db.query(func.count(Entry.id)).filter(Entry.consumed_on == day).scalar()
    )

    return jsonify(
        {
            "date": day.isoformat(),
            "consumed": consumed,
            "goal": goal_dict,
            "entries_count": entries_count,
        }
    ), 200
