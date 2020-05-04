"""
Utility functions for various operations with units.

GNU General Public License v3.0: See the LICENSE file.
"""


import math
from typing import List, Tuple
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.datasets import units
from AoE2ScenarioParser.datasets.players import Player
import util
import util_scn


# TODO incorporate library updates for managing units.
# TODO don't access _parsed_data directly


def is_unit(unit_name: str) -> bool:
    """Returns True if unit_name is a valid unit name, False otherwise."""
    return unit_name in units.unit_names.inverse


def copy_unit(scn: AoE2Scenario, unit: UnitStruct, player: int) -> UnitStruct:
    """
    Adds a copy of unit to the player's list of units in scenario scn.

    Returns the unit that is added.
    """
    unit_id = util_scn.get_and_inc_unit_id(scn)
    u = scn.object_manager.unit_manager.add_unit(
        player=Player(player),
        x=unit.x,
        y=unit.y,
        z=unit.z,
        unit_id=unit.unit_id,
        rotation=unit.rotation
    )
    set_id(u, unit_id)
    return u


def remove(scn: AoE2Scenario, unit: UnitStruct, p: Player) -> None:
    """
    Removes the unit with reference id uid from the given player in the
    scenario.

    Raises a ValueError if the unit does not exist.
    """
    scn.object_manager.unit_manager.get_player_units(p).remove(unit)


def get_units_array(scn: AoE2Scenario, player: int) -> List[UnitStruct]:
    """
    Returns the array of units in scenario for the given player.

    Raises a ValueError if player is not in 0, ..., 8.
    """
    return scn.object_manager.unit_manager.get_player_units(Player(player))


def units_in_area(unit_array: List[UnitStruct],
                  x1: float, y1: float,
                  x2: float, y2: float) -> List[UnitStruct]:
    """
    Returns all units in the square with left corner (x1, y1)
    and right corner (x2, y2), both corners inclusive.
    """
    return [unit for unit in unit_array
            if x1 <= get_x(unit) <= x2 and y1 <= get_y(unit) <= y2]


def change_player(scn: AoE2Scenario, unit: UnitStruct,
                  pi: Player, pj: Player) -> None:
    """
    Removes a unit from control of player pi and adds an equivalent unit to
    the control of player pj.
    Returns the unit that is added to pj.
    The reference id of the removed unit is maintained in the added unit.

    Raises a ValueError if pi == pj or if unit does not belong to player pi.
    """
    if pi == pj:
        raise ValueError(f'Player numbers must be different, both are {pi}.')
    remove(scn, unit, pi)
    return scn.object_manager.unit_manager.add_unit(
        player=pj,
        x=unit.x,
        y=unit.y,
        z=unit.z,
        rotation=unit.rotation,
        reference_id=unit.reference_id,
        unit_id=unit.unit_id
    )


def get_x(unit: UnitStruct) -> float:
    """Returns the unit's x coordinate."""
    return unit.x


def get_y(unit: UnitStruct) -> float:
    """Returns the unit's y coordinate."""
    return unit.y


def set_x(unit: UnitStruct, x: float):
    """Sets the unit's x coordinate to x."""
    unit.x = x


def set_y(unit: UnitStruct, y: float):
    """Sets the unit's y coordinate to y."""
    unit.y = y


def get_tile(unit: UnitStruct) -> Tuple[int, int]:
    """
    Returns the integer x and y coordinates of the tile on which
    the unit is positioned.
    """
    return (int(get_x(unit)), int(get_y(unit)))


def get_id(unit: UnitStruct) -> int:
    """Returns the unit's id number."""
    return unit.reference_id


def set_id(unit: UnitStruct, unit_id: int) -> None:
    """
    Sets the unit's id number to unit_id.

    Raises a ValueError if unit_id is negative.
    """
    if unit_id < 0:
        raise ValueError(f'unit id {unit_id} may not be negative.')
    unit.reference_id = unit_id


def get_facing(unit: UnitStruct) -> float:
    """Returns the angle (in radians) giving the unit's facing direction."""
    return unit.rotation


def set_facing(unit: UnitStruct, theta: float) -> None:
    """
    Sets unit to face the direction given by the angle theta.

    Raises:
        ValueError if theta does not satisfy 0 <= theta < math.tau.
    """
    if theta < 0.0 or theta >= math.tau:
        raise ValueError(f'theta {theta} is not in [0, tau).')
    unit.rotation = theta


def flip_facing_h(unit: UnitStruct) -> None:
    """Mirrors the unit's facing across a horizontal axis (math.pi / 4.0)."""
    # Mods by tau because the scenario editor seems to place units facing
    # at radian angles not strictly less than tau.
    theta = get_facing(unit) % math.tau
    phi = util.flip_angle_h(theta)
    set_facing(unit, phi)


def get_unit_constant(unit: UnitStruct) -> int:
    """Returns the int unit constant (the unit id in AGE)."""
    return unit.unit_id


def get_name(unit: UnitStruct) -> str:
    """Returns the string name of the unit (e.g. Militia, Archer)."""
    return units.unit_names[get_unit_constant(unit)]


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


def rad_to_facet(theta: float) -> int:
    """
    Returns a Facet value in {0, 1, ..., 15} representing the facing
    of a unit with facing value theta.

    Raises a ValueError if theta is not in the interval [0, 2pi).
    """
    # TODO ok, actually need to figure out how the facets work...
    if theta < 0.0 or theta >= math.tau:
        raise ValueError(f'{theta} is not in [0, 2pi).')
    return (round(16 * theta / math.tau) - 2) % 16


def facet_to_rad(facet: int) -> float:
    """
    Returns the float value in [0, 2pi) representing the radian angle
    at which a unit with the given facet is facing.

    Raises a ValueError if facet is not between 0 and 15, inclusive.
    """
    if facet < 0 or facet > 15:
        raise ValueError(f'{facet} is not between 0 and 15, inclusive.')
    # TODO facets don't correspond to radians like this...
    return facet * math.tau / 16.0
