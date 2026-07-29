from collections import defaultdict


class EventBus:
    """Pub/Sub, not classic Observer: subscribers register against an
    arbitrary event-name string (e.g. 'piece_settled', 'game_over'), not
    against a specific subject instance, and emit() fans a payload out to
    every callback registered under that same name. Deliberately kept this
    way - GameState/GameSession/Screen/NetworkSession all need to react to
    named occurrences without holding a reference to "the" one subject
    being observed, and new event names can be added without touching
    existing subscribers."""

    def __init__(self):
        self._subscribers: dict[str, list] = defaultdict(list)

    def subscribe(self, event: str, callback):
        self._subscribers[event].append(callback)

    def emit(self, event: str, **kwargs):
        for cb in self._subscribers[event]:
            cb(**kwargs)
