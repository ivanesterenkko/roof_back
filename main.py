from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache

# from prometheus_fastapi_instrumentator import Instrumentator

from redis import asyncio as aioredis

from app.db import delete_tables, create_tables
from app.users.router import router as user_router
from app.users.payment_router import router as payment_router
from app.users.account_router import router as account_router
from app.projects.router import router as roof_router
from app.base.router import router as base_router

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()

    try:
        redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf8",
            decode_responses=True
        )
        app.state.redis = redis
        FastAPICache.init(RedisBackend(redis), prefix="cache")
    except Exception as e:
        print(f"Error initializing Redis: {e}")
        app.state.redis = None

    yield

    # Закрываем Redis соединение
    if app.state.redis:
        await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

app.include_router(user_router)
app.include_router(roof_router)
app.include_router(base_router)
app.include_router(account_router)
app.include_router(payment_router)

origins = [
    "http://localhost:8001",
    "http://localhost:5173",
    "https://roof-pro.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie",
                   "Access-Control-Allow-Headers",
                   "Access-Control-Allow-Origin", "Authorization"],
)


# Подключаем эндпоинт для сбора метрик
# instrumentator = Instrumentator(
#     should_group_status_codes=False,
#     excluded_handlers=[".*admin.*", "/metrics"]
# )

# instrumentator.instrument(app).expose(app)
