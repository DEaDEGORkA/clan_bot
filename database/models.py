from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    """Модель пользователя"""
    user_id: int
    chat_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_assigned: bool = False
    is_blocked: bool = False
    last_activity: Optional[datetime] = None
    warnings_count: int = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class ProfanityWord(BaseModel):
    """Модель матного слова"""
    id: Optional[int] = None
    word: str
    created_at: datetime = datetime.now()

class LogEntry(BaseModel):
    """Модель записи лога"""
    log_id: Optional[int] = None
    user_id: int
    action: str
    details: Optional[str] = None
    created_at: datetime = datetime.now()

class RoleHistory(BaseModel):
    """История назначения ролей"""
    history_id: Optional[int] = None
    user_id: int
    role_name: str
    assigned_at: datetime = datetime.now()
    removed_at: Optional[datetime] = None
    reason: Optional[str] = None
