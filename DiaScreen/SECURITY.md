# Руководство по безопасности DiaScreen

## Критические улучшения безопасности

### 1. Переменные окружения

**ВАЖНО:** Все секретные данные теперь хранятся в файле `.env`, который не должен попадать в git.

Создайте файл `.env` в корне проекта `DiaScreen/` со следующим содержимым:

```env
# Django Settings
SECRET_KEY=ваш-секретный-ключ-здесь
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=DiaScreenRAG
DB_USER=postgres
DB_PASSWORD=ваш-пароль-бд
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-пароль-приложения
DEFAULT_FROM_EMAIL=DiaScreen <ваш-email@gmail.com>

# RAG API
RAG_API_URL=http://127.0.0.1:8001/get-response
RAG_PERSONAL_API_URL=http://127.0.0.1:8001/get-response/personalized

# Security Settings (для продакшена установите True)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
```

### 2. Генерация SECRET_KEY

Для генерации нового SECRET_KEY выполните:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Или используйте онлайн-генератор Django secret key.

### 3. Настройки для продакшена

В файле `.env` для продакшена установите:

```env
DEBUG=False
ALLOWED_HOSTS=ваш-домен.com,www.ваш-домен.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

## Реализованные меры безопасности

### ✅ Защита от утечки секретов
- Все секреты вынесены в переменные окружения
- `.env` файл исключен из git (уже в .gitignore)

### ✅ Заголовки безопасности
- `X-Frame-Options: DENY` - защита от clickjacking
- `X-Content-Type-Options: nosniff` - защита от MIME-sniffing
- `X-XSS-Protection` - защита от XSS
- HSTS (настраивается через переменные окружения)

### ✅ Защита сессий
- `SESSION_COOKIE_HTTPONLY = True` - защита от XSS
- `SESSION_COOKIE_AGE = 86400` - сессия истекает через 24 часа
- `SESSION_SAVE_EVERY_REQUEST = True` - обновление сессии при каждом запросе
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` - истечение при закрытии браузера

### ✅ CSRF защита
- `CSRF_COOKIE_HTTPONLY = True`
- Встроенная защита Django CSRF middleware

### ✅ Rate Limiting
- Защита от брутфорса на `/login/` и `/register/`
- Лимит: 5 попыток за 15 минут с одного IP

### ✅ Логирование безопасности
- Все попытки входа логируются в `logs/security.log`
- Неудачные попытки входа отслеживаются
- Доступ к чувствительным endpoints логируется

### ✅ Валидация паролей
- Минимальная длина пароля
- Проверка на общие пароли
- Проверка на числовые пароли
- Проверка на схожесть с username

### ✅ Защита от SQL Injection
- Django ORM автоматически экранирует запросы
- Использование параметризованных запросов

### ✅ Защита от XSS
- Автоматическое экранирование в шаблонах Django
- `escapeHtml` функция в JavaScript для уведомлений

## Дополнительные рекомендации

### 1. Регулярные обновления
- Регулярно обновляйте Django и зависимости
- Проверяйте уязвимости: `pip list --outdated`
- Используйте `safety check` для проверки уязвимостей

### 2. Резервное копирование
- Настройте автоматическое резервное копирование БД
- Храните резервные копии в безопасном месте

### 3. Мониторинг
- Регулярно проверяйте логи безопасности
- Настройте алерты на подозрительную активность

### 4. HTTPS
- В продакшене обязательно используйте HTTPS
- Получите SSL сертификат (Let's Encrypt бесплатный)

### 5. Двухфакторная аутентификация
- В проекте уже есть `django-two-factor-auth`
- Рекомендуется включить для администраторов

### 6. Ограничение доступа к админке
- Измените URL админки (не `/admin/`)
- Используйте сильные пароли для администраторов
- Ограничьте доступ по IP (через веб-сервер)

## Проверка безопасности

### Перед деплоем проверьте:

1. ✅ `DEBUG = False` в продакшене
2. ✅ `ALLOWED_HOSTS` содержит только ваши домены
3. ✅ Все секреты в `.env`, а не в коде
4. ✅ HTTPS настроен и работает
5. ✅ Логирование работает
6. ✅ Rate limiting активен
7. ✅ Резервное копирование настроено

## Контакты для сообщений о безопасности

Если вы обнаружили уязвимость, пожалуйста, сообщите об этом ответственно.

