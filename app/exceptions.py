from fastapi import HTTPException, status


class AutoException(HTTPException):

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = ""

    def __init__(self):

        super().__init__(status_code=self.status_code, detail=self.detail)

class SlopeNotFound(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Скат не найден."

class SheetNotFound(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Лист кровли не найден."

class LineNotFound(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Линия не найдена."

class ProjectNotFound(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Проект не найден."

class ProjectStepLimit(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Превышен лимит шагов в проекте."

class ProjectStepError(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Вы пытаетесь перейти на недопустимый шаг."

class RoofNotFound(AutoException):

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Кровельное покрытие не найдено."


class ProjectAlreadyExists(AutoException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Проект с данным названием уже существует."

class UserAlreadyExistsException(AutoException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь уже существует"


class IncorrectEmailOrPasswordException(AutoException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный логин или пароль"


class TokenExpiredException(AutoException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Срок действия токена истек"


class TokenAbsentException(AutoException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен отсутствует"


class IncorrectTokenFormatException(AutoException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный формат токена"


class UserIsNotPresentException(AutoException):
    status_code = status.HTTP_401_UNAUTHORIZED