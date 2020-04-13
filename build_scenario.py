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

# To move a unit one square to the North, add 1 to its x coordinate and
# subtract 1 from its y coordinate. These assignments move the unit
# one tile up and to the left, then one tile up and to the right,
# cumulatively moving it one tile North.

# A Tiny-sized map has 120x120 tiles.
# A Giant-sized map has 240x240 tiles (although there are a few maps
# that are hard-coded to be 255x255, thanks ES).

# Unit angles are given in radians (as a 32-bit float).
# 0.0 is facing Northeast, and the radian values increase clockwise.


import argparse
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Set
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.objects.trigger_obj import TriggerObject
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.pieces.structs.variable_change import (
    VariableChangeStruct
)
from AoE2ScenarioParser.datasets import conditions, effects
import event
from event import Fight, Minigame
import util
import util_techs
import util_triggers
import util_units


# Relative path to the template scenario file.
SCENARIO_TEMPLATE = 'scenario-template.aoe2scenario'


# Relative path to the unit scenario file.
UNIT_TEMPLATE = 'unit-template.aoe2scenario'


# Default output scenario name.
OUTPUT = 'Micro Wars.aoe2scenario'


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


# The number of seconds to wait between launching the scenario and
# setting the round counter to 1
DELAY_BEGIN = 5


# The number of seconds to wait after ending a round.
# After this delay finishes, another timer of DELAY_ROUND_BEFORE
# is used after performing basic setup for the next round.
DELAY_ROUND_AFTER = 3


# The number of seconds to wait before starting a round.
DELAY_ROUND_BEFORE = 3


# The number of seconds to wait before ending the scenario when a
# player has won.
DELAY_VICTORY = 10


# The number of tiles along a border of the map.
MAP_WIDTH = 240


# X coordinate of the player's starting view.
START_VIEW_X = 121


# Y coordinate of the player's starting view.
START_VIEW_Y = 120


# The x coordinate of the location around which to center fights.
FIGHT_CENTER_X = 121


# The y coordinate of the location around which to center fights.
FIGHT_CENTER_Y = 120


# The number of tiles from the center an army's average should start.
FIGHT_OFFSET = 7


# The trigger name for the init tiebreaker trigger.
TIEBREAKER_INIT_NAME = '[T] Initialize Tiebreaker'


# The trigger name for the trigger that begins checking which player
# has won when there is no tie.
CHECK_WINNER_NAME = '[V] Check Winner'


# Name of the round counter trigger displayed in the menu and on screen.
ROUND_OBJ_NAME = '[O] Round Objective Header'


# Name of the tiebreaker header objective displayed in the menu and on screen.
TIEBREAKER_OBJ_NAME = '[O] Tiebreaker'


# Unit ID for a Map Revealer object.
UNIT_ID_MAP_REVEALER = 837


# Pairs of integer (x, y) tiles at which to create map revealers.
REVEALER_LOCATIONS = [
    # (FIGHT_CENTER_X, FIGHT_CENTER_Y)
    (x, y)
    for x in range(FIGHT_CENTER_X - 18, FIGHT_CENTER_X + 19, 3)
    for y in range(FIGHT_CENTER_Y - 18, FIGHT_CENTER_Y + 19, 3)
]


# Trigger for creating map revealers.
REVEALER_CREATE_NAME = '[I] Create Map Revealers'


# Unit ID for Player 1's Castle in the Castle Siege minigame.
CS_P1_CASTLE_ID = 813


# Unit ID for Player 2's Castle in the Castle Siege minigame.
CS_P2_CASTLE_ID = 830


class ChangeVarOp(Enum):
    """Represents the value for the operation of a Change Variable Effect."""
    set_op = 1
    add = 2
    subtract = 3
    multiply = 4
    divide = 5


class VarValComp(Enum):
    """Represents the value for the comparison of a Variable Value Condition."""
    equal = 0
    less = 1
    larger = 2
    less_or_equal = 3
    larger_or_equal = 4


class ScnData:
    """
    An instance represents data to mutate while processing a scenario.

    The typical use case for creating a Micro Wars scenario is:
    1. Perform file I/O to parse the template scenario and event files.
    2. Pass the parsed data to the initializer to create a ScnData object.
    3. Call the setup_scenario method.
    4. Call the write_to_file method.
    """

    # TODO map minigame to method

    # TODO annotate the type of the events list
    def __init__(self, scn: AoE2Scenario, events):
        """Initializes a new ScnData object for the scenario scn."""
        self._scn = scn
        self._events = events

        # Bidirectional map from a trigger's name to its index.
        self._trigger_ids = bidict()

        # Bidirectional map from a variable's name to its index.
        self._var_ids = bidict()

        # Maps the name of a trigger t to a set of triggers that t activates.
        self._activate_triggers: Dict[str, Set[str]] = defaultdict(set)

        # Maps the name of a trigger t to a set of triggers that t deactivates.
        self._deactivate_triggers: Dict[str, Set[str]] = defaultdict(set)

        # self._round_objective[k] is the list of names of the triggers
        # to activate to display the objectives for round k.
        self._round_objectives: List[List[str]] = [
            [] for __ in range(len(self._events))
        ]

    @property
    def num_rounds(self):
        """Returns the number of rounds, not including the tiebreaker."""
        return len(self._events) - 1

    def setup_scenario(self):
        """
        Modifies the internal scenario file to support the changes
        for Micro Wars!
        """
        self._name_variables()
        self._add_ai_triggers()
        self._add_initial_triggers()
        self._setup_rounds()
        self._add_activate_and_deactivate_effects()

    def write_to_file(self, file_path):
        """
        Writes the current scn file to `file_path`.

        Overwrites any file currently at that path.
        """
        self._scn.write_to_file(file_path)

    def _add_trigger(self, name: str):
        """
        Adds a trigger named name to the scenario and trigger_ids bidict.
        Raises a ValueError if a trigger with that name already exists.
        Returns the created trigger object.
        """
        if name in self._trigger_ids:
            raise ValueError(f'{name} is already the name of a trigger.')
        self._trigger_ids[name] = len(self._trigger_ids)
        return self._scn.object_manager.get_trigger_object().add_trigger(name)

    def _add_trigger_header(self, name: str) -> None:
        """
        Appends a trigger section header with title `name`.

        A header trigger serves no functional purpose, but allows
        the trigger list to be broken up into sections so that
        it is more human-readable in the editor.

        Raises a ValueError if creating this trigger would create a
        trigger with a duplicate name.
        """
        trigger_name = f'-- {name} --'
        self._add_trigger(trigger_name)

    def _add_activate(self, name_source: str, name_target: str):
        """
        Appends name_target to the list of triggers activated by name_source.
        Raises a ValueError if name_source already should activate name_target.
        """
        if name_target in self._activate_triggers[name_source]:
            raise ValueError(f'{name_source} already activates {name_target}.')
        self._activate_triggers[name_source].add(name_target)

    def _add_deactivate(self, name_source: str, name_target: str):
        """
        Appends name_target to the list of triggers deactivated by name_source.
        Raises a ValueError if name_source already should deactivate
        name_target.
        """
        if name_target in self._deactivate_triggers[name_source]:
            raise ValueError(
                f'{name_source} already deactivates {name_target}.')
        self._deactivate_triggers[name_source].add(name_target)

    def _add_activate_and_deactivate_effects(self):
        """
        Adds all activate and deactivate triggers specified in the fields.

        This method should be called at the end of setup_scenario after all
        triggers are created.
        """
        trigger_mgr = self._scn.object_manager.get_trigger_object()
        effect_mapping_and_function = [
            (self._activate_triggers, util_triggers.add_effect_activate),
            (self._deactivate_triggers, util_triggers.add_effect_deactivate)
        ]
        for mapping, add_effect in effect_mapping_and_function:
            for source_name, target_names in mapping.items():
                for target_name in target_names:
                    source_id = self._trigger_ids[source_name]
                    source = trigger_mgr.get_trigger(trigger_id=source_id)
                    target_id = self._trigger_ids[target_name]
                    add_effect(source, target_id)

    def _add_effect_p1_score(self, trigger: TriggerObject,
                             pts: int) -> None:
        """Adds effects to trigger that change p1's score by pts."""
        p1_plus = trigger.add_effect(effects.change_variable)
        p1_plus.quantity = pts
        p1_plus.operation = ChangeVarOp.add.value
        p1_plus.from_variable = self._var_ids['p1-score']
        p1_plus.message = 'p1-score'
        diff_plus = trigger.add_effect(effects.change_variable)
        diff_plus.quantity = pts
        diff_plus.operation = ChangeVarOp.add.value
        diff_plus.from_variable = self._var_ids['score-difference']
        diff_plus.message = 'score-difference'

    def _add_effect_p2_score(self, trigger: TriggerObject,
                             pts: int) -> None:
        """Adds effects to trigger that change p2's score by pts."""
        p2_plus = trigger.add_effect(effects.change_variable)
        p2_plus.quantity = pts
        p2_plus.operation = ChangeVarOp.add.value
        p2_plus.from_variable = self._var_ids['p2-score']
        p2_plus.message = 'p2-score'
        diff_subtract = trigger.add_effect(effects.change_variable)
        diff_subtract.quantity = pts
        diff_subtract.operation = ChangeVarOp.subtract.value
        diff_subtract.from_variable = self._var_ids['score-difference']
        diff_subtract.message = 'score-difference'

    def _name_variables(self) -> None:
        """Sets the names for trigger variables in the scenario."""
        trigger_piece = self._scn.parsed_data['TriggerPiece']
        var_count = trigger_piece.retrievers[6]
        var_change = trigger_piece.retrievers[7].data
        for name, __ in INITIAL_VARIABLES:
            var = VariableChangeStruct()
            index = var_count.data
            self._var_ids[name] = index
            var.retrievers[0].data = index
            var.retrievers[1].data = name
            var_change.append(var)
            var_count.data += 1

    def _add_ai_triggers(self) -> None:
        """
        Adds triggers for informing players if the correct AI script
        is not loaded.
        """
        # AI signals do not work in multiplayer on DE.
        # If they do get fixed, this method should create three triggers:
        # 1. Declare AI Victory
        #    * Starts Disabled
        #    * Timer: 10
        #    * Declare Victory: Player 3
        # 2. * AI Script Not Loaded
        #    * Timer: 5
        #    * Activate Trigger: Declare AI Victory
        #    * Display Instructions: Micro Wars AI Script not Loaded
        # 3. AI Script Loaded
        #    * Condition: AI Signal 0
        #    * Disable Trigger: AI Script Not Loaded
        # In lieu of this feature, we create a workaround by adding stone
        # to the AI player and using an Accumulate Attribute condition to
        # disable the message and declare victory triggers.
        self._add_trigger_header('AI')
        ai_victory_name = '[AI] Declare AI Victory'
        ai_not_loaded_name = '[AI] AI Script not Loaded'
        ai_loaded_name = '[AI] Script Loaded'

        ai_victory = self._add_trigger(ai_victory_name)
        ai_victory.enabled = False
        util_triggers.add_cond_timer(ai_victory, 10)
        ai_declare_winner = ai_victory.add_effect(effects.declare_victory)
        ai_declare_winner.player_source = 3

        ai_not_loaded = self._add_trigger(ai_not_loaded_name)
        util_triggers.add_cond_timer(ai_not_loaded, 5)
        self._add_activate(ai_not_loaded_name, ai_victory_name)
        ai_msg = ai_not_loaded.add_effect(effects.display_instructions)
        ai_msg.player_source = 3
        ai_msg.message = 'Micro Wars AI Script is not Loaded'
        ai_msg.display_time = 10
        ai_msg.play_sound = False
        ai_msg.sound_name = '\x00'
        ai_msg.string_id = -1

        ai_loaded = self._add_trigger(ai_loaded_name)
        stone_2197 = ai_loaded.add_condition(conditions.accumulate_attribute)
        stone_2197.amount_or_quantity = 2197
        stone_2197.resource_type_or_tribute_list = 2 # TODO make enum
        stone_2197.player = 3
        self._add_deactivate(ai_loaded_name, ai_not_loaded_name)

    def _add_initial_triggers(self) -> None:
        """
        Adds initial triggers for initializing variables,
        listing player objectives, and starting the first round.
        """
        self._add_trigger_header('Init')
        self._initialize_variable_values()
        self._add_start_timer()
        self._set_start_views()
        self._create_map_revealer_triggers()
        self._add_objectives()
        self._add_victory_conditions()

    def _initialize_variable_values(self) -> None:
        """
        Initializes the variables used in the scenario to have their
        starting values.
        """
        trigger_name = '[I] Initialize Variables'
        init_vars = self._add_trigger(trigger_name)
        init_vars.description = 'Initializes variable starting values.'

        for index, (name, value) in enumerate(INITIAL_VARIABLES):
            change_var = init_vars.add_effect(effects.change_variable)
            change_var.quantity = value
            change_var.operation = ChangeVarOp.set_op.value
            change_var.from_variable = index
            change_var.message = name

    def _add_start_timer(self) -> None:
        """
        Adds a short timer before starting the first round by setting the round
        counter to 1.
        """
        trigger_name = '[I] Initialize Start Timer'
        init_timer = self._add_trigger(trigger_name)
        init_timer.description = 'Initializes a start timer to start round 1.'

        util_triggers.add_cond_timer(init_timer, DELAY_BEGIN)
        inc_round_count = init_timer.add_effect(effects.change_variable)
        inc_round_count.quantity = 1
        inc_round_count.operation = ChangeVarOp.add.value
        inc_round_count.from_variable = self._var_ids['round']
        inc_round_count.message = 'round'

    def _set_start_views(self) -> None:
        """
        Uses Change View Effects to set the player start views.
        This trigger is a workaround, since setting the start views
        through the Options menu does not work for
        multiplayer scenarios.
        """
        trigger_name = '[I] Initialize Starting Player Views'
        init_views = self._add_trigger(trigger_name)
        init_views.description = 'Changes p1 and p2 view to the middle.'

        for player in (1, 2):
            change_view = init_views.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x = START_VIEW_X
            change_view.location_y = START_VIEW_Y
            change_view.scroll = False

    def _create_map_revealer_triggers(self) -> None:
        """
        Creates a set of map revealers to cover the middle area.
        Loops and disables itself.
        Can be re-enabled to make additional map revealers.
        """
        create_revealers = self._add_trigger(REVEALER_CREATE_NAME)
        create_revealers.enabled = False
        create_revealers.looping = True
        self._add_deactivate(REVEALER_CREATE_NAME, REVEALER_CREATE_NAME)
        for player in (1, 2):
            for (x, y) in REVEALER_LOCATIONS:
                create = create_revealers.add_effect(effects.create_object)
                create.object_list_unit_id = UNIT_ID_MAP_REVEALER
                create.player_source = player
                create.location_x = x
                create.location_y = y
        # TODO map revealers for minigames

    def _add_objectives(self) -> None:
        """
        Sets up the player objectives to display the score both
        on the side of the screen and in the objectives menu.
        """
        self._add_trigger_header('Objectives')

        # Menu objectives
        obj_title_name = '[O] Objectives Title'
        obj_title = self._add_trigger(obj_title_name)
        obj_title.display_as_objective = True
        obj_title.description_order = 200
        obj_title.header = True
        obj_title.description = 'Micro Wars!'
        util_triggers.add_cond_gaia_defeated(obj_title)

        obj_description_name = '[O] Objectives Description'
        obj_description = self._add_trigger(obj_description_name)
        obj_description.display_as_objective = True
        obj_description.description_order = 199
        obj_description.description = "Each round is worth 100 points. Win points by killing your opponent's units or by completing special objectives." # pylint: disable=line-too-long
        util_triggers.add_cond_gaia_defeated(obj_description)

        obj_score_header_name = '[O] Objectives Score Header'
        obj_score_header = self._add_trigger(obj_score_header_name)
        obj_score_header.display_as_objective = True
        obj_score_header.description_order = 100
        obj_score_header.description = 'Score:'
        obj_score_header.header = True
        util_triggers.add_cond_gaia_defeated(obj_score_header)

        obj_score_p1_name = '[O] Objectives Score P1'
        obj_score_p1 = self._add_trigger(obj_score_p1_name)
        obj_score_p1.display_as_objective = True
        obj_score_p1.description_order = 99
        obj_score_p1.description = 'Player 1: <p1-score>'
        obj_p1_wins_cond = obj_score_p1.add_condition(conditions.variable_value)
        obj_p1_wins_cond.amount_or_quantity = 1
        obj_p1_wins_cond.variable = self._var_ids['p1-wins']
        obj_p1_wins_cond.comparison = VarValComp.equal.value

        obj_score_p2_name = '[O] Objectives Score P2'
        obj_score_p2 = self._add_trigger(obj_score_p2_name)
        obj_score_p2.display_as_objective = True
        obj_score_p2.description_order = 98
        obj_score_p2.description = 'Player 2: <p2-score>'
        obj_p2_wins_cond = obj_score_p2.add_condition(conditions.variable_value)
        obj_p2_wins_cond.amount_or_quantity = 1
        obj_p2_wins_cond.variable = self._var_ids['p2-wins']
        obj_p2_wins_cond.comparison = VarValComp.equal.value

        # Displayed Objectives
        disp_score_header_name = '[O] Display Score Header'
        disp_score_header = self._add_trigger(disp_score_header_name)
        disp_score_header.display_on_screen = True
        disp_score_header.description_order = 100
        disp_score_header.short_description = 'Score:'
        disp_score_header.header = True
        util_triggers.add_cond_gaia_defeated(disp_score_header)

        disp_score_p1_name = '[O] Display Score P1'
        disp_score_p1 = self._add_trigger(disp_score_p1_name)
        disp_score_p1.display_on_screen = True
        disp_score_p1.description_order = 99
        disp_score_p1.short_description = 'P1: <p1-score>'
        disp_p1_wins_cond = disp_score_p1.add_condition(
            conditions.variable_value)
        disp_p1_wins_cond.amount_or_quantity = 1
        disp_p1_wins_cond.variable = self._var_ids['p1-wins']
        disp_p1_wins_cond.comparison = VarValComp.equal.value

        disp_score_p2_name = '[O] Display Score P2'
        disp_score_p2 = self._add_trigger(disp_score_p2_name)
        disp_score_p2.display_on_screen = True
        disp_score_p2.description_order = 98
        disp_score_p2.short_description = 'P2: <p2-score>'
        disp_p2_wins_cond = disp_score_p2.add_condition(
            conditions.variable_value)
        disp_p2_wins_cond.amount_or_quantity = 1
        disp_p2_wins_cond.variable = self._var_ids['p2-wins']
        disp_p2_wins_cond.comparison = VarValComp.equal.value

        round_text = f'Round <round> / {self.num_rounds}:'
        round_obj = self._add_trigger(ROUND_OBJ_NAME)
        round_obj.header = True
        round_obj.enabled = False
        round_obj.display_as_objective = True
        round_obj.display_on_screen = True
        round_obj.description_order = 75
        round_obj.short_description = round_text
        round_obj.description = round_text
        round_obj.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(round_obj)

        tiebreaker_text = 'Tiebreaker'
        tiebreaker_obj = self._add_trigger(TIEBREAKER_OBJ_NAME)
        tiebreaker_obj.header = True
        tiebreaker_obj.enabled = False
        tiebreaker_obj.display_as_objective = True
        tiebreaker_obj.display_on_screen = True
        tiebreaker_obj.description_order = 75
        tiebreaker_obj.short_description = tiebreaker_text
        tiebreaker_obj.description = tiebreaker_text
        tiebreaker_obj.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(tiebreaker_obj)

        for e_index, e in enumerate(self._events):
            if e_index != 0:
                if isinstance(e, Minigame):
                    self._add_minigame_objective(e, e_index)
                else:
                    fight_obj_text = e.objectives_description()
                    fight_obj_name = f'[O] Fight {e_index} Objective'
                    self._round_objectives[e_index].append(fight_obj_name)
                    fight_obj = self._add_trigger(fight_obj_name)
                    fight_obj.enabled = False
                    fight_obj.display_as_objective = True
                    fight_obj.display_on_screen = True
                    fight_obj.description_order = 50
                    fight_obj.short_description = fight_obj_text
                    fight_obj.description = fight_obj_text
                    fight_obj.mute_objectives = True
                    util_triggers.add_cond_gaia_defeated(fight_obj)

    def _add_minigame_objective(self, mg: Minigame, index: int):
        """
        Adds the objectives corresponding to minigame mg to the
        index of _round_objectives.

        Checks _round_objective[index] contains an empty list.
        """
        assert self._round_objectives[index] == []

        if mg.name == 'Castle Siege':
            self._add_castle_siege_objectives(index)
        # TODO implement other minigames.
        else:
            raise AssertionError(f'Minigame {mg.name} not implemented.')

    def _add_castle_siege_objectives(self, index: int):
        """Adds the objectives for the Castle Siege minigame."""
        obj_cs_name = f'[O] Round {index} Castle Siege'
        self._round_objectives[index].append(obj_cs_name)
        obj_cs = self._add_trigger(obj_cs_name)
        obj_cs.enabled = False
        obj_cs.description = "Raise your opponent's Castle or defeat their entire army to win." # pylint: disable=line-too-long
        obj_cs.short_description = "Raise your opponent's Castle."
        obj_cs.display_as_objective = True
        obj_cs.display_on_screen = True
        obj_cs.description_order = 50
        obj_cs.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_cs)

        obj_cs_p1_name = f'[O] Castle Siege Player 1 Castle Destroyed'
        self._round_objectives[index].append(obj_cs_p1_name)
        obj_cs_p1 = self._add_trigger(obj_cs_p1_name)
        obj_cs_p1.enabled = False
        obj_cs_p1.description = "- Player 1 Castle Destroyed"
        obj_cs_p1.short_description = "- P1 Castle Destroyed"
        obj_cs_p1.display_as_objective = True
        obj_cs_p1.display_on_screen = True
        obj_cs_p1.description_order = 49
        obj_cs_p1.mute_objectives = True
        p1_castle_destroyed = obj_cs_p1.add_condition(conditions.destroy_object)
        p1_castle_destroyed.unit_object = CS_P1_CASTLE_ID

        obj_cs_p2_name = f'[O] Castle Siege Player 2 Castle Destroyed'
        self._round_objectives[index].append(obj_cs_p2_name)
        obj_cs_p2 = self._add_trigger(obj_cs_p2_name)
        obj_cs_p2.enabled = False
        obj_cs_p2.description = "- Player 2 Castle Destroyed"
        obj_cs_p2.short_description = "- P2 Castle Destroyed"
        obj_cs_p2.display_as_objective = True
        obj_cs_p2.display_on_screen = True
        obj_cs_p2.description_order = 48
        obj_cs_p2.mute_objectives = True
        p2_castle_destroyed = obj_cs_p2.add_condition(conditions.destroy_object)
        p2_castle_destroyed.unit_object = CS_P2_CASTLE_ID

    def _add_victory_conditions(self):
        """
        Adds triggers to display victory messages and win the game after a
        short timer, once one of the p1-wins or p2-wins variables is set.
        """
        self._add_trigger_header('Victory')

        rounds_completed_name = '[V] Rounds Completed'
        check_tie_name = '[V] Check Tie'
        check_not_tie_name = '[V] Check Not Tie'
        check_p1_winner_name = '[V] Check Player 1 Winner'
        check_p2_winner_name = '[V] Check Player 2 Winner'

        rounds_completed = self._add_trigger(rounds_completed_name)
        counter = rounds_completed.add_condition(conditions.variable_value)
        # Adds 1 to the number of rounds to adjust for the tiebreaker.
        counter.amount_or_quantity = self.num_rounds + 1
        counter.variable = self._var_ids['round']
        counter.comparison = VarValComp.equal.value
        self._add_activate(rounds_completed_name, check_tie_name)
        self._add_activate(rounds_completed_name, check_not_tie_name)

        check_tie = self._add_trigger(check_tie_name)
        check_tie.enabled = False
        diff0 = check_tie.add_condition(conditions.variable_value)
        diff0.amount_or_quantity = 0
        diff0.variable = self._var_ids['score-difference']
        diff0.comparison = VarValComp.equal.value
        self._add_deactivate(check_tie_name, check_not_tie_name)
        self._add_activate(check_tie_name, TIEBREAKER_INIT_NAME)

        check_not_tie = self._add_trigger(check_not_tie_name)
        check_not_tie.enabled = False
        diff_not_0 = check_not_tie.add_condition(conditions.variable_value)
        diff_not_0.amount_or_quantity = 0
        diff_not_0.variable = self._var_ids['score-difference']
        diff_not_0.comparison = VarValComp.equal.value
        diff_not_0.inverted = True
        self._add_deactivate(check_not_tie_name, check_tie_name)
        self._add_activate(check_not_tie_name, CHECK_WINNER_NAME)

        check_winner = self._add_trigger(CHECK_WINNER_NAME)
        check_winner.enabled = False
        self._add_activate(CHECK_WINNER_NAME, check_p1_winner_name)
        self._add_activate(CHECK_WINNER_NAME, check_p2_winner_name)

        check_p1_winner = self._add_trigger(check_p1_winner_name)
        check_p1_winner.enabled = False
        diff_pos = check_p1_winner.add_condition(conditions.variable_value)
        diff_pos.amount_or_quantity = 0
        diff_pos.variable = self._var_ids['score-difference']
        diff_pos.comparison = VarValComp.larger.value
        self._add_deactivate(check_p1_winner_name, check_p2_winner_name)
        set_p1_win = check_p1_winner.add_effect(effects.change_variable)
        set_p1_win.quantity = 1
        set_p1_win.operation = ChangeVarOp.set_op.value
        set_p1_win.from_variable = self._var_ids['p1-wins']
        set_p1_win.message = 'p1-wins'

        check_p2_winner = self._add_trigger(check_p2_winner_name)
        check_p2_winner.enabled = False
        diff_neg = check_p2_winner.add_condition(conditions.variable_value)
        diff_neg.amount_or_quantity = 0
        diff_neg.variable = self._var_ids['score-difference']
        diff_neg.comparison = VarValComp.less.value
        self._add_deactivate(check_p2_winner_name, check_p1_winner_name)
        set_p2_win = check_p2_winner.add_effect(effects.change_variable)
        set_p2_win.quantity = 1
        set_p2_win.operation = ChangeVarOp.set_op.value
        set_p2_win.from_variable = self._var_ids['p2-wins']
        set_p2_win.message = 'p2-wins'

        is_victorious_p1 = self._add_trigger('[V] Player 1 is Victorious')
        cond_p1_wins = is_victorious_p1.add_condition(conditions.variable_value)
        cond_p1_wins.amount_or_quantity = 1
        cond_p1_wins.variable = self._var_ids['p1-wins']
        cond_p1_wins.comparison = VarValComp.equal.value

        msg_p1 = is_victorious_p1.add_effect(effects.display_instructions)
        msg_p1.player_source = 1
        msg_p1.message = '<BLUE>Player 1 is Victorious!'
        msg_p1.display_time = 10
        msg_p1.play_sound = False
        msg_p1.sound_name = '\x00'
        msg_p1.string_id = -1

        self._add_activate(is_victorious_p1.name.rstrip('\x00'),
                           '[V] Declare Player 1 Victory')
        self._add_deactivate(is_victorious_p1.name.rstrip('\x00'),
                             '[V] Player 2 is Victorious')

        is_victorious_p2 = self._add_trigger('[V] Player 2 is Victorious')

        cond_p2_wins = is_victorious_p2.add_condition(conditions.variable_value)
        cond_p2_wins.amount_or_quantity = 1
        cond_p2_wins.variable = self._var_ids['p2-wins']
        cond_p2_wins.comparison = VarValComp.equal.value

        msg_p2 = is_victorious_p2.add_effect(effects.display_instructions)
        msg_p2.player_source = 2
        msg_p2.message = '<RED>Player 2 is Victorious!'
        msg_p2.display_time = 10
        msg_p2.play_sound = False
        msg_p2.sound_name = '\x00'
        msg_p2.string_id = -1

        self._add_activate(is_victorious_p2.name.rstrip('\x00'),
                           '[V] Declare Player 2 Victory')
        self._add_deactivate(is_victorious_p2.name.rstrip('\x00'),
                             '[V] Player 1 is Victorious')

        declare_victory_p1 = self._add_trigger('[V] Declare Player 1 Victory')
        declare_victory_p1.enabled = False
        util_triggers.add_cond_timer(declare_victory_p1, DELAY_VICTORY)
        util_triggers.add_effect_delcare_victory(declare_victory_p1, 1)

        declare_victory_p2 = self._add_trigger('[V] Declare Player 2 Victory')
        declare_victory_p2.enabled = False
        util_triggers.add_cond_timer(declare_victory_p2, DELAY_VICTORY)
        util_triggers.add_effect_delcare_victory(declare_victory_p2, 2)

    def _setup_rounds(self) -> None:
        """
        Copies the units from the fight data and adds triggers for each
        round of units.
        """
        for index, e in enumerate(self._events):
            if isinstance(e, Minigame):
                self._add_trigger_header(f'Minigame {index}')
                self._add_minigame(index, e)
            else:
                self._add_trigger_header(
                    f'Fight {index}' if index else 'Tiebreaker')
                self._add_fight(index, e)

    def _add_minigame(self, index: int, mg: Minigame) -> None:
        """Adds the minigame mg with the given index."""
        # TODO map revealer minigame transitions
        # TODO use enum instead of checking name
        if mg.name == 'Castle Siege':
            self._add_castle_siege(index)
        else:
            raise AssertionError(f'Minigame {mg.name} is not implemented.')

    def _add_castle_siege(self, index: int) -> None:
        """
        Adds the Castle Siege minigame at the given index.

        Checks the index is not 0 (cannot us a minigame as the tiebreaker).
        """
        assert index
        prefix = f'[R{index}]' if index else '[T]'
        init_name = f'{prefix} Initialize Round'
        begin_name = f'{prefix} Begin Round'
        p1_wins_name = f'{prefix} Player 1 Wins Round'
        p1_loses_castle_name = f'{prefix} Player 1 Loses Castle'
        p1_loses_army_name = f'{prefix} Player 1 Loses Army'
        p2_wins_name = f'{prefix} Player 2 Wins Round'
        p2_loses_castle_name = f'{prefix} Player 2 Loses Castle'
        p2_loses_army_name = f'{prefix} Player 2 Loses Army'
        cleanup_name = f'{prefix} Cleanup Round'
        increment_name = f'{prefix} Increment Round'

        init = self._add_trigger(init_name)
        init_var = init.add_condition(conditions.variable_value)
        init_var.amount_or_quantity = index
        init_var.variable = self._var_ids['round']
        init_var.comparison = VarValComp.equal.value
        if index == 1:
            self._add_activate(init_name, ROUND_OBJ_NAME)
            # TODO transition minigame map revealers
            self._add_activate(init_name, REVEALER_CREATE_NAME)
        obj_names = self._round_objectives[index]
        for obj_name in obj_names:
            self._add_activate(init_name, obj_name)
        self._add_activate(init_name, begin_name)
        p1_stone = init.add_effect(effects.modify_resource)
        p1_stone.quantity = 650 # TODO magic number
        p1_stone.tribute_list = 2 # TODO magic number
        p1_stone.player_source = 1
        p1_stone.item_id = -1
        p1_stone.operation = ChangeVarOp.set_op.value # TODO rename enum
        p2_stone = init.add_effect(effects.modify_resource)
        p2_stone.quantity = 650 # TODO magic number
        p2_stone.tribute_list = 2 # TODO magic number
        p2_stone.player_source = 2
        p2_stone.item_id = -1
        p2_stone.operation = ChangeVarOp.set_op.value # TODO rename enum

        # TODO research minigame techs

        for player in (1, 2):
            change_view = init.add_effect(effects.change_view)
            change_view.player_source = player
            # TODO remove magic numbers
            change_view.location_x = 120
            change_view.location_y = 40

        begin = self._add_trigger(begin_name)
        begin.enabled = False
        util_triggers.add_cond_timer(begin, DELAY_ROUND_BEFORE)
        # Begin changes ownership
        p3_units = util_units.get_units_array(self._scn, 3)
        # TODO remove magic numbers
        cs_units = util_units.units_in_area(p3_units, 80.0, 0, 160.0, 80.0)
        unit_player_pairs = []
        for unit in cs_units:
            pos = util_units.get_x(unit) + util_units.get_y(unit)
            player_target = 1 if pos < 160.0 else 2 # TODO remove magic number
            change_to_player = begin.add_effect(effects.change_ownership)
            change_to_player.number_of_units_selected = 1
            change_to_player.player_source = 3
            change_to_player.player_target = player_target
            uid = util_units.get_id(unit)
            change_to_player.selected_object_id = uid
            unit_player_pairs.append((uid, player_target))

        # Cleanup
        # TODO remove stone

        # p2 loses castle
        p2_loses_castle = self._add_trigger(p2_loses_castle_name)
        p2_c_cond = p2_loses_castle.add_condition(conditions.destroy_object)
        p2_c_cond.unit_object = CS_P2_CASTLE_ID
        self._add_activate(p2_loses_castle_name, p1_wins_name)
        self._add_deactivate(p2_loses_castle_name, p2_loses_army_name)
        self._add_deactivate(p2_loses_castle_name, p1_loses_castle_name)
        self._add_deactivate(p2_loses_castle_name, p1_loses_army_name)

        # p2 loses army
        p2_loses_army = self._add_trigger(p2_loses_army_name)
        for unit in cs_units:
            pos = util_units.get_x(unit) + util_units.get_y(unit)
            uid = util_units.get_id(unit)
            if pos >= 160.0 and uid != CS_P2_CASTLE_ID:
                p2_u_cond = p2_loses_army.add_condition(
                    conditions.destroy_object)
                p2_u_cond.unit_object = uid
        self._add_activate(p2_loses_army_name, p2_wins_name)
        self._add_deactivate(p2_loses_army_name, p1_loses_castle_name)
        self._add_deactivate(p2_loses_army_name, p1_loses_army_name)
        self._add_deactivate(p2_loses_army_name, p2_loses_castle_name)

        # p1 wins
        p1_wins = self._add_trigger(p1_wins_name)
        p1_wins.enabled = False
        self._add_effect_p1_score(p1_wins, event.MAX_POINTS)
        self._add_activate(p1_wins_name, cleanup_name)

        # p1 loses castle
        p1_loses_castle = self._add_trigger(p1_loses_castle_name)
        p1_c_cond = p1_loses_castle.add_condition(conditions.destroy_object)
        p1_c_cond.unit_object = CS_P1_CASTLE_ID
        self._add_activate(p1_loses_castle_name, p2_wins_name)
        self._add_deactivate(p1_loses_castle_name, p1_loses_army_name)
        self._add_deactivate(p1_loses_castle_name, p2_loses_castle_name)
        self._add_deactivate(p1_loses_castle_name, p2_loses_army_name)

        # p1 loses army
        p1_loses_army = self._add_trigger(p1_loses_army_name)
        for unit in cs_units:
            pos = util_units.get_x(unit) + util_units.get_y(unit)
            uid = util_units.get_id(unit)
            if pos < 160.0 and uid != CS_P1_CASTLE_ID:
                p1_u_cond = p1_loses_army.add_condition(
                    conditions.destroy_object)
                p1_u_cond.unit_object = uid
        self._add_activate(p1_loses_army_name, p1_wins_name)
        self._add_deactivate(p1_loses_army_name, p2_loses_castle_name)
        self._add_deactivate(p1_loses_army_name, p2_loses_army_name)
        self._add_deactivate(p1_loses_army_name, p1_loses_castle_name)

        # p2 wins
        p2_wins = self._add_trigger(p2_wins_name)
        p2_wins.enabled = False
        self._add_effect_p2_score(p2_wins, event.MAX_POINTS)
        self._add_activate(p2_wins_name, cleanup_name)

        cleanup = self._add_trigger(cleanup_name)
        cleanup.enabled = False
        self._add_activate(cleanup_name, increment_name)
        if index == self.num_rounds:
            self._add_deactivate(cleanup_name, ROUND_OBJ_NAME)
        # Cleanup removes units from player control.
        for uid, player_source in unit_player_pairs:
            change_from_player = cleanup.add_effect(effects.change_ownership)
            change_from_player.number_of_units_selected = 1
            change_from_player.player_source = player_source
            change_from_player.player_target = 3
            change_from_player.selected_object_id = uid

        increment_round = self._add_trigger(increment_name)
        increment_round.enabled = False
        util_triggers.add_cond_timer(increment_round, DELAY_ROUND_AFTER)

        change_round = increment_round.add_effect(effects.change_variable)
        change_round.quantity = 1
        change_round.operation = ChangeVarOp.add.value
        change_round.from_variable = self._var_ids['round']
        change_round.message = 'round'
        obj_names = self._round_objectives[index]
        for obj_name in obj_names:
            self._add_deactivate(cleanup_name, obj_name)

    def _add_fight(self, index: int, f: Fight) -> None:
        """Adds the fight with the given index."""
        # TODO map revealer minigame transitions
        prefix = f'[R{index}]' if index else '[T]'
        if index:
            init_name = f'{prefix} Initialize Round'
        else:
            init_name = TIEBREAKER_INIT_NAME
        begin_name = f'{prefix} Begin Round'
        p1_wins_name = f'{prefix} Player 1 Wins Round'
        p2_wins_name = f'{prefix} Player 2 Wins Round'
        cleanup_name = f'{prefix} Cleanup Round'
        increment_name = f'{prefix} Increment Round'

        init = self._add_trigger(init_name)
        if index:
            init_var = init.add_condition(conditions.variable_value)
            init_var.amount_or_quantity = index
            init_var.variable = self._var_ids['round']
            init_var.comparison = VarValComp.equal.value
            if index == 1:
                self._add_activate(init_name, ROUND_OBJ_NAME)
                # TODO transition minigame map revealers
                self._add_activate(init_name, REVEALER_CREATE_NAME)
            obj_names = self._round_objectives[index]
            for obj_name in obj_names:
                self._add_activate(init_name, obj_name)
        else:
            # Disables the tiebreaker. The tiebreak launches only when
            # enabled manually.
            init.enabled = False
            self._add_activate(init_name, TIEBREAKER_OBJ_NAME)
        self._add_activate(init_name, begin_name)

        for player in (1, 2, 3):
            for tech_name in f.techs:
                tech_id = util_techs.TECH_IDS[tech_name]
                util_triggers.add_effect_research_tech(init, tech_id, player)

        for player in (1, 2):
            change_view = init.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x = FIGHT_CENTER_X
            change_view.location_y = FIGHT_CENTER_Y

        begin = self._add_trigger(begin_name)
        begin.enabled = False
        util_triggers.add_cond_timer(begin, DELAY_ROUND_BEFORE)

        p1_wins = self._add_trigger(p1_wins_name)
        self._add_deactivate(p1_wins_name, p2_wins_name)
        self._add_activate(p1_wins_name, cleanup_name)
        self._add_effect_p1_score(p1_wins, self._events[index].p1_bonus)
        p2_wins = self._add_trigger(p2_wins_name)
        self._add_deactivate(p2_wins_name, p1_wins_name)
        self._add_activate(p2_wins_name, cleanup_name)
        self._add_effect_p2_score(p2_wins, self._events[index].p2_bonus)

        cleanup = self._add_trigger(cleanup_name)
        cleanup.enabled = False
        self._add_activate(cleanup_name, increment_name)
        if index == self.num_rounds:
            self._add_deactivate(cleanup_name, ROUND_OBJ_NAME)

        increment_round = self._add_trigger(increment_name)
        increment_round.enabled = False
        util_triggers.add_cond_timer(increment_round, DELAY_ROUND_AFTER)
        if index:
            change_round = increment_round.add_effect(effects.change_variable)
            change_round.quantity = 1
            change_round.operation = ChangeVarOp.add.value
            change_round.from_variable = self._var_ids['round']
            change_round.message = 'round'
            obj_names = self._round_objectives[index]
            for obj_name in obj_names:
                self._add_deactivate(cleanup_name, obj_name)
        else:
            # The tiebreaker activates checking the winner, rather than
            # changing the round.
            self._add_deactivate(increment_name, TIEBREAKER_OBJ_NAME)
            self._add_activate(increment_name, CHECK_WINNER_NAME)

        for unit in f.p1_units:
            self._add_unit(index, unit, 1, init, begin, p1_wins, p2_wins,
                           cleanup)
        for unit in f.p2_units:
            self._add_unit(index, unit, 2, init, begin, p1_wins, p2_wins,
                           cleanup)

    def _add_unit(self, fight_index: int, unit: UnitStruct, from_player: int,
                  init: TriggerObject, begin: TriggerObject,
                  p1_wins: TriggerObject, p2_wins: TriggerObject,
                  cleanup: TriggerObject) -> None:
        """
        Adds the unit from player `from_player` to the scenario.
        `fight_index` is the index of the fight in which the unit participates.
        Checks that from_player is 1 or 2.
        """
        assert from_player in (1, 2)

        u = util_units.copy_unit(self._scn, unit, 3)
        uid = util_units.get_id(u)

        # Hides the unit in the top corner.
        util_units.set_x(u, MAP_WIDTH - 0.5)
        util_units.set_y(u, 0.5)

        # Init handles teleportation.
        teleport = init.add_effect(effects.teleport_object)
        teleport.number_of_units_selected = 1
        teleport.player_source = 3
        teleport.selected_object_id = uid
        teleport.location_x = util_units.get_x(unit)
        teleport.location_y = util_units.get_y(unit)

        # Begin handles ownership changes.
        change_own = begin.add_effect(effects.change_ownership)
        change_own.number_of_units_selected = 1
        change_own.player_source = 3
        change_own.player_target = from_player
        change_own.selected_object_id = uid

        # Changes points (using the player number).
        unit_name = util_units.get_name(u)
        pts = self._events[fight_index].points[unit_name]
        prefix = f'[R{fight_index}]' if fight_index else '[T]'
        pretty_name = util.pretty_print_name(unit_name)
        change_pts_name = f'{prefix} P{from_player} loses {pretty_name} ({uid})'
        change_pts = self._add_trigger(change_pts_name)
        unit_killed = change_pts.add_condition(conditions.destroy_object)
        unit_killed.unit_object = uid
        if from_player == 1:
            self._add_effect_p2_score(change_pts, pts)
            util_triggers.add_cond_destroy_obj(p2_wins, uid)
            self._add_deactivate(p1_wins.name.rstrip('\x00'), change_pts_name)
        else:
            self._add_effect_p1_score(change_pts, pts)
            util_triggers.add_cond_destroy_obj(p1_wins, uid)
            self._add_deactivate(p2_wins.name.rstrip('\x00'), change_pts_name)
        util_triggers.add_effect_remove_obj(cleanup, uid, from_player)


def build_scenario(scenario_template: str = SCENARIO_TEMPLATE,
                   unit_template: str = UNIT_TEMPLATE,
                   event_json: str = event.DEFAULT_FILE,
                   output: str = OUTPUT):
    """
    Builds the scenario.

    Parameters:
        scenario_template: The source of the map, players, and scenario
            objectives. The units are copied to this scenario, and triggers
            are added to it.
        unit_template: A template of unit formations to copy for fights.
        output: The output path to which the resulting scenario is written.
    """
    units_scn = AoE2Scenario(unit_template)
    fight_data_list = event.load_fight_data(event_json)
    events = event.make_fights(units_scn, fight_data_list,
                               (FIGHT_CENTER_X, FIGHT_CENTER_Y), FIGHT_OFFSET)
    scn = AoE2Scenario(scenario_template)
    scn_data = ScnData(scn, events)
    scn_data.setup_scenario()
    scn_data.write_to_file(output)


def call_build_scenario(args):
    """Unpacks arguments from command line args and builds the scenario."""
    scenario_map = args.map[0]
    units_scn = args.units[0]
    event_json = args.events[0]
    out = args.output[0]

    # Checks the output path is different from all input paths.
    matches = []
    if out == scenario_map:
        matches.append('map')
    if out == units_scn:
        matches.append('units')
    if out == event_json:
        matches.append('events')
    if matches:
        conflicts = ', '.join(matches)
        msg = f"The output path '{out}' conflicts with: {conflicts}."
        raise ValueError(msg)

    build_scenario(scenario_template=scenario_map, unit_template=units_scn,
                   event_json=event_json, output=out)


def build_publish_files(args):
    """
    Unpacks arguments from command line args and builds the files needed
    to upload the scenario as a mod.
    """
    raise AssertionError('Not implemented.')


def scratch(args): # pylint: disable=unused-argument
    """Runs a simple test experiment."""
    scratch_path = 'scratch.aoe2scenario'
    print(scratch_path)
    scn = AoE2Scenario(SCENARIO_TEMPLATE)
    p3_units = util_units.get_units_array(scn, 3)
    for u in p3_units:
        if util_units.get_unit_constant(u) == 82:
            x = util_units.get_x(u)
            y = util_units.get_y(u)
            unit_id = util_units.get_id(u)
            print(f'id: {unit_id} - ({x}, {y})')


def main():
    parser = argparse.ArgumentParser(description='Builds Micro Wars!')
    subparsers = parser.add_subparsers()

    parser_build = subparsers.add_parser('build', help='Builds the scenario.')
    parser_build.add_argument('--map', nargs=1, default=[SCENARIO_TEMPLATE],
                              help='Filepath to the map template input file.')
    parser_build.add_argument('--units', nargs=1, default=[UNIT_TEMPLATE],
                              help='Filepath to the unit template input file.')
    parser_build.add_argument('--events', nargs=1, default=[event.DEFAULT_FILE],
                              help='Filepath to the event json file.')
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
