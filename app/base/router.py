from fastapi import APIRouter, Depends
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.dao import Accessory_baseDAO, RoofsDAO, TariffsDAO
from app.base.schemas import (
    AccessoryBDRequest,
    AccessoryBDResponse,
    RoofRequest,
    RoofResponse,
    TariffRequest,
    TariffResponse
)
from app.db import get_session
from app.exceptions import RoofNotFound, TariffNotFound
from app.users.dependencies import get_current_user
from app.users.models import Users

router = APIRouter(prefix="/base", tags=["Base"])


@router.post("/roofs_base", description="Добавление покрытия в библиотеку")
async def add_roof_base(
    roof: RoofRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Добавляет новое покрытие в библиотеку.

    :param roof: Данные покрытия для добавления.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Словарь с идентификатором созданного покрытия.
    """
    new_roof = await RoofsDAO.add(
        session,
        name=roof.name,
        type=roof.type,
        overall_width=roof.overall_width,
        useful_width=roof.useful_width,
        overlap=roof.overlap,
        len_wave=roof.len_wave,
        max_length=roof.max_length,
        min_length=roof.min_length,
        imp_sizes=roof.imp_sizes
    )
    return {"roof_id": new_roof.id}


@router.get("/roofs_base", description="Получение покрытий из библиотеки")
async def get_roof_base(
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> list[RoofResponse]:
    """
    Возвращает список покрытий из библиотеки.

    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Список объектов RoofResponse.
    :raises RoofNotFound: Если покрытия не найдены.
    """
    roofs = await RoofsDAO.find_all(session)
    if not roofs:
        raise RoofNotFound
    return [
        RoofResponse(
            id=roof.id,
            name=roof.name,
            type=roof.type,
            overall_width=roof.overall_width,
            useful_width=roof.useful_width,
            overlap=roof.overlap,
            len_wave=roof.len_wave,
            max_length=roof.max_length,
            min_length=roof.min_length,
            imp_sizes=roof.imp_sizes
        )
        for roof in roofs
    ]


@router.delete("/roofs_base/{roof_id}", description="Удаление покрытия из библиотеки")
async def delete_roof_base(
    roof_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет покрытие из библиотеки по его идентификатору.

    :param roof_id: Идентификатор покрытия.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    """
    await RoofsDAO.delete_(session, model_id=roof_id)


@router.post("/accessories_base", description="Добавление доборного в библиотеку")
async def add_accessories_base(
    accessory: AccessoryBDRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Добавляет новый доборный материал в библиотеку.

    :param accessory: Данные доборного материала.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Словарь с идентификатором созданного доборного материала.
    """
    new_accessory = await Accessory_baseDAO.add(
        session,
        name=accessory.name,
        type=accessory.type,
        parent_type=accessory.parent_type,
        overall_width=accessory.overall_width,
        useful_width=accessory.useful_width,
        overlap=accessory.overlap,
        price=accessory.price,
        modulo=accessory.modulo,
        material=accessory.material
    )
    return {"accessory_id": new_accessory.id}


@router.get("/accessories_base", description="Получение доборных из библиотеки")
async def get_accessories_base(
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> list[AccessoryBDResponse]:
    """
    Возвращает список доборных материалов из библиотеки.

    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Список объектов AccessoryBDResponse.
    :raises RoofNotFound: Если доборные материалы не найдены.
    """
    accessories = await Accessory_baseDAO.find_all(session)
    if not accessories:
        raise RoofNotFound  # Если имеется отдельное исключение для доборных, замените его на корректное.
    return [
        AccessoryBDResponse(
            id=acc.id,
            name=acc.name,
            type=acc.type,
            parent_type=acc.parent_type,
            overall_width=acc.overall_width,
            useful_width=acc.useful_width,
            overlap=acc.overlap,
            price=acc.price,
            modulo=acc.modulo,
            material=acc.material
        )
        for acc in accessories
    ]


@router.delete("/accessories_base/{accessory_bd_id}", description="Удаление доборного из библиотеки")
async def delete_accessories_base(
    accessory_bd_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет доборный материал из библиотеки по его идентификатору.

    :param accessory_id: Идентификатор доборного материала.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    """
    await Accessory_baseDAO.delete_(session, model_id=accessory_bd_id)


@router.post("/tariff", description="Добавление тарифа в библиотеку")
async def add_tariff(
    data: TariffRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> TariffResponse:
    """
    Добавляет новый тариф в библиотеку.

    :param data: Данные тарифа.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Объект TariffResponse с данными созданного тарифа.
    """
    tariff = await TariffsDAO.add(
        session,
        name=data.name,
        limit_users=data.limit_users,
        price=data.price
    )
    return TariffResponse(
        id=tariff.id,
        name=tariff.name,
        limit_users=tariff.limit_users,
        price=tariff.price
    )


@router.get("/tariff", description="Получение тарифов из библиотеки")
async def get_tariffs(
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> list[TariffResponse]:
    """
    Возвращает список тарифов из библиотеки.

    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Список объектов TariffResponse.
    :raises TariffNotFound: Если тарифы не найдены.
    """
    tariffs = await TariffsDAO.find_all(session)
    if not tariffs:
        raise TariffNotFound
    return [
        TariffResponse(
            id=tariff.id,
            name=tariff.name,
            limit_users=tariff.limit_users,
            price=tariff.price
        )
        for tariff in tariffs
    ]
