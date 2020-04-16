"""
Utility functions for various operations with units.

GNU General Public License v3.0: See the LICENSE file.
"""


import copy
import math
from typing import List, Tuple
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.datasets import units
import util
import util_scn


# TODO incorporate library updates for managing units.


# Bidirectional map between unit names and ids.
UNIT_IDS = bidict()
for _u in units.__dict__:
    if '__' not in _u and 'get_unit_id_by_string' not in _u:
        UNIT_IDS[_u] = units.get_unit_id_by_string(_u)


def is_unit(unit_name: str) -> bool:
    """Returns True if unit_name is a valid unit name, False otherwise."""
    return unit_name in UNIT_IDS


def copy_unit(scn: AoE2Scenario, unit: UnitStruct, player: int) -> UnitStruct:
    """
    Adds a copy of unit to the player's list of units in scenario scn.

    Returns the unit that is added.
    """
    copied_unit = copy.deepcopy(unit)
    unit_id = util_scn.get_and_inc_unit_id(scn)
    set_id(copied_unit, unit_id)
    unit_array = scn.parsed_data['UnitsPiece'].retrievers[4].data[player]
    unit_array.retrievers[0].data += 1
    unit_array.retrievers[1].data.append(copied_unit)
    return copied_unit


def get_units_array(scenario: AoE2Scenario, player: int) -> List[UnitStruct]:
    """
    Returns the array of units in scenario for the given player.

    Raises a ValueError if player is not in 1, ..., 8.
    """
    if player < 1 or player > 8:
        msg = f'Player number {player} is not between 1 and 8 (inclusive).'
        raise ValueError(msg)
    player_units = scenario.parsed_data['UnitsPiece'].retrievers[4].data[player]
    unit_array = player_units.retrievers[1].data
    # Ensures the returned object is a list, even if there is only one unit.
    if not isinstance(player_units.retrievers[1].data, list):
        unit_array = [unit_array]
    return unit_array


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

    Raises a ValueError if i == j.
    """
    if i == j:
        raise ValueError(f'Player numbers must be different, both are {i}.')

    # The a PlayerUnits struct has the unit count and the array of units.
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
    unit.retrievers[0].data = x


def set_y(unit: UnitStruct, y: float):
    """Sets the unit's y coordinate to y."""
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


def set_id(unit: UnitStruct, unit_id: int) -> None:
    """
    Sets the unit's id number to unit_id.

    Raises a ValueError if unit_id is negative.
    """
    if unit_id < 0:
        raise ValueError(f'unit id {unit_id} may not be negative.')
    unit.retrievers[3].data = unit_id


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


def get_unit_constant(unit: UnitStruct) -> int:
    """Returns the int unit constant (the unit id in AGE)."""
    return unit.retrievers[4].data


def get_name(unit: UnitStruct) -> str:
    """Returns the string name of the unit (e.g. Militia, Archer)."""
    return UNIT_IDS.inverse[get_unit_constant(unit)]


def avg_pos(unit_list: List[UnitStruct]) -> Tuple[float, float]:
    """
    Returns the average position of all units in unit_list.

    Raises a ValueError if unit_list is empty.
    """
    if not unit_list:
        raise ValueError(f'unit_list is empty.')
    n = len(unit_list)
    return (sum(get_x(unit) for unit in unit_list) / n,
            sum(get_y(unit) for unit in unit_list) / n)


def center_pos(unit: UnitStruct, avg: Tuple[float, float],
               center: Tuple[float, float], offset: int) -> Tuple[int, int]:
    """
    Returns the position of unit relative to the center, moved up by
    offset tiles, with the unit in a group of units with
    average position avg.
    """
    # Translates to the origin (0, 0),
    # then translates to the new center,
    # then applies the offset.
    x = get_x(unit) - avg[0] + center[0] + offset
    y = get_y(unit) - avg[1] + center[1] - offset
    return (int(x), int(y))


def center_pos_flipped(unit: UnitStruct, avg: Tuple[float, float],
                       center: Tuple[float, float],
                       offset: int) -> Tuple[int, int]:
    """
    Returns the position of the unit relative to the center, moved down
    by offset tiles, with the unit in a group of units with average
    position avg. Performs a reflection about the horizontal axis of
    the unit's position relative to the group's average position.
    """
    # Translates to the origin (0, 0).
    x = get_x(unit) - avg[0]
    y = get_y(unit) - avg[1]
    # Flips position across the horizontal axis.
    x, y = y, x
    # Translates to the center and applies the offset.
    x += center[0] - offset
    y += center[1] + offset
    return (int(x), int(y))


def center_units(unit_array: List[UnitStruct], center: Tuple[float, float],
                 offset: int) -> None:
    """Centers the units in unit_array with distance offset from the center."""
    avg = avg_pos(unit_array)
    for unit in unit_array:
        new_pos = center_pos(unit, avg, center, offset)
        set_x(unit, new_pos[0])
        set_y(unit, new_pos[1])


def center_units_flip(unit_array: List[UnitStruct], center: Tuple[float, float],
                      offset: int) -> None:
    """
    Centers and flips the units in unit_array with distance offset
    from the center.
    """
    avg = avg_pos(unit_array)
    for unit in unit_array:
        flip_facing_h(unit)
        new_pos = center_pos_flipped(unit, avg, center, offset)
        set_x(unit, new_pos[0])
        set_y(unit, new_pos[1])
