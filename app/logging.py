import logging

from loguru import logger

from app.config import settings


class InterceptHandler(logging.Handler):
    LEVELS_MAP = {
        logging.CRITICAL: "CRITICAL",
        logging.ERROR: "ERROR",
        logging.WARNING: "WARNING",
        logging.INFO: "INFO",
    }

    def _get_level(self, record):
        return self.LEVELS_MAP.get(record.levelno, record.levelno)

    def emit(self, record):
        logger_opt = logger.opt(depth=8, exception=record.exc_info)
        logger_opt.log(self._get_level(record), record.getMessage())


async def setup():
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG)
    logger.add(settings.PATH_LOGS, rotation="5 MB")
