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
# For an approximation, 0.0 is facing North, and the radian values
# increase clockwise.


import argparse
from typing import List
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct


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
    print(f"parsed data UnitsPiece type: {type(scenario.parsed_data['UnitsPiece'])}")
    player_units = scenario.parsed_data['UnitsPiece'].retrievers[4].data[player]
    print(type(player_units))
    return player_units.retrievers[1].data


def unit_get_x(unit: UnitStruct) -> float:
    """Returns the unit's x coordinate."""
    return unit.retrievers[0].data


def unit_get_y(unit: UnitStruct) -> float:
    """Returns the unit's y coordinate."""
    return unit.retrievers[1].data


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
    # p1_template_units = get_units_array(units_scenario, 1)
    # print(f'p1 num_units: {len(p1_template_units)}')
    # for unit in p1_template_units:
    #     unit_id = unit_get_id(unit)
    #     x = unit_get_x(unit)
    #     y = unit_get_y(unit)
    #     theta = unit_get_facing(unit)
    #     print(f'id: {unit_id}, x: {x}, y: {y}, theta: {theta}')
    #     unit_get_name(unit)

    print(map_dimensions(units_scenario))

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


def main():
    parser = argparse.ArgumentParser(description='Builds Micro Wars!')
    subparsers = parser.add_subparsers()
    parser_build = subparsers.add_parser('build', help='Builds the scenario')
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

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
