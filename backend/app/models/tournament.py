import uuid
from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)   # P25, P100, ...
    gender = Column(String, nullable=False)     # M, F, MIX
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    indoor = Column(Boolean, default=False)
    is_finished = Column(Boolean, default=False)
    bracket_generated = Column(Boolean, default=False)
    selected_court_ids = Column(Text, nullable=True) 