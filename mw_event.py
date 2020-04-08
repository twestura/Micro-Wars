"""
Represents unit fights or minigames for Micro Wars.

GNU General Public License v3.0: See the LICENSE file.
"""


from abc import ABC, abstractmethod


# TODO abstract class for events
class Event(ABC):
    """An instance represents data for initializing a fight or a minigame."""

    @abstractmethod
    def add_triggers(self, triggers):
        pass # TODO annotate trigger type, specify


# TODO subclass for fights
class Fight(Event):
    """An instance represents a fight in the middle of the map."""
    pass


# TODO subclass for minigames
class MiniGame(Event):
    """An instance represents a minigame on the edge of the map."""
    pass
