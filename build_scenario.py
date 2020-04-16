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
import math
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
from util_triggers import ChangeVarOp, VarValComp
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


# Delay before running the cleanup trigger (necessary to all for seeing
# unit death animations to completion before the units are removed).
DELAY_CLEANUP = 3


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


# Trigger name for creating map revealers for center fights.
REVEALER_FIGHT_CREATE_NAME = '[I] Create Fight Map Revealers'


# Trigger name for hiding map revealers for center fights.
REVEALER_FIGHT_HIDE_NAME = '[I] Hide Fight Map Revealers'


# Unit ID of Flag A.
FLAG_A_UCONST = 600


# Unit ids for Player 1's flags around the DauT Castle hill.
DC_FLAGS_P1 = [168, 149, 151, 153, 170, 155, 172, 173, 175, 178]


# Unit ids for Player 2's flags around the DauT Castle hill.
DC_FLAGS_P2 = [148, 150, 152, 169, 154, 171, 156, 176, 174, 177]


# The Stone quantity to assign for each player at the start of the
# DauT Castle minigame.
DC_STONE = 1300


# Unit constant of a Castle.
CASTLE_UCONST = 82


# Unit ID for Player 1's Castle in the Castle Siege minigame.
CS_P1_CASTLE_ID = 813


# Unit ID for Player 2's Castle in the Castle Siege minigame.
CS_P2_CASTLE_ID = 830


class _TriggerNames:
    """An instance represents the names of triggers for a specific index."""

    def __init__(self, index: int):
        """
        Initializes a new _TriggerNames object for the given index.

        Raises a ValueError if index < 0.
        """
        if index < 0:
            raise ValueError(f'index {index} must be nonnegative.')
        self._index = index
        self._prefix = f'[R{index}]' if index else '[T]'

    @property
    def index(self) -> int:
        """Returns the index represented by this _TriggerNames object."""
        return self._index

    @property
    def prefix(self) -> str:
        """Returns the prefix for the trigger names."""
        return self._prefix

    @property
    def init(self) -> str:
        """Returns the name of the init trigger."""
        return (f'{self.prefix} Initialize Round'
                if self.index
                else TIEBREAKER_INIT_NAME)

    @property
    def begin(self) -> str:
        """Returns the name of the begin trigger."""
        return f'{self.prefix} Begin Round'

    @property
    def p1_wins(self) -> str:
        """Returns the name of the p1 wins trigger."""
        return f'{self.prefix} Player 1 Wins Round'

    @property
    def p2_wins(self) -> str:
        """Returns the name of the p2 wins trigger."""
        return f'{self.prefix} Player 2 Wins Round'

    @property
    def cleanup(self) -> str:
        """Returns the name of the cleanup trigger."""
        return f'{self.prefix} Cleanup Round'

    @property
    def inc(self) -> str:
        """Returns the name of the increment trigger."""
        return f'{self.prefix} Increment Round'

    def __str__(self):
        return f'Trigger Names at index {self.index}'


class _RoundTriggers:
    """
    An instance contains the basic 6 triggers for each round in the
    scenario data.
    The object is initialized with the basic conditions and effects
    that are repeated for every round. Each trigger has a property
    that can be used to modify the trigger specifically for each
    round.
    """

    # TODO figure out how to use ScnData as a type annotation for scn,
    # even though the class hasn't been created yet (gets a red line in pylint)
    def __init__(self, scn_data, index: int):
        """
        Initializes a base set of triggers in the scenario data
        for the given index.

        Raises a ValueError if index is negative.
        """
        if index < 0:
            raise ValueError(f'index {index} must be nonnegative.')
        self._scn = scn_data
        self._index = index
        self._names = _TriggerNames(index)

        self._init = self._scn._add_trigger(self.names.init)
        if index:
            init_var = self._init.add_condition(conditions.variable_value)
            init_var.amount_or_quantity = index
            init_var.variable = self._scn._var_ids['round']
            init_var.comparison = VarValComp.equal.value
            # Begins displaying the objective Round 1/n in round 1.
            if index == 1:
                self._scn._add_activate(self.names.init, ROUND_OBJ_NAME)
            # Displays the round objectives.
            obj_names = self._scn._round_objectives[index]
            for obj_name in obj_names:
                self._scn._add_activate(self.names.init, obj_name)
        else:
            # Disables init for the tiebreaker. The tiebreaker launches
            # only when enabled manually.
            self._init.enabled = False
            self._scn._add_activate(self.names.init, TIEBREAKER_OBJ_NAME)

        # Turns on the middle fight map revealers if the current
        # index is a fight and the revealers are currently off, that is,
        # if fight is the very first event or the previous event was
        # a minigame.
        if (isinstance(self._scn._events[index], Fight)
                and (index == 1
                     or isinstance(self._scn._events[index - 1], Minigame))):
            self._scn._add_activate(self.names.init, REVEALER_FIGHT_CREATE_NAME)

        self._scn._research_techs(self._init, index)

        self._scn._add_activate(self.names.init, self.names.begin)

        self._begin = self._scn._add_trigger(self.names.begin)
        self._begin.enabled = False
        util_triggers.add_cond_timer(self._begin, DELAY_ROUND_BEFORE)

        self._p1_wins = self._scn._add_trigger(self.names.p1_wins)
        self._p1_wins.enabled = False
        self._p2_wins = self._scn._add_trigger(self.names.p2_wins)
        self._p2_wins.enabled = False

        self._cleanup = self._scn._add_trigger(self.names.cleanup)
        self._cleanup.enabled = False
        util_triggers.add_cond_timer(self._cleanup, DELAY_CLEANUP)
        self._scn._add_activate(self.names.cleanup, self.names.inc)
        # Disables the Round N/N counter for the final round.
        if index == self._scn.num_rounds:
            self._scn._add_deactivate(self.names.cleanup, ROUND_OBJ_NAME)
        # TODO handle map revealers for minigames
        elif isinstance(self._scn._events[index + 1], Minigame):
            self._scn._add_activate(self.names.cleanup,
                                    REVEALER_FIGHT_HIDE_NAME)
        # Deactivates round-specific objectives
        obj_names = self._scn._round_objectives[index]
        for obj_name in obj_names:
            self._scn._add_deactivate(self.names.cleanup, obj_name)

        self._inc = self._scn._add_trigger(self.names.inc)
        self._inc.enabled = False
        util_triggers.add_cond_timer(self._inc, DELAY_ROUND_AFTER)

        if index:
            change_round = self._inc.add_effect(effects.change_variable)
            change_round.quantity = 1
            change_round.operation = ChangeVarOp.add.value
            change_round.from_variable = self._scn._var_ids['round']
            change_round.message = 'round'
        else:
            # The tiebreaker activates checking the winner, rather than
            # changing the round.
            self._scn._add_deactivate(self.names.inc, TIEBREAKER_OBJ_NAME)
            self._scn._add_activate(self.names.inc, CHECK_WINNER_NAME)

    @property
    def index(self):
        """Returns the index of this round of triggers."""
        return self._index

    @property
    def names(self):
        """Returns the name container for this round of triggers."""
        return self._names

    @property
    def init(self):
        """Returns the init trigger."""
        return self._init

    @property
    def begin(self):
        """Returns the begin trigger."""
        return self._begin

    @property
    def p1_wins(self):
        """Returns the p1 wins trigger."""
        return self._p1_wins

    @property
    def p2_wins(self):
        """Returns the p2 wins trigger."""
        return self._p2_wins

    @property
    def cleanup(self):
        """Returns the cleanup trigger."""
        return self._cleanup

    @property
    def inc(self):
        """Returns the round increment trigger."""
        return self._inc

    def __str__(self):
        return f'Triggers for round {self.index}.'


class ScnData:
    """
    An instance represents data to mutate while processing a scenario.

    The typical use case for creating a Micro Wars scenario is:
    1. Perform file I/O to parse the template scenario and event files.
    2. Pass the parsed data to the initializer to create a ScnData object.
    3. Call the setup_scenario method.
    4. Call the write_to_file method.
    """

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

        # The set of technologies researched by the currently added triggers.
        self._researched_techs = set()

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

    def _add_effect_research_tech(self, trigger: TriggerObject,
                                  tech_name: str) -> None:
        """
        Adds an effect to trigger to research the technology given by
        tech_name if it's not already researched. The technology is researched
        for all players.

        Checks tech_name is a valid technology name.
        """
        assert util_techs.is_tech(tech_name), f'{tech_name} is not a tech.'
        if tech_name not in self._researched_techs:
            self._researched_techs.add(tech_name)
            tech_id = util_techs.TECH_IDS[tech_name]
            for player in (1, 2, 3):
                util_triggers.add_effect_research_tech(trigger, tech_id, player)

    def _research_techs(self, trigger: TriggerObject, index: int) -> None:
        """
        Adds effects to trigger to research the initial techs for the event
        in the round given by index.
        """
        e = self._events[index]
        if isinstance(e, Minigame):
            name = e.name
            if name == 'Galley Micro':
                techs = ['fletching']
            elif name == 'DauT Castle':
                techs = ['loom', 'castle_age', 'crossbowman',
                         'elite_skirmisher', 'fletching', 'bodkin_arrow',
                         'sanctity', 'atonement', 'redemption']
            elif name == 'Castle Siege':
                techs = ['loom', 'imperial_age', 'hoardings', 'chemistry',
                         'capped_ram', 'siege_ram', 'pikeman', 'halberdier']
            else:
                raise AssertionError(f'No techs specified for minigame {name}.')
        else:
            techs = e.techs
        for tech in techs:
            self._add_effect_research_tech(trigger, tech)


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
        # In lieu of this feature, we create a workaround by adding Stone
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
        stone_2197.resource_type_or_tribute_list = util_triggers.ACC_ATTR_STONE
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
        create_revealers = self._add_trigger(REVEALER_FIGHT_CREATE_NAME)
        create_revealers.enabled = False
        create_revealers.looping = True
        self._add_deactivate(REVEALER_FIGHT_CREATE_NAME,
                             REVEALER_FIGHT_CREATE_NAME)
        for player in (1, 2):
            for (x, y) in REVEALER_LOCATIONS:
                create = create_revealers.add_effect(effects.create_object)
                create.object_list_unit_id = UNIT_ID_MAP_REVEALER
                create.player_source = player
                create.location_x = x
                create.location_y = y

        hide_revealers = self._add_trigger(REVEALER_FIGHT_HIDE_NAME)
        hide_revealers.enabled = False
        hide_revealers.looping = True
        self._add_deactivate(REVEALER_FIGHT_HIDE_NAME, REVEALER_FIGHT_HIDE_NAME)
        for player in (1, 2):
            remove = hide_revealers.add_effect(effects.remove_object)
            remove.player_source = player
            x1, y1 = util.min_point(REVEALER_LOCATIONS)
            x2, y2 = util.max_point(REVEALER_LOCATIONS)
            util_triggers.set_effect_area(remove, x1, y1, x2, y2)

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

    def _add_minigame_objective(self, mg: Minigame, index: int) -> None:
        """
        Adds the objectives corresponding to minigame mg to the
        index of _round_objectives.

        Checks _round_objective[index] contains an empty list.
        """
        assert self._round_objectives[index] == []
        if mg.name == 'Galley Micro':
            self._add_galley_micro_objectives(index)
        elif mg.name == 'DauT Castle':
            self._add_daut_castle_objectives(index)
        elif mg.name == 'Castle Siege':
            self._add_castle_siege_objectives(index)
        else:
            raise AssertionError(f'Minigame {mg.name} not implemented.')

    def _add_galley_micro_objectives(self, index: int) -> None:
        """Adds the objectives for the Galley Micro minigame"""
        obj_galley_name = f'[O] Round {index} Galley Micro'
        self._round_objectives[index].append(obj_galley_name)
        obj_galley = self._add_trigger(obj_galley_name)
        obj_galley.enabled = False
        obj_galley.description = '* Galley: 10'
        obj_galley.short_description = '* Galley: 10'
        obj_galley.display_as_objective = True
        obj_galley.display_on_screen = True
        obj_galley.description_order = 50
        obj_galley.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_galley)

    def _add_daut_castle_objectives(self, index: int):
        """Adds the objectives for the DauT Castle minigame."""
        obj_daut_name = f'[O] Round {index} DauT Castle'
        self._round_objectives[index].append(obj_daut_name)
        obj_daut = self._add_trigger(obj_daut_name)
        obj_daut.enabled = False
        obj_daut.description = "Build a Castle (strictly) inside of the Flags, or defeat your opponent's army." # pylint: disable=line-too-long
        obj_daut.short_description = 'Build a Castle inside the Flags.'
        obj_daut.display_as_objective = True
        obj_daut.display_on_screen = True
        obj_daut.description_order = 50
        obj_daut.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_daut)

        p3_units = util_units.get_units_array(self._scn, 3)
        units_in_area = util_units.units_in_area(p3_units, 0.0, 0.0, 80.0, 80.0)
        flag_positions = [
            (util_units.get_x(flag_a), util_units.get_y(flag_a))
            for flag_a in units_in_area
            if util_units.get_unit_constant(flag_a) == FLAG_A_UCONST
        ]
        x1, y1 = (math.floor(pos) for pos in util.min_point(flag_positions))
        x2, y2 = (math.ceil(pos) for pos in util.max_point(flag_positions))
        # Adjusts positions to keep the Castle strictly inside the flags.
        x1 += 3
        y1 += 3
        x2 -= 3
        y2 -= 3

        obj_daut_p1_name = f'[O] DauT Castle Player 1 Castle Constructed'
        self._round_objectives[index].append(obj_daut_p1_name)
        obj_daut_p1 = self._add_trigger(obj_daut_p1_name)
        obj_daut_p1.enabled = False
        obj_daut_p1.description = '- Player 1 Castle Constructed'
        obj_daut_p1.short_description = '- P1 Castle Constructed'
        obj_daut_p1.display_as_objective = True
        obj_daut_p1.display_on_screen = True
        obj_daut_p1.description_order = 49
        obj_daut_p1.mute_objectives = True
        p1_castle_in_area = obj_daut_p1.add_condition(conditions.object_in_area)
        p1_castle_in_area.amount_or_quantity = 1
        p1_castle_in_area.player = 1
        p1_castle_in_area.object_list = CASTLE_UCONST
        util_triggers.set_cond_area(p1_castle_in_area, x1, y1, x2, y2)

        obj_daut_p2_name = f'[O] DauT Castle Player 2 Castle Constructed'
        self._round_objectives[index].append(obj_daut_p2_name)
        obj_daut_p2 = self._add_trigger(obj_daut_p2_name)
        obj_daut_p2.enabled = False
        obj_daut_p2.description = '- Player 2 Castle Constructed'
        obj_daut_p2.short_description = '- P2 Castle Constructed'
        obj_daut_p2.display_as_objective = True
        obj_daut_p2.display_on_screen = True
        obj_daut_p2.description_order = 48
        obj_daut_p2.mute_objectives = True
        p2_castle_in_area = obj_daut_p2.add_condition(conditions.object_in_area)
        p2_castle_in_area.amount_or_quantity = 1
        p2_castle_in_area.player = 2
        p2_castle_in_area.object_list = CASTLE_UCONST
        util_triggers.set_cond_area(p2_castle_in_area, x1, y1, x2, y2)

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
        util_triggers.add_cond_hp0(obj_cs_p1, CS_P1_CASTLE_ID)

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
        util_triggers.add_cond_hp0(obj_cs_p2, CS_P2_CASTLE_ID)

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
        if mg.name == 'Galley Micro':
            self._add_galley_micro(index)
        elif mg.name == 'DauT Castle':
            self._add_daut_castle(index)
        elif mg.name == 'Castle Siege':
            self._add_castle_siege(index)
        else:
            raise AssertionError(f'Minigame {mg.name} is not implemented.')

    def _add_galley_micro(self, index: int) -> None:
        """
        Adds the Galley Micro minigame at the given index.

        Checks the index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)

        # TODO map revealers

        for player in (1, 2):
            change_view = rts.init.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x = 120
            change_view.location_y = 200

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        util_triggers.add_cond_pop0(rts.p1_wins, 2)
        self._add_activate(rts.names.begin, rts.names.p2_wins)
        util_triggers.add_cond_pop0(rts.p2_wins, 1)

        prefix = f'[R{index}]'
        galleys = util_units.get_units_array(self._scn, 3)
        galleys = util_units.units_in_area(galleys, 80, 160, 160, 240)
        for galley in galleys:
            pos = util_units.get_x(galley) + util_units.get_y(galley)
            player = 1 if pos < 320 else 2
            util_triggers.add_effect_change_own_unit(rts.begin, 3, player,
                                                     util_units.get_id(galley))

            uid = util_units.get_id(galley)
            change_pts_name = f'{prefix} P{player} loses Galley ({uid})'
            change_pts = self._add_trigger(change_pts_name)
            change_pts.enabled = False
            self._add_activate(rts.names.begin, change_pts_name)
            galley_sunk = change_pts.add_condition(conditions.destroy_object)
            galley_sunk.unit_object = uid
            if player == 1:
                self._add_effect_p2_score(change_pts, 10)
                self._add_deactivate(rts.names.p1_wins, change_pts_name)
            else:
                self._add_effect_p1_score(change_pts, 10)
                self._add_deactivate(rts.names.p2_wins, change_pts_name)

            util_triggers.add_effect_remove_obj(rts.cleanup, uid, player)

        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_activate(rts.names.p1_wins, rts.names.cleanup)
        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        self._add_activate(rts.names.p2_wins, rts.names.cleanup)


    def _add_daut_castle(self, index: int) -> None:
        """
        Adds the DauT Castle minigame at the given index.

        Checks the index is not 0 (cannot us a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        prefix = f'[R{index}]' if index else '[T]'
        p1_wins_name = f'{prefix} Player 1 Wins Round'
        p1_builds_castle_name = f'{prefix} Player 1 Constructs Castle'
        p1_loses_army_name = f'{prefix} Player 1 Loses Army'
        p2_wins_name = f'{prefix} Player 2 Wins Round'
        p2_builds_castle_name = f'{prefix} Player 2 Constructs Castle'
        p2_loses_army_name = f'{prefix} Player 2 Loses Army'

        # Transitions map revealers.
        # TODO make DauT Castle Map Revealers
        # if index == 1 or isinstance(self._events[index-1], Minigame):
        #     self._add_activate(init_name, REVEALER_FIGHT_CREATE_NAME)

        for player in (1, 2):
            util_triggers.add_effect_modify_res(rts.init, player, 1300,
                                                util_triggers.ACC_ATTR_STONE)

        p3_units = util_units.get_units_array(self._scn, 3)
        units_in_area = util_units.units_in_area(p3_units, 0.0, 0.0, 80.0, 80.0)
        flags = [
            flag_a
            for flag_a in units_in_area
            if util_units.get_unit_constant(flag_a) == FLAG_A_UCONST
        ]
        flag_positions = [
            (util_units.get_x(flag_a), util_units.get_y(flag_a))
            for flag_a in flags
        ]
        # The min and max positions in which the Castle can be constructed.
        x1, y1 = (math.floor(pos) for pos in util.min_point(flag_positions))
        x2, y2 = (math.ceil(pos) for pos in util.max_point(flag_positions))
        avg = util_units.avg_pos(flags)
        # Adjusts positions to keep the Castle strictly inside the flags.
        x1 += 3
        y1 += 3
        x2 -= 3
        y2 -= 3

        for player in (1, 2):
            change_view = rts.init.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x = round(avg[0])
            change_view.location_y = round(avg[1])

        # Begin changes ownership.
        p3_units = util_units.get_units_array(self._scn, 3)
        daut_units = util_units.units_in_area(p3_units, 0.0, 0.0, 80.0, 80.0)
        for unit in daut_units:
            if util_units.get_unit_constant(unit) == FLAG_A_UCONST:
                continue
            pos = util_units.get_x(unit) + util_units.get_y(unit)
            player_target = 1 if pos < 80.0 else 2
            util_triggers.add_effect_change_own_unit(
                rts.begin, 3, player_target, util_units.get_id(unit))
        for k, flag_uids in enumerate((DC_FLAGS_P1, DC_FLAGS_P2)):
            player_target = k + 1
            for uid in flag_uids:
                util_triggers.add_effect_change_own_unit(
                    rts.begin, 3, player_target, uid)

        # p1 constructs castle
        p1_builds_castle = self._add_trigger(p1_builds_castle_name)
        p1_builds_castle.enabled = False
        self._add_activate(rts.names.begin, p1_builds_castle_name)
        p1_c_cond = p1_builds_castle.add_condition(conditions.object_in_area)
        p1_c_cond.amount_or_quantity = 1
        p1_c_cond.player = 1
        p1_c_cond.object_list = CASTLE_UCONST
        util_triggers.set_cond_area(p1_c_cond, x1, y1, x2, y2)
        self._add_activate(p1_builds_castle_name, p1_wins_name)
        self._add_deactivate(p1_builds_castle_name, p1_loses_army_name)
        self._add_deactivate(p1_builds_castle_name, p2_builds_castle_name)
        self._add_deactivate(p1_builds_castle_name, p2_loses_army_name)

        # p2 loses army
        p2_loses_army = self._add_trigger(p2_loses_army_name)
        p2_loses_army.enabled = False
        self._add_activate(rts.names.begin, p2_loses_army_name)
        util_triggers.add_cond_pop0(p2_loses_army, 2)
        self._add_activate(p2_loses_army_name, p1_wins_name)
        self._add_deactivate(p2_loses_army_name, p1_builds_castle_name)
        self._add_deactivate(p2_loses_army_name, p1_loses_army_name)
        self._add_deactivate(p2_loses_army_name, p2_builds_castle_name)

        # p1 wins
        rts.p1_wins.enabled = False
        self._add_effect_p1_score(rts.p1_wins, event.MAX_POINTS)
        self._add_activate(p1_wins_name, rts.names.cleanup)

        # p2 constructs castle
        p2_builds_castle = self._add_trigger(p2_builds_castle_name)
        p2_builds_castle.enabled = False
        self._add_activate(rts.names.begin, p2_builds_castle_name)
        p2_c_cond = p2_builds_castle.add_condition(conditions.object_in_area)
        p2_c_cond.amount_or_quantity = 1
        p2_c_cond.player = 2
        p2_c_cond.object_list = CASTLE_UCONST
        util_triggers.set_cond_area(p2_c_cond, x1, y1, x2, y2)
        self._add_activate(p2_builds_castle_name, p2_wins_name)
        self._add_deactivate(p2_builds_castle_name, p2_loses_army_name)
        self._add_deactivate(p2_builds_castle_name, p1_builds_castle_name)
        self._add_deactivate(p2_builds_castle_name, p1_loses_army_name)

        # p1 loses army
        p1_loses_army = self._add_trigger(p1_loses_army_name)
        p1_loses_army.enabled = False
        self._add_activate(rts.names.begin, p1_loses_army_name)
        util_triggers.add_cond_pop0(p1_loses_army, 1)
        self._add_activate(p1_loses_army_name, p2_wins_name)
        self._add_deactivate(p1_loses_army_name, p2_builds_castle_name)
        self._add_deactivate(p1_loses_army_name, p2_loses_army_name)
        self._add_deactivate(p1_loses_army_name, p1_builds_castle_name)

        # p2 wins
        rts.p2_wins.enabled = False
        self._add_effect_p2_score(rts.p2_wins, event.MAX_POINTS)
        self._add_activate(p2_wins_name, rts.names.cleanup)

        # Cleanup removes units from player control.
        change_1_to_3 = rts.cleanup.add_effect(effects.change_ownership)
        change_1_to_3.player_source = 1
        change_1_to_3.player_target = 3
        # Don't include (0, 0), since p1's Invisible Object is there.
        util_triggers.set_effect_area(change_1_to_3, 1, 1, 79, 79)
        change_2_to_3 = rts.cleanup.add_effect(effects.change_ownership)
        change_2_to_3.player_source = 2
        change_2_to_3.player_target = 3
        util_triggers.set_effect_area(change_2_to_3, 0, 0, 79, 79)

        # Removes stone after round is over
        for player in (1, 2):
            util_triggers.add_effect_modify_res(
                rts.cleanup, player, 0, util_triggers.ACC_ATTR_STONE)

    def _add_castle_siege(self, index: int) -> None:
        """
        Adds the Castle Siege minigame at the given index.

        Checks the index is not 0 (cannot us a minigame as the tiebreaker).
        """
        assert index
        prefix = f'[R{index}]' if index else '[T]'
        rts = _RoundTriggers(self, index)
        p1_loses_castle_name = f'{prefix} Player 1 Loses Castle'
        p1_loses_army_name = f'{prefix} Player 1 Loses Army'
        p2_loses_castle_name = f'{prefix} Player 2 Loses Castle'
        p2_loses_army_name = f'{prefix} Player 2 Loses Army'

        # Transitions map revealers.
        # TODO make Castle Siege Map Revealers
        # if index == 1 or isinstance(self._events[index-1], Minigame):
        #     self._add_activate(init_name, REVEALER_FIGHT_CREATE_NAME)

        for player in (1, 2):
            change_view = rts.init.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x = 120
            change_view.location_y = 40
            util_triggers.add_effect_modify_res(
                rts.init, player, 650, util_triggers.ACC_ATTR_STONE)

        # Begin changes ownership
        p3_units = util_units.get_units_array(self._scn, 3)
        cs_units = util_units.units_in_area(p3_units, 80.0, 0, 160.0, 80.0)
        unit_player_pairs = []
        for unit in cs_units:
            pos = util_units.get_x(unit) + util_units.get_y(unit)
            target = 1 if pos < 160.0 else 2
            uid = util_units.get_id(unit)
            util_triggers.add_effect_change_own_unit(rts.begin, 3, target, uid)
            unit_player_pairs.append((uid, target))

        # p2 loses castle
        p2_loses_castle = self._add_trigger(p2_loses_castle_name)
        p2_loses_castle.enabled = False
        self._add_activate(rts.names.begin, p2_loses_castle_name)
        util_triggers.add_cond_hp0(p2_loses_castle, CS_P2_CASTLE_ID)
        self._add_activate(p2_loses_castle_name, rts.names.p1_wins)
        self._add_deactivate(p2_loses_castle_name, p2_loses_army_name)
        self._add_deactivate(p2_loses_castle_name, p1_loses_castle_name)
        self._add_deactivate(p2_loses_castle_name, p1_loses_army_name)

        # p2 loses army
        p2_loses_army = self._add_trigger(p2_loses_army_name)
        p2_loses_army.enabled = False
        self._add_activate(rts.names.begin, p2_loses_army_name)
        util_triggers.add_cond_pop0(p2_loses_army, 2)
        self._add_activate(p2_loses_army_name, rts.names.p1_wins)
        self._add_deactivate(p2_loses_army_name, p1_loses_castle_name)
        self._add_deactivate(p2_loses_army_name, p1_loses_army_name)
        self._add_deactivate(p2_loses_army_name, p2_loses_castle_name)

        # p1 wins
        rts.p1_wins.enabled = False
        self._add_effect_p1_score(rts.p1_wins, event.MAX_POINTS)
        self._add_activate(rts.names.p1_wins, rts.names.cleanup)

        # p1 loses castle
        p1_loses_castle = self._add_trigger(p1_loses_castle_name)
        p1_loses_castle.enabled = False
        self._add_activate(rts.names.begin, p1_loses_castle_name)
        util_triggers.add_cond_hp0(p1_loses_castle, CS_P1_CASTLE_ID)
        self._add_activate(p1_loses_castle_name, rts.names.p2_wins)
        self._add_deactivate(p1_loses_castle_name, p1_loses_army_name)
        self._add_deactivate(p1_loses_castle_name, p2_loses_castle_name)
        self._add_deactivate(p1_loses_castle_name, p2_loses_army_name)

        # p1 loses army
        p1_loses_army = self._add_trigger(p1_loses_army_name)
        p1_loses_army.enabled = False
        self._add_activate(rts.names.begin, p1_loses_army_name)
        util_triggers.add_cond_pop0(p1_loses_army, 1)
        self._add_activate(p1_loses_army_name, rts.names.p2_wins)
        self._add_deactivate(p1_loses_army_name, p2_loses_castle_name)
        self._add_deactivate(p1_loses_army_name, p2_loses_army_name)
        self._add_deactivate(p1_loses_army_name, p1_loses_castle_name)

        # p2 wins
        rts.p2_wins.enabled = False
        self._add_effect_p2_score(rts.p2_wins, event.MAX_POINTS)
        self._add_activate(rts.names.p2_wins, rts.names.cleanup)

        # Cleanup removes units from player control.
        for uid, player_source in unit_player_pairs:
            change_from_player = rts.cleanup.add_effect(
                effects.change_ownership)
            change_from_player.number_of_units_selected = 1
            change_from_player.player_source = player_source
            change_from_player.player_target = 3
            change_from_player.selected_object_id = uid

        # Removes stone after round is over
        for player in (1, 2):
            util_triggers.add_effect_modify_res(
                rts.cleanup, player, 0, util_triggers.ACC_ATTR_STONE)

    def _add_fight(self, index: int, f: Fight) -> None:
        """Adds the fight with the given index."""
        rts = _RoundTriggers(self, index)

        for player in (1, 2):
            change_view = rts.init.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x = FIGHT_CENTER_X
            change_view.location_y = FIGHT_CENTER_Y

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        self._add_activate(rts.names.begin, rts.names.p2_wins)

        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_activate(rts.names.p1_wins, rts.names.cleanup)
        self._add_effect_p1_score(rts.p1_wins, self._events[index].p1_bonus)
        util_triggers.add_cond_pop0(rts.p1_wins, 2)

        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        self._add_activate(rts.names.p2_wins, rts.names.cleanup)
        self._add_effect_p2_score(rts.p2_wins, self._events[index].p2_bonus)
        util_triggers.add_cond_pop0(rts.p2_wins, 1)

        for unit in f.p1_units:
            self._add_fight_unit(index, unit, 1, rts)
        for unit in f.p2_units:
            self._add_fight_unit(index, unit, 2, rts)

    def _add_fight_unit(self, fight_index: int, unit: UnitStruct,
                        from_player: int, rts: _RoundTriggers) -> None:
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

        util_triggers.add_effect_teleport(rts.init, uid, util_units.get_x(unit),
                                          util_units.get_y(unit), 3)

        # Begin handles ownership changes.
        util_triggers.add_effect_change_own_unit(rts.begin, 3, from_player, uid)

        # Changes points (using the player number).
        unit_name = util_units.get_name(u)
        pts = self._events[fight_index].points[unit_name]
        prefix = f'[R{fight_index}]' if fight_index else '[T]'
        pretty_name = util.pretty_print_name(unit_name)
        change_pts_name = f'{prefix} P{from_player} loses {pretty_name} ({uid})'
        change_pts = self._add_trigger(change_pts_name)
        change_pts.enabled = False
        self._add_activate(rts.names.begin, change_pts_name)
        unit_killed = change_pts.add_condition(conditions.destroy_object)
        unit_killed.unit_object = uid
        if from_player == 1:
            self._add_effect_p2_score(change_pts, pts)
            self._add_deactivate(rts.names.p1_wins, change_pts_name)
        else:
            self._add_effect_p1_score(change_pts, pts)
            self._add_deactivate(rts.names.p2_wins, change_pts_name)
        util_triggers.add_effect_remove_obj(rts.cleanup, uid, from_player)


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
    p3_units = util_units.units_in_area(p3_units, 0, 0, 80, 80)
    flags = [u for u in p3_units
             if util_units.get_unit_constant(u) == FLAG_A_UCONST]
    flags.sort(key=lambda u: (util_units.get_x(u), util_units.get_y(u)))
    for flag in flags:
        x = util_units.get_x(flag)
        y = util_units.get_y(flag)
        unit_id = util_units.get_id(flag)
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
