"""CLI エントリポイント.

使い方:
    python -m karyu_tech_news --help
    python -m karyu_tech_news validate-sources
"""
from karyu_tech_news.main import app

if __name__ == "__main__":
    app()
