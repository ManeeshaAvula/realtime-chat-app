from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from .database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room = Column(String(64), index=True, nullable=False)
    username = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
