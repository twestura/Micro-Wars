"""
Represents unit fights for Micro Wars.

GNU General Public License v3.0: See the LICENSE file.
"""


import copy
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
            if point_value < 0:
                msg = f'{unit_name}: {point_value} must be nonnegative.'
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
    Represents a fight between players with two groups of units.

    The individual units are positioned in the place where they are teleported
    for the fight to begin.
    """

    def __init__(self, fight_data: FightData,
                 p1_units: List[UnitStruct], p2_units: List[UnitStruct]):
        """
        Initializes a new fight with the fight data and unit lists.

        Raise a ValueError if a player has no units, if the total
        possible point values exceed the max limit, or if there is
        no point value for some unit in the fight.
        """
        self.techs = fight_data.techs
        self.points = fight_data.points
        self.p1_units = p1_units
        self.p2_units = p2_units

        if not self.p1_units:
            raise ValueError('Player 1 has no units.')
        if not self.p2_units:
            raise ValueError('Player 2 has no units.')

        self._p2_bonus = MAX_POINTS
        for unit in self.p1_units:
            name = util_units.get_name(unit)
            if name not in self.points:
                raise ValueError(f'There is no point value for {name}.')
            pts = self.points[name]
            self._p2_bonus -= pts
            if self._p2_bonus < 0:
                msg = f"Player 1's units exceed the point limit {MAX_POINTS}."
                raise ValueError(msg)

        self._p1_bonus = MAX_POINTS
        for unit in self.p2_units:
            name = util_units.get_name(unit)
            if name not in self.points:
                raise ValueError(f'There is no point value for {name}.')
            pts = self.points[name]
            self._p1_bonus -= pts
            if self._p1_bonus < 0:
                msg = f"Player 2's units exceed the point limit {MAX_POINTS}."
                raise ValueError(msg)

    def objectives_description(self) -> str:
        """
        Returns the string used to display the objectives for this fight.
        The objectives include each unit name and the number of points
        the unit is worth, organized from highest to lowest point value.
        """
        return '\n'.join(
            f'* {util.pretty_print_name(name)}: {points}'
            for name, points in sorted(self.points.items(), key=lambda t: -t[1])
        )

    @property
    def p1_bonus(self):
        """
        Returns the number of bonus points Player 1 earns for winning
        this Fight.
        """
        return self._p1_bonus

    @property
    def p2_bonus(self):
        """
        Returns the number of bonus points Player 2 earns for winning
        this Fight.
        """
        return self._p2_bonus


def make_fights(units_scn: AoE2Scenario, fds: List[FightData],
                center_x: int, center_y: int, offset: int) -> List[Fight]:
    """
    Raises a ValueError if there is an invalid fight, or if there are too many
    fights.

    center_x and center_y are the coordinates around which the fight is
    centered.
    offset is the number of tiles away from the center to move the units.

    The fight at index k is loaded at the kth tile in the units_scn.
    """
    num_fights = len(fds)
    if num_fights > FIGHT_LIMIT:
        msg = f'There are {num_fights} fights, but the limit is {FIGHT_LIMIT}.'
        raise ValueError(msg)
    center = (center_x, center_y)

    p1_units_all = util_units.get_units_array(units_scn, 1)
    p2_units_all = util_units.get_units_array(units_scn, 2)

    fights = []
    for index, fd in enumerate(fds):
        x1, y1 = get_start_tile(index)
        x2, y2 = x1 + TILE_WIDTH, y1 + TILE_WIDTH
        p1_units = util_units.units_in_area(p1_units_all, x1, y1, x2, y2)
        if not p1_units:
            raise ValueError(f'Fight {index} has no units.')
        p2_units = util_units.units_in_area(p2_units_all, x1, y1, x2, y2)
        if not p2_units:
            # Symmetrical fight where only 1 player has units.
            # Creates a single, mirrored fight.
            p2_units = [copy.deepcopy(unit) for unit in p1_units]
            util_units.center_units(p1_units, center, offset)
            util_units.center_units_flip(p2_units, center, offset)
            fights.append(Fight(fd, p1_units, p2_units))
        else:
            # Asymmetrical fight where p1 and p2 both have units.
            # Creates two rounds, with players switching units between fights.
            p1_units2 = [copy.deepcopy(unit) for unit in p2_units]
            p2_units2 = [copy.deepcopy(unit) for unit in p1_units]

            util_units.center_units(p1_units, center, offset)
            util_units.center_units(p2_units, center, -offset)
            fights.append(Fight(fd, p1_units, p2_units))

            util_units.center_units_flip(p1_units2, center, -offset)
            util_units.center_units_flip(p2_units2, center, offset)
            fights.append(Fight(fd, p1_units2, p2_units2))
    return fights


def load_fight_data(filepath: str = DEFAULT_FILE) -> List[FightData]:
    """
    Parses the fight json at filepath and returns a list of the
    fight information from that file.
    """
    with open(filepath) as json_file:
        loaded = json.loads(json_file.read())
    return [FightData(dct['techs'], dct['points']) for dct in loaded]
