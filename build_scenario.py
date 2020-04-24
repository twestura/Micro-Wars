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
from typing import Dict, List, Set, Tuple
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.objects.trigger_obj import TriggerObject
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.pieces.structs.changed_variable import (
    ChangedVariableStruct
)
from AoE2ScenarioParser.datasets import conditions, effects, techs
from AoE2ScenarioParser.datasets.players import Player
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


# Default scenario from which to pull the Xbow Timer units.
XBOW_TEMPLATE = 'xbow-timer-template.aoe2scenario'


# Default scenario from which to pull the Arena units.
ARENA_TEMPLATE = 'arena-units.aoe2scenario'


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
    ('p1-boar', 0),
    ('p2-boar', 0),
    ('p1-most-relics', 0),
    ('p2-most-relics', 0),
    ('p1-king-killed', 0),
    ('p2-king-killed', 0)
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


# Trigger name for creating map revealers for center fights.
REVEALER_FIGHT_CREATE_NAME = '[I] Create Fight Map Revealers'


# Trigger name for hiding map revealers for center fights.
REVEALER_HIDE_NAME = '[I] Hide Map Revealers'


# Flag A reference ids for Player 1 in Steal the Bacon.
BOAR_FLAGS_1 = [39843, 39845, 39847, 39849, 39851]


# Flag B reference ids for Player 2 in Steal the Bacon.
BOAR_FLAGS_2 = [39842, 39844, 39846, 39848, 39850]


# Maps each flag id to its x and y tile coordinates.
BOAR_FLAG_POS = {
    39842: (187, 106),
    39843: (198, 103),
    39844: (209, 104),
    39845: (217, 112),
    39846: (218, 123),
    39847: (215, 134),
    39848: (204, 137),
    39849: (193, 136),
    39850: (185, 128),
    39851: (184, 117),
}


# Unit reference id for Player 1's starting Scout in Steal the Bacon.
BOAR_SC_1 = 39910


# Position of Player 1's starting Scout in Steal the Bacon.
BOAR_SC_1_POS = (185, 104)


# Position of Player 2's starting Scout in Steal the Bacon.
BOAR_SC_2_POS = (217, 136)


# Unit reference id for Player 2's starting Scout in Steal the Bacon.
BOAR_SC_2 = 39911


# Number of Points scored for capturing a Boar in Steal the Bacon.
BOAR_POINTS = 20


# Unit constant for a Wild Boar.
UCONST_BOAR = 48


# Unit constant for a Scout Cavalry.
UCONST_SC = 448


# Unit constant for an Archer.
UCONST_ARCHER = 4


# Unit constant for a Skirmisher.
UCONST_SKIRM = 7


# Unit constant for a Crossbowman.
UCONST_XBOW = 24


# Unit constant for a Monk.
UCONST_MONK = 125


# Unit constant for a Monastery.
UCONST_MONASTERY = 104


# Unit constant for a Relic.
UCONST_RELIC = 285


# Unit constant for a King.
UCONST_KING = 434


# Positions of the Relics in the Capture the Relic minigame.
RELIC_POSITIONS = {(28, 125), (35, 132), (48, 112)}


# The number of relics captured at the end of a round of Capture the Relic.
ROUND_RELICS = {1: 3, 2: 6, 3: 9}


# Reference IDs for Player 1's Monasteries in Capture the Relic.
MONASTERIES_P1 = [10456, 10457]


# Reference IDs for Player 2's Monasteries in Capture the Relic.
MONASTERIES_P2 = [10454, 10455]


# Reference IDs for each Player's Monasteries in Capture the Relic.
MONASTERIES = {
    1: MONASTERIES_P1,
    2: MONASTERIES_P2,
}


# Unit ID of Flag A.
FLAG_A_UCONST = 600


# Unit ids for Player 1's flags around the DauT Castle hill.
DC_FLAGS_P1 = [168, 149, 151, 153, 170, 155, 172, 178]


# Unit ids for Player 2's flags around the DauT Castle hill.
DC_FLAGS_P2 = [148, 150, 152, 169, 154, 171, 156, 177]


# The Stone quantity to assign for each player at the start of the
# DauT Castle minigame.
DC_STONE = 1300


# Unit constant of a Castle.
CASTLE_UCONST = 82


# Unit ID for Player 1's Castle in the Castle Siege minigame.
CS_P1_CASTLE_ID = 813


# Unit ID for Player 2's Castle in the Castle Siege minigame.
CS_P2_CASTLE_ID = 830


# Unit ID for the flag/king of Player 1 in the Regicide game.
REGICIDE_KING_ID_P1 = 52842


# Unit ID for the flag/king of Player 2 in the Regicide game.
REGICIDE_KING_ID_P2 = 52916


# Center positions of minigames to be used when changing the view.
MINIGAME_CENTERS = {
    'Regicide': (200, 40),
    'Steal the Bacon': (200, 120),
    'Galley Micro': (119, 200),
    'Xbow Timer': (40, 200),
    'Capture the Relic': (40, 120),
    'DauT Castle': (36, 36),
    'Castle Siege': (120, 40),
}


def map_revealer_pos(pos: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Yields a set of map revealers locations centered around pos."""
    x, y = pos
    return [(a, b)
            for a in range(x - 24, x + 25, 3)
            for b in range(y - 24, y + 25, 3)]


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
        # a minigame, or if the event is a minigame (which can't be repeated).
        e = self._scn._events[index]
        prev = self._scn._events[index - 1]
        if isinstance(e, Fight) and (index == 1 or isinstance(prev, Minigame)):
            self._scn._add_activate(self.names.init, REVEALER_FIGHT_CREATE_NAME)
        elif isinstance(self._scn._events[index], Minigame):
            self._scn._add_activate(self.names.init,
                                    self._scn._revealers[e.name])

        center_pos = (MINIGAME_CENTERS[e.name]
                      if isinstance(e, Minigame)
                      else (FIGHT_CENTER_X, FIGHT_CENTER_Y))
        for player in (1, 2):
            change_view = self._init.add_effect(effects.change_view)
            change_view.player_source = player
            change_view.location_x, change_view.location_y = center_pos

        self._scn._research_techs(self._init, index)

        self._scn._add_activate(self.names.init, self.names.begin)

        self._begin = self._scn._add_trigger(self.names.begin)
        self._begin.enabled = False
        util_triggers.add_cond_timer(self._begin, DELAY_ROUND_BEFORE)

        self._p1_wins = self._scn._add_trigger(self.names.p1_wins)
        self._p1_wins.enabled = False
        self._scn._add_activate(self.names.p1_wins, self.names.cleanup)
        self._p2_wins = self._scn._add_trigger(self.names.p2_wins)
        self._p2_wins.enabled = False
        self._scn._add_activate(self.names.p2_wins, self.names.cleanup)

        self._cleanup = self._scn._add_trigger(self.names.cleanup)
        self._cleanup.enabled = False
        util_triggers.add_cond_timer(self._cleanup, DELAY_CLEANUP)
        self._scn._add_activate(self.names.cleanup, self.names.inc)
        # Disables the Round N/N counter for the final round.
        if index == self._scn.num_rounds:
            self._scn._add_deactivate(self.names.cleanup, ROUND_OBJ_NAME)

        if ((isinstance(e, Fight)
             and index != self._scn.num_rounds
             and isinstance(self._scn._events[index + 1], Minigame)
            ) or isinstance(e, Minigame)):
            self._scn._add_activate(self.names.cleanup, REVEALER_HIDE_NAME)

        # Deactivates round-specific objectives
        obj_names = self._scn._round_objectives[index]
        for obj_name in obj_names:
            self._scn._add_deactivate(self.names.cleanup, obj_name)

        self._inc = self._scn._add_trigger(self.names.inc)
        self._inc.enabled = False
        delay_after = DELAY_ROUND_AFTER
        # Hard codes a longer delay for Castle Siege so the destruction
        # animation can play.
        if isinstance(e, Minigame) and e.name == 'Castle Siege':
            delay_after += 5
        util_triggers.add_cond_timer(self._inc, delay_after)

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
    def __init__(self, scn: AoE2Scenario, events, xbow_scn: AoE2Scenario,
                 arena: AoE2Scenario):
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

        # Maps a minigame name to name of its create map revealer trigger.
        # Also maps 'Fight' to the create fight map revealer trigger name.
        self._revealers = dict()

        # Scenario for the Xbow Timer template units.
        self._xbow_scn = xbow_scn

        # Scenario for the arena template units.
        self._arena = arena

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
        return self._scn.object_manager.trigger_manager.add_trigger(name)

    def _add_trigger_header(self, name: str) -> None:
        """
        Appends a trigger section header with title `name`.

        A header trigger serves no functional purpose, but allows
        the trigger list to be broken up into sections so that
        it is more human-readable in the editor.

        Raises a ValueError if creating this trigger would create a
        trigger with a duplicate name.
        """
        header_name = f'-- {name} --'
        header = self._add_trigger(header_name)
        header.enabled = False

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
        trigger_mgr = self._scn.object_manager.trigger_manager
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
        p3_wood = trigger.add_effect(effects.modify_resource)
        p3_wood.quantity = pts
        p3_wood.tribute_list = util_triggers.ACC_ATTR_WOOD
        p3_wood.player_source = 3
        p3_wood.operation = ChangeVarOp.add.value

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
        p3_food = trigger.add_effect(effects.modify_resource)
        p3_food.quantity = pts
        p3_food.tribute_list = util_triggers.ACC_ATTR_FOOD
        p3_food.player_source = 3
        p3_food.operation = ChangeVarOp.add.value

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
            tech_id = techs.tech_names.inverse[tech_name]
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
            if name == 'Steal the Bacon':
                event_techs = ['loom']
            elif name == 'Galley Micro':
                event_techs = ['fletching']
            elif name == 'Xbow Timer':
                event_techs = ['feudal_age', 'fletching']
            elif name == 'Capture the Relic':
                event_techs = ['castle_age', 'crossbowman', 'fletching',
                               'bodkin_arrow']
            elif name == 'DauT Castle':
                event_techs = ['loom', 'castle_age', 'crossbowman',
                               'elite_skirmisher', 'fletching', 'bodkin_arrow',
                               'sanctity', 'atonement', 'redemption']
            elif name == 'Castle Siege':
                event_techs = ['loom', 'imperial_age', 'hoardings', 'chemistry',
                               'capped_ram', 'siege_ram',
                               'pikeman', 'halberdier']
            elif name == 'Regicide':
                event_techs = [
                    'long_swordsman', 'two_handed_swordsman', 'champion',
                    'cavalier', 'paladin', 'elite_cataphract', 'logistica'
                ]
            else:
                raise AssertionError(f'No techs specified for minigame {name}.')
        else:
            event_techs = e.techs
        for tech in event_techs:
            self._add_effect_research_tech(trigger, tech)

    def _name_variables(self) -> None:
        """Sets the names for trigger variables in the scenario."""
        # Accesses _parsed_data directly, since interface is not yet finished.
        trigger_piece = self._scn._parsed_data['TriggerPiece'] # pylint: disable=protected-access
        var_count = trigger_piece.retrievers[6]
        var_change = trigger_piece.retrievers[7].data
        for name, __ in INITIAL_VARIABLES:
            var = ChangedVariableStruct()
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

    def _add_revealer_trigger(self, name: str) -> None:
        """
        Adds a create trigger for map revealers for the event given by name.

        name is 'Fight' for a fight or the name of a minigame for a minigame.
        Checks that name satisfies this precondition.
        """
        assert name == 'Fight' or name in MINIGAME_CENTERS
        create_name = f'[I] Create {name} Map Revealers'
        self._revealers[name] = create_name
        create_revealers = self._add_trigger(create_name)
        create_revealers.enabled = False
        create_revealers.looping = True
        self._add_deactivate(create_name, create_name)
        revealer_pos = map_revealer_pos((FIGHT_CENTER_X, FIGHT_CENTER_Y)
                                        if name == 'Fight'
                                        else MINIGAME_CENTERS[name])
        for player in (1, 2):
            for (x, y) in revealer_pos:
                create = create_revealers.add_effect(effects.create_object)
                create.object_list_unit_id = UNIT_ID_MAP_REVEALER
                create.player_source = player
                create.location_x = x
                create.location_y = y

    def _create_map_revealer_triggers(self) -> None:
        """
        Creates a set of map revealers to cover fight and minigame areas.
        Loops and disables itself.
        Can be re-enabled to make additional map revealers.

        Also adds a "Hide" trigger that removes all map revealers on the map.
        """
        self._add_revealer_trigger('Fight')
        for name in MINIGAME_CENTERS:
            self._add_revealer_trigger(name)

        hide_revealers = self._add_trigger(REVEALER_HIDE_NAME)
        hide_revealers.enabled = False
        hide_revealers.looping = True
        self._add_deactivate(REVEALER_HIDE_NAME, REVEALER_HIDE_NAME)
        for player in (1, 2):
            remove = hide_revealers.add_effect(effects.remove_object)
            remove.player_source = player
            remove.object_list_unit_id = UNIT_ID_MAP_REVEALER
            util_triggers.set_effect_area(remove, 0, 0, 239, 239)

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
        if mg.name == 'Steal the Bacon':
            self._add_steal_the_bacon_objectives(index)
        elif mg.name == 'Galley Micro':
            self._add_galley_micro_objectives(index)
        elif mg.name == 'Xbow Timer':
            self._add_xbow_timer_objectives(index)
        elif mg.name == 'Capture the Relic':
            self._add_ctr_objectives(index)
        elif mg.name == 'DauT Castle':
            self._add_daut_castle_objectives(index)
        elif mg.name == 'Castle Siege':
            self._add_castle_siege_objectives(index)
        elif mg.name == 'Regicide':
            self._add_regicide_objectives(index)
        else:
            raise AssertionError(f'Minigame {mg.name} not implemented.')

    def _add_steal_the_bacon_objectives(self, index: int) -> None:
        """Adds the objectives for the Steal the Bacon minigame."""
        obj_boar_name = f'[O] Round {index} Steal the Bacon'
        self._round_objectives[index].append(obj_boar_name)
        obj_boar = self._add_trigger(obj_boar_name)
        obj_boar.enabled = False
        obj_boar.description = 'Lure a Boar to one of your Flags to capture it. Each Boar is worth 20 Points. Upon capturing a Boar you receive an additional Scout. If all of your Scouts die, you receive one additional Scout after 10 seconds.' # pylint: disable=line-too-long
        obj_boar.short_description = '20 Points per Boar'
        obj_boar.display_as_objective = True
        obj_boar.display_on_screen = True
        obj_boar.description_order = 50
        obj_boar.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_boar)

        obj_boar_1_name = f'[O] Steal the Bacon Player 1 Boar'
        self._round_objectives[index].append(obj_boar_1_name)
        obj_boar_1 = self._add_trigger(obj_boar_1_name)
        obj_boar_1.enabled = False
        obj_boar_1.description = '- Player 1: <p1-boar> / 5 Boar'
        obj_boar_1.short_description = '- P1: <p1-boar> / 5 Boar'
        obj_boar_1.display_as_objective = True
        obj_boar_1.display_on_screen = True
        obj_boar_1.description_order = 49
        obj_boar_1.mute_objectives = True
        boar1_var = obj_boar_1.add_condition(conditions.variable_value)
        boar1_var.amount_or_quantity = 5
        boar1_var.variable = self._var_ids['p1-boar']
        boar1_var.comparison = VarValComp.equal.value

        obj_boar_2_name = f'[O] Steal the Bacon Player 2 Boar'
        self._round_objectives[index].append(obj_boar_2_name)
        obj_boar_2 = self._add_trigger(obj_boar_2_name)
        obj_boar_2.enabled = False
        obj_boar_2.description = '- Player 2: <p2-boar> / 5 Boar'
        obj_boar_2.short_description = '- P2: <p2-boar> / 5 Boar'
        obj_boar_2.display_as_objective = True
        obj_boar_2.display_on_screen = True
        obj_boar_2.description_order = 48
        obj_boar_2.mute_objectives = True
        boar2_var = obj_boar_2.add_condition(conditions.variable_value)
        boar2_var.amount_or_quantity = 5
        boar2_var.variable = self._var_ids['p2-boar']
        boar2_var.comparison = VarValComp.equal.value

    def _add_galley_micro_objectives(self, index: int) -> None:
        """Adds the objectives for the Galley Micro minigame."""
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

    def _add_xbow_timer_objectives(self, index: int) -> None:
        """Adds the objectives the Xbow Timer minigame."""
        obj_xbow_name = f'[O] Round {index} Xbow Timer'
        self._round_objectives[index].append(obj_xbow_name)
        obj_xbow = self._add_trigger(obj_xbow_name)
        obj_xbow.enabled = False
        obj_xbow.description = '* Archer: 1\n* Crossbowman: 1\n* Skirmisher: 1'
        obj_xbow.short_description = (
            '* Archer: 1\n* Crossbowman: 1\n* Skirmisher: 1')
        obj_xbow.display_as_objective = True
        obj_xbow.display_on_screen = True
        obj_xbow.description_order = 50
        obj_xbow.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_xbow)

    def _add_ctr_objectives(self, index: int) -> None:
        """Adds the objectives for the Capture the Relic minigame."""
        obj_ctr_name = f'[O] Round {index} Capture the Relic'
        self._round_objectives[index].append(obj_ctr_name)
        obj_ctr = self._add_trigger(obj_ctr_name)
        obj_ctr.enabled = False
        obj_ctr.description = 'Capturing a Relic is worth 10 points. There are 3 rounds, each with 3 relics to capture. Capturing the most relics in total is worth an additional 10 points.' # pylint: disable=line-too-long
        obj_ctr.display_as_objective = True
        obj_ctr.description_order = 50
        obj_ctr.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_ctr)

        obj_ctr_p1_name = f'[O] Capture the Relic Player 1 Relics'
        self._round_objectives[index].append(obj_ctr_p1_name)
        obj_ctr_p1 = self._add_trigger(obj_ctr_p1_name)
        obj_ctr_p1.enabled = False
        obj_ctr_p1.description = 'Player 1: <Relics Captured, 1> / 9 Relics'
        obj_ctr_p1.short_description = 'P1: <Relics Captured, 1> / 9 Relics'
        obj_ctr_p1.display_as_objective = True
        obj_ctr_p1.display_on_screen = True
        obj_ctr_p1.description_order = 49
        obj_ctr_p1.mute_objectives = True
        obj_ctr_p1_var = obj_ctr_p1.add_condition(conditions.variable_value)
        obj_ctr_p1_var.amount_or_quantity = 1
        obj_ctr_p1_var.variable = self._var_ids['p1-most-relics']
        obj_ctr_p1_var.comparison = VarValComp.equal.value

        obj_ctr_p2_name = f'[O] Capture the Relic Player 2 Relics'
        self._round_objectives[index].append(obj_ctr_p2_name)
        obj_ctr_p2 = self._add_trigger(obj_ctr_p2_name)
        obj_ctr_p2.enabled = False
        obj_ctr_p2.description = 'Player 2: <Relics Captured, 2> / 9 Relics'
        obj_ctr_p2.short_description = 'P2: <Relics Captured, 2> / 9 Relics'
        obj_ctr_p2.display_as_objective = True
        obj_ctr_p2.display_on_screen = True
        obj_ctr_p2.description_order = 48
        obj_ctr_p2.mute_objectives = True
        obj_ctr_p2_var = obj_ctr_p2.add_condition(conditions.variable_value)
        obj_ctr_p2_var.amount_or_quantity = 1
        obj_ctr_p2_var.variable = self._var_ids['p2-most-relics']
        obj_ctr_p2_var.comparison = VarValComp.equal.value

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

    def _add_regicide_objectives(self, index: int):
        """Adds the objectives for the Regicide minigame."""
        obj_king_name = f'[O] Round {index} Regicide'
        self._round_objectives[index].append(obj_king_name)
        obj_king = self._add_trigger(obj_king_name)
        obj_king.enabled = False
        obj_king.description = 'Kill the enemy King to win. Win 1 point for every enemy unit killed. Kill the King to defeat the entire army.' # pylint: disable=line-too-long
        obj_king.display_as_objective = True
        obj_king.description_order = 50
        obj_king.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_king)

        obj_king1_killed_name = f"[O] Regicide Kill Player 1's King"
        self._round_objectives[index].append(obj_king1_killed_name)
        obj_king1_killed = self._add_trigger(obj_king1_killed_name)
        obj_king1_killed.enabled = False
        obj_king1_killed.description = '- Player 1 King Killed'
        obj_king1_killed.short_description = '- P1 King Killed'
        obj_king1_killed.display_as_objective = True
        obj_king1_killed.display_on_screen = True
        obj_king1_killed.description_order = 49
        obj_king1_killed.mute_objectives = True
        k1_destroyed = obj_king1_killed.add_condition(conditions.variable_value)
        k1_destroyed.amount_or_quantity = 1
        k1_destroyed.variable = self._var_ids['p1-king-killed']
        k1_destroyed.comparison = VarValComp.equal.value

        obj_king2_killed_name = f"[O] Regicide Kill Player 2's King"
        self._round_objectives[index].append(obj_king2_killed_name)
        obj_king2_killed = self._add_trigger(obj_king2_killed_name)
        obj_king2_killed.enabled = False
        obj_king2_killed.description = '- Player 2 King Killed'
        obj_king2_killed.short_description = '- P2 King Killed'
        obj_king2_killed.display_as_objective = True
        obj_king2_killed.display_on_screen = True
        obj_king2_killed.description_order = 48
        obj_king2_killed.mute_objectives = True
        k2_destroyed = obj_king2_killed.add_condition(conditions.variable_value)
        k2_destroyed.amount_or_quantity = 1
        k2_destroyed.variable = self._var_ids['p2-king-killed']
        k2_destroyed.comparison = VarValComp.equal.value

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
        if mg.name == 'Steal the Bacon':
            self._add_steal_the_bacon(index)
        elif mg.name == 'Galley Micro':
            self._add_galley_micro(index)
        elif mg.name == 'Xbow Timer':
            self._add_xbow_timer(index)
        elif mg.name == 'Capture the Relic':
            self._add_ctr(index)
        elif mg.name == 'DauT Castle':
            self._add_daut_castle(index)
        elif mg.name == 'Castle Siege':
            self._add_castle_siege(index)
        elif mg.name == 'Regicide':
            self._add_regicide(index)
        else:
            raise AssertionError(f'Minigame {mg.name} is not implemented.')

    def _add_steal_the_bacon(self, index: int) -> None:
        """
        Adds the Steal the Bacon minigame at the given index.

        Checks the index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        prefix = f'[R{index}]'
        umgr = self._scn.object_manager.unit_manager

        boar_units = {
            unit
            for unit in umgr.get_units_in_area(
                x1=160.0, y1=80.0, x2=240.0, y2=160.0, players=[Player.GAIA])
            if unit.unit_id == UCONST_BOAR
        }
        boar_dead_name = f'{prefix} All Boar are Dead'

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        self._add_activate(rts.names.begin, rts.names.p2_wins)
        self._add_activate(rts.names.begin, boar_dead_name)

        util_triggers.add_effect_change_own_unit(rts.begin, 3, 1, BOAR_SC_1)
        util_triggers.add_effect_change_own_unit(rts.begin, 3, 2, BOAR_SC_2)
        for flag in BOAR_FLAGS_1:
            util_triggers.add_effect_change_own_unit(rts.begin, 3, 1, flag)
        for flag in BOAR_FLAGS_2:
            util_triggers.add_effect_change_own_unit(rts.begin, 3, 2, flag)

        for player, pos in ((1, BOAR_SC_1_POS), (2, BOAR_SC_2_POS)):
            scout_respawn1_name = f'{prefix} P{player} Scout Respawn 1'
            scout_countdown_name = f'{prefix} P{player} Scout Countdown'
            scout_respawn1 = self._add_trigger(scout_respawn1_name)
            scout_respawn1.enabled = False
            self._add_activate(rts.names.begin, scout_respawn1_name)
            scout_respawn1.looping = True
            util_triggers.add_cond_pop0(scout_respawn1, player)
            self._add_deactivate(scout_respawn1_name, scout_respawn1_name)
            self._add_activate(scout_respawn1_name, scout_countdown_name)
            self._add_deactivate(rts.names.cleanup, scout_respawn1_name)

            scout_countdown = self._add_trigger(scout_countdown_name)
            scout_countdown.enabled = False
            util_triggers.add_cond_timer(scout_countdown, 10)
            scout_create1 = scout_countdown.add_effect(effects.create_object)
            scout_create1.object_list_unit_id = UCONST_SC
            scout_create1.player_source = player
            scout_create1.location_x, scout_create1.location_y = pos
            self._add_activate(scout_countdown_name, scout_respawn1_name)
            self._add_deactivate(rts.names.cleanup, scout_countdown_name)

        for player, flags in ((1, BOAR_FLAGS_1), (2, BOAR_FLAGS_2)):
            for uid in flags:
                name = f'{prefix} P{player} Capture at Flag {uid}'
                self._add_activate(rts.names.begin, name)
                capture = self._add_trigger(name)
                capture.enabled = False
                flag_x, flag_y = BOAR_FLAG_POS[uid]
                boar_in_area = capture.add_condition(conditions.object_in_area)
                boar_in_area.amount_or_quantity = 1
                boar_in_area.player = 0
                boar_in_area.object_list = UCONST_BOAR
                util_triggers.set_cond_area(boar_in_area,
                                            flag_x, flag_y, flag_x, flag_y)

                boar_remove = capture.add_effect(effects.remove_object)
                boar_remove.object_list_unit_id = UCONST_BOAR
                boar_remove.player_source = 0
                util_triggers.set_effect_area(
                    boar_remove, flag_x - 1, flag_y - 1, flag_x + 1, flag_y + 1)

                replace = capture.add_effect(effects.replace_object)
                replace.number_of_units_selected = 1
                replace.player_source = player
                replace.player_target = player
                replace.selected_object_id = uid
                replace.object_list_unit_id = FLAG_A_UCONST
                replace.object_list_unit_id_2 = UCONST_SC
                if player == 1:
                    self._add_effect_p1_score(capture, BOAR_POINTS)
                else:
                    self._add_effect_p2_score(capture, BOAR_POINTS)
                inc_var = capture.add_effect(effects.change_variable)
                inc_var.quantity = 1
                inc_var.operation = ChangeVarOp.add.value
                var_name = f'p{player}-boar'
                inc_var.from_variable = self._var_ids[var_name]
                inc_var.message = var_name

                for win_trigger_name in (rts.names.p1_wins, rts.names.p2_wins):
                    self._add_deactivate(win_trigger_name, name)

        p1_boar = rts.p1_wins.add_condition(conditions.variable_value)
        p1_boar.amount_or_quantity = 5
        p1_boar.variable = self._var_ids['p1-boar']
        p1_boar.comparison = VarValComp.equal.value
        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_deactivate(rts.names.p1_wins, boar_dead_name)

        p2_boar = rts.p2_wins.add_condition(conditions.variable_value)
        p2_boar.amount_or_quantity = 5
        p2_boar.variable = self._var_ids['p2-boar']
        p2_boar.comparison = VarValComp.equal.value
        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        self._add_deactivate(rts.names.p2_wins, boar_dead_name)

        boar_dead = self._add_trigger(boar_dead_name)
        boar_dead.enabled = False
        for boar in boar_units:
            destroy = boar_dead.add_condition(conditions.destroy_object)
            destroy.unit_object = boar.reference_id
        self._add_deactivate(boar_dead_name, rts.names.p1_wins)
        self._add_deactivate(boar_dead_name, rts.names.p2_wins)
        self._add_activate(boar_dead_name, rts.names.cleanup)

        # Cleanup removes units from player control.
        for player_source in (1, 2):
            cleanup_change = rts.cleanup.add_effect(effects.change_ownership)
            cleanup_change.player_source = player_source
            cleanup_change.player_target = 3
            util_triggers.set_effect_area(cleanup_change, 160, 80, 239, 159)

    def _add_galley_micro(self, index: int) -> None:
        """
        Adds the Galley Micro minigame at the given index.

        Checks the index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)

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
            util_triggers.add_effect_change_own_unit(
                rts.begin, 3, player, util_units.get_id(galley))
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
        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)

    def _add_xbow_timer(self, index: int) -> None:
        """
        Adds the Xbow Timer minigame at the given index.

        Checks index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)

        prefix = f'[R{index}]'

        cleanup1_name = f'{prefix} Xbow Timer Cleanup Round 1'
        init2_name = f'{prefix} Xbow Timer Init Round 2'
        begin2_name = f'{prefix} Xbow Timer Begin Round 2'

        p1_r1_win_name = f'{prefix} Xbow Timer Player 1 Wins Round 1'
        p2_r1_win_name = f'{prefix} Xbow Timer Player 2 Wins Round 1'

        res_xbow_1_name = f'{prefix} Xbow Timer Research Player 1'
        res_xbow_2_name = f'{prefix} Xbow Timer Research Player 2'

        timer_r1 = rts.begin.add_effect(effects.display_timer)
        timer_r1.variable_or_timer = 0
        timer_r1.time_unit = util_triggers.TimerUnits.minutes.value
        timer_r1.display_time = 1
        timer_r1.message = '<BLUE>%d until Crossbowman.'
        res_xbow_1 = self._add_trigger(res_xbow_1_name)
        res_xbow_1.enabled = False
        util_triggers.add_cond_timer(res_xbow_1, 60)
        self._add_activate(rts.names.begin, res_xbow_1_name)
        xbow1 = res_xbow_1.add_effect(effects.replace_object)
        xbow1.player_source = 1
        xbow1.player_target = 1
        xbow1.object_list_unit_id = UCONST_ARCHER
        xbow1.object_list_unit_id_2 = UCONST_XBOW
        util_triggers.set_effect_area(xbow1, 0, 160, 79, 239)
        bodkin1_attack = res_xbow_1.add_effect(effects.change_object_attack)
        bodkin1_attack.aa_quantity = 1
        bodkin1_attack.aa_armor_or_attack_type = 3
        bodkin1_attack.player_source = 1
        bodkin1_attack.object_list_unit_id = UCONST_XBOW
        bodkin1_attack.operation = util_triggers.ChangeVarOp.add.value
        util_triggers.set_effect_area(bodkin1_attack, 0, 160, 79, 239)
        bodkin1_range = res_xbow_1.add_effect(effects.change_object_range)
        bodkin1_range.quantity = 1
        bodkin1_range.player_source = 1
        bodkin1_range.object_list_unit_id = UCONST_XBOW
        bodkin1_range.operation = util_triggers.ChangeVarOp.add.value
        util_triggers.set_effect_area(bodkin1_range, 0, 160, 79, 239)

        cleanup1 = self._add_trigger(cleanup1_name)
        cleanup1.enabled = False
        util_triggers.add_cond_timer(cleanup1, DELAY_CLEANUP)
        for clean in (cleanup1, rts.cleanup):
            for player in (1, 2):
                clean_a = clean.add_effect(effects.remove_object)
                clean_a.player_source = player
                clean_a.object_list_unit_id = UCONST_ARCHER
                util_triggers.set_effect_area(clean_a, 0, 160, 79, 239)
                clean_c = clean.add_effect(effects.remove_object)
                clean_c.player_source = player
                clean_c.object_list_unit_id = UCONST_XBOW
                util_triggers.set_effect_area(clean_c, 0, 160, 79, 239)
                clean_s = clean.add_effect(effects.remove_object)
                clean_s.player_source = player
                clean_s.object_list_unit_id = UCONST_SKIRM
                util_triggers.set_effect_area(clean_s, 0, 160, 79, 239)
        self._add_activate(cleanup1_name, init2_name)

        init2 = self._add_trigger(init2_name)
        init2.enabled = False
        util_triggers.add_cond_timer(init2, DELAY_ROUND_AFTER)
        self._add_activate(init2_name, begin2_name)

        begin2 = self._add_trigger(begin2_name)
        begin2.enabled = False
        util_triggers.add_cond_timer(begin2, DELAY_ROUND_BEFORE)
        self._add_activate(begin2_name, rts.names.p1_wins)
        self._add_activate(begin2_name, rts.names.p2_wins)

        archers = util_units.get_units_array(self._xbow_scn, 1)
        archers = util_units.units_in_area(archers, 0.0, 80.0, 160.0, 240.0)
        skirms = util_units.get_units_array(self._xbow_scn, 2)
        skirms = util_units.units_in_area(skirms, 0.0, 80.0, 160.0, 240.0)

        p1_r1_win = self._add_trigger(p1_r1_win_name)
        p1_r1_win.enabled = False
        self._add_activate(rts.names.begin, p1_r1_win_name)
        self._add_deactivate(p2_r1_win_name, p1_r1_win_name)
        util_triggers.add_cond_pop0(p1_r1_win, 2)
        self._add_effect_p1_score(p1_r1_win, 50 - len(skirms))
        self._add_activate(p1_r1_win_name, cleanup1_name)
        clear_timer_p1_r1 = p1_r1_win.add_effect(effects.clear_timer)
        clear_timer_p1_r1.variable_or_timer = 0
        self._add_deactivate(p1_r1_win_name, res_xbow_1_name)

        p2_r1_win = self._add_trigger(p2_r1_win_name)
        p2_r1_win.enabled = False
        self._add_activate(rts.names.begin, p2_r1_win_name)
        self._add_deactivate(p1_r1_win_name, p2_r1_win_name)
        util_triggers.add_cond_pop0(p2_r1_win, 1)
        self._add_effect_p2_score(p2_r1_win, 50 - len(archers))
        self._add_activate(p2_r1_win_name, cleanup1_name)
        clear_timer_p2_r1 = p2_r1_win.add_effect(effects.clear_timer)
        clear_timer_p2_r1.variable_or_timer = 0
        self._add_deactivate(p2_r1_win_name, res_xbow_1_name)

        # Round 1
        for unit in archers:
            archer = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(archer)
            x = int(util_units.get_x(archer))
            y = int(util_units.get_y(archer))
            util_triggers.add_effect_teleport(rts.init, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(rts.begin, 3, 1, uid)
            util_units.set_x(archer, MAP_WIDTH - 0.5)
            util_units.set_y(archer, 0.5)
            change_pts_name = f'{prefix} P1 loses Archer ({uid})'
            change_pts = self._add_trigger(change_pts_name)
            change_pts.enabled = False
            self._add_activate(rts.names.begin, change_pts_name)
            util_triggers.add_cond_destroy_obj(change_pts, uid)
            self._add_deactivate(cleanup1_name, change_pts_name)
            self._add_effect_p2_score(change_pts, 1)

        for unit in skirms:
            skirm = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(skirm)
            x = int(util_units.get_x(skirm))
            y = int(util_units.get_y(skirm))
            util_triggers.add_effect_teleport(rts.init, uid, x, y, 3)
            skirm_pa = rts.init.add_effect(effects.change_object_armor)
            skirm_pa.aa_quantity = 1
            skirm_pa.aa_armor_or_attack_type = 3
            skirm_pa.number_of_units_selected = 1
            skirm_pa.player_source = 3
            skirm_pa.selected_object_id = uid
            skirm_ma = rts.init.add_effect(effects.change_object_armor)
            skirm_ma.aa_quantity = 1
            skirm_ma.aa_armor_or_attack_type = 4
            skirm_ma.number_of_units_selected = 1
            skirm_ma.player_source = 3
            skirm_ma.selected_object_id = uid
            util_triggers.add_effect_change_own_unit(rts.begin, 3, 2, uid)
            util_units.set_x(skirm, MAP_WIDTH - 0.5)
            util_units.set_y(skirm, 0.5)
            change_pts_name = f'{prefix} P2 loses Skirmisher ({uid})'
            change_pts = self._add_trigger(change_pts_name)
            change_pts.enabled = False
            self._add_activate(rts.names.begin, change_pts_name)
            util_triggers.add_cond_destroy_obj(change_pts, uid)
            self._add_deactivate(cleanup1_name, change_pts_name)
            self._add_effect_p1_score(change_pts, 1)

        # Round 2
        for unit in archers:
            archer = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(archer)
            x = int(util_units.get_x(archer))
            y = int(util_units.get_y(archer))
            util_triggers.add_effect_teleport(init2, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(begin2, 3, 2, uid)
            util_units.set_x(archer, MAP_WIDTH - 0.5)
            util_units.set_y(archer, 0.5)
            change_pts_name = f'{prefix} P2 loses Archer ({uid})'
            change_pts = self._add_trigger(change_pts_name)
            change_pts.enabled = False
            self._add_activate(begin2_name, change_pts_name)
            util_triggers.add_cond_destroy_obj(change_pts, uid)
            self._add_deactivate(rts.names.p2_wins, change_pts_name)
            self._add_effect_p1_score(change_pts, 1)

        for unit in skirms:
            skirm = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(skirm)
            x = int(util_units.get_x(skirm))
            y = int(util_units.get_y(skirm))
            util_triggers.add_effect_teleport(init2, uid, x, y, 3)
            skirm_pa = init2.add_effect(effects.change_object_armor)
            skirm_pa.aa_quantity = 1
            skirm_pa.aa_armor_or_attack_type = 3
            skirm_pa.number_of_units_selected = 1
            skirm_pa.player_source = 3
            skirm_pa.selected_object_id = uid
            skirm_ma = init2.add_effect(effects.change_object_armor)
            skirm_ma.aa_quantity = 1
            skirm_ma.aa_armor_or_attack_type = 4
            skirm_ma.number_of_units_selected = 1
            skirm_ma.player_source = 3
            skirm_ma.selected_object_id = uid
            util_triggers.add_effect_change_own_unit(begin2, 3, 1, uid)
            util_units.set_x(skirm, MAP_WIDTH - 0.5)
            util_units.set_y(skirm, 0.5)
            change_pts_name = f'{prefix} P1 loses Skirmisher ({uid})'
            change_pts = self._add_trigger(change_pts_name)
            change_pts.enabled = False
            self._add_activate(begin2_name, change_pts_name)
            util_triggers.add_cond_destroy_obj(change_pts, uid)
            self._add_deactivate(rts.names.p1_wins, change_pts_name)
            self._add_effect_p2_score(change_pts, 1)

        timer_r2 = begin2.add_effect(effects.display_timer)
        timer_r2.variable_or_timer = 0
        timer_r2.time_unit = util_triggers.TimerUnits.minutes.value
        timer_r2.display_time = 1
        timer_r2.message = '<RED>%d until Crossbowman.'
        res_xbow_2 = self._add_trigger(res_xbow_2_name)
        res_xbow_2.enabled = False
        util_triggers.add_cond_timer(res_xbow_2, 60)
        self._add_activate(begin2_name, res_xbow_2_name)
        xbow2 = res_xbow_2.add_effect(effects.replace_object)
        xbow2.player_source = 2
        xbow2.player_target = 2
        xbow2.object_list_unit_id = UCONST_ARCHER
        xbow2.object_list_unit_id_2 = UCONST_XBOW
        util_triggers.set_effect_area(xbow1, 0, 160, 79, 239)
        bodkin2_attack = res_xbow_2.add_effect(effects.change_object_attack)
        bodkin2_attack.aa_quantity = 1
        bodkin2_attack.aa_armor_or_attack_type = 3
        bodkin2_attack.player_source = 2
        bodkin2_attack.object_list_unit_id = UCONST_XBOW
        bodkin2_attack.operation = util_triggers.ChangeVarOp.add.value
        util_triggers.set_effect_area(bodkin1_attack, 0, 160, 79, 239)
        bodkin2_range = res_xbow_2.add_effect(effects.change_object_range)
        bodkin2_range.quantity = 1
        bodkin2_range.player_source = 2
        bodkin2_range.object_list_unit_id = UCONST_XBOW
        bodkin2_range.operation = util_triggers.ChangeVarOp.add.value
        util_triggers.set_effect_area(bodkin1_range, 0, 160, 79, 239)

        # Player 1 Wins Round 2
        util_triggers.add_cond_pop0(rts.p1_wins, 2)
        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_effect_p1_score(rts.p1_wins, 50 - len(archers))
        clear_timer_p1_r2 = rts.p1_wins.add_effect(effects.clear_timer)
        clear_timer_p1_r2.variable_or_timer = 0
        self._add_deactivate(rts.names.p1_wins, res_xbow_2_name)

        # Player 2 Wins Round 2
        util_triggers.add_cond_pop0(rts.p2_wins, 1)
        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        self._add_effect_p2_score(rts.p2_wins, 50 - len(skirms))
        clear_timer_p2_r2 = rts.p2_wins.add_effect(effects.clear_timer)
        clear_timer_p2_r2.variable_or_timer = 0
        self._add_deactivate(rts.names.p2_wins, res_xbow_2_name)

    def _add_ctr(self, index: int) -> None:
        """
        Adds the Capture the Relic minigame at the given index.

        Checks index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)

        # TODO disable Monastery techs

        prefix = f'[R{index}]'

        util_triggers.add_effect_modify_res(
            rts.init, 10000, util_triggers.ACC_ATTR_GOLD)

        begin2_name = f'{prefix} Capture the Relic Begin Round 2'
        begin3_name = f'{prefix} Capture the Relic Begin Round 3'
        create_relics_name = f'{prefix} Capture the Relic Create Relics'
        round_cleanup_name = f'{prefix} Capture the Relic Round Cleanup'

        r1_cond_names = [f'{prefix} Capture the Relic {i}-{ROUND_RELICS[1]-i}'
                         for i in range(ROUND_RELICS[1] + 1)]

        r2_cond_names = [f'{prefix} Capture the Relic {i}-{ROUND_RELICS[2]-i}'
                         for i in range(ROUND_RELICS[2] + 1)]

        r3_cond_names = [f'{prefix} Capture the Relic {i}-{ROUND_RELICS[3]-i}'
                         for i in range(ROUND_RELICS[3] + 1)]

        p1_template = util_units.get_units_array(self._arena, 1)
        p2_template = util_units.get_units_array(self._arena, 2)

        p1_pos = (19, 100)
        p2_pos = (59, 141)

        begin2 = self._add_trigger(begin2_name)
        begin2.enabled = False
        util_triggers.add_cond_timer(begin2, 3)
        for tech_name in ['sanctity', 'redemption']:
            self._add_effect_research_tech(begin2, tech_name)
        begin3 = self._add_trigger(begin3_name)
        begin3.enabled = False
        util_triggers.add_cond_timer(begin3, 3)
        self._add_effect_research_tech(begin3, 'atonement')

        # R1 - P1
        r1p1 = util_units.units_in_area(p1_template, 0.0, 0.0, 10.0, 10.0)
        for unit in r1p1:
            u = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(u)
            util_units.set_x(u, MAP_WIDTH - 0.5)
            util_units.set_y(u, 0.5)
            x = int(util_units.get_x(unit)) - 0 + p1_pos[0] + 1
            y = int(util_units.get_y(unit)) - 0 + p1_pos[1] + 1
            util_triggers.add_effect_teleport(rts.begin, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(rts.begin, 3, 1, uid)

        # R1 - P2
        r1p2 = util_units.units_in_area(p2_template, 10.0, 0.0, 20.0, 10.0)
        for unit in r1p2:
            u = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(u)
            util_units.set_x(u, MAP_WIDTH - 0.5)
            util_units.set_y(u, 0.5)
            x = int(util_units.get_x(unit)) - 19 + p2_pos[0] + 1
            y = int(util_units.get_y(unit)) - 9 + p2_pos[1]
            util_triggers.add_effect_teleport(rts.begin, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(rts.begin, 3, 2, uid)

        # R2 - P1
        r2p1 = util_units.units_in_area(p1_template, 0.0, 10.0, 10.0, 20.0)
        for unit in r2p1:
            u = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(u)
            util_units.set_x(u, MAP_WIDTH - 0.5)
            util_units.set_y(u, 0.5)
            x = int(util_units.get_x(unit)) - 0 + p1_pos[0] + 1
            y = int(util_units.get_y(unit)) - 10 + p1_pos[1] + 1
            util_triggers.add_effect_teleport(begin2, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(begin2, 3, 1, uid)

        # R2 - P2
        r2p2 = util_units.units_in_area(p2_template, 10.0, 10.0, 20.0, 20.0)
        for unit in r2p2:
            u = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(u)
            util_units.set_x(u, MAP_WIDTH - 0.5)
            util_units.set_y(u, 0.5)
            x = int(util_units.get_x(unit)) - 19 + p2_pos[0] + 1
            y = int(util_units.get_y(unit)) - 19 + p2_pos[1]
            util_triggers.add_effect_teleport(begin2, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(begin2, 3, 2, uid)

        # R3 - P1
        r3p1 = util_units.units_in_area(p1_template, 0.0, 20.0, 10.0, 30.0)
        for unit in r3p1:
            u = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(u)
            util_units.set_x(u, MAP_WIDTH - 0.5)
            util_units.set_y(u, 0.5)
            x = int(util_units.get_x(unit)) - 0 + p1_pos[0] + 1
            y = int(util_units.get_y(unit)) - 20 + p1_pos[1] + 1
            util_triggers.add_effect_teleport(begin3, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(begin3, 3, 1, uid)

        # R3 - P2
        r3p2 = util_units.units_in_area(p2_template, 10.0, 20.0, 20.0, 30.0)
        for unit in r3p2:
            u = util_units.copy_unit(self._scn, unit, 3)
            uid = util_units.get_id(u)
            util_units.set_x(u, MAP_WIDTH - 0.5)
            util_units.set_y(u, 0.5)
            x = int(util_units.get_x(unit)) - 19 + p2_pos[0] + 1
            y = int(util_units.get_y(unit)) - 29 + p2_pos[1]
            util_triggers.add_effect_teleport(begin3, uid, x, y, 3)
            util_triggers.add_effect_change_own_unit(begin3, 3, 2, uid)

        change_own_p1 = rts.begin.add_effect(effects.change_ownership)
        change_own_p1.player_source = 3
        change_own_p1.player_target = 1
        util_triggers.set_effect_area(change_own_p1, 0, 80, 39, 119)

        change_own_p2 = rts.begin.add_effect(effects.change_ownership)
        change_own_p2.player_source = 3
        change_own_p2.player_target = 2
        util_triggers.set_effect_area(change_own_p2, 40, 120, 79, 159)

        create_relics = self._add_trigger(create_relics_name)
        create_relics.enabled = False
        create_relics.looping = True
        self._add_deactivate(create_relics_name, create_relics_name)
        for x, y in RELIC_POSITIONS:
            create = create_relics.add_effect(effects.create_object)
            create.player_source = 0
            create.location_x = x
            create.location_y = y
            create.object_list_unit_id = UCONST_RELIC

        for name in (rts.names.begin, begin2_name, begin3_name):
            self._add_activate(name, create_relics_name)

        # Additional consts consists of Monks and all units added by
        # the Arena template scenario.
        p1_tmp = util_units.get_units_array(self._arena, 1)
        p2_tmp = util_units.get_units_array(self._arena, 2)
        additional_consts = {UCONST_MONK}
        for uarray in (p1_tmp, p2_tmp):
            for u in uarray:
                uconst = util_units.get_unit_constant(u)
                additional_consts.add(uconst)

        round_cleanup = self._add_trigger(round_cleanup_name)
        round_cleanup.enabled = False
        round_cleanup.looping = True
        self._add_deactivate(round_cleanup_name, round_cleanup_name)
        for player in (1, 2):
            for uconst in additional_consts:
                remove = round_cleanup.add_effect(effects.remove_object)
                remove.player_source = player
                remove.object_list_unit_id = uconst
                util_triggers.set_effect_area(remove, 0, 80, 79, 159)

        # Capturing 3 relics activates round 2.
        for i, name in enumerate(r1_cond_names):
            j = ROUND_RELICS[1] - i
            relics1 = self._add_trigger(name)
            relics1.enabled = False
            self._add_activate(rts.names.begin, name)
            if i:
                acci = relics1.add_condition(conditions.accumulate_attribute)
                acci.amount_or_quantity = i
                acci.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_RELICS)
                acci.player = 1
            if j:
                accj = relics1.add_condition(conditions.accumulate_attribute)
                accj.amount_or_quantity = j
                accj.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_RELICS)
                accj.player = 2
            for n in r1_cond_names:
                if name != n:
                    self._add_deactivate(name, n)
            self._add_activate(name, round_cleanup_name)
            self._add_activate(name, begin2_name)

        # Capturing 6 relics activates round 3.
        for i, name in enumerate(r2_cond_names):
            j = ROUND_RELICS[2] - i
            relics2 = self._add_trigger(name)
            relics2.enabled = False
            self._add_activate(begin2_name, name)
            if i:
                acci = relics2.add_condition(conditions.accumulate_attribute)
                acci.amount_or_quantity = i
                acci.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_RELICS)
                acci.player = 1
            if j:
                accj = relics2.add_condition(conditions.accumulate_attribute)
                accj.amount_or_quantity = j
                accj.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_RELICS)
                accj.player = 2
            for n in r2_cond_names:
                if name != n:
                    self._add_deactivate(name, n)
            self._add_activate(name, round_cleanup_name)
            self._add_activate(name, begin3_name)

        # Capturing 9 relics checks which player wins and awards points.
        for i, name in enumerate(r3_cond_names):
            j = ROUND_RELICS[3] - i
            relics3 = self._add_trigger(name)
            relics3.enabled = False
            self._add_activate(begin3_name, name)
            if i:
                acci = relics3.add_condition(conditions.accumulate_attribute)
                acci.amount_or_quantity = i
                acci.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_RELICS)
                acci.player = 1
            if j:
                accj = relics3.add_condition(conditions.accumulate_attribute)
                accj.amount_or_quantity = j
                accj.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_RELICS)
                accj.player = 2
            if i > j:
                self._add_activate(name, rts.names.p1_wins)
                self._add_effect_p1_score(relics3, 10)
            else:
                self._add_activate(name, rts.names.p2_wins)
                self._add_effect_p2_score(relics3, 10)
            self._add_effect_p1_score(relics3, i * 10)
            self._add_effect_p2_score(relics3, j * 10)
            for n in r3_cond_names:
                if name != n:
                    self._add_deactivate(name, n)
            self._add_activate(name, round_cleanup_name)

        monastery_loss_names = (f'{prefix} Player 1 Loses Monasteries',
                                f'{prefix} Player 2 Loses Monasteries')
        for k, name in enumerate(monastery_loss_names):
            player = k + 1
            monastery_loss = self._add_trigger(name)
            for monastery in MONASTERIES[player]:
                loss = monastery_loss.add_condition(conditions.destroy_object)
                loss.unit_object = monastery
            self._add_activate(rts.names.begin, name)
            self._add_activate(name, rts.names.cleanup)
            self._add_deactivate(rts.names.p1_wins, name)
            self._add_deactivate(rts.names.p2_wins, name)
            for cond_name in r1_cond_names + r2_cond_names + r3_cond_names:
                self._add_deactivate(name, cond_name)

            if player == 1:
                self._add_effect_p2_score(monastery_loss, 100)
            else:
                self._add_effect_p1_score(monastery_loss, 100)

        # Cleanup removes units from player control.
        change_1_to_3 = rts.cleanup.add_effect(effects.change_ownership)
        change_1_to_3.player_source = 1
        change_1_to_3.player_target = 3
        util_triggers.set_effect_area(change_1_to_3, 0, 80, 79, 159)
        change_2_to_3 = rts.cleanup.add_effect(effects.change_ownership)
        change_2_to_3.player_source = 2
        change_2_to_3.player_target = 3
        util_triggers.set_effect_area(change_2_to_3, 0, 80, 79, 159)

        util_triggers.add_effect_modify_res(
            rts.cleanup, 0, util_triggers.ACC_ATTR_GOLD)


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

        util_triggers.add_effect_modify_res(
            rts.init, 1300, util_triggers.ACC_ATTR_STONE)

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
        # Adjusts positions to keep the Castle strictly inside the flags.
        x1 += 3
        y1 += 3
        x2 -= 3
        y2 -= 3

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
        self._add_effect_p1_score(rts.p1_wins, event.MAX_POINTS)

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
        self._add_effect_p2_score(rts.p2_wins, event.MAX_POINTS)

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
        util_triggers.add_effect_modify_res(
            rts.cleanup, 0, util_triggers.ACC_ATTR_STONE)

    def _add_castle_siege(self, index: int) -> None:
        """
        Adds the Castle Siege minigame at the given index.

        Checks the index is not 0 (cannot us a minigame as the tiebreaker).
        """
        assert index
        # TODO disable Castle units and techs
        prefix = f'[R{index}]' if index else '[T]'
        rts = _RoundTriggers(self, index)
        p1_loses_castle_name = f'{prefix} Player 1 Loses Castle'
        p1_loses_army_name = f'{prefix} Player 1 Loses Army'
        p2_loses_castle_name = f'{prefix} Player 2 Loses Castle'
        p2_loses_army_name = f'{prefix} Player 2 Loses Army'

        util_triggers.add_effect_modify_res(
            rts.init, 650, util_triggers.ACC_ATTR_STONE)

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

        # Cleanup removes units from player control.
        for uid, player_source in unit_player_pairs:
            change_from_player = rts.cleanup.add_effect(
                effects.change_ownership)
            change_from_player.number_of_units_selected = 1
            change_from_player.player_source = player_source
            change_from_player.player_target = 3
            change_from_player.selected_object_id = uid

        # Removes stone after round is over
        util_triggers.add_effect_modify_res(
            rts.cleanup, 0, util_triggers.ACC_ATTR_STONE)

    def _add_regicide(self, index: int) -> None:
        """
        Adds the Regicide minigame at the given index.

        Checks index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        prefix = f'[R{index}]' if index else '[T]'

        kill_king_triggers = dict()

        for k, kingid in enumerate((REGICIDE_KING_ID_P1, REGICIDE_KING_ID_P2)):
            player = k + 1
            replace_flag = rts.init.add_effect(effects.replace_object)
            replace_flag.number_of_units_selected = 1
            replace_flag.selected_object_id = kingid
            replace_flag.player_source = 3
            replace_flag.player_target = player
            replace_flag.object_list_unit_id = FLAG_A_UCONST
            replace_flag.object_list_unit_id_2 = UCONST_KING

            kill_king_name = f"{prefix} Player {player}'s King Killed"
            self._add_activate(rts.names.begin, kill_king_name)
            self._add_deactivate(rts.names.cleanup, kill_king_name)
            kill_king = self._add_trigger(kill_king_name)
            kill_king.enabled = False
            kill_cond = kill_king.add_condition(conditions.object_in_area)
            kill_cond.amount_or_quantity = 1
            kill_cond.player = player
            kill_cond.object_list = UCONST_KING
            kill_cond.inverted = True
            util_triggers.set_cond_area(kill_cond, 160, 0, 239, 79)
            record_kill = kill_king.add_effect(effects.change_variable)
            record_kill.quantity = 1
            record_kill.operation = ChangeVarOp.add.value
            record_kill.from_variable = self._var_ids[f'p{player}-king-killed']
            kill_king_triggers[player] = kill_king

        # Use a small buffer to avoid selecting the units at the very top
        # of the map.
        p3_units = self._scn.object_manager.unit_manager.get_units_in_area(
            x1=160.0, y1=5.0, x2=235.0, y2=80.0, players=[Player.THREE])
        for unit in p3_units:
            if unit.unit_id == FLAG_A_UCONST:
                continue
            pos = unit.x + unit.y
            player = 1 if pos < 240.0 else 2
            uid = unit.reference_id
            util_triggers.add_effect_change_own_unit(rts.begin, 3, player, uid)
            name = unit.name
            pts_name = f"{prefix} Regicide Kill P{player}'s {name} ({uid})"
            self._add_activate(rts.names.begin, pts_name)
            self._add_deactivate(rts.names.cleanup, pts_name)
            award_pts = self._add_trigger(pts_name)
            unit_killed = award_pts.add_condition(conditions.destroy_object)
            unit_killed.unit_object = uid
            king_death = kill_king_triggers[player]
            kill_unit = king_death.add_effect(effects.kill_object)
            kill_unit.number_of_units_selected = 1
            kill_unit.selected_object_id = uid
            kill_unit.player_source = player
            if player == 1:
                self._add_effect_p2_score(award_pts, 1)
            else:
                self._add_effect_p1_score(award_pts, 1)

        stalemate_name = f'{prefix} Regicide Stalemate'
        stalemate = self._add_trigger(stalemate_name)
        stalemate.enabled = False
        self._add_activate(rts.names.begin, stalemate_name)
        self._add_activate(stalemate_name, rts.names.cleanup)
        self._add_deactivate(stalemate_name, rts.names.p1_wins)
        self._add_deactivate(stalemate_name, rts.names.p2_wins)
        for player in (1, 2):
            pop1 = stalemate.add_condition(conditions.accumulate_attribute)
            pop1.player = player
            pop1.amount_or_quantity = 1
            pop1.resource_type_or_tribute_list = (
                util_triggers.ACC_ATTR_POP_HEADROOM)
            popnot2 = stalemate.add_condition(conditions.accumulate_attribute)
            popnot2.player = player
            popnot2.amount_or_quantity = 2
            popnot2.resource_type_or_tribute_list = (
                util_triggers.ACC_ATTR_POP_HEADROOM)
            popnot2.inverted = True

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        util_triggers.add_cond_pop0(rts.p1_wins, 2)

        self._add_activate(rts.names.begin, rts.names.p2_wins)
        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        util_triggers.add_cond_pop0(rts.p2_wins, 1)

        # Cleanup removes units from player control.
        for player_source in (1, 2):
            cleanup_change = rts.cleanup.add_effect(effects.change_ownership)
            cleanup_change.player_source = player_source
            cleanup_change.player_target = 3
            util_triggers.set_effect_area(cleanup_change, 160, 0, 239, 79)

    def _add_fight(self, index: int, f: Fight) -> None:
        """Adds the fight with the given index."""
        rts = _RoundTriggers(self, index)

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        self._add_activate(rts.names.begin, rts.names.p2_wins)

        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_effect_p1_score(rts.p1_wins, self._events[index].p1_bonus)
        util_triggers.add_cond_pop0(rts.p1_wins, 2)

        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
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
                   xbow_template: str = XBOW_TEMPLATE,
                   arena_template: str = ARENA_TEMPLATE,
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
    scn = AoE2Scenario(scenario_template)
    units_scn = AoE2Scenario(unit_template)
    fight_data_list = event.load_fight_data(event_json)
    events = event.make_fights(units_scn, fight_data_list,
                               (FIGHT_CENTER_X, FIGHT_CENTER_Y), FIGHT_OFFSET)
    xbow_scn = (AoE2Scenario(xbow_template)
                if any(isinstance(e, Minigame) and e.name == 'Xbow Timer'
                       for e in events)
                else None)
    arena_scn = (AoE2Scenario(arena_template)
                 if any(isinstance(e, Minigame)
                        and e.name == 'Capture the Relic'
                        for e in events)
                 else None)
    scn_data = ScnData(scn, events, xbow_scn, arena_scn)
    scn_data.setup_scenario()
    scn_data.write_to_file(output)


def call_build_scenario(args):
    """Unpacks arguments from command line args and builds the scenario."""
    scenario_map = args.map[0]
    units_scn = args.units[0]
    event_json = args.events[0]
    xbow_scn = args.xbow[0]
    arena_scn = args.arena[0]
    out = args.output[0]

    # Checks the output path is different from all input paths.
    matches = []
    if out == scenario_map:
        matches.append('map')
    if out == units_scn:
        matches.append('units')
    if out == event_json:
        matches.append('events')
    if out == xbow_scn:
        matches.append('xbow')
    if out == arena_scn:
        matches.append('arena')
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
    # scratch_path = 'scratch.aoe2scenario'
    scn = AoE2Scenario(SCENARIO_TEMPLATE)
    umgr = scn.object_manager.unit_manager
    unit_array = umgr.get_units_in_area(x1=160.0, y1=0.0, x2=240.0, y2=80.0,
                                        players=[Player.THREE])
    for u in unit_array:
        if u.unit_id == FLAG_A_UCONST:
            uid = u.reference_id
            x = u.x
            y = u.y
            print(f'{uid} - ({x}, {y})')


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
    parser_build.add_argument('--xbow', nargs=1, default=[XBOW_TEMPLATE],
                              help='Filepath to the xbow timer units file.')
    parser_build.add_argument('--arena', nargs=1, default=[ARENA_TEMPLATE],
                              help='Filepath to the arena units file.')
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
