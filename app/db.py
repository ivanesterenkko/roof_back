from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


DATABASE_URL = settings.db_url

engine = create_async_engine(DATABASE_URL)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
    )


class Base(DeclarativeBase):

    def as_dict(self) -> dict:

        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


async def create_tables():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def delete_tables():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
