# Сервис по агрегации данных из API для киберспортивных мероприятий

## Инструкция по развертыванию

### 1. Создание .env файла

Создайте в корневой папке проекта файл .env и скопируйте параметры из .env.template в новый файл. Если вы хотите задать свои данные для логина, пароля и имени базы данных, тогда поменяйте соответствующие поля POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, PGPORT и т.д.

## 2. Поднятие docker-compose

В корневой папке проекта (где лежит docker-compose.yml) пропишите

```cli
docker compose up --build
```

### 3. Применить alembic миграции

После поднятия контейнеров, пропишите в консоли, чтобы применить миграции

```cli
docker compose exec app sh -c "uv run alembic upgrade head" 
```

Чтобы откатить миграции пропишите

```cli
docker compose exec app sh -c "uv run alembic downgrade base" 
```
