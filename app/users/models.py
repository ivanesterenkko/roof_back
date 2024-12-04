import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Users(Base):

    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    login: Mapped[str] = mapped_column(nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)

    projects = relationship("Projects", back_populates="user")
    session = relationship("Session", back_populates="sessions")

    def __str__(self):

        return f"Пользователь {self.login}"

class Sessions(Base):
    __tablename__ = 'sessions'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jwt_token: Mapped[str] = mapped_column(nullable=False, unique=True)
    created_at: Mapped[DateTime] = mapped_column(default=datetime.utcnow)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    user = relationship("Users", back_populates="session")