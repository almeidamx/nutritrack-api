"""Ponto de entrada WSGI (gunicorn: `gunicorn wsgi:app`)."""
from app import app

if __name__ == "__main__":
    # Execucao local sem gunicorn: python wsgi.py
    app.run(host="0.0.0.0", port=5000, debug=True)
