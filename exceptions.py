class IndexError(Exception):
    """Список домашних работ пуст"""
    pass


class MessageError(Exception):
    """Исключение не для пересылки в telegram."""
    pass


class WrongResponseCodeError(Exception):
    """Статус ответа при запросе к API Яндекс Практикум отличается от 200"""
    pass


class AvailabilityError(Exception):
    """Ошибка доступности переменных окружения"""
    pass


class NoMessageError(Exception):
    """Ошибка отправки сообщения в телеграмм"""
    pass
