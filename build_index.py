"""Rebuilds the FAISS knowledge-base index. Run after adding or editing KB articles:  python build_index.py"""
from app import create_app
from app.services.rag import build_index

app = create_app()
with app.app_context():
    print(f"Index built with {build_index()} chunks.")