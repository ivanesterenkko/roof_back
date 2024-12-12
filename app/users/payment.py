from aiohttp import ClientSession
from app.config import settings


def get_cart_order(tariff: dict, duration: int, order_id: str):

    data = {
        "cart": {
            "items": [
                {
                    "productId": rate_id,
                    "quantity": {
                        "count": "1"
                    },
                    "title": rate["name_rate"],
                    "total": str(rate[term_rate])
                }
            ],
            "total": {
                "amount": str(rate[term_rate])
            }
        },
        "currencyCode": "RUB",
        "orderId": order_id,
        "redirectUrls": {
            "onError": "string",
            "onSuccess": settings.REDIRECT_URL + "?" + "order_id=" + order_id
        }
    }

    return data


def get_cart_order_tochka(tariff: dict, duration: int, login: str, name: str):
    if duration == 1:
        count_month_text = "1 месяц"
    elif duration == 1:
        count_month_text = "6 месяцев"
    else:
        count_month_text = "1 год"
    rate_name = rate['name_rate']
    return {
              "Data": {
                "customerCode": "304379782", #company_id?
                "amount": duration,
                "purpose": f"Оплата подписки за использование сервиса FeedbackLab. Тариф - '{rate_name}'. {count_month_text}",
                "redirectUrl": "https://feedbacklab.online",
                "taxSystemCode" : "usn_income",
                "paymentMode": [
                  "sbp",
                  "card"
                ],
                "Client": {
                  "name": name,
                  "email": login,
                #   "phone": phone
                },
                "Items": [
                  {
                   "vatType" : "vat0",
                    "name": f"Подписка за использование сервиса FeedbackLab. Тариф - '{rate_name}'. {count_month_text}",
                    "amount": str(rate[term_rate]),
                    "quantity": 1,
                    "paymentMethod": "full_payment",
                    "paymentObject": "service"
                  }
                ]
              }
            }


class TochkaBankService:

    headers = {
        "Authorization": f"Bearer {settings.API_KEY_TOCHKA}"
    }

    @classmethod
    async def __helper_request(
            cls,
            session: ClientSession,
            method: str,
            url: str,
            params: dict | None,
            headers: dict | None,
            request_body: dict | None
    ):

        if method == "GET":
            response = await session.request(method, url, params=params, headers=headers)
        else:
            response = await session.request(method, url, json=request_body, headers=headers)
        return response

    @classmethod
    async def __make_request(
            cls,
            session: ClientSession,
            method: str,
            url: str,
            params: dict | None,
            headers: dict | None,
            request_body: dict | None
    ):

        response = await cls.__helper_request(
            session,
            method,
            url,
            params,
            headers,
            request_body
        )
        if response.status == 200:
            try:
                data = await response.json()
                return data
            except Exception as ex:
                print(ex, flush=True)
                text = await response.text()
                print(text, flush=True)
                if not text:
                    return None
                raise Exception(f"Can't parse response: {text}")

    @classmethod
    async def create_payment_link(
          cls,
          data: dict,
          session: ClientSession) -> dict:

        url = "https://enter.tochka.com/uapi/acquiring/v1.0/payments_with_receipt"

        data = await cls.__make_request(
            session=session,
            request_body=data,
            headers=cls.headers,
            params=None,
            method="POST",
            url=url
        )
        return data

    @classmethod
    async def get_operation_list(cls,
                                 session: ClientSession,):

        url = "https://enter.tochka.com/uapi/acquiring/v1.0/payments?customerCode=304379782"

        data = await cls.__make_request(
            url=url,
            method="GET",
            params=None,
            request_body=None,
            headers=cls.headers,
            session=session
        )

        # print(data)
        return data

    @classmethod
    async def get_operation_info(cls, operation_id: str, session: ClientSession):

        url = f"https://enter.tochka.com/uapi/acquiring/v1.0/payments/{operation_id}"

        data = await cls.__make_request(
            url=url,
            method="GET",
            params=None,
            request_body=None,
            headers=cls.headers,
            session=session
        )

        return data
