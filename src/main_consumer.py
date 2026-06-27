import asyncio

import aio_pika

from src.core.config import settings
from src.core.logger import log

RABBITMQ_URL = settings.rabbitmq.rabbitmq_url
EXCHANGE_NAME = settings.exchange_name
ROUTING_KEY = settings.routing_key
QUEUE_NAME = "test_matches_queue"  # Имя очереди для проверки
OUTPUT_FILE = "consumed_matches.jsonl"


async def main():
    # Подключаемся к RabbitMQ
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()

        # Устанавливаем prefetch count (сколько сообщений забирать за раз)
        # 10 означает, что консьюмер не будет брать больше 10 сообщений, пока не обработает их
        await channel.set_qos(prefetch_count=10)

        # 1. Декларируем Exchange (на случай, если консьюмер запустится раньше продюсера)
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME,
            type=aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        # 2. Создаем очередь, в которую будут падать сообщения
        queue = await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
        )

        # 3. Привязываем очередь к Exchange по routing_key
        await queue.bind(exchange, routing_key=ROUTING_KEY)

        log.info(
            f"[*] Ждем сообщений из очереди '{QUEUE_NAME}'. Для выхода нажмите CTRL+C"
        )
        log.info(f"[*] Данные будут записываться в файл: {OUTPUT_FILE}")

        # 4. Начинаем слушать очередь
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                # Контекстный менеджер process() автоматически отправит ACK (сообщение обработано)
                # при успешном выходе из блока, или NACK, если внутри будет ошибка.
                async with message.process():
                    payload = message.body.decode()
                    # Выводим в консоль короткое превью (первые 100 символов)
                    log.info(f"[x] Получено сообщение: {payload[:100]}...")

                    # Дописываем сообщение в файл
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(payload + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Остановка консьюмера...")
