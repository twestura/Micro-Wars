"""
Represents unit fights for Micro Wars.

GNU General Public License v3.0: See the LICENSE file.
"""


import json
from enum import Enum
from typing import Dict, List, Tuple
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
import util
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


class FightType(Enum):
    """Represents whether a fight is symmetrical or asymmetrical."""
    sym = 0
    asym = 1


class Fight:
    """
    Represents either a symmetrical fight with one unit source player
    or an asymmetrical fight with two unit source players.

    A symmetrical fight consists of a single round where each player's units
    mirrors the other's units.
    An asymmetrical fight consists of two rounds where each player has
    a different army composition. After the first round, the players
    swap armies.
    """

    def __init__(self,
                 fight_data: FightData,
                 player_units: Dict[int, List[UnitStruct]]):
        """
        Initializes a new fight with the fight data and unit lists.

        Raise a ValueError if the point values exceed the max limit
        or if there is no point value for some unit in the fight.
        """
        self.techs = fight_data.techs
        self.points = fight_data.points
        # self.player_units[k] is the list of units for player k.
        # If self.player_units[2] is empty, the fight is symmetrical.
        # Otherwise the fight is asymmetrical.
        self.player_units = player_units
        if not player_units[1]:
            raise ValueError(f'This fight has no units.')

    @property
    def fight_type(self):
        """Returns whether this fight is symmetrical or asymmetrical."""
        return FightType.asym if self.player_units[2] else FightType.sym

    def objectives_description(self) -> str:
        """
        Returns the string used to display the objectives for this fight.
        The objectives include each unit name and the number of points
        the unit is worth, organized from highest to lowest point value.
        """
        str_components = [
            f'* {util.pretty_print_name(name)}: {points}'
            for name, points in sorted(self.points.items(), key=lambda t: -t[1])
        ]
        return '\n'.join(str_components)


def make_fights(units_scn: AoE2Scenario, fd: List[FightData]) -> List[Fight]:
    """
    Raises a ValueError if there is an invalid fight, or if there are too many
    fights.

    The fight at index k is loaded at the kth tile in the units_scn.
    """
    num_fights = len(fd)
    if num_fights > FIGHT_LIMIT:
        msg = f'There are {num_fights} fights, but the limit is {FIGHT_LIMIT}.'
        raise ValueError(msg)

    overall_units = {
        1: util_units.get_units_array(units_scn, 1),
        2: util_units.get_units_array(units_scn, 2),
    }

    fights = []
    for index, fight in enumerate(fd):
        x1, y1 = get_start_tile(index)
        x2, y2 = x1 + TILE_WIDTH, y1 + TILE_WIDTH
        fight_units = {
            1: util_units.units_in_area(overall_units[1], x1, y1, x2, y2),
            2: util_units.units_in_area(overall_units[2], x1, y1, x2, y2),
        }
        if not fight_units[1]:
            raise ValueError(f'Fight {index} has no units.')
        for units_in_square in fight_units.values():
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
        fights.append(Fight(fight, overall_units))
    return fights


# TODO instead of just validation, let's create actual fight objects
# These objects can then be processed to add the triggers by the scenario.

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
