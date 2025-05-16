from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.dao import TariffsDAO
from app.exceptions import OrderNotFound
# from app.users.payment import TochkaBankService, get_cart_order_tochka
from ..projects.dao import ProjectsDAO
from .auth import get_password_hash
from .dao import CompanyDAO, OrdersDAO, SubscriptionDAO, UsersDAO
from .dependencies import get_current_user, get_session
from .models import Users
from .schemas import OrderRequest, OrderResponse, SubscriptionResponse


router = APIRouter(prefix="/payment", tags=["Payment"])


@router.post("/order", description="Получение ссылки на оплату")
async def create_order(
      order_data: OrderRequest,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> OrderResponse:
    tariff = await TariffsDAO.find_by_id(session, order_data.tariff_id)
    subscription = await SubscriptionDAO.add(
        session,
        tariff_id=tariff.id,
        company_id=user.company_id
    )
        # cart_order = get_cart_order_tochka(
    #     tariff=tariff,
    #     duration=order_data.duration,
    #     login=user.login,
    #     name=user.name
    #     )

    # data_payment = await TochkaBankService.create_payment_link(
    #     data=cart_order,
    #     session=HttpClient.get_session()
    # )
    # print(data_payment)
    new_order = await OrdersDAO.add(
        session,
        subscription_id=subscription.id,
        is_paid=False,
        duration=order_data.duration
    )
    
    return OrderResponse(
        id=new_order.id,
        subscription_id=new_order.subscription_id,
        duration=new_order.duration,
        is_paid=new_order.is_paid
    )


@router.post("/successful_payment_card")
async def successful_payment(
        order_id: UUID4,
        session: AsyncSession = Depends(get_session)
) -> SubscriptionResponse:
    order = await OrdersDAO.find_by_id(session, order_id)
    if not order:
        raise OrderNotFound

    order = await OrdersDAO.update_(
        session,
        model_id=order_id,
        is_paid=True
    )

    expired_at = datetime.utcnow() + timedelta(days=30 * order.duration)

    subscription = await SubscriptionDAO.update_(
        session,
        model_id=order.subscription_id,
        expired_at=expired_at
    )

    return SubscriptionResponse(
        id=subscription.id,
        expired_at=subscription.expired_at,
        tariff_id=subscription.tariff_id,
        company_id=subscription.company_id
    )


# @router.post("/successful_payment_sbp")
# @version(2)
# async def successful_payment_sbp(
#         transaction_id: str
# ):
#     print("Ручка на оплату", flush=True)
#     orders: list[Orders] = await OrdersDAO.find_all(is_paid=False)
#     print(orders, flush=True)
#     finish = False
#     for order in orders:
#         if finish:
#             break
#         operation_id = order.uuid_order

#         operation = await TochkaBankService.get_operation_info(
#             operation_id=operation_id,
#             session=HttpClient.get_session()
#         )
#         # print(operation, flush=True)
#         if operation is None:
#             continue
#         operation = operation["Data"]["Operation"][0]
#         print(operation, flush=True)

#         if operation.get("transactionId"):

#             if operation["transactionId"] == transaction_id:
#                 finish = True
#                 print(f"Нашёл заказ с transactionId | {transaction_id}", flush=True)

#                 school: Schools = await SchoolsDAO.find_by_id(
#                     id_school=order.school_id
#                 )

#                 if school:
#                     term_rate = order.term_rate

#                     datetime_now = datetime.now(pytz.timezone("Europe/Moscow"))

#                     expire_rate = datetime_now + timedelta(days=30 * term_rate)
#                     print(expire_rate)

#                     await SchoolsDAO.update(
#                         id_model=school.id_school,
#                         name_subscription=order.rate_name,
#                         subscription_date_end=expire_rate.date()
#                     )

#                     await OrdersDAO.update(
#                         id_model=order.order_id,
#                         is_paid=True
#                     )
#                     print(f"Обновил тариф у школы: {school.id_school}", flush=True)
#                     break
#     if not finish:
#         print("Нет операции", flush=True)
#         raise HTTPException(status_code=404)




# @router.post("/successful_payment")
# async def successful_payment(
#         transaction_id: str
# ):
#     print("успешная оплата", flush=True)
#     print(transaction_id, flush=True)
#     operation_list = await TochkaBankService.get_operation_list(session=HttpClient.get_session())
#     for operation in operation_list["Data"]["Operation"]:
#         print(operation, flush=True)
#         if operation["transactionId"] == transaction_id:
#             print("Нашёл нужную транзакцию", flush=True)
#             operation_id = operation["operationId"]

#             order = await OrdersDAO.find_by_id(uuid_order=operation_id)

#             if order:

#                 school: Schools = await SchoolsDAO.find_by_id(
#                     id_school=order.school_id
#                 )

#                 if school:
#                     term_rate = order.term_rate

#                     datetime_now = datetime.now(pytz.timezone("Europe/Moscow"))

#                     expire_rate = datetime_now + timedelta(days=30 * term_rate)
#                     print(expire_rate)

#                     await SchoolsDAO.update(
#                         id_model=school.id_school,
#                         name_subscription=order.rate_name,
#                         subscription_date_end=expire_rate.date()
#                     )

#                     await OrdersDAO.update(
#                         id_model=order.order_id,
#                         is_paid=True
#                     )
#                     print(f"Обновил тариф у школы: {school.id_school}", flush=True)
#                     break




# # @router.post("/order", description="Получение ссылки на оплату")
# # @version(2)
# # async def create_order(
# #         order_data: SOrderCreate,
# #         user: SchoolUsers = Depends(get_current_user)
# # ):
# #
# #     rate_id = order_data.rate_id
# #     term_rate = order_data.term_rate
# #     uuid_order = str(uuid.uuid4())
# #     print(uuid_order)
# #
# #     if term_rate == "one_month":
# #         count_month = 1
# #     elif term_rate == "six_month":
# #         count_month = 6
# #     else:
# #         count_month = 12
# #
# #     rate = rates[rate_id]
# #
# #     now_datetime = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%Y-%m-%d %H:%M")
# #     now_datetime = datetime.strptime(now_datetime, "%Y-%m-%d %H:%M")
# #     price_rate = rate[term_rate]
# #
# #     new_order: Orders = await OrdersDAO.add(
# #         school_id=user.id_school,
# #         datetime_order=now_datetime,
# #         is_paid=False,
# #         rate_name=rate["name_rate"],
# #         term_rate=count_month,
# #         price_rate=int(price_rate),
# #         uuid_order=uuid_order
# #     )
# #     print(new_order)
# #
# #     cart_order = get_cart_order(
# #         rate=rate,
# #         rate_id=str(rate_id),
# #         term_rate=term_rate,
# #         order_id=uuid_order
# #     )
# #     print(cart_order)
# #     yandex_pay_data = YandexPayService.create_link_payment(
# #         data=cart_order
# #     )
# #     print(yandex_pay_data, flush=True)
# #     if yandex_pay_data:
# #         return {
# #             "payment_url": yandex_pay_data["data"]["paymentUrl"]
# #         }
# #     else:
# #         return None


# @router.get("/successful_pay", description="Обработка успешного платежа", response_class=HTMLResponse)
# @version(2)
# async def successful_payment(
#         order_id: str,
#         request: Request
# ):

#     order: Orders = await OrdersDAO.find_by_id(
#         uuid_order=order_id
#     )
#     print(order)
#     status_order = YandexPayService.get_status_payment(
#         order_id=order_id
#     )
#     print(status_order, flush=True)
#     if status_order:

#         status_payment = status_order['data']['order']['paymentStatus']

#         if status_payment == StatusPayment.SUCCESS:

#             school: Schools = await SchoolsDAO.find_by_id(
#                 id_school=order.school_id
#             )

#             if school:

#                 term_rate = order.term_rate

#                 datetime_now = datetime.now(pytz.timezone("Europe/Moscow"))

#                 expire_rate = datetime_now + timedelta(days=30 * term_rate)
#                 print(expire_rate)

#                 await SchoolsDAO.update(
#                     id_model=school.id_school,
#                     name_subscription=order.rate_name,
#                     subscription_date_end=expire_rate.date()
#                 )

#                 await OrdersDAO.update(
#                     id_model=order.order_id,
#                     is_paid=True
#                 )

#                 return """
#                 <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <title>Title</title>
# </head>
# <body>
#     <h1>Оплата прошла успешно.</h1>
#     <p>Перейдите на <a href='https://feedbacklab.online'>главную страницу</a></p>
# </body>
# </html>"""


# @router.post("/v1/webhook")
# async def webhook(request: Request):
#     """Обработка webhook-уведомлений от платежного сервиса.

#     :param request: Запрос FastAPI.
#     :return: Ответ с кодом 200 для подтверждения получения уведомления.
#     """
#     # Получение данных из запроса
#     data = await request.json()
#     print(data, flush=True)
#     logging.info(f'Получено webhook-уведомление: {json.dumps(data, indent=4)}')

#     # Обработка данных уведомления
#     # ... ваш код обработки уведомлений ...

#     # Отправка ответа для подтверждения получения уведомления
#     return JSONResponse({'status': 'ok'})
