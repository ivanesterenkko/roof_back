from uuid import UUID
from app.projects.dao import LinesDAO
import json


undo_registry = {}
redo_registry = {}

async def add_function_to_undo(request, user_id: str, func_name: str, args: dict, undo_data: dict):
    """
    Добавляет действие в Undo-стек в Redis.

    :param user_id: Идентификатор пользователя.
    :param func_name: Название функции.
    :param args: Аргументы, с которыми функция была вызвана.
    :param undo_data: Данные для отката.
    """
    redis = request.app.state.redis
    undo_key = f"undo_stack:{user_id}"
    redo_key = f"redo_stack:{user_id}"
    
    action = {
        "func_name": func_name,
        "args": {key: str(value) if isinstance(value, UUID) else value for key, value in args.items()},
        "undo_data": {key: str(value) if isinstance(value, UUID) else value for key, value in undo_data.items()},
    }
    
    # Добавляем действие в Undo-стек
    await redis.lpush(undo_key, json.dumps(action))
    
    # Очищаем Redo-стек (новое действие делает redo недействительным)
    await redis.delete(redo_key)


def register_undo(func_name):
    """
    Декоратор для регистрации undo-функций.
    """
    def decorator(func):
        undo_registry[func_name] = func
        return func
    return decorator

def register_redo(func_name):
    """
    Декоратор для регистрации функций в реестре Redo.
    """
    def decorator(func):
        redo_registry[func_name] = func
        return func
    return decorator

async def undo_action(request, user_id: str):
    """
    Выполняет Undo для последнего действия из Redis.

    :param user_id: Идентификатор пользователя.
    :return: Результат выполнения Undo.
    """
    redis = request.app.state.redis
    undo_key = f"undo_stack:{user_id}"
    redo_key = f"redo_stack:{user_id}"
    
    # Извлекаем последнее действие из Undo-стека
    last_action = await redis.lpop(undo_key)
    if not last_action:
        return {"error": "Nothing to undo"}
    
    action = json.loads(last_action)
    func_name = action["func_name"]
    args = action["args"]
    undo_data = action["undo_data"]
    
    # Сохраняем действие в Redo-стек для возможного повторения
    await redis.lpush(redo_key, json.dumps(action))
    
    # Выполняем обратную функцию
    if func_name in undo_registry:
        undo_func = undo_registry[func_name]
        return await undo_func(args, undo_data)
    else:
        return {"error": f"Undo function not found for {func_name}"}

async def redo_action(request, user_id: str):
    """
    Выполняет Redo для последнего отменённого действия из Redis.

    :param user_id: Идентификатор пользователя.
    :return: Результат выполнения Redo.
    """
    redis = request.app.state.redis
    redo_key = f"redo_stack:{user_id}"
    undo_key = f"undo_stack:{user_id}"
    
    # Извлекаем последнее действие из Redo-стека
    last_action = await redis.lpop(redo_key)
    if not last_action:
        return {"error": "Nothing to redo"}
    
    action = json.loads(last_action)
    func_name = action["func_name"]
    args = action["args"]
    undo_data = action["undo_data"]
    
    # Сохраняем действие в Undo-стек для возможности его отмены
    await redis.lpush(undo_key, json.dumps(action))
    
    # Выполняем исходную функцию
    if func_name in redo_registry:
        redo_func = redo_registry[func_name]
        return await redo_func(args, undo_data)
    else:
        return {"error": f"Redo function not found for {func_name}"}


@register_undo("delete_line")
async def undo_delete_line(args, undo_data):
    """
    Откат удаления линии.
    """
    await LinesDAO.add(
        project_id=undo_data["project_id"],
        name=undo_data["line_name"],
        x_start=undo_data["x_start"],
        y_start=undo_data["y_start"],
        x_end=undo_data["x_end"],
        y_end=undo_data["y_end"],
        type=undo_data["line_type"],
        length=undo_data["line_length"],
    )

@register_undo("add_line")
async def undo_add_line(args, undo_data):
    """
    Откат добавления линии.
    """
    await LinesDAO.delete_(model_id=undo_data["line_id"])

@register_undo("update_line")
async def undo_update_line(args, undo_data):
    """
    Откат обновления линии.
    """
    await LinesDAO.update_(
        model_id=undo_data["line_id"],
        x_start=undo_data["x_start"],
        y_start=undo_data["y_start"],
        x_end=undo_data["x_end"],
        y_end=undo_data["y_end"],
        length=undo_data["line_length"]
    )

@register_redo("add_line")
async def redo_add_line(args, undo_data):
    """
    Повторяет действие добавления линии.
    """
    await LinesDAO.add(
        project_id=args["project_id"],
        name=undo_data["line_name"],
        x_start=undo_data["x_start"],
        y_start=undo_data["y_start"],
        x_end=undo_data["x_end"],
        y_end=undo_data["y_end"],
        type=undo_data["line_type"],
        length=undo_data["line_length"],
    )

@register_redo("delete_line")
async def redo_delete_line(args, undo_data):
    """
    Повторяет действие удаления линии.
    """
    await LinesDAO.delete_(model_id=args["line_id"])