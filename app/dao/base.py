from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import insert, select, delete, update, Result
from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
    """
    Базовый класс DAO, в котором:
    1) Вместо создания новой сессии в каждом методе, принимаем существующую `session: AsyncSession`.
    2) Сохраняем названия методов из старой реализации (find_by_id, find_one_or_none, find_all, add, delete_, update_, find_with_filters).
    3) Логику commit() выносим за пределы DAO (в вызывающий код, где открывается транзакция).
    """

    model = None  # Каждая наследуемая DAO-класс должна указать свою модель, например: model = UserModel

    @classmethod
    async def find_by_id(cls, session: AsyncSession, model_id: UUID) -> Optional[Any]:
        """
        Вернуть одну запись по её ID или None.
        """
        query = select(cls.model).filter_by(id=model_id)
        result: Result = await session.execute(query)
        return result.unique().scalars().one_or_none()

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, **filter_by) -> Optional[Any]:
        """
        Вернуть одну запись по фильтрам или None.
        """
        query = select(cls.model).filter_by(**filter_by)
        result: Result = await session.execute(query)
        return result.scalars().one_or_none()

    @classmethod
    async def find_all(cls, session: AsyncSession, **filter_by) -> List[Any]:
        """
        Вернуть все записи, удовлетворя фильтрам (или все записи, если фильтры не заданы).
        """
        query = select(cls.model).filter_by(**filter_by)
        result: Result = await session.execute(query)
        return result.scalars().unique().all()

    @classmethod
    async def add(cls, session: AsyncSession, **data) -> Optional[Any]:
        """
        Добавить новую запись в таблицу и вернуть её (как словарь колонок).
        Если нужно вернуть именно объект ORM, лучше использовать session.add(...) и session.flush().
        """
        query = insert(cls.model).values(**data).returning(cls.model.__table__.columns)
        result: Result = await session.execute(query)
        # Вместо commit делаем flush (если хотим сразу получить айдишники и т.д.):
        await session.flush()
        return result.mappings().first()

    @classmethod
    async def delete_(cls, session: AsyncSession, model_id: UUID) -> None:
        """
        Удалить запись по ID.
        """
        query = delete(cls.model).where(cls.model.id == model_id)
        await session.execute(query)
        await session.flush()

    @classmethod
    async def update_(cls, session: AsyncSession, model_id: UUID, **data) -> Optional[Any]:
        """
        Обновить запись по ID и вернуть изменённые поля.
        """
        query = (
            update(cls.model)
            .where(cls.model.id == model_id)
            .values(**data)
            .returning(cls.model.__table__.columns)
        )
        result: Result = await session.execute(query)
        await session.flush()
        return result.mappings().first()

    @classmethod
    async def find_with_filters(cls, session: AsyncSession, *filters) -> List[Any]:
        """
        Вернуть записи по переданным фильтрам (произвольным условным выражениям).
        Например: find_with_filters(User.id == some_id, User.name == some_name)
        """
        query = select(cls.model.__table__.columns).filter(*filters)
        result: Result = await session.execute(query)
        return result.mappings().all()
