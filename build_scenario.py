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
from enum import Enum
from typing import List
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.pieces.structs.variable_change import VariableChangeStruct # pylint: disable=line-too-long
from AoE2ScenarioParser.datasets import conditions, effects, techs, units
import util


# Relative path to the template scenario file.
SCENARIO_TEMPLATE = 'scenario-template.aoe2scenario'


# Relative path to the unit scenario file.
UNIT_TEMPLATE = 'unit-template.aoe2scenario'


# Default output scenario name.
OUTPUT = 'Micro Wars.aoe2scenario'


# Bidirectional map between unit names and ids.
UNIT_IDS = bidict()
for x in units.__dict__:
    if '__' not in x and 'get_unit_id_by_string' not in x:
        UNIT_IDS[x] = units.get_unit_id_by_string(x)


# Bidirectional map between technology names and ids.
TECH_IDS = bidict()
for x in techs.__dict__:
    if '__' not in x and 'get_tech_id_by_string' not in x:
        TECH_IDS[x] = techs.get_tech_id_by_string(x)


# The number of scenario editor variables.
NUM_VARIABLES = 256


# Initial variables for keeping track of player scores and round progress,
# stored as (variable-name, initial-value) pairs.
INITIAL_VARIABLES = [
    ('p1-score', 0),
    ('p2-score', 0),
    ('score-difference', 0),
    ('p1-wins', 0),
    ('p2-wins', 0),
    ('round', 0),
]


# The number of seconds to wait between rounds.
BETWEEN_ROUND_DELAY = 5


# X coordinate of the player's starting view.
START_VIEW_X = 120


# Y coordinate of the player's starting view.
START_VIEW_Y = 119


class ChangeVarOp(Enum):
    """Represents the value for the operation of a Change Variable Effect."""
    set_op = 1
    add = 2
    subtract = 3
    multiply = 4
    divide = 5


class VarValComp(Enum):
    """Represents the value for the comparison of a Variable Value Condition."""
    equal = 1
    less = 2
    larger = 3
    less_or_equal = 4
    larger_or_equal = 5


def add_trigger(scn: AoE2Scenario, trigger_ids, name: str):
    """
    Adds a trigger named name to the scenario and trigger_ids bidict.
    Raises a ValueError if a trigger with that name already exists.
    Returns the created trigger object.
    """
    if name in trigger_ids:
        raise ValueError(f'{name} is already the name of a trigger.')
    trigger_ids[name] = len(trigger_ids)
    return scn.object_manager.get_trigger_object().add_trigger(name)


def add_cond_gaia_defeated(trigger) -> None:
    """
    Adds a condition to trigger that the gaia player is defeated.

    This condition will never be True. It can be used to ensure that
    objectives are never checked off.
    """
    gaia_defeated = trigger.add_condition(conditions.player_defeated)
    gaia_defeated.player = 0


# Various utility functions to make dealing with units more ergonomic.
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
    """Returns all units in the square with corners (x1, y1) and (x2, y2)."""
    return [unit for unit in unit_array
            if x1 <= unit_get_x(unit) <= x2 and y1 <= unit_get_y(unit) <= y2]


def unit_change_player(scenario: AoE2Scenario,
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


def name_variables(scn: AoE2Scenario) -> None:
    """Sets the names for trigger variables in the scenario scn."""
    trigger_piece = scn.parsed_data['TriggerPiece']
    var_count = trigger_piece.retrievers[6]
    var_change = trigger_piece.retrievers[7].data
    for name, __ in INITIAL_VARIABLES:
        var = VariableChangeStruct()
        var.retrievers[0].data = var_count.data
        var.retrievers[1].data = name
        var_change.append(var)
        var_count.data += 1


def add_trigger_header(scn: AoE2Scenario, trigger_ids, name: str) -> None:
    """
    Appends a trigger section header with title `name`.

    trigger_ids is a bidict mapping trigger names to their trigger indices.

    A header trigger serves no functional purpose, but allows
    the trigger list to be broken up into sections so that
    it is more human-readable in the editor.

    Raises a ValueError if creating this trigger would create a
    trigger with a duplicate name.
    """
    trigger_name = f'-- {name} --'
    add_trigger(scn, trigger_ids, trigger_name)


def initialize_variable_values(scn: AoE2Scenario, trigger_ids) -> None:
    """
    Initializes the variables used in the scenario to have their
    starting values.
    """
    trigger_name = '[I] Initialize Variables'
    init_vars = add_trigger(scn, trigger_ids, trigger_name)
    init_vars.description = 'Initializes variables to their starting values.'

    for index, (name, value) in enumerate(INITIAL_VARIABLES):
        change_var = init_vars.add_effect(effects.change_variable)
        change_var.quantity = value
        change_var.operation = ChangeVarOp.set_op.value
        change_var.from_variable = index
        change_var.message = name # Not strictly necessary, since names are set.


def add_start_timer(scn: AoE2Scenario, trigger_ids) -> None:
    """
    Adds a short timer before starting the first round by setting the round
    counter to 1.
    """
    trigger_name = '[I] Initialize Start Timer'
    init_timer = add_trigger(scn, trigger_ids, trigger_name)
    init_timer.description = 'Initializes a start timer to start round 1.'

    timer = init_timer.add_condition(conditions.timer)
    timer.timer = BETWEEN_ROUND_DELAY
    inc_round_count = init_timer.add_effect(effects.change_variable)
    inc_round_count.quantity = 1
    inc_round_count.operation = ChangeVarOp.add.value
    inc_round_count.from_variable = 5 # TODO magic number alert
    inc_round_count.message = 'round' # TODO magic


def set_start_views(scn: AoE2Scenario, trigger_ids) -> None:
    """
    Uses Change View Effects to set the player start views.
    This trigger is a workaround, since setting the start views
    through the Options menu does not work for
    multiplayer scenarios.
    """
    trigger_name = '[I] Initialize Starting Player Views'
    init_views = add_trigger(scn, trigger_ids, trigger_name)
    init_views.description = 'Changes p1 and p2 view to the middle.'

    for player in (1, 2):
        change_view = init_views.add_effect(effects.change_view)
        change_view.player_source = player
        change_view.location_x = START_VIEW_X
        change_view.location_y = START_VIEW_Y
        change_view.scroll = False


def add_objectives(scn: AoE2Scenario, trigger_ids) -> None:
    """
    Sets up the player objectives to display the score both
    on the side of the screen and in the objectives menu.
    """
    add_trigger_header(scn, trigger_ids, 'Objectives')

    score_header_name = '[O] Score Header'
    score_header = add_trigger(scn, trigger_ids, score_header_name)
    score_header.display_on_screen = True
    score_header.description_order = 100
    score_header.short_description = 'Score'
    score_header.header = True
    add_cond_gaia_defeated(score_header)
    # TODO set score_header attributes

    pass # TODO implement


# TODO how mutually to activate/deactivate triggers?
# Should I keep a map from trigger name to trigger id?

def add_initial_triggers(scn: AoE2Scenario, trigger_ids) -> None:
    """
    Adds initial triggers for initializing variables, listing player objectives,
    and starting the first round.
    """
    add_trigger_header(scn, trigger_ids, 'Init')
    initialize_variable_values(scn, trigger_ids)
    add_start_timer(scn, trigger_ids)
    set_start_views(scn, trigger_ids)
    add_objectives(scn, trigger_ids)


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
    scn = AoE2Scenario(scenario_template)
    # triggers = util_triggers.TriggerUtil(scn)

    # units_scn = AoE2Scenario(unit_template)

    # parse fight data
    # add in minigames
    # events = []

    # Maps a trigger name to its trigger index number.
    trigger_ids = bidict()

    name_variables(scn)
    add_initial_triggers(scn, trigger_ids)

    # for event in events:
    #     event.add_triggers(triggers)

    # add victory condition triggers

    scn.write_to_file(output)

    print('Triggers:')
    for name, index in trigger_ids.items():
        print(f'{index}: {name}')


def call_build_scenario(args):
    """Unpacks arguments from command line args and builds the scenario."""
    scenario_map = args.map[0]
    units_scn = args.units[0]
    out = args.output[0]

    # Checks the output path is different from all input paths.
    matches = []
    if out == scenario_map:
        matches.append('map')
    if out == units_scn:
        matches.append('units')
    if matches:
        conflicts = ', '.join(matches)
        msg = f"The output path '{out}' conflicts with: {conflicts}."
        raise ValueError(msg)

    build_scenario(scenario_template=scenario_map, unit_template=units_scn,
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
    scratch_path = 'scratch.aoe2scenario'
    print(scratch_path)
    for name in sorted(TECH_IDS):
        print(name)
    # TODO test naming variables
    # scn = AoE2Scenario(scratch_path)
    # trigger_mgr = scn.object_manager.get_trigger_object()
    # print(trigger_mgr.get_trigger_as_string(trigger_id=0))
    # output_path = 'scratch.aoe2scenario'
    # units_scenario_in = AoE2Scenario(UNIT_TEMPLATE)
    # units_scenario_out = AoE2Scenario(UNIT_TEMPLATE)
    # triggers_out = util_triggers.TriggerUtil(units_scenario_out)

    # p1_template_units_in = get_units_array(units_scenario_in, 1)
    # p1_template_units_out = get_units_array(units_scenario_out, 1)
    # for unit in units_in_area(p1_template_units_out, 20.0, 0.0, 40.0, 20.0):
    #     pass
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
    # unit_change_player(units_scenario_out, 0, 1, 2)
    # triggers_out.add_header('Hello, World!')
    # units_scenario_out.write_to_file(output_path)


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
