class IndexErroror(Exception):
    """Список домашних работ пуст"""
    pass


class MessageTelegramError(Exception):
    """Исключение не для пересылки в telegram."""
    pass


class ApiError(Exception):
    """Статус ответа при запросе к API Яндекс Практикум отличается от 200"""
    pass


class AvailabilityError(Exception):
    """Ошибка доступности переменных окружения"""
    pass


class NoMessageToTelegramError (Exception):
    """Ошибка отправки сообщения в телеграмм"""
    pass
