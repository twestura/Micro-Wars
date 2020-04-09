"""
Utility functions for various operations with units.

GNU General Public License v3.0: See the LICENSE file.
"""


import math
from typing import List, Tuple
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.datasets import units
import util


# Bidirectional map between unit names and ids.
UNIT_IDS = bidict()
for u in units.__dict__:
    if '__' not in u and 'get_unit_id_by_string' not in u:
        UNIT_IDS[u] = units.get_unit_id_by_string(u)


def is_unit(unit_name: str) -> bool:
    """Returns True if unit_name is a valid unit name, False otherwise."""
    return unit_name in UNIT_IDS


def get_units_array(scenario: AoE2Scenario, player: int) -> List[UnitStruct]:
    """
    Returns the array of units in scenario for the given player.

    Raises a ValueError if player is not in 1, ..., 8.
    """
    if player < 1 or player > 8:
        msg = f'Player number {player} is not between 1 and 8 (inclusive).'
        raise ValueError(msg)
    player_units = scenario.parsed_data['UnitsPiece'].retrievers[4].data[player]
    return player_units.retrievers[1].data


def units_in_area(unit_array: List[UnitStruct],
                  x1: float, y1: float,
                  x2: float, y2: float) -> List[UnitStruct]:
    """
    Returns all units in the square with left corner (x1, y1)
    and right corner (x2, y2), both corners inclusive.
    """
    return [unit for unit in unit_array
            if x1 <= get_x(unit) <= x2 and y1 <= get_y(unit) <= y2]


def change_player(scenario: AoE2Scenario,
                  unit_index: int, i: int, j: int) -> None:
    """
    Moves a unit from control of player i to player j.
    unit_index is the original index of the unit to move in the units array
    of player i.

    Raises a ValueError if i == j, if i and j are not valid players
    in the scenario, or if unit_index is not a valid unit index.
    """
    # There is a PlayerUnits struct that has the unit count and the
    # array of units.
    # TODO raise ValueError
    if i == j:
        raise ValueError(f'Player numbers must be different, both are {i}.')
    pi_units = scenario.parsed_data['UnitsPiece'].retrievers[4].data[i]
    pj_units = scenario.parsed_data['UnitsPiece'].retrievers[4].data[j]

    # Changes the array lengths.
    pi_units.retrievers[0].data -= 1
    pj_units.retrievers[0].data += 1

    # Transfers the unit.
    unit = pi_units.retrievers[1].data[unit_index]
    del pi_units.retrievers[1].data[unit_index]
    pj_units.retrievers[1].data.append(unit)


def get_x(unit: UnitStruct) -> float:
    """Returns the unit's x coordinate."""
    return unit.retrievers[0].data


def get_y(unit: UnitStruct) -> float:
    """Returns the unit's y coordinate."""
    return unit.retrievers[1].data


def set_x(unit: UnitStruct, x: float):
    """Sets the unit's x coordinate to x."""
    # TODO handle out of bounds errors
    unit.retrievers[0].data = x


def set_y(unit: UnitStruct, y: float):
    """Sets the unit's y coordinate to y."""
    # TODO handle out of bounds errors
    unit.retrievers[1].data = y


def get_tile(unit: UnitStruct) -> Tuple[int, int]:
    """
    Returns the integer x and y coordinates of the tile on which
    the unit is positioned.
    """
    return (int(get_x(unit)), int(get_y(unit)))


def get_id(unit: UnitStruct) -> int:
    """Returns the unit's id number."""
    return unit.retrievers[3].data


def get_facing(unit: UnitStruct) -> float:
    """Returns the angle (in radians) giving the unit's facing direction."""
    return unit.retrievers[6].data


def set_facing(unit: UnitStruct, theta: float) -> None:
    """
    Sets unit to face the direction given by the angle theta.

    Raises:
        ValueError if theta does not satisfy 0 <= theta < math.tau.
    """
    if theta < 0.0 or theta >= math.tau:
        raise ValueError(f'theta {theta} is not in [0, tau).')
    unit.retrievers[6].data = theta


def flip_facing_h(unit: UnitStruct) -> None:
    """Mirrors the unit's facing across a horizontal axis (math.pi / 4.0)."""
    # Mods by tau because the scenario editor seems to place units facing
    # at radian angles not strictly less than tau.
    theta = get_facing(unit) % math.tau
    phi = util.flip_angle_h(theta)
    set_facing(unit, phi)


def get_name(unit: UnitStruct) -> str:
    """Returns the string name of the unit (e.g. Militia, Archer)."""
    # TODO test
    unit_constant = unit.retrievers[4].data
    return UNIT_IDS.inverse[unit_constant]
