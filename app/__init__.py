"""Fabrica da aplicacao NutriTrack API.

flask-openapi3 gera o Swagger interativo (usado no video) a partir dos schemas
Pydantic das rotas. O Swagger fica em /openapi (ex.: /openapi/swagger).
"""
from flask import jsonify
from flask_cors import CORS
from flask_openapi3 import Info, OpenAPI

from .database import SessionLocal, init_db


def create_app() -> OpenAPI:
    info = Info(
        title="NutriTrack API",
        version="1.0.0",
        description=(
            "API do diario alimentar NutriTrack. Atua como intermediaria em "
            "cadeia entre o front e a Open Food Facts: consome, normaliza e "
            "cacheia os dados externos, e faz o CRUD dos registros de consumo."
        ),
    )
    app = OpenAPI(__name__, info=info)

    # CORS liberado: em dev o front (5173) chama a API (5000) direto; em
    # producao o nginx faz proxy em /api (mesma origem), entao e inofensivo.
    CORS(app)

    # Registro das rotas.
    from .routes.entries import bp as entries_bp
    from .routes.goal import bp as goal_bp
    from .routes.products import bp as products_bp
    from .routes.summary import bp as summary_bp

    app.register_api(products_bp)
    app.register_api(entries_bp)
    app.register_api(goal_bp)
    app.register_api(summary_bp)

    @app.get("/api/health")
    def health():
        """Healthcheck simples (usado pelo Docker e pelo front)."""
        return jsonify({"status": "ok"}), 200

    @app.teardown_appcontext
    def remove_session(exception=None):
        SessionLocal.remove()

    # Cria o schema no boot (idempotente).
    init_db()
    return app


app = create_app()
