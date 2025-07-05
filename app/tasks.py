from celery import Celery
from .config import settings
from .database import SessionLocal
from .models import Fixture, SignalResult
from datetime import datetime
from .signals import SIGNAL_HANDLERS
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert

celery = Celery(__name__, broker=settings.CELERY_BROKER_URL)
celery.conf.result_backend = settings.CELERY_RESULT_BACKEND

@celery.task
def compute_signals_for_fixture(fixture_id: int):
    db = SessionLocal()
    fixture = db.query(Fixture).get(fixture_id)

    for sig_id, handler in SIGNAL_HANDLERS.items():
        status, value, note = handler(fixture, db)
        stmt = insert(SignalResult).values(
            fixture_id=fixture_id,
            signal_id=int(sig_id),
            status=status,
            value=value,
            note=note,
            created_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=["fixture_id", "signal_id"],
            set_={
                "status": status,
                "value": value,
                "note": note,
                "created_at": datetime.utcnow()
            }
        )
        db.execute(stmt)

    db.commit()
    db.close()
    
# This file contains the Celery task for computing signals for a fixture.
# It retrieves the fixture from the database, computes each signal using the registered handlers,
# and inserts or updates the results in the SignalResult table.