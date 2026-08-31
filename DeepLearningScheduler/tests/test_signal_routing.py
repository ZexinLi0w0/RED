import asyncio

import pytest

from handler_signaling import (
    FOREIGN_SIGNAL_REQUEUE_BACKOFF_SECONDS,
    _requeue_foreign_signal,
)


class RecordingQueue:
    def __init__(self):
        self.messages = []

    def put(self, message):
        self.messages.append(message)


def test_foreign_signal_requeue_yields_to_the_addressed_consumer(monkeypatch):
    queue = RecordingQueue()
    observed_sleeps = []

    async def record_sleep(seconds):
        observed_sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", record_sleep)

    asyncio.run(_requeue_foreign_signal(queue, "controller-reply"))

    assert queue.messages == ["controller-reply"]
    assert observed_sleeps == [FOREIGN_SIGNAL_REQUEUE_BACKOFF_SECONDS]
    assert FOREIGN_SIGNAL_REQUEUE_BACKOFF_SECONDS > 0
