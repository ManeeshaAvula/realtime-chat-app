from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room: str
    username: str
    content: str
    created_at: datetime


class RoomOut(BaseModel):
    room: str
    members: int
    message_count: int


class RoomListOut(BaseModel):
    rooms: List[RoomOut]
