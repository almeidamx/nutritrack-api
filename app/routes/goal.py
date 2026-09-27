"""Rotas da Goal (meta diaria). Singleton com upsert no PUT."""
from flask import jsonify
from flask_openapi3 import APIBlueprint, Tag

from ..database import SessionLocal
from ..models import GOAL_SINGLETON_ID, Goal
from ..schemas import GoalUpdate

tag = Tag(name="Meta", description="Alvo diario de calorias e macros")
bp = APIBlueprint("goal", __name__, url_prefix="/api", abp_tags=[tag])


def _get_or_create_goal(db) -> Goal:
    goal = db.get(Goal, GOAL_SINGLETON_ID)
    if goal is None:
        goal = Goal(id=GOAL_SINGLETON_ID)  # usa os defaults do model
        db.add(goal)
        db.commit()
    return goal


@bp.get("/goal", summary="Le a meta diaria")
def get_goal():
    db = SessionLocal()
    goal = _get_or_create_goal(db)
    return jsonify(goal.to_dict()), 200


@bp.put("/goal", summary="Atualiza a meta diaria (upsert)")
def put_goal(body: GoalUpdate):
    db = SessionLocal()
    goal = _get_or_create_goal(db)
    goal.energy_kcal = body.energy_kcal
    goal.proteins = body.proteins
    goal.carbohydrates = body.carbohydrates
    goal.fat = body.fat
    db.commit()
    return jsonify(goal.to_dict()), 200
