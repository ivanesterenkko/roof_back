from fastapi import APIRouter, Depends
from pydantic import UUID4
from app.base.dao import Accessory_baseDAO, RoofsDAO, TariffsDAO
from app.base.schemas import (AccessoryBDRequest, AccessoryBDResponse, RoofRequest, RoofResponse,
                              TariffRequest, TariffResponse)
from app.exceptions import RoofNotFound, TariffNotFound
from app.users.dependencies import get_current_user
from app.users.models import Users

router = APIRouter(prefix="/base", tags=["Base"])


@router.post("/roofs_base", description="Добавление покрытия в библиотеку")
async def add_roof_base(
      roof: RoofRequest,
      user: Users = Depends(get_current_user)
      ) -> None:
    roof = await RoofsDAO.add(
        name=roof.name,
        type=roof.type,
        overall_width=roof.overall_width,
        useful_width=roof.useful_width,
        overlap=roof.overlap,
        max_length=roof.max_length,
        min_length=roof.min_length
        )
    return {"roof_id": roof.id}


@router.get("/roofs_base", description="Получение покрытий из библиотеки")
async def get_roof_base(
      user: Users = Depends(get_current_user)
      ) -> list[RoofResponse]:
    results = await RoofsDAO.find_all()
    if not results:
        raise RoofNotFound
    return [
        RoofResponse(
            id=result.id,
            name=result.name,
            type=result.type,
            overall_width=result.overall_width,
            useful_width=result.useful_width,
            overlap=result.overlap,
            max_length=result.max_length,
            min_length=result.min_length
            ) for result in results]


@router.delete("/roofs_base", description="Удаление покрытия из библиотеки")
async def delete_roof_base(
      roof_id: UUID4,
      user: Users = Depends(get_current_user)) -> None:
    await RoofsDAO.delete_(model_id=roof_id)


@router.post("/accessories_base", description="Добавление доборного в библиотеку")
async def add_accessories_base(
      accessory: AccessoryBDRequest,
      user: Users = Depends(get_current_user)
      ) -> None:
    accessory = await Accessory_baseDAO.add(
        name=accessory.name,
        type=accessory.type,
        parent_type=accessory.parent_type,
        price=accessory.price,
        overlap=accessory.overlap,
        length=accessory.length
        )
    return {"accessory_id": accessory.id}


@router.get("/accessories_base", description="Получение доборных из библиотеки")
async def get_accessories_base(
      user: Users = Depends(get_current_user)
      ) -> list[AccessoryBDResponse]:
    results = await Accessory_baseDAO.find_all()
    if not results:
        raise RoofNotFound
    return [
        AccessoryBDResponse(
            id=result.id,
            name=result.name,
            type=result.type,
            parent_type=result.parent_type,
            price=result.price,
            overlap=result.overlap,
            length=result.length
            ) for result in results]


@router.delete("/accessories_base", description="Удаление доборного из библиотеки")
async def delete_accessories_base(
      roof_id: UUID4,
      user: Users = Depends(get_current_user)) -> None:
    await Accessory_baseDAO.delete_(model_id=roof_id)


@router.post("/tariff", description="Добавление тарифа в библиотеку")
async def add_tariff(
      data: TariffRequest,
      user: Users = Depends(get_current_user)
      ) -> TariffResponse:
    tariff = await TariffsDAO.add(
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
      user: Users = Depends(get_current_user)
      ) -> list[TariffResponse]:
    tariffs = await TariffsDAO.find_all()
    if not tariffs:
        raise TariffNotFound
    return [
        TariffResponse(
            id=tariff.id,
            name=tariff.name,
            limit_users=tariff.limit_users,
            price=tariff.price
        ) for tariff in tariffs
    ]
