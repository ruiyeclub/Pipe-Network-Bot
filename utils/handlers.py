import asyncio
from functools import wraps
from json import JSONDecodeError
from typing import TypeVar, Optional, Callable

from loguru import logger
from models import OperationResult

from core.exceptions.base import APIError

T = TypeVar('T')


def error_handler(*, return_operation_result: bool = False):
    """
    Декоратор для обработки ошибок асинхронных методов
    Args:
        return_operation_result (bool): Возвращать ли OperationResult при ошибке
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except APIError as error:
                self = args[0]
                logger.error(f"Account: {self.account_data.email} | {func.__name__} failed (APIError): {error}")
                if hasattr(self, 'handle_api_error'):
                    await self.handle_api_error(error)

            except JSONDecodeError as error:
                self = args[0]
                logger.error(f"Account: {self.account_data.email} | {func.__name__} failed (JSONDecodeError): {error}")

            except asyncio.TimeoutError:
                self = args[0]
                logger.error(f"Account: {self.account_data.email} | {func.__name__} timeout")
                if hasattr(self, 'handle_timeout'):
                    await self.handle_timeout()

            except Exception as error:
                self = args[0]
                logger.error(f"Account: {self.account_data.email} | {func.__name__} failed (Exception): {error}", exc_info=True)

            if return_operation_result:
                self = args[0]
                return OperationResult(
                    identifier=self.account_data.email,
                    data=getattr(self.account_data, 'password', None),
                    status=False
                )
            return None

        return wrapper
    return decorator

