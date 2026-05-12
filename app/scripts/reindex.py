"""
ETL скрипт — індексація існуючих заявок з PostgreSQL в Elasticsearch
Запуск: docker compose exec api python app/scripts/reindex.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.submission import Submission
from sqlalchemy.orm import joinedload
from app.services.search_service import index_submission

def reindex_all():
    db = SessionLocal()
    try:
        submissions = (
            db.query(Submission)
            .options(joinedload(Submission.authors))
            .all()
        )
        print(f"Знайдено заявок: {len(submissions)}")
        success = 0
        errors = 0
        for s in submissions:
            try:
                index_submission(s)
                print(f"  ✓ {s.title}")
                success += 1
            except Exception as e:
                print(f"  ✗ {s.title}: {e}")
                errors += 1
        print(f"\nГотово: {success} проіндексовано, {errors} помилок")
    finally:
        db.close()

if __name__ == "__main__":
    reindex_all()