# Task Management API

Учебный сервис управления задачами на Python 3.11+, FastAPI и PostgreSQL. Пользователь управляет своими задачами. Администратор видит все задачи и может менять роли пользователей.

## Запуск

Из корня проекта, при запущенном Docker с Compose v2:

```bash
docker-compose up -d
# Если Compose установлен как плагин Docker:
docker compose up -d
```

| Компонент | Адрес |
| --- | --- |
| Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Проверка доступности API и БД | [http://localhost:8000/healthz](http://localhost:8000/healthz) |
| Почтовый ящик Mailpit | [http://localhost:8025](http://localhost:8025) |
| PostgreSQL | `db:5432` внутри сети Compose |

При запуске Compose собирает образ приложения. Контейнер `migrate` применяет миграции Alembic до запуска API. Для остановки используйте `docker compose down`. Данные PostgreSQL хранятся в томе `postgres-data`. После изменений в коде используйте `docker compose up -d --build`.

Настройки из [.env.example](.env.example) можно скопировать в `.env`. По умолчанию при старте API создаёт случайный ключ JWT. Чтобы токены оставались действительными после перезапуска, задайте `JWT_SECRET` с помощью `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Если меняете `POSTGRES_PASSWORD` для новой БД, укажите тот же пароль в `DATABASE_URL`, экранировав специальные символы по правилам URL.

## Права доступа

| Метод | Путь | Доступ |
| --- | --- | --- |
| POST | `/auth/register` | Публичный. Новая учётная запись получает роль `USER` |
| POST | `/auth/login` | Публичный. Принимает форму OAuth2 или JSON, возвращает `access_token` |
| GET | `/auth/profile` | Профиль пользователя, которому выдан токен |
| GET, POST | `/tasks` | `USER` видит свои задачи, `ADMIN` видит все. Новая задача принадлежит создателю |
| GET, PUT, DELETE | `/tasks/{task_id}` | Владелец задачи или `ADMIN` |
| GET | `/admin/users` | Только `ADMIN` |
| PUT | `/admin/users/{user_id}/role` | Только `ADMIN` |

JWT передаётся в заголовке `Authorization: Bearer <token>` и по умолчанию действует 30 минут. Роль проверяется в базе при каждом запросе, поэтому изменение роли действует и для ранее выданного токена. Пароли хешируются через bcrypt с помощью `CryptContext`. Зависимость `libpass` предоставляет совместимый API Passlib. Минимум 8 символов, максимум 72 байта в UTF-8.

Для назначения первого администратора зарегистрируйте его через API и выполните команду в своём экземпляре Compose:

```bash
docker compose exec api python -m src.cli grant-admin admin@example.com
```

## Примеры запросов

Примеры используют Bash, `curl` и `jq`.

```bash
API=http://localhost:8000

curl -fsS "$API/auth/register" -H 'Content-Type: application/json' \
  -d '{"email":"student@example.com","password":"secure123","name":"Иван Иванов"}'

TOKEN="$(curl -fsS "$API/auth/login" \
  --data-urlencode 'username=student@example.com' \
  --data-urlencode 'password=secure123' | jq -er '.access_token')"
AUTH="Authorization: Bearer $TOKEN"

curl -fsS "$API/auth/profile" -H "$AUTH"

TASK_ID="$(curl -fsS "$API/tasks" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"Разработать API","description":"Добавить CRUD","priority":"high","deadline":"2026-12-01T18:00:00Z"}' | jq -er '.id')"

curl -fsS "$API/tasks?status=pending&priority=high&limit=10&offset=0" -H "$AUTH"
curl -fsS "$API/tasks/$TASK_ID" -H "$AUTH"
curl -fsS -X PUT "$API/tasks/$TASK_ID" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"status":"in_progress"}'
curl -fsS -X DELETE "$API/tasks/$TASK_ID" -H "$AUTH"
```

В Swagger UI нажмите **Authorize** и введите email в поле `username` и пароль в поле `password`. Swagger получит JWT через OAuth2 Password Flow. Эндпоинт `POST /auth/login` также принимает JSON с полями `email` и `password`.

- Регистрация и создание задачи возвращают `200 OK`, удаление — `204 No Content`. Недействительный токен даёт `401`, запрос к админ-эндпоинту с ролью `USER` — `403`. Чужая или отсутствующая задача возвращает `404`. Повторная регистрация того же email возвращает `409`, а некорректные входные данные — `422`.
- Список задач отсортирован по `id` и поддерживает фильтры `status` и `priority`. Значения по умолчанию для пагинации — `offset=0` и `limit=20`. Максимальный `limit` — 100.
- Статусы задач — `pending`, `in_progress`, `done`. Приоритеты — `low`, `medium`, `high`. По умолчанию новая задача получает `pending` и `medium`.
- `PUT` меняет переданные поля. `description` и `deadline` можно очистить значением `null`. Дедлайн без часового пояса интерпретируется как UTC.
- После сохранения новой задачи FastAPI запускает отправку письма через SMTP в фоновом режиме. В локальной конфигурации письмо видно в Mailpit. При сбое SMTP задача остаётся в базе, а ошибка записывается в журнал. В MVP отправка выполняется без повторных попыток.

Для работы с ролями войдите под администратором и подставьте его токен и ID пользователя:

```bash
curl -fsS "$API/admin/users" -H "Authorization: Bearer $ADMIN_TOKEN"
curl -fsS -X PUT "$API/admin/users/$USER_ID/role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"role":"ADMIN"}'
```

## Тесты и CI

При запущенном Docker выполните из корня проекта:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest tests/
```

Testcontainers поднимает изолированный PostgreSQL 16. Перед тестами применяется миграция Alembic и проверяется соответствие схемы моделям. Тесты используют `httpx.AsyncClient` и проверяют регистрацию и вход, CRUD, фильтрацию, RBAC, ошибки и формирование письма. Предупреждения pytest считаются ошибками. GitHub Actions на `push` и `pull_request` устанавливает зависимости из `requirements.txt`, запускает тесты, выполняет `docker-compose up -d` и проверяет API и получение письма в Mailpit.

## Архитектура

- `src/api` содержит маршруты, зависимости FastAPI и схемы Pydantic. Зависимости образуют цепочку `get_session → get_uow → get_user_service/get_task_service`. Маршруты вызывают методы сервисов.
- `src/services` содержит классы `UserService` и `TaskService`. Каждый сервис получает `UnitOfWork` через конструктор. Сценарии выполняются внутри `async with self.uow`.
- `src/repositories` выполняет запросы к PostgreSQL через асинхронный SQLAlchemy 2.0.
- `src/utils/unit_of_work.py` получает `AsyncSession` и объединяет репозитории `users` и `tasks`. При успешном выходе из контекста он выполняет `commit`, а при исключении — `rollback`. Сессия закрывается в `finally`. Репозитории выполняют запросы и `flush`, а транзакцией управляет UoW.
- `src/models` содержит модели ORM, `alembic` — версионируемые миграции.
