from queue import Queue

import pytest

from control_signal import SignalCommand, generate_signal
from controller_signaling import HandlerQueueRouter


def test_handler_queue_router_delivers_to_only_the_target_handler() -> None:
    queues = {5: Queue(), 7: Queue()}
    router = HandlerQueueRouter(queues)
    signal = generate_signal(5, SignalCommand.RUN, "--taskid example")

    router.put(signal)

    assert queues[5].get_nowait() == signal
    assert queues[7].empty()


def test_handler_queue_router_rejects_unknown_handler() -> None:
    router = HandlerQueueRouter({5: Queue()})
    signal = generate_signal(7, SignalCommand.RUN, "--taskid example")

    with pytest.raises(ValueError, match="no command queue registered"):
        router.put(signal)
