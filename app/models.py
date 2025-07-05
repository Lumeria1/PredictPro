from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class Fixture(Base):
    __tablename__ = "fixtures"
    id = Column(Integer, primary_key=True, index=True)
    competition = Column(String, index=True, nullable=False)
    season = Column(String, nullable=False)
    kickoff = Column(DateTime, index=True, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    home_team_api_id = Column(Integer, index=True, nullable=False)
    away_team_api_id = Column(Integer, index=True, nullable=False)
    league_api_id = Column(Integer, index=True, nullable=False)
    signals = relationship("SignalResult", back_populates="fixture", cascade="all, delete-orphan")

class SignalResult(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id", ondelete="CASCADE"), index=True, nullable=False)
    signal_id = Column(Integer, index=True, nullable=False)
    status = Column(String(1), nullable=False)  # 'Y', 'N', or '-'
    value = Column(Float, nullable=True)        # Numeric metric (e.g., goals or xG)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
    __table_args__ = (
        UniqueConstraint('fixture_id', 'signal_id', name='uq_fixture_signal'),
    )
    fixture = relationship("Fixture", back_populates="signals")