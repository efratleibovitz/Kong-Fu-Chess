from collections import defaultdict


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list] = defaultdict(list)

    def subscribe(self, event: str, callback):
        self._subscribers[event].append(callback)

    def emit(self, event: str, **kwargs):
        for cb in self._subscribers[event]:
            cb(**kwargs)
