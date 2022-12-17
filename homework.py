import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

from dotenv import load_dotenv
import requests
import telegram

from exceptions import DateStampError, WrongResponseCodeError

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
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения в телеграм: {error}')
    else:
        logging.debug('Сообщение в телеграм успешно отправлено.')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseCodeError(
                'Неверный ответ сервера: '
                f'http_code = {response.status_code};'
                f'reason = {response.reason};'
                f'content = {response.text}'
            )
        return response.json()
    except requests.exceptions.RequestException as error:
        message = f'Ошибка подключения к эндпоинту Api-сервиса:{error}'
        raise WrongResponseCodeError(message)


def check_response(response):
    """Проверяет ответ API соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('response должен быть dict')
    if 'homeworks' not in response:
        raise KeyError('Ошибка словаря по ключу homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Тип значения "homeworks" не list')
    if 'current_date' not in response:
        raise DateStampError('Ключ "current_date" отсутствует в словаре')
    if not isinstance(response['current_date'], int):
        raise DateStampError('Ключ "current_date" не того типа')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('В ответе API отсутствует ключ homework_name')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Статус {homework_status} не найден')
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
            if homeworks:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                if last_error != message:
                    send_message(bot, message)
                    last_error = message
            else:
                logging.debug('Статус домашки не изменился')
            timestamp = response.get('current_date')
        except DateStampError as error:
            logging.error(
                f'Дата последней проверки изменений некорректна: {error}'
            )
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            if last_error != message:
                send_message(bot, message)
                last_error = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
