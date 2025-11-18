# Быстрая настройка безопасности

## Шаг 1: Создайте файл .env

Создайте файл `DiaScreen/.env` со следующим содержимым:

```env
SECRET_KEY=django-insecure-)h!-te3)iuvevp_4pg@!dj9g^=k=qzg8#3q#)5^9w8)7@l9qx%
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=DiaScreenRAG
DB_USER=postgres
DB_PASSWORD=deniel9949
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=danissimo228337@gmail.com
EMAIL_HOST_PASSWORD=jftl ntaw iezl ediw
DEFAULT_FROM_EMAIL=DiaScreen <danissimo228337@gmail.com>

RAG_API_URL=http://127.0.0.1:8001/get-response
RAG_PERSONAL_API_URL=http://127.0.0.1:8001/get-response/personalized

SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
```

**ВАЖНО:** После создания `.env` файла, **ОБЯЗАТЕЛЬНО** измените все пароли и секретные ключи!

## Шаг 2: Генерация нового SECRET_KEY

Выполните в терминале:

```bash
cd DiaScreen
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Скопируйте сгенерированный ключ и замените `SECRET_KEY` в файле `.env`.

## Шаг 3: Проверка работы

Запустите сервер:

```bash
python manage.py runserver
```

Проверьте:
- ✅ Приложение запускается без ошибок
- ✅ Логи создаются в папке `DiaScreen/logs/`
- ✅ Rate limiting работает (попробуйте 6 раз неправильно войти)

## Что было улучшено:

1. ✅ **Секреты в переменных окружения** - пароли и ключи не в коде
2. ✅ **Rate limiting** - защита от брутфорса (5 попыток за 15 минут)
3. ✅ **Логирование безопасности** - все попытки входа логируются
4. ✅ **Заголовки безопасности** - защита от XSS, clickjacking и др.
5. ✅ **Защита сессий** - безопасные настройки cookies
6. ✅ **Валидация входных данных** - защита от open redirect
7. ✅ **Логирование доступа** - отслеживание доступа к чувствительным endpoints

## Для продакшена:

1. Установите `DEBUG=False` в `.env`
2. Установите правильные `ALLOWED_HOSTS`
3. Включите HTTPS настройки:
   - `SECURE_SSL_REDIRECT=True`
   - `SESSION_COOKIE_SECURE=True`
   - `CSRF_COOKIE_SECURE=True`
   - `SECURE_HSTS_SECONDS=31536000`

Подробнее см. `SECURITY.md`

