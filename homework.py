import logging
import os
import sys
import telegram
from telegram import TelegramError
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
from dotenv import load_dotenv

from exceptions import *

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(lineno)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных для работы программы."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.debug(f'Сообщение в телеграм отправлено: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as error:
        logging.error(f'Ошибка отправки сообщения в телеграм: {error}')
    else:
        logging.info('Сообщение в телеграм успешно отправлено.')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса"""
    logging.info('Проверка на запрос к APi-сервису начата.')
    timestamp = timestamp or int(time.time())
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            raise ApiError(
                'Неверный ответ сервера: '
                f'http_code = {response.status_code}; '
                f'reason = {response.reason}; '
                f'content = {response.text}'
            )
        return response.json()
    except Exception as error:
        message = f'Ошибка подключения к эндпоинту Api-сервиса:{error}'
        raise ApiError(message)


def check_response(response):
    """Проверяет ответ API соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('response должен быть dict')
    if 'homeworks' not in response:
        raise KeyError('Ошибка словаря по ключу homeworks')
    list_homeworks = response.get('homeworks', [])
    if not isinstance(list_homeworks, list):
        raise TypeError('Тип значения "homeworks" не list')
    if not list_homeworks:
        raise IndexError('Получен пустой список домашних работ')
    return list_homeworks


def parse_status(homework):
    """Извлекает из информации статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('В ответе API отсутствует ключ homework_name')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Статус {homework_status} не найден')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = (
            'Отсутствуют обязательные переменные окружения: '
            'TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN '
            'Бот остановлен!'
        )
        logging.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            timestamp = response.get('current_date', int(time.time()))
            if len(homeworks) > 0:
                send_message(bot, parse_status(homeworks[0]))
        except NoMessageToTelegramError as error:
            logging.error(f'Сбой в работе программы: {error}', exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            if last_error != error:
                send_message(bot, message)
                last_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
