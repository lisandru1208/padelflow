from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ClubUser(Base):
    __tablename__ = "club_users"

    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(String, default="ja")
