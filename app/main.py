from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, Fixture
from .config import settings
from .tasks import compute_signals_for_fixture
from datetime import datetime, timedelta

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.APP_NAME)

# Enable CORS for Swagger POSTs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/fixtures/{date}")
def list_fixtures(date: str, db: Session = Depends(get_db)):
    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")
    start_dt = datetime.combine(day, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    return db.query(Fixture).filter(
        Fixture.kickoff >= start_dt,
        Fixture.kickoff < end_dt
    ).all()

@app.post("/compute/{fixture_id}")
def compute(fixture_id: int):
    compute_signals_for_fixture.delay(fixture_id)
    return {"status": "scheduled", "fixture_id": fixture_id}