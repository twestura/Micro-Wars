"""
Represents unit fights for Micro Wars.

GNU General Public License v3.0: See the LICENSE file.
"""

import collections
import json
from typing import Dict, List, Tuple
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
import util_techs
import util_units


# Default filepath from which to load fight data.
DEFAULT_FILE = 'fights.json'


# The maximum number of fights, including the tiebreaker.
FIGHT_LIMIT = 36


# The number of tiles in a fight square.
TILE_WIDTH = 20


# The fight grid consists of FIGHT_GRID_LENGTH x FIGHT_GRID_LENGTH squares.
FIGHT_GRID_LENGTH = 6


# The maximum number of points a fight is worth.
MAX_POINTS = 100


def get_start_tile(index: int) -> Tuple[int, int]:
    """
    Returns the integer (x, y) tile coordinates of the starting tile
    for the fight number index.
    """
    y, x = divmod(index, FIGHT_GRID_LENGTH)
    return x * TILE_WIDTH, y * TILE_WIDTH


class FightData:
    """An instance represents a fight in the middle of the map."""

    def __init__(self, techs: List[str], points: Dict[str, int]):
        """
        Initializes a new FightData object.

        Arguments:
            techs: The names of the technologies researched at the start of
                the fight.
            points: A map from unit name to the number of points killing that
                unit is worth.
        Raises:
            ValueError:
                * An element of techs is not a valid technology name.
                * A key in points is not a valid unit name.
                * A value in points is nonpositive.
        """
        self.techs = techs
        self.points = points
        for tech_name in self.techs:
            if not util_techs.is_tech(tech_name):
                raise ValueError(f'{tech_name} is not a valid tech name.')
        for unit_name, point_value in self.points.items():
            if not util_units.is_unit(unit_name):
                raise ValueError(f'{unit_name} is not a valid unit name.')
            if point_value <= 0:
                msg = f'{unit_name}: {point_value} must have a positive value.'
                raise ValueError(msg)

    def __str__(self):
        return json.dumps({'techs': self.techs, 'points': self.points})

    @staticmethod
    def from_json(s: str):
        """Returns a FightData object that is represented by json string s."""
        loaded = json.loads(s)
        return FightData(loaded['techs'], loaded['points'])


def validate_fights(units_scn: AoE2Scenario, fights: List[FightData]) -> None:
    """
    Raises a ValueError if there is an invalid fight, or if there are too many
    fights.

    The fight at index k is loaded at the kth tile.
    """
    num_fights = len(fights)
    if num_fights > FIGHT_LIMIT:
        msg = f'There are {num_fights} fights, but the limit is {FIGHT_LIMIT}.'
        raise ValueError(msg)

    player_units = {
        1: util_units.get_units_array(units_scn, 1),
        2: util_units.get_units_array(units_scn, 2),
    }

    for index, fight in enumerate(fights):
        for units_array in player_units.values():
            x1, y1 = get_start_tile(index)
            x2, y2 = x1 + TILE_WIDTH, y1 + TILE_WIDTH
            units_in_square = util_units.units_in_area(units_array,
                                                       x1, y1, x2, y2)
            points = 0
            for unit in units_in_square:
                name = util_units.get_name(unit)
                if name not in fight.points:
                    msg = f'{name} is not a unit in fight {index}.'
                    raise ValueError(msg)
                points += fight.points[name]
                if points > MAX_POINTS:
                    msg = f'Fight {index} points {points} > limit {MAX_POINTS}.'
                    raise ValueError(msg)


def load_fight_data(filepath: str = DEFAULT_FILE) -> List[FightData]:
    """
    Parses the fight json at filepath and returns a list of the
    fight information from that file.
    """
    with open(filepath) as json_file:
        loaded = json.loads(json_file.read())
    return [FightData(dct['techs'], dct['points']) for dct in loaded]
