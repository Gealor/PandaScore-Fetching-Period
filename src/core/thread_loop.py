import asyncio
import threading
from typing import Any
from typing import Coroutine


# серебрянная пуля асинхронности и Celery - лучший способ реализовать поддержку асинхронности в Celery
class CeleryEventLoop:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and self._loop.is_running():
            return self._loop

        with self._lock:
            if self._loop is not None and self._loop.is_running():
                return self._loop

            self._loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=self._run_loop,
                args=(self._loop, ),
                name='celery-event-loop',
                daemon=True,
            )
            thread.start()
            return self._loop

    def _run_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def run(self, coro: Coroutine[Any, Any, None]) -> None:
        future = asyncio.run_coroutine_threadsafe(coro, self.get_loop())
        future.result()

celery_event_loop = CeleryEventLoop()
