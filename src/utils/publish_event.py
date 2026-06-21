import aio_pika

from src.core.config import settings
from src.schemas.pandascore.match_dto import MatchPostDTO


async def get_exchange(
    channel: aio_pika.abc.AbstractChannel,
    exchange_name: str,
) -> aio_pika.abc.AbstractExchange:
    return await channel.declare_exchange(
        exchange_name,
        type=aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

async def publish(
    channel: aio_pika.abc.AbstractChannel,
    object: str,
    exchange: aio_pika.abc.AbstractExchange,
    routing_key: str,
) -> None:
    await exchange.publish(
        aio_pika.Message(
            body=object.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=routing_key,
    )


async def publish_match(
    channel: aio_pika.abc.AbstractChannel,
    exchange: aio_pika.abc.AbstractExchange,
    match: MatchPostDTO
) -> None:
    await publish(
        channel=channel,
        object=match.model_dump_json(),
        exchange=exchange,
        routing_key=settings.routing_key
    )