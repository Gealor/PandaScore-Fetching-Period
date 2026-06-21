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

## Подписка на события матчей (RabbitMQ)

### 1. Узнать данные об очереди и ключ маршрутизации

- Тип обменника: **topic**
- Имя обменника (Exchange Name): **posts_exchange** (лежит в .env файле)
- Ключ маршрутизации(Routing Key): **posts.created** (лежит в .env файле)

### 2. Для подключения вашего сервиса запросите у администратора доступы к RabbitMQ

- AMQP URL:

```url
amqp://<user>:<password>@<host>:<port>/
```

### 3. Сообщения отправляются в формате JSON (тип доставки PERSISTENT). Каждое сообщение содержит подробную информацию о матче:

```json
{
    "external_id": 1547960,
    "external_source": "pandascore",
    "slug": "team-spirit-2026-06-22",
    "status": "running",
    "scheduled_at": "2026-06-21T12:00:00Z",
    "begin_at": "2026-06-21T12:08:42Z",
    "end_at": null,
    "videogame": {
        "id": 34,
        "name": "Mobile Legends: Bang Bang",
        "slug": "mlbb"
    },
    "league": {
        "id": 5304,
        "name": "BetBoom Rise of Legends",
        "slug": "mlbb-betboom-rise-of-legends",
        "image_url": null
    },
    "tournament": {
        "name": "Playoffs",
        "tier": "c",
        "winner_id": null
    },
    "opponents": [
        {
            "type": "Team",
            "opponent": {
                "id": 135142,
                "name": "Team Spirit",
                "acronym": "TS",
                "image_url": "https://cdn-api.pandascore.co/images/team/image/135142/163px_team_spirit_2022_lightmode.png"
            }
        },
        {
            "type": "Team",
            "opponent": {
                "id": 135708,
                "name": "FORZE Esports",
                "acronym": null,
                "image_url": "https://cdn-api.pandascore.co/images/team/image/135708/428px_forze_esports_2023_february_full_darkmode.png"
            }
        }
    ],
    "winner_id": null,
    "results": [
        {
            "team_id": 135142,
            "score": 2
        },
        {
            "team_id": 135708,
            "score": 1
        }
    ],
    "streams_list": [
        {
            "main": true,
            "official": true,
            "raw_url": "https://www.youtube.com/watch?v=JknUl-NiOUM"
        }
    ],
    "modified_at": "2026-06-21T13:57:11Z"
}
```

С моделью данных вы можете ознакомиться в папке **src/schemas/pandascore/match_dto.py**.

### 4. Шаги для реализации на стороне подписчика

Чтобы начать получать сообщения в своем сервисе, выполните следующие шаги в коде вашего консьюмера:

1. Создайте подключение к RabbitMQ и откройте канал.
2. Объявите обменник (Exchange) с именем Exchange Name и типом topic (это действие идемпотентно, оно не перезапишет существующий обменник, но гарантирует, что он существует).
3. Объявите вашу собственную очередь с уникальным именем (например, notification_service_matches). Сделайте её durable=True, чтобы сообщения не терялись при перезапуске брокера.
4. Свяжите (Bind) вашу очередь с обменником, используя Routing Key.
5. Настройте QoS (Prefetch Count), например, в значение 10 или 50, чтобы ваш сервис не захлебнулся при массовом наплыве сообщений.
Запустите цикл прослушивания очереди и не забывайте отправлять ACK (Acknowledgment) после успешной обработки каждого сообщения.
