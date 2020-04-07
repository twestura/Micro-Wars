"""
Creates files for the Micro Wars scenario.

GNU General Public License v3.0: See the LICENSE file.
"""


# Notes on coordinates:
# Unit coordinates are stored as float (x, y).
# (0.0, 0.0) is at the left corner of the map.
# x increases from the bottom-left to the top-right. /
# y increases from the top-left to the bottom-right. \
# A tile (x, y) has its left corner at position (x, y), where
# x and y are integers.
# Often triggers need integer values for locations. For example, the Teleport
# Object trigger accepts two integer coordinates and places the unit at the
# left corner of the corresponding tile.

# A Giant-sized map has 240x240 tiles (although there are a few maps
# that are hard-coded to be 255x255, thanks ES).

# Unit angles are given in radians (as a 32-bit float).
# For an approximation, 0.0 is facing Northeast, and the radian values
# increase clockwise.


import argparse
import math
from typing import List
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
import util


# Relative path to the template scenario file.
SCENARIO_TEMPLATE = 'scenario-template.aoe2scenario'


# Relative path to the unit scenario file.
UNIT_TEMPLATE = 'unit-template.aoe2scenario'


# Default output scenario name.
OUTPUT = 'Micro Wars.aoe2scenario'


# Various utility functions to make dealing with units more ergonomic.
def get_units_array(scenario: AoE2Scenario, player: int) -> List[UnitStruct]:
    """
    Returns the array of units in scenario for the given player.

    Raises a ValueError if player is not in 1, ..., 8.
    """
    # TODO figure out how the player number actually is used.
    if player < 1 or player > 8:
        msg = f'Player number {player} is not between 1 and 8 (inclusive).'
        raise ValueError(msg)
    # print(f"parsed data UnitsPiece type: {type(scenario.parsed_data['UnitsPiece'])}")
    player_units = scenario.parsed_data['UnitsPiece'].retrievers[4].data[player]
    # print(type(player_units))
    return player_units.retrievers[1].data


def units_in_area(units: List[UnitStruct],
                  x1: float, y1: float,
                  x2: float, y2: float) -> List[UnitStruct]:
    """Returns all units in the square with corners (x1, y1) and (x2, y2)."""
    return [unit for unit in units
            if x1 <= unit_get_x(unit) <= x2 and y1 <= unit_get_y(unit) <= y2]


# def unit_max_id(scenario: AoE2Scenario) -> int:
    """Returns the maximum id of all units in units, or 0 if units is empty."""
    # scenario.
    # TODO hmm... maybe take the max over all players? Need number of players
    # return max((unit_get_id(unit) for unit in units), default=0)


def unit_get_x(unit: UnitStruct) -> float:
    """Returns the unit's x coordinate."""
    return unit.retrievers[0].data


def unit_get_y(unit: UnitStruct) -> float:
    """Returns the unit's y coordinate."""
    return unit.retrievers[1].data


def unit_set_x(unit: UnitStruct, x: float):
    """Sets the unit's x coordinate to x."""
    # TODO handle out of bounds errors
    unit.retrievers[0].data = x


def unit_set_y(unit: UnitStruct, y: float):
    """Sets the unit's y coordinate to y."""
    # TODO handle out of bounds errors
    unit.retrievers[1].data = y


def unit_get_tile(unit: UnitStruct) -> (int, int):
    """
    Returns the integer x and y coordinates of the tile on which
    the unit is positioned.
    """
    return (int(unit_get_x(unit)), int(unit_get_y(unit)))


def unit_get_id(unit: UnitStruct) -> int:
    """Returns the unit's id number."""
    return unit.retrievers[3].data


def unit_get_facing(unit: UnitStruct) -> float:
    """Returns the angle (in radians) giving the unit's facing direction."""
    return unit.retrievers[6].data


def unit_set_facing(unit: UnitStruct, theta: float) -> None:
    """
    Sets unit to face the direction given by the angle theta.

    Raises:
        ValueError if theta does not satisfy 0 <= theta < math.tau.
    """
    if theta < 0.0 or theta >= math.tau:
        raise ValueError(f'theta {theta} is not in [0, tau).')
    unit.retrievers[6].data = theta


def unit_facing_flip_h(unit: UnitStruct) -> None:
    """Mirrors the unit's facing across a horizontal axis (math.pi / 4.0)."""
    # Mods by tau because the scenario editor seems to place units facing
    # at radian angles not strictly less than tau.
    theta = unit_get_facing(unit) % math.tau
    phi = util.flip_angle_h(theta)
    unit_set_facing(unit, phi)


def unit_get_name(unit: UnitStruct) -> str:
    """Returns the string name of the unit (e.g. Militia, Archer)."""
    unit_constant = unit.retrievers[4].data
    # TODO find out how to use the unit constant to get the name.
    print(unit_constant)
    return ''


# Utility functions for handling terrain.
def map_dimensions(scenario: AoE2Scenario) -> (int, int):
    map_piece = scenario.parsed_data['MapPiece']
    width = map_piece.retrievers[9].data
    height = map_piece.retrievers[10].data
    return width, height


def build_scenario(scenario_template: str = SCENARIO_TEMPLATE,
                   unit_template: str = UNIT_TEMPLATE, output: str = OUTPUT):
    """
    Builds the scenario.

    Parameters:
        scenario_template: The source of the map, players, and scenario
            objectives. The units are copied to this scenario, and triggers
            are added to it.
        unit_template: A template of unit formations to copy for fights.
        output: The output path to which the resulting scenario is written.
    """
    # scenario = AoE2Scenario(scenario_template)
    # object_manager = scenario.object_manager
    # trigger_manager = object_manager.get_trigger_object()
    # print(trigger_manager.get_summary_as_string())

    units_scenario = AoE2Scenario(unit_template)
    # units_obj_manager = units_scenario.object_manager
    p1_template_units = get_units_array(units_scenario, 1)
    # print(f'p1 num_units: {len(p1_template_units)}')
    # for unit in p1_template_units:
    #     unit_id = unit_get_id(unit)
    #     x = unit_get_x(unit)
    #     y = unit_get_y(unit)
    #     theta = unit_get_facing(unit)
    #     print(f'id: {unit_id}, x: {x}, y: {y}, theta: {theta}')
    #     unit_get_name(unit)


    # print(f'max_id: {unit_max_id(p1_template_units)}')
    # print(map_dimensions(units_scenario))

    # scenario.write_to_file(output)


def call_build_scenario(args):
    """Unpacks arguments from command line args and builds the scenario."""
    scenario_map = args.map[0]
    units = args.units[0]
    out = args.output[0]

    # Checks the output path is different from all input paths.
    matches = []
    if out == scenario_map:
        matches.append('map')
    if out == units:
        matches.append('units')
    if matches:
        conflicts = ', '.join(matches)
        msg = f"The output path '{out}' conflicts with: {conflicts}."
        raise ValueError(msg)

    build_scenario(scenario_template=scenario_map, unit_template=units,
                   output=out)


def build_publish_files(args):
    """
    Unpacks arguments from command line args and builds the files needed
    to upload the scenario as a mod.
    """
    raise AssertionError('Not implemented.')


def scratch(args): # pylint: disable=unused-argument
    """
    Runs a simple test experiment.
    """
    output_path = 'scratch.aoe2scenario'
    units_scenario_in = AoE2Scenario(UNIT_TEMPLATE)
    units_scenario_out = AoE2Scenario(UNIT_TEMPLATE)

    p1_template_units_in = get_units_array(units_scenario_in, 1)
    p1_template_units_out = get_units_array(units_scenario_out, 1)
    for unit in units_in_area(p1_template_units_out, 20.0, 0.0, 40.0, 20.0):
        pass
    # for unit, copy in zip(p1_template_units_in, p1_template_units_out):
        # unit_facing_flip_h(unit)
        # unit_set_x(unit, 239.5)
        # unit_set_y(unit, 0.5)
        # unit_set_facing(unit, 0.0)
        # unit_set_x(copy, 239.5)
        # unit_set_y(copy, 0.5)
        # unit_id = unit_get_id(unit)
        # x = unit_get_x(unit)
        # y = unit_get_y(unit)
        # theta = unit_get_facing(unit)
        # print(f'id: {unit_id}, x: {x}, y: {y}, theta: {theta}')
    units_scenario_out.write_to_file(output_path)


def main():
    parser = argparse.ArgumentParser(description='Builds Micro Wars!')
    subparsers = parser.add_subparsers()

    parser_build = subparsers.add_parser('build', help='Builds the scenario.')
    parser_build.add_argument('--map', nargs=1, default=[SCENARIO_TEMPLATE],
                              help='Filepath to the map template input file.')
    parser_build.add_argument('--units', nargs=1, default=[UNIT_TEMPLATE],
                              help='Filepath to the unit template input file.')
    parser_build.add_argument('--output', '-o', nargs=1, default=[OUTPUT],
                              help='Filepath to which the output is written, must differ from all input files.') #pylint: disable=line-too-long
    parser_build.set_defaults(func=call_build_scenario)

    parser_publish = subparsers.add_parser('publish',
                                           help='Creates mod upload files.')
    parser_publish.set_defaults(func=build_publish_files)


    parser_scratch = subparsers.add_parser('scratch', help='Runs a test.')
    parser_scratch.set_defaults(func=scratch)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
