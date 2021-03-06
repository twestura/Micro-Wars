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
from collections import Counter, defaultdict
import math
from typing import Dict, List, Set, Tuple
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.objects.condition_obj import ConditionObject
from AoE2ScenarioParser.objects.effect_obj import EffectObject
from AoE2ScenarioParser.objects.trigger_obj import TriggerObject
from AoE2ScenarioParser.pieces.structs.unit import UnitStruct
from AoE2ScenarioParser.pieces.structs.changed_variable import (
    ChangedVariableStruct
)
from AoE2ScenarioParser.datasets import (
    buildings, conditions, effects, techs, units
)
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


# File input name for the all minigames scenario.
ALL_MINIGAMES_EVENTS = 'event-minigames.json'


# File output name for the all minigames scenario.
ALL_MINIGAMES_OUTPUT = 'Minigames.aoe2scenario'


# String names of all minigames.
MINIGAME_NAMES = (
    'Steal the Bacon',
    'Tower Battlefield',
    'Galley Micro',
    'Xbow Timer',
    'Capture the Relic',
    'DauT Castle',
    'Castle Siege',
    'Regicide'
)


# Maps a minigame name to its event file.
INDIVIDUAL_MINIGAME_EVENTS = {
    name: f"event1-{'-'.join(name.lower().split())}.json"
    for name in MINIGAME_NAMES
}


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
    ('p1-battlefield-points', 0),
    ('p2-battlefield-points', 0),
    ('p1-most-relics', 0),
    ('p2-most-relics', 0),
    ('p1-castle-constructed', 0),
    ('p2-castle-constructed', 0),
    ('p1-castle-destroyed', 0),
    ('p2-castle-destroyed', 0),
    ('p1-hero-killed', 0),
    ('p2-hero-killed', 0)
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


# Trigger name for hiding map revealers for center fights.
REVEALER_HIDE_NAME = '[I] Hide Map Revealers'


# Number of Points scored for capturing a Boar in Steal the Bacon.
BOAR_POINTS = 20


# The number of points awarded every interval for holding a Flag.
TOWER_AWARD_POINTS = 1


# The number of seconds to wait to award points for holding a Flag.
TOWER_AWARD_TIME = 5


# The maximum number of Towers that can surround a Tower Battlefield Flag.
TOWER_MAX_NUM = 5
# TODO setting to the area of 25 tiles caused a memory error, so for now
# I'll call it a tie if both players have at least 5 towers.
# TOWER_MAX_NUM = 25


# Unit constant for an Invisible Object.
UCONST_INVISIBLE_OBJECT = 1291


# Unit constant for a Wild Boar.
UCONST_BOAR = 48


# Unit constant for the Boar's dead unit.
UCONST_BOAR_DEAD = 356


# Unit constant for an Archery Range.
UCONST_ARCHERY_RANGE = 87


# Unit constant for a Barracks.
UCONST_BARRACKS = 12


# Unit constant for a House.
UCONST_HOUSE = 70


# Unit constant for a Stable.
UCONST_STABLE = 101


# Unit constant for a Town Center.
UCONST_TC = 109


# Unit constant for a Watch Tower.
UCONST_WATCH_TOWER = 79


# Unit constant for a Scout Cavalry.
UCONST_SC = 448


# Unit constant for a Female Villager.
UCONST_VIL_F = 293


# Unit constant for a Male Villager.
UCONST_VIL_M = 83


# Unit constant for an Archer.
UCONST_ARCHER = 4


# Unit constant for a Skirmisher.
UCONST_SKIRM = 7


# Unit constant for a Crossbowman.
UCONST_XBOW = 24


# Int value for pierce attack and armor classes.
CLASS_PIERCE = 3


# Int value for melee attack and armor classes.
CLASS_MELEE = 4


# Unit constant for a Monk.
UCONST_MONK = 125


# Unit constant for a Monastery.
UCONST_MONASTERY = 104


# Unit constant for a Relic.
UCONST_RELIC = 285


# Unit constant for a King.
UCONST_KING = 434


# Set of all unit constants that represent Villagers.
UCONST_VILS = {
    units.villager_female, units.villager_male,
    units.builder, units.repairer,
    units.lumberjack, units.stone_miner, units.gold_miner,
    units.farmer, units.hunter, units.forager, units.shepherd, units.fisherman
}


# Positions of the Relics in the Capture the Relic minigame.
RELIC_POSITIONS = {(28, 125), (35, 132), (48, 112)}


# The number of relics captured at the end of a round of Capture the Relic.
ROUND_RELICS = {1: 3, 2: 6, 3: 9}


# Unit ID of Flag A.
FLAG_A_UCONST = 600


# The Stone quantity to assign for each player at the start of the
# DauT Castle minigame.
DC_STONE = 1300


# Unit constand for the Genghis Khan hero.
UCONST_GENGHIS_KHAN = 731


# Unit constand for the Joan of Arc hero.
UCONST_JOAN_OF_ARC = 629


# TODO parse these two from the command line
# Default hero to use for the Regicide minigame.
REGICIDE_DEFAULT_HERO = units.king
# REGICIDE_DEFAULT_HERO = UCONST_GENGHIS_KHAN
# REGICIDE_DEFAULT_HERO = UCONST_JOAN_OF_ARC


# Default value for whether to buff the stats of the Regicide hero.
REGICIDE_DEFAULT_BUFF = False
# REGICIDE_DEFAULT_BUFF = True


# Center positions of minigames to be used when changing the view.
MINIGAME_CENTERS = {
    'Steal the Bacon': (200, 120),
    'Tower Battlefield': (200, 200),
    'Galley Micro': (119, 200),
    'Xbow Timer': (40, 200),
    'Capture the Relic': (40, 120),
    'DauT Castle': (36, 36),
    'Castle Siege': (120, 39),
    'Regicide': (200, 40),
}


def other_player(p: Player):
    """
    Returns Player.TWO if p is Player.ONE.
    Returns Player.ONE if p is Player.TWO.
    """
    return p is Player.ONE and Player.TWO or Player.ONE


def map_revealer_pos(pos: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Yields a set of map revealer locations centered around pos."""
    x, y = pos
    return [(a, b)
            for a in range(x - 27, x + 28, 3)
            for b in range(y - 27, y + 28, 3)]


def _tb_hold_flag_name(index: int, player: int, flag: str) -> str:
    """
    Returns the name of the trigger of tower battlefields in
    the given round for increasing the score of the player
    holding the given flag.

    index is the round index of the Tower Battlefield minigame.
    player is 1 or 2.
    flag is one of 'A', 'B', or 'C'.
    """
    return f'[R{index}] Player {player} Holds Flag {flag}'


def _tb_defeated_name(index: int, player: int, enemy_points: int) -> str:
    """
    Returns the name of the trigger of tower battlefields in
    the given round index for the player being defeated when
    the other player has scored the given number of points.
    """
    return f'[R{index}] Player {player} Defeated with {enemy_points} P2 Points Scored' # pylint: disable=line-too-long


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

        # TODO Toggle map revealers before running init effects
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
        center_pos = (MINIGAME_CENTERS[e.name]
                      if isinstance(e, Minigame)
                      else (FIGHT_CENTER_X, FIGHT_CENTER_Y))
        if (isinstance(e, Minigame)
                or isinstance(e, Fight)
                and (index == 1 or isinstance(prev, Minigame))):
            self._scn._add_revealers(self.init, center_pos)

        for p in (Player.ONE, Player.TWO):
            change_view = self._init.add_effect(effects.change_view)
            change_view.player_source = p.value
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
    def __init__(self, scn: AoE2Scenario, events, xbow_scn: AoE2Scenario,
                 arena: AoE2Scenario, regicide_hero=REGICIDE_DEFAULT_HERO,
                 regicide_buff=REGICIDE_DEFAULT_BUFF):
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

        # Hero unit to use for the Regicide minigame.
        self._regicide_hero = regicide_hero

        # True to buff the hero for the Regicide minigame, False otherwise.
        self._regicide_buff = regicide_buff

    @property
    def num_rounds(self):
        """Returns the number of rounds, not including the tiebreaker."""
        return len(self._events) - 1

    def setup_scenario(self):
        """
        Modifies the internal scenario file to support the changes
        for Micro Wars!
        """
        self._clear_unused_units()
        self._name_variables()
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

    def _add_effect_score(self, trigger: TriggerObject, player: Player,
                          pts: int) -> None:
        """Adds effects to trigger to change the player's score by pts."""
        if player == Player.ONE:
            self._add_effect_p1_score(trigger, pts)
        elif player == Player.TWO:
            self._add_effect_p2_score(trigger, pts)
        else:
            raise ValueError(f'{player} is not Player 1 or Player 2.')

    def _create_unit_sequence_explicit(
            self, p: Player, unit: UnitStruct, init: TriggerObject,
            begin: TriggerObject, remove=True,
            buff=REGICIDE_DEFAULT_BUFF) -> None:
        """
        Same as _create_unit_sequence, but allows for manual specification
        of the init and begin triggers, rather than using a _RoundTriggers
        object. See that method's specification for details.

        There's a buff parameter, used specifically for
        the Xbow Timer and regicide minigames. This parameter creates
        skirmishers with +1 to their melee and pierce armors and hero
        units with various bonus stats.
        """
        if remove:
            util_units.remove(self._scn, unit, p)
        x, y = int(unit.x), int(unit.y)

        create = init.add_effect(effects.create_object)
        create.object_list_unit_id = unit.unit_id
        create.player_source = p.value
        if unit.unit_id == units.trebuchet_packed:
            create.facet = util_units.rad_to_facet_treb(unit.rotation)
        elif unit.unit_id == buildings.stone_wall:
            # Hard codes the Facet values for the Capture the Relic
            # Stone Walls. Wall pieces have only 5 rotation values,
            # but they don't seem to make sense.
            if p == Player.ONE:
                if x == 32:
                    create.facet = 2 if y in (98, 113) else 1
                else:
                    create.facet = 2 if x in (17, 32) else 0
            else:
                if x == 47:
                    create.facet = 2 if y in (128, 140) else 1
                else:
                    create.facet = 2 if x in (47, 61) else 0
        else:
            create.facet = util_units.rad_to_facet(unit.rotation)
        create.location_x, create.location_y = x, y

        if buff:
            if unit.unit_id == units.skirmisher:
                for armor in (CLASS_MELEE, CLASS_PIERCE):
                    change = init.add_effect(effects.change_object_armor)
                    change.aa_quantity = 1
                    change.aa_armor_or_attack_type = armor
                    change.player_source = p.value
                    change.operation = ChangeVarOp.add.value
                    util_triggers.set_effect_area(change, 0, 160, 79, 239)
            elif unit.unit_id == units.king:
                change = init.add_effect(effects.change_object_hp)
                change.quantity = 250
                change.player_source = p.value
                change.operation = ChangeVarOp.set_op.value
                change.object_list_unit_id = units.king
                util_triggers.set_effect_area(change, 160, 5, 235, 79)
            elif unit.unit_id == UCONST_GENGHIS_KHAN:
                change_hp = init.add_effect(effects.change_object_hp)
                change_hp.quantity = 100
                change_hp.player_source = p.value
                change_hp.operation = ChangeVarOp.add.value
                change_hp.object_list_unit_id = UCONST_GENGHIS_KHAN
                util_triggers.set_effect_area(change_hp, 160, 5, 235, 79)
                change_attack = init.add_effect(effects.change_object_attack)
                change_attack.aa_quantity = 2
                change_attack.aa_armor_or_attack_type = CLASS_PIERCE
                change_attack.player_source = p.value
                change_attack.operation = ChangeVarOp.add.value
                change_attack.object_list_unit_id = UCONST_GENGHIS_KHAN
                util_triggers.set_effect_area(change_attack, 160, 5, 235, 79)
                change_range = init.add_effect(effects.change_object_range)
                change_range.quantity = 2
                change_range.player_source = p.value
                change_range.operation = ChangeVarOp.add.value
                change_range.object_list_unit_id = UCONST_GENGHIS_KHAN
                util_triggers.set_effect_area(change_range, 160, 5, 235, 79)
            elif unit.unit_id == UCONST_JOAN_OF_ARC:
                change_hp = init.add_effect(effects.change_object_hp)
                change_hp.quantity = 100
                change_hp.player_source = p.value
                change_hp.operation = ChangeVarOp.add.value
                change_hp.object_list_unit_id = UCONST_JOAN_OF_ARC
                util_triggers.set_effect_area(change_hp, 160, 5, 235, 79)
                change_attack = init.add_effect(effects.change_object_attack)
                change_attack.aa_quantity = 2
                change_attack.aa_armor_or_attack_type = CLASS_MELEE
                change_attack.player_source = p.value
                change_attack.operation = ChangeVarOp.add.value
                change_attack.object_list_unit_id = UCONST_JOAN_OF_ARC
                util_triggers.set_effect_area(change_attack, 160, 5, 235, 79)
                for armor_class in (CLASS_MELEE, CLASS_PIERCE):
                    change_armor = init.add_effect(effects.change_object_armor)
                    change_armor.aa_quantity = 1
                    change_armor.aa_armor_or_attack_type = armor_class
                    change_armor.player_source = p.value
                    change_armor.operation = ChangeVarOp.add.value
                    change_armor.object_list_unit_id = UCONST_JOAN_OF_ARC
                    util_triggers.set_effect_area(change_armor, 160, 5, 235, 79)

        to0 = init.add_effect(effects.change_ownership)
        to0.player_source = p.value
        to0.player_target = Player.GAIA.value
        to0.object_list_unit_id = unit.unit_id
        to0.area_1_x, to0.area_1_y = x, y
        to0.area_2_x, to0.area_2_y = x, y

        top = begin.add_effect(effects.change_ownership)
        top.player_source = Player.GAIA.value
        top.player_target = p.value
        top.object_list_unit_id = unit.unit_id
        top.area_1_x, top.area_1_y = x, y
        top.area_2_x, top.area_2_y = x, y

    def _create_unit_sequence(self, p: Player, unit: UnitStruct,
                              rts: _RoundTriggers, remove=True,
                              buff=REGICIDE_DEFAULT_BUFF) -> None:
        """
        Adds a sequence of effects to create the given unit for player p.
        If remove is True, then also removes the unit from p's list of units,
        leaving only the trigger to create it.

        Adds create unit and change ownership effects to rts.init to create
        the unit for the given player, then change it's ownership immediately
        to the Gaia player. The ownership change is necessary, as the
        Map Revealers would change the ownership of the unit were it first
        created as Gaia.

        Adds a change ownership effect to rts.begin to change the ownership of
        the unit to player p.

        Raises a ValueError if remove is True and player p does not already
        have the unit.
        """
        self._create_unit_sequence_explicit(
            p, unit, rts.init, rts.begin, remove, buff)

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
            tid = techs.tech_names.inverse[tech_name]
            for p in (Player.GAIA, Player.ONE, Player.TWO):
                util_triggers.add_effect_research_tech(trigger, tid, p.value)

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
            elif name == 'Tower Battlefield':
                event_techs = ['loom', 'feudal_age', 'man_at_arms']
            elif name == 'Galley Micro':
                event_techs = ['feudal_age', 'fletching']
            elif name == 'Xbow Timer':
                event_techs = ['feudal_age', 'fletching']
            elif name == 'Capture the Relic':
                event_techs = ['castle_age', 'crossbowman', 'fletching',
                               'bodkin_arrow']
            elif name == 'DauT Castle':
                event_techs = [
                    'loom', 'castle_age', 'crossbowman',
                    'elite_skirmisher', 'fletching', 'bodkin_arrow',
                    'sanctity', 'atonement', 'redemption',
                    'bloodlines',
                ]
            elif name == 'Castle Siege':
                event_techs = [
                    'loom', 'imperial_age', 'hoardings', 'chemistry',
                    'capped_ram', 'siege_ram',
                    'pikeman', 'halberdier', 'squires',
                    'elite_cataphract', 'logistica',
                    'forging', 'iron_casting', 'blast_furnace',
                    'scale_mail_armor', 'chain_mail_armor', 'plate_mail_armor',
                    'scale_barding_armor', 'chain_barding_armor',
                    'plate_barding_armor',
                    'fletching', 'bodkin_arrow', 'bracer',
                    'padded_archer_armor', 'leather_archer_armor',
                    'ring_archer_armor',
                    'thumb_ring', 'ballistics', 'chemistry',
                    'siege_engineers',
                    'bloodlines', 'husbandry',
                ]
            elif name == 'Regicide':
                event_techs = [
                    'imperial_age',
                    'squires', 'man_at_arms',
                    'long_swordsman', 'two_handed_swordsman', 'champion',
                    'crossbowman', 'arbalester',
                    'cavalier', 'paladin', 'elite_cataphract', 'logistica',
                    'forging', 'iron_casting', 'blast_furnace',
                    'scale_mail_armor', 'chain_mail_armor', 'plate_mail_armor',
                    'scale_barding_armor', 'chain_barding_armor',
                    'plate_barding_armor',
                    'fletching', 'bodkin_arrow', 'bracer',
                    'padded_archer_armor', 'leather_archer_armor',
                    'ring_archer_armor',
                    'thumb_ring', 'ballistics', 'chemistry',
                    'siege_engineers',
                    'bloodlines', 'husbandry',
                ]
            else:
                raise AssertionError(f'No techs specified for minigame {name}.')
        else:
            event_techs = e.techs
        for tech in event_techs:
            self._add_effect_research_tech(trigger, tech)

    def _clear_unused_units(self) -> None:
        """
        Removes units from minigames that are not included in the events.

        Currently this method turns these units into invisible objects.
        A future implementation actually may remove the units.
        """
        mgs = {e.name for e in self._events if isinstance(e, Minigame)}
        umgr = self._scn.object_manager.unit_manager
        overall_units = []
        for p in (Player.GAIA, Player.ONE, Player.TWO):
            if 'Steal the Bacon' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        160.0, 80.0, 240.0, 160.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'Tower Battlefield' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        160.0, 160.0, 240.0, 240.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'Galley Micro' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        80.0, 160.0, 160.0, 240.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'Xbow Timer' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        0.0, 160.0, 80.0, 240.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'Capture the Relic' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        0.0, 80.0, 80.0, 160.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'DauT Castle' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        0.0, 0.0, 80.0, 80.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'Castle Siege' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        80.0, 0.0, 160.0, 80.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
            if 'Regicide' not in mgs:
                overall_units.extend(
                    (p, unit)
                    for unit in umgr.get_units_in_area(
                        160.0, 0.0, 240.0, 80.0, players=[p])
                    if unit.unit_id != UCONST_INVISIBLE_OBJECT)
        for p, unit in overall_units:
            util_units.remove(self._scn, unit, p)

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

    def _add_initial_triggers(self) -> None:
        """
        Adds initial triggers for initializing variables,
        listing player objectives, and starting the first round.
        """
        self._add_trigger_header('Init')
        self._initialize_variable_values()
        self._add_start_timer()
        self._set_start_views()
        self._create_map_revealer_remover()
        self._remove_boar_food()
        self._change_train_locations()
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
        for p in (Player.ONE, Player.TWO):
            change_view = init_views.add_effect(effects.change_view)
            change_view.player_source = p.value
            change_view.location_x = START_VIEW_X
            change_view.location_y = START_VIEW_Y
            change_view.scroll = False

    def _add_revealers(self, trigger: TriggerObject,
                       center: Tuple[int, int]) -> None:
        """
        Adds a sequence of effects to trigger for creating map revealers
        centered at tile with x and y coordinates given by center.
        """
        for p in (Player.ONE, Player.TWO):
            for (x, y) in map_revealer_pos(center):
                create = trigger.add_effect(effects.create_object)
                create.object_list_unit_id = UNIT_ID_MAP_REVEALER
                create.player_source = p.value
                create.location_x, create.location_y = x, y

    def _create_map_revealer_remover(self) -> None:
        """
        Creates a "Hide" trigger that removes all map revealers on the map.
        Loops and disables itself.
        """
        hide_revealers = self._add_trigger(REVEALER_HIDE_NAME)
        hide_revealers.enabled = False
        hide_revealers.looping = True
        self._add_deactivate(REVEALER_HIDE_NAME, REVEALER_HIDE_NAME)
        for p in (Player.GAIA, Player.ONE, Player.TWO):
            remove = hide_revealers.add_effect(effects.remove_object)
            remove.player_source = p.value
            remove.object_list_unit_id = UNIT_ID_MAP_REVEALER
            util_triggers.set_effect_area(remove, 0, 0, 239, 239)

    def _remove_boar_food(self) -> None:
        """
        Sets the food stored on Boar to 0 so the Steal the Bacon minigame
        can be skipped quickly by deleting the Boar.
        """
        # TODO this doesn't work for some reason...
        boar_food = self._add_trigger('[I] Set Boar Food to 0')
        for uid in (UCONST_BOAR, UCONST_BOAR_DEAD):
            modify = boar_food.add_effect(effects.modify_attribute)
            modify.quantity = 0
            modify.object_list_unit_id = uid
            modify.player_source = Player.GAIA.value
            modify.operation = ChangeVarOp.set_op.value
            modify.object_attributes = 21 # Amount of First Resource

    def _change_train_locations(self) -> None:
        """
        Changes the train locations of various units and technologies
        for the minigames.
        """
        change_locs = self._add_trigger('[I] Change Research/Train Locations')
        for p in (1, 2):
            for t in [techs.wheelbarrow, techs.hand_cart, techs.castle_age,
                      techs.imperial_age, techs.town_patrol,
                      techs.supplies, techs.long_swordsman, techs.pikeman,
                      techs.squires, techs.two_handed_swordsman, techs.champion,
                      techs.arson, techs.halberdier,
                      techs.crossbowman, techs.arbalester,
                      techs.elite_skirmisher, techs.thumb_ring,
                      techs.heavy_cav_archer,
                      techs.light_cavalry, techs.hussar,
                      techs.husbandry, techs.cavalier, techs.paladin,
                      techs.heavy_camel_rider,
                      techs.gold_mining, techs.stone_mining,
                      techs.gold_shaft_mining, techs.stone_shaft_mining,
                      techs.atonement, techs.redemption, techs.fervor,
                      techs.sanctity, techs.heresy, techs.block_printing,
                      techs.illumination, techs.faith, techs.theocracy,
                      techs.greek_fire, techs.logistica,
                      techs.hoardings, techs.conscription,
                      techs.spies_and_treason]:
                tech = change_locs.add_effect(effects.change_research_location)
                tech.player_source = p
                tech.technology = t
                tech.object_list_unit_id_2 = buildings.wonder
            for u in [units.cataphract, units.elite_cataphract,
                      units.petard, units.trebuchet, units.trebuchet_packed,
                      units.knight, units.cavalier, units.paladin,
                      units.camel_rider, units.heavy_camel_rider,
                      units.cavalry_archer, units.heavy_cavalry_archer,
                      units.hand_cannoneer]:
                unit = change_locs.add_effect(effects.change_train_location)
                unit.player_source = p
                unit.object_list_unit_id = u
                unit.object_list_unit_id_2 = buildings.wonder


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
        elif mg.name == 'Tower Battlefield':
            self._add_tower_battlefield_objectives(index)
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

    def _add_tower_battlefield_objectives(self, index: int) -> None:
        """Adds the objectives for the Tower Battlefield minigame."""
        obj_tower_header_name = f'[O] Round {index} Tower Battlefield'
        self._round_objectives[index].append(obj_tower_header_name)
        obj_tower_header = self._add_trigger(obj_tower_header_name)
        obj_tower_header.enabled = False
        obj_tower_header.description = 'Tower Battlefield'
        obj_tower_header.short_description = 'Tower Battlefield'
        obj_tower_header.display_as_objective = True
        obj_tower_header.display_on_screen = True
        obj_tower_header.description_order = 50
        obj_tower_header.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_tower_header)

        obj_tower_desc_name = f'[O] Round {index} Tower Battlefield Description'
        self._round_objectives[index].append(obj_tower_desc_name)
        obj_tower_desc = self._add_trigger(obj_tower_desc_name)
        obj_tower_desc.enabled = False
        obj_tower_desc.description = 'Control a Flag build building more Towers near it than your opponent. You gain 1 point every 5 seconds you control a Flag. Collection 100 points to win the round.' # pylint: disable=line-too-long
        obj_tower_desc.display_as_objective = True
        obj_tower_desc.description_order = 49
        obj_tower_desc.mute_objectives = True
        util_triggers.add_cond_gaia_defeated(obj_tower_desc)

        obj_tower_p1_name = f'[O] Round {index} Tower Battlefield P1 Points'
        self._round_objectives[index].append(obj_tower_p1_name)
        obj_tower_p1 = self._add_trigger(obj_tower_p1_name)
        obj_tower_p1.enabled = False
        obj_tower_p1.description = 'Player 1: <p1-battlefield-points> / 100'
        obj_tower_p1.short_description = 'P1: <p1-battlefield-points> / 100'
        obj_tower_p1.display_as_objective = True
        obj_tower_p1.display_on_screen = True
        obj_tower_p1.description_order = 48
        obj_tower_p1.mute_objectives = True
        var1_cond = obj_tower_p1.add_condition(conditions.variable_value)
        var1_cond.amount_or_quantity = event.MAX_POINTS
        var1_cond.variable = self._var_ids['p1-battlefield-points']
        var1_cond.comparison = VarValComp.equal.value

        obj_tower_p2_name = f'[O] Round {index} Tower Battlefield P2 Points'
        self._round_objectives[index].append(obj_tower_p2_name)
        obj_tower_p2 = self._add_trigger(obj_tower_p2_name)
        obj_tower_p2.enabled = False
        obj_tower_p2.description = 'Player 2: <p2-battlefield-points> / 100'
        obj_tower_p2.short_description = 'P2: <p2-battlefield-points> / 100'
        obj_tower_p2.display_as_objective = True
        obj_tower_p2.display_on_screen = True
        obj_tower_p2.description_order = 47
        obj_tower_p2.mute_objectives = True
        var1_cond = obj_tower_p2.add_condition(conditions.variable_value)
        var1_cond.amount_or_quantity = event.MAX_POINTS
        var1_cond.variable = self._var_ids['p2-battlefield-points']
        var1_cond.comparison = VarValComp.equal.value

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
        castle1_made = obj_daut_p1.add_condition(conditions.variable_value)
        castle1_made.amount_or_quantity = 1
        castle1_made.variable = self._var_ids['p1-castle-constructed']
        castle1_made.comparison = VarValComp.equal.value

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
        castle2_made = obj_daut_p2.add_condition(conditions.variable_value)
        castle2_made.amount_or_quantity = 1
        castle2_made.variable = self._var_ids['p2-castle-constructed']
        castle2_made.comparison = VarValComp.equal.value

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
        castle1_destroyed = obj_cs_p1.add_condition(conditions.variable_value)
        castle1_destroyed.amount_or_quantity = 1
        castle1_destroyed.variable = self._var_ids['p1-castle-destroyed']
        castle1_destroyed.comparison = VarValComp.equal.value

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
        castle2_destroyed = obj_cs_p2.add_condition(conditions.variable_value)
        castle2_destroyed.amount_or_quantity = 1
        castle2_destroyed.variable = self._var_ids['p2-castle-destroyed']
        castle2_destroyed.comparison = VarValComp.equal.value

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

        obj_king1_killed_name = f"[O] Regicide Kill Player 1's Hero"
        self._round_objectives[index].append(obj_king1_killed_name)
        obj_king1_killed = self._add_trigger(obj_king1_killed_name)
        obj_king1_killed.enabled = False
        obj_king1_killed.description = '- Player 1 Hero Killed'
        obj_king1_killed.short_description = '- P1 Hero Killed'
        obj_king1_killed.display_as_objective = True
        obj_king1_killed.display_on_screen = True
        obj_king1_killed.description_order = 49
        obj_king1_killed.mute_objectives = True
        k1_destroyed = obj_king1_killed.add_condition(conditions.variable_value)
        k1_destroyed.amount_or_quantity = 1
        k1_destroyed.variable = self._var_ids['p1-hero-killed']
        k1_destroyed.comparison = VarValComp.equal.value

        obj_king2_killed_name = f"[O] Regicide Kill Player 2's Hero"
        self._round_objectives[index].append(obj_king2_killed_name)
        obj_king2_killed = self._add_trigger(obj_king2_killed_name)
        obj_king2_killed.enabled = False
        obj_king2_killed.description = '- Player 2 Hero Killed'
        obj_king2_killed.short_description = '- P2 Hero Killed'
        obj_king2_killed.display_as_objective = True
        obj_king2_killed.display_on_screen = True
        obj_king2_killed.description_order = 48
        obj_king2_killed.mute_objectives = True
        k2_destroyed = obj_king2_killed.add_condition(conditions.variable_value)
        k2_destroyed.amount_or_quantity = 1
        k2_destroyed.variable = self._var_ids['p2-hero-killed']
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
        elif mg.name == 'Tower Battlefield':
            self._add_tower_battlefield(index)
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
        boar_dead_name = f'{prefix} All Boar are Dead'

        umgr = self._scn.object_manager.unit_manager

        boar_units = {
            unit
            for unit in umgr.get_units_in_area(
                x1=160.0, y1=80.0, x2=240.0, y2=160.0, players=[Player.GAIA])
            if unit.unit_id == UCONST_BOAR
        }

        scouts = dict()
        player_flags = {Player.ONE: set(), Player.TWO: set()}

        for p in (Player.ONE, Player.TWO):
            for unit in umgr.get_units_in_area(160.0, 80.0, 240.0, 160.0,
                                               players=[p]):
                if unit.unit_id == units.scout_cavalry:
                    scouts[p] = unit
                elif unit.unit_id == FLAG_A_UCONST:
                    player_flags[p].add(unit)
                else:
                    raise AssertionError(f'unit is not handled {unit}.')

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        self._add_activate(rts.names.begin, rts.names.p2_wins)
        self._add_activate(rts.names.begin, boar_dead_name)


        for p, scout in scouts.items():
            util_units.remove(self._scn, scout, p)
            x, y = int(scout.x), int(scout.y)
            create = rts.init.add_effect(effects.create_object)
            create.object_list_unit_id = units.scout_cavalry
            create.player_source = p.value
            create.facet = util_units.rad_to_facet(scout.rotation)
            create.location_x, create.location_y = x, y

            to_0 = rts.init.add_effect(effects.change_ownership)
            to_0.player_source = p.value
            to_0.player_target = Player.GAIA.value
            to_0.object_list_unit_id = units.scout_cavalry
            to_0.area_1_x, to_0.area_1_y = x, y
            to_0.area_2_x, to_0.area_2_y = x, y

            to_p = rts.begin.add_effect(effects.change_ownership)
            to_p.player_source = Player.GAIA.value
            to_p.player_target = p.value
            to_p.object_list_unit_id = units.scout_cavalry
            to_p.area_1_x, to_p.area_1_y = x, y
            to_p.area_2_x, to_p.area_2_y = x, y

            scout_respawn1_name = f'{prefix} P{p.value} Scout Respawn 1'
            scout_countdown_name = f'{prefix} P{p.value} Scout Countdown'
            scout_respawn1 = self._add_trigger(scout_respawn1_name)
            scout_respawn1.enabled = False
            self._add_activate(rts.names.begin, scout_respawn1_name)
            scout_respawn1.looping = True
            util_triggers.add_cond_pop0(scout_respawn1, p.value)
            self._add_deactivate(scout_respawn1_name, scout_respawn1_name)
            self._add_activate(scout_respawn1_name, scout_countdown_name)
            self._add_deactivate(rts.names.cleanup, scout_respawn1_name)

            scout_countdown = self._add_trigger(scout_countdown_name)
            scout_countdown.enabled = False
            util_triggers.add_cond_timer(scout_countdown, 10)
            scout_create1 = scout_countdown.add_effect(effects.create_object)
            scout_create1.object_list_unit_id = units.scout_cavalry
            scout_create1.player_source = p.value
            scout_create1.location_x = int(scout.x)
            scout_create1.location_y = int(scout.y)
            self._add_activate(scout_countdown_name, scout_respawn1_name)
            self._add_deactivate(rts.names.cleanup, scout_countdown_name)

        for p, flags in player_flags.items():
            for flag in flags:
                util_units.remove(self._scn, flag, p)
                x, y = int(flag.x), int(flag.y)

                create = rts.init.add_effect(effects.create_object)
                create.object_list_unit_id = FLAG_A_UCONST
                create.player_source = p.value
                create.facet = util_units.rad_to_facet(flag.rotation)
                create.location_x, create.location_y = x, y

                to_0 = rts.init.add_effect(effects.change_ownership)
                to_0.player_source = p.value
                to_0.player_target = Player.GAIA.value
                to_0.object_list_unit_id = FLAG_A_UCONST
                to_0.area_1_x, to_0.area_1_y = x, y
                to_0.area_2_x, to_0.area_2_y = x, y

                to_p = rts.begin.add_effect(effects.change_ownership)
                to_p.player_source = Player.GAIA.value
                to_p.player_target = p.value
                to_p.object_list_unit_id = FLAG_A_UCONST
                to_p.area_1_x, to_p.area_1_y = x, y
                to_p.area_2_x, to_p.area_2_y = x, y

                name = f'{prefix} P{p.value} Capture at ({flag.x}, {flag.y})'
                self._add_activate(rts.names.begin, name)
                capture = self._add_trigger(name)
                capture.enabled = False
                boar_in_area = capture.add_condition(conditions.object_in_area)
                boar_in_area.amount_or_quantity = 1
                boar_in_area.player = 0
                boar_in_area.object_list = UCONST_BOAR
                util_triggers.set_cond_area(boar_in_area, x, y, x, y)

                boar_remove = capture.add_effect(effects.remove_object)
                boar_remove.object_list_unit_id = UCONST_BOAR
                boar_remove.player_source = 0
                # Leaves a small buffer to ensure the Boar is removed.
                util_triggers.set_effect_area(
                    boar_remove, x - 1, y - 1, x + 1, y + 1)

                replace = capture.add_effect(effects.replace_object)
                replace.player_source = p.value
                replace.player_target = p.value
                replace.object_list_unit_id = FLAG_A_UCONST
                replace.object_list_unit_id_2 = units.scout_cavalry
                util_triggers.set_effect_area(replace, x, y, x, y)
                if p == Player.ONE:
                    self._add_effect_p1_score(capture, BOAR_POINTS)
                else:
                    self._add_effect_p2_score(capture, BOAR_POINTS)
                inc_var = capture.add_effect(effects.change_variable)
                inc_var.quantity = 1
                inc_var.operation = ChangeVarOp.add.value
                var_name = f'p{p.value}-boar'
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
            # util_triggers.add_cond_hp0(boar_dead, boar.reference_id)
            destroy = boar_dead.add_condition(conditions.destroy_object)
            destroy.unit_object = boar.reference_id
        self._add_deactivate(boar_dead_name, rts.names.p1_wins)
        self._add_deactivate(boar_dead_name, rts.names.p2_wins)
        self._add_activate(boar_dead_name, rts.names.cleanup)

        # Cleanup removes units from player control.
        for player_source in (1, 2):
            cleanup_change = rts.cleanup.add_effect(effects.change_ownership)
            cleanup_change.player_source = player_source
            cleanup_change.player_target = 0
            util_triggers.set_effect_area(cleanup_change, 160, 80, 239, 159)

    def _add_tower_battlefield(self, index: int) -> None:
        """
        Adds the Tower Battlefield minigame at the given index.

        Checks the index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        umgr = self._scn.object_manager.unit_manager
        prefix = f'[R{index}]'

        for res in (util_triggers.ACC_ATTR_WOOD, util_triggers.ACC_ATTR_FOOD,
                    util_triggers.ACC_ATTR_GOLD):
            util_triggers.add_effect_modify_res(rts.begin, 10000, res)
        util_triggers.add_effect_modify_res(rts.begin, 300,
                                            util_triggers.ACC_ATTR_STONE)

        next_flag = 'A'
        flag_positions = dict()
        for unit in umgr.get_units_in_area(160.0, 160.0, 240.0, 240.0,
                                           players=[Player.GAIA]):
            if unit.unit_id != FLAG_A_UCONST:
                continue
            x, y = int(unit.x), int(unit.y)
            flag_positions[next_flag] = (x, y)
            next_flag = chr(ord(next_flag) + 1)
            util_units.remove(self._scn, unit, Player.GAIA)

            create = rts.init.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = Player.ONE.value
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x, create.location_y = x, y

            to0 = rts.init.add_effect(effects.change_ownership)
            to0.player_source = Player.ONE.value
            to0.player_target = Player.GAIA.value
            to0.object_list_unit_id = unit.unit_id
            to0.area_1_x, to0.area_1_y = x, y
            to0.area_2_x, to0.area_2_y = x, y

        for p in (Player.ONE, Player.TWO):
            for unit in umgr.get_units_in_area(160.0, 160.0, 240.0, 240.0,
                                               players=[p]):
                if unit.unit_id != UCONST_INVISIBLE_OBJECT:
                    self._create_unit_sequence(p, unit, rts)

        # Looping triggers for adding points while a player holds a flag.
        add_points_names = []
        for player in (1, 2):
            for flag in flag_positions:
                name = _tb_hold_flag_name(index, player, flag)
                add_points_names.append(name)
                add_points = self._add_trigger(name)
                add_points.enabled = False
                add_points.looping = True
                self._add_deactivate(rts.names.p1_wins, name)
                self._add_deactivate(rts.names.p2_wins, name)
                util_triggers.add_cond_timer(add_points, TOWER_AWARD_TIME)
                for p in (1, 2):
                    bound = add_points.add_condition(conditions.variable_value)
                    bound.amount_or_quantity = event.MAX_POINTS
                    bound.variable = self._var_ids[f'p{p}-battlefield-points']
                    bound.comparison = VarValComp.less.value
                if player == 1:
                    self._add_effect_p1_score(add_points, TOWER_AWARD_POINTS)
                else:
                    self._add_effect_p2_score(add_points, TOWER_AWARD_POINTS)
                add = add_points.add_effect(effects.change_variable)
                add.quantity = TOWER_AWARD_POINTS
                add.operation = ChangeVarOp.add.value
                var_add_name = f'p{player}-battlefield-points'
                add.from_variable = self._var_ids[var_add_name]
                add.message = var_add_name

        scoring_trigger_names = []
        for i in range(TOWER_MAX_NUM + 1):
            for j in range(TOWER_MAX_NUM + 1):
            # TODO the next line is for the "full" towers, not the "cutoff"
            # versions to avoid the MemoryError.
            # for j in range(TOWER_MAX_NUM + 1 - i):
                for flag, (x, y) in flag_positions.items():
                    name = f'{prefix} Capture Flag {flag} with Score {i}-{j}'
                    scoring_trigger_names.append(name)
                    capture = self._add_trigger(name)
                    capture.enabled = False
                    capture.looping = True
                    self._add_activate(rts.names.begin, name)
                    x1 = x - 2
                    y1 = y - 2
                    x2 = x + 2
                    y2 = y + 2

                    def add_change_ownership(pi: Player, pj: Player,
                                             x: int, y: int,
                                             trigger=capture) -> None:
                        """
                        Adds a change ownership effect to capture to change
                        the flag at (x, y) from pi to pj.
                        """
                        change = trigger.add_effect(effects.change_ownership)
                        change.player_source = pi.value
                        change.player_target = pj.value
                        change.object_list_unit_id = FLAG_A_UCONST
                        change.area_1_x = x
                        change.area_1_y = y
                        change.area_2_x = x
                        change.area_2_y = y

                    # p1 score not >= i + 1.
                    p1_upper = capture.add_condition(conditions.object_in_area)
                    p1_upper.inverted = True
                    p1_upper.player = 1
                    p1_upper.amount_or_quantity = i + 1
                    p1_upper.object_list = UCONST_WATCH_TOWER
                    # p1 score >= i.
                    p1_lower = capture.add_condition(conditions.object_in_area)
                    p1_lower.player = 1
                    p1_lower.amount_or_quantity = i
                    p1_lower.object_list = UCONST_WATCH_TOWER
                    # p2 score not >= j + 1.
                    p2_upper = capture.add_condition(conditions.object_in_area)
                    p2_upper.inverted = True
                    p2_upper.player = 2
                    p2_upper.amount_or_quantity = j + 1
                    p2_upper.object_list = UCONST_WATCH_TOWER
                    # p2 score >= j.
                    p2_lower = capture.add_condition(conditions.object_in_area)
                    p2_lower.player = 2
                    p2_lower.amount_or_quantity = j
                    p2_lower.object_list = UCONST_WATCH_TOWER
                    for cond in (p1_upper, p1_lower, p2_upper, p2_lower):
                        util_triggers.set_cond_area(cond, x1, y1, x2, y2)
                    if i < j:
                        owner = capture.add_condition(conditions.object_in_area)
                        owner.inverted = True
                        owner.player = 2
                        owner.amount_or_quantity = 1
                        owner.object_list = FLAG_A_UCONST
                        util_triggers.set_cond_area(owner, x, y, x, y)
                        add_change_ownership(Player.ONE, Player.TWO, x, y)
                        add_change_ownership(Player.GAIA, Player.TWO, x, y)
                        self._add_deactivate(
                            name, _tb_hold_flag_name(index, 1, flag))
                        self._add_activate(
                            name, _tb_hold_flag_name(index, 2, flag))
                    elif i == j:
                        owner = capture.add_condition(conditions.object_in_area)
                        owner.inverted = True
                        owner.player = 0
                        owner.amount_or_quantity = 1
                        owner.object_list = FLAG_A_UCONST
                        util_triggers.set_cond_area(owner, x, y, x, y)
                        add_change_ownership(Player.ONE, Player.GAIA, x, y)
                        add_change_ownership(Player.TWO, Player.GAIA, x, y)
                        self._add_deactivate(
                            name, _tb_hold_flag_name(index, 1, flag))
                        self._add_deactivate(
                            name, _tb_hold_flag_name(index, 2, flag))
                    else:
                        owner = capture.add_condition(conditions.object_in_area)
                        owner.inverted = True
                        owner.player = 1
                        owner.amount_or_quantity = 1
                        owner.object_list = FLAG_A_UCONST
                        util_triggers.set_cond_area(owner, x, y, x, y)
                        add_change_ownership(Player.TWO, Player.ONE, x, y)
                        add_change_ownership(Player.GAIA, Player.ONE, x, y)
                        self._add_activate(
                            name, _tb_hold_flag_name(index, 1, flag))
                        self._add_deactivate(
                            name, _tb_hold_flag_name(index, 2, flag))

        for p in (Player.ONE, Player.TWO):
            for enemy_points in range(event.MAX_POINTS):
                defeated_name = _tb_defeated_name(index, p.value, enemy_points)
                defeated = self._add_trigger(defeated_name)
                defeated.enabled = False
                self._add_activate(rts.names.begin, defeated_name)
                self._add_deactivate(rts.names.p1_wins, defeated_name)
                self._add_deactivate(rts.names.p2_wins, defeated_name)
                for point_name in add_points_names:
                    self._add_deactivate(defeated_name, point_name)
                for scoring_trigger_name in scoring_trigger_names:
                    self._add_deactivate(defeated_name, scoring_trigger_name)
                # Deactivates all other such triggers.
                for player_ in (1, 2):
                    for enemy_points_ in range(event.MAX_POINTS):
                        if p.value != player_ and enemy_points != enemy_points_:
                            self._add_deactivate(
                                defeated_name,
                                _tb_defeated_name(index, player_, enemy_points_)
                            )

                # A player is defeated when they have no units and all of their
                # starting buildings are destroyed.
                util_triggers.add_cond_pop0(defeated, p.value)
                for building_const in (
                        buildings.archery_range, buildings.barracks,
                        buildings.stable, buildings.town_center,
                        buildings.watch_tower):
                    no_build = defeated.add_condition(conditions.object_in_area)
                    no_build.inverted = True
                    no_build.player = p.value
                    no_build.amount_or_quantity = 1
                    no_build.object_list = building_const
                    util_triggers.set_cond_area(no_build, 160, 160, 238, 238)
                other_p = Player.TWO if p == Player.ONE else Player.ONE
                other_points = defeated.add_condition(conditions.variable_value)
                other_points.amount_or_quantity = enemy_points
                other_var_name = f'p{other_p.value}-battlefield-points'
                other_points.variable = self._var_ids[other_var_name]
                other_points.comparison = VarValComp.equal.value
                remaining_points = event.MAX_POINTS - enemy_points
                add_points = defeated.add_effect(effects.change_variable)
                add_points.quantity = remaining_points
                add_points.operation = ChangeVarOp.add.value
                add_points.from_variable = self._var_ids[other_var_name]
                add_points.message = other_var_name
                self._add_effect_score(defeated, other_p, remaining_points)

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        var_p1 = rts.p1_wins.add_condition(conditions.variable_value)
        var_p1.amount_or_quantity = event.MAX_POINTS
        var_p1.variable = self._var_ids['p1-battlefield-points']
        var_p1.comparison = VarValComp.equal.value
        for scoring_trigger_name in scoring_trigger_names:
            self._add_deactivate(rts.names.p1_wins, scoring_trigger_name)

        self._add_activate(rts.names.begin, rts.names.p2_wins)
        var_p2 = rts.p2_wins.add_condition(conditions.variable_value)
        var_p2.amount_or_quantity = event.MAX_POINTS
        var_p2.variable = self._var_ids['p2-battlefield-points']
        var_p2.comparison = VarValComp.equal.value
        for scoring_trigger_name in scoring_trigger_names:
            self._add_deactivate(rts.names.p2_wins, scoring_trigger_name)

        # Cleanup removes units from player control.
        for p in (Player.ONE, Player.TWO):
            change_to_0 = rts.cleanup.add_effect(effects.change_ownership)
            change_to_0.player_source = p.value
            change_to_0.player_target = Player.GAIA.value
            util_triggers.set_effect_area(change_to_0, 160, 160, 238, 238)
        # Removes Villagers so they stop gathering resources.
        for uconst in UCONST_VILS:
            remove_vils = rts.cleanup.add_effect(effects.remove_object)
            remove_vils.player_source = Player.GAIA.value
            remove_vils.object_list_unit_id = uconst
            util_triggers.set_effect_area(remove_vils, 160, 160, 238, 238)

        for res in (util_triggers.ACC_ATTR_WOOD, util_triggers.ACC_ATTR_FOOD,
                    util_triggers.ACC_ATTR_GOLD, util_triggers.ACC_ATTR_STONE):
            util_triggers.add_effect_modify_res(rts.cleanup, 0, res)

    def _add_galley_micro(self, index: int) -> None:
        """
        Adds the Galley Micro minigame at the given index.

        Checks the index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        umgr = self._scn.object_manager.unit_manager

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        util_triggers.add_cond_pop0(rts.p1_wins, 2)
        self._add_activate(rts.names.begin, rts.names.p2_wins)
        util_triggers.add_cond_pop0(rts.p2_wins, 1)

        prefix = f'[R{index}]'
        for p in (Player.ONE, Player.TWO):
            galleys = umgr.get_units_in_area(80.0, 160.0, 160.0, 240.0,
                                             players=[p])
            for g in galleys:
                self._create_unit_sequence(p, g, rts)
            ngalleys = len(galleys)
            for k in range(ngalleys):
                pts_name = f'{prefix} P{p.value} Galley {k}'
                pts = self._add_trigger(pts_name)
                pts.enabled = False
                obj_in_area = pts.add_condition(conditions.object_in_area)
                obj_in_area.inverted = True
                util_triggers.set_cond_area(obj_in_area, 80, 160, 159, 239)
                obj_in_area.amount_or_quantity = k + 1
                obj_in_area.player = p.value
                obj_in_area.object_list = units.galley
                self._add_activate(rts.names.begin, pts_name)
                self._add_deactivate(
                    rts.names.p1_wins if p == Player.ONE else rts.names.p2_wins,
                    pts_name)
                self._add_effect_score(
                    pts,
                    Player.TWO if p == Player.ONE else Player.ONE,
                    event.MAX_POINTS // ngalleys)
                remove = rts.cleanup.add_effect(effects.remove_object)
                remove.object_list_unit_id = units.galley
                remove.player_source = p.value
                util_triggers.set_effect_area(remove, 80, 160, 159, 239)

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
        x1, y1, x2, y2 = 0, 160, 79, 239
        def set_condition_area(condition: ConditionObject):
            util_triggers.set_cond_area(condition, x1, y1, x2, y2)
        def set_effect_area(effect: EffectObject):
            util_triggers.set_effect_area(effect, x1, y1, x2, y2)

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
        xbow1.player_source = Player.ONE.value
        xbow1.player_target = Player.ONE.value
        xbow1.object_list_unit_id = units.archer
        xbow1.object_list_unit_id_2 = units.crossbowman
        set_effect_area(xbow1)
        bodkin1_attack = res_xbow_1.add_effect(effects.change_object_attack)
        bodkin1_attack.aa_quantity = 1
        bodkin1_attack.aa_armor_or_attack_type = CLASS_PIERCE
        bodkin1_attack.player_source = 1
        bodkin1_attack.object_list_unit_id = units.crossbowman
        bodkin1_attack.operation = util_triggers.ChangeVarOp.add.value
        set_effect_area(bodkin1_attack)
        bodkin1_range = res_xbow_1.add_effect(effects.change_object_range)
        bodkin1_range.quantity = 1
        bodkin1_range.player_source = 1
        bodkin1_range.object_list_unit_id = units.archer
        bodkin1_range.operation = util_triggers.ChangeVarOp.add.value
        set_effect_area(bodkin1_range)

        cleanup1 = self._add_trigger(cleanup1_name)
        cleanup1.enabled = False
        util_triggers.add_cond_timer(cleanup1, DELAY_CLEANUP)
        for clean in (cleanup1, rts.cleanup):
            for p in (Player.ONE, Player.TWO):
                clean_a = clean.add_effect(effects.remove_object)
                clean_a.player_source = p.value
                clean_a.object_list_unit_id = units.archer
                set_effect_area(clean_a)
                clean_c = clean.add_effect(effects.remove_object)
                clean_c.player_source = p.value
                clean_c.object_list_unit_id = units.crossbowman
                set_effect_area(clean_c)
                clean_s = clean.add_effect(effects.remove_object)
                clean_s.player_source = p.value
                clean_s.object_list_unit_id = units.skirmisher
                set_effect_area(clean_s)
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

        umgr_temp = self._xbow_scn.object_manager.unit_manager
        archers = umgr_temp.get_units_in_area(0.0, 80.0, 160.0, 240.0,
                                              players=[Player.ONE])
        skirms = umgr_temp.get_units_in_area(0.0, 80.0, 160.0, 240.0,
                                             players=[Player.TWO])

        p1_r1_win = self._add_trigger(p1_r1_win_name)
        p1_r1_win.enabled = False
        self._add_activate(rts.names.begin, p1_r1_win_name)
        self._add_deactivate(p2_r1_win_name, p1_r1_win_name)
        util_triggers.add_cond_pop0(p1_r1_win, Player.TWO.value)
        self._add_effect_p1_score(p1_r1_win,
                                  event.MAX_POINTS // 2 - len(skirms))
        self._add_activate(p1_r1_win_name, cleanup1_name)
        clear_timer_p1_r1 = p1_r1_win.add_effect(effects.clear_timer)
        clear_timer_p1_r1.variable_or_timer = 0
        self._add_deactivate(p1_r1_win_name, res_xbow_1_name)

        p2_r1_win = self._add_trigger(p2_r1_win_name)
        p2_r1_win.enabled = False
        self._add_activate(rts.names.begin, p2_r1_win_name)
        self._add_deactivate(p1_r1_win_name, p2_r1_win_name)
        util_triggers.add_cond_pop0(p2_r1_win, Player.ONE.value)
        self._add_effect_p2_score(p2_r1_win,
                                  event.MAX_POINTS // 2 - len(archers))
        self._add_activate(p2_r1_win_name, cleanup1_name)
        clear_timer_p2_r1 = p2_r1_win.add_effect(effects.clear_timer)
        clear_timer_p2_r1.variable_or_timer = 0
        self._add_deactivate(p2_r1_win_name, res_xbow_1_name)

        # Round 1
        for archer in archers:
            self._create_unit_sequence(Player.ONE, archer, rts, False)
        for k in range(len(archers)):
            pts_name = f'{prefix} P{Player.ONE.value} Archer {k}'
            pts = self._add_trigger(pts_name)
            pts.enabled = False
            for uconst in (units.archer, units.crossbowman):
                obj_in_area = pts.add_condition(conditions.object_in_area)
                obj_in_area.inverted = True
                set_condition_area(obj_in_area)
                obj_in_area.amount_or_quantity = k + 1
                obj_in_area.player = Player.ONE.value
                obj_in_area.object_list = uconst
            self._add_activate(rts.names.begin, pts_name)
            self._add_deactivate(p1_r1_win_name, pts_name)
            self._add_effect_p2_score(pts, 1)

        for skirm in skirms:
            self._create_unit_sequence_explicit(
                Player.TWO, skirm, rts.init, rts.begin, False, True)
        for k in range(len(skirms)):
            pts_name = f'{prefix} P{Player.TWO.value} Skirm {k}'
            pts = self._add_trigger(pts_name)
            pts.enabled = False
            obj_in_area = pts.add_condition(conditions.object_in_area)
            obj_in_area.inverted = True
            set_condition_area(obj_in_area)
            obj_in_area.amount_or_quantity = k + 1
            obj_in_area.player = Player.TWO.value
            obj_in_area.object_list = units.skirmisher
            self._add_activate(rts.names.begin, pts_name)
            self._add_deactivate(p2_r1_win_name, pts_name)
            self._add_effect_p1_score(pts, 1)

        # Round 2
        for archer in archers:
            self._create_unit_sequence_explicit(
                Player.TWO, archer, init2, begin2, False)
        for k in range(len(archers)):
            pts_name = f'{prefix} P{Player.TWO.value} Archer {k}'
            pts = self._add_trigger(pts_name)
            pts.enabled = False
            for uconst in (units.archer, units.crossbowman):
                obj_in_area = pts.add_condition(conditions.object_in_area)
                obj_in_area.inverted = True
                set_condition_area(obj_in_area)
                obj_in_area.amount_or_quantity = k + 1
                obj_in_area.player = Player.TWO.value
                obj_in_area.object_list = uconst
            self._add_activate(begin2_name, pts_name)
            self._add_deactivate(rts.names.p2_wins, pts_name)
            self._add_effect_p1_score(pts, 1)

        for skirm in skirms:
            self._create_unit_sequence_explicit(
                Player.ONE, skirm, init2, begin2, False, True)
        for k in range(len(skirms)):
            pts_name = f'{prefix} P{Player.ONE.value} Skirm {k}'
            pts = self._add_trigger(pts_name)
            pts.enabled = False
            obj_in_area = pts.add_condition(conditions.object_in_area)
            obj_in_area.inverted = True
            set_condition_area(obj_in_area)
            obj_in_area.amount_or_quantity = k + 1
            obj_in_area.player = Player.ONE.value
            obj_in_area.object_list = units.skirmisher
            self._add_activate(begin2_name, pts_name)
            self._add_deactivate(rts.names.p1_wins, pts_name)
            self._add_effect_p2_score(pts, 1)

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
        xbow2.player_source = Player.TWO.value
        xbow2.player_target = Player.TWO.value
        xbow2.object_list_unit_id = UCONST_ARCHER
        xbow2.object_list_unit_id_2 = UCONST_XBOW
        set_effect_area(xbow1)
        bodkin2_attack = res_xbow_2.add_effect(effects.change_object_attack)
        bodkin2_attack.aa_quantity = 1
        bodkin2_attack.aa_armor_or_attack_type = CLASS_PIERCE
        bodkin2_attack.player_source = 2
        bodkin2_attack.object_list_unit_id = UCONST_XBOW
        bodkin2_attack.operation = util_triggers.ChangeVarOp.add.value
        set_effect_area(bodkin1_attack)
        bodkin2_range = res_xbow_2.add_effect(effects.change_object_range)
        bodkin2_range.quantity = 1
        bodkin2_range.player_source = 2
        bodkin2_range.object_list_unit_id = UCONST_XBOW
        bodkin2_range.operation = util_triggers.ChangeVarOp.add.value
        set_effect_area(bodkin1_range)

        # Player 1 Wins Round 2
        util_triggers.add_cond_pop0(rts.p1_wins, Player.TWO.value)
        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_effect_p1_score(rts.p1_wins,
                                  event.MAX_POINTS // 2 - len(archers))
        clear_timer_p1_r2 = rts.p1_wins.add_effect(effects.clear_timer)
        clear_timer_p1_r2.variable_or_timer = 0
        self._add_deactivate(rts.names.p1_wins, res_xbow_2_name)

        # Player 2 Wins Round 2
        util_triggers.add_cond_pop0(rts.p2_wins, Player.ONE.value)
        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        self._add_effect_p2_score(rts.p2_wins,
                                  event.MAX_POINTS // 2 - len(skirms))
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
        umgr = self._scn.object_manager.unit_manager

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

        self._add_effect_research_tech(rts.begin, 'atonement')
        begin2 = self._add_trigger(begin2_name)
        begin2.enabled = False
        util_triggers.add_cond_timer(begin2, 3)
        for tech_name in ['sanctity', 'redemption']:
            self._add_effect_research_tech(begin2, tech_name)
        begin3 = self._add_trigger(begin3_name)
        begin3.enabled = False
        util_triggers.add_cond_timer(begin3, 3)

        # Invisible objects cause issues with Monks, uses Create Object instead.

        # R1 - P1
        r1p1 = util_units.units_in_area(p1_template, 0.0, 0.0, 10.0, 10.0)
        for unit in r1p1:
            create = rts.begin.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = 1
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x = int(util_units.get_x(unit)) - 0 + p1_pos[0] + 1
            create.location_y = int(util_units.get_y(unit)) - 0 + p1_pos[1] + 1

        # R1 - P2
        r1p2 = util_units.units_in_area(p2_template, 10.0, 0.0, 20.0, 10.0)
        for unit in r1p2:
            create = rts.begin.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = 2
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x = int(util_units.get_x(unit)) - 19 + p2_pos[0] + 1
            create.location_y = int(util_units.get_y(unit)) - 9 + p2_pos[1]

        # R2 - P1
        r2p1 = util_units.units_in_area(p1_template, 0.0, 10.0, 10.0, 20.0)
        for unit in r2p1:
            create = begin2.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = 1
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x = int(util_units.get_x(unit)) - 0 + p1_pos[0] + 1
            create.location_y = int(util_units.get_y(unit)) - 10 + p1_pos[1] + 1

        # R2 - P2
        r2p2 = util_units.units_in_area(p2_template, 10.0, 10.0, 20.0, 20.0)
        for unit in r2p2:
            create = begin2.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = 2
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x = int(util_units.get_x(unit)) - 19 + p2_pos[0] + 1
            create.location_y = int(util_units.get_y(unit)) - 19 + p2_pos[1]

        # R3 - P1
        r3p1 = util_units.units_in_area(p1_template, 0.0, 20.0, 10.0, 30.0)
        for unit in r3p1:
            create = begin3.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = 1
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x = int(util_units.get_x(unit)) - 0 + p1_pos[0] + 1
            create.location_y = int(util_units.get_y(unit)) - 20 + p1_pos[1] + 1

        # R3 - P2
        r3p2 = util_units.units_in_area(p2_template, 10.0, 20.0, 20.0, 30.0)
        for unit in r3p2:
            create = begin3.add_effect(effects.create_object)
            create.object_list_unit_id = unit.unit_id
            create.player_source = 2
            create.facet = util_units.rad_to_facet(unit.rotation)
            create.location_x = int(util_units.get_x(unit)) - 19 + p2_pos[0] + 1
            create.location_y = int(util_units.get_y(unit)) - 29 + p2_pos[1]

        for p in (Player.ONE, Player.TWO):
            for unit in umgr.get_units_in_area(0.0, 80.0, 80.0, 160.0,
                                               players=[p]):
                self._create_unit_sequence(p, unit, rts)

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

        # Defeats a player if they lose their Monasteries.
        for p in (Player.ONE, Player.TWO):
            name = f'{prefix} P{p.value} Loses Monasteries'
            other_p = Player.TWO if p == Player.ONE else Player.ONE
            other_name = f'{prefix} P{other_p.value} Loses Monasteries'
            lose = self._add_trigger(name)
            lose.enabled = False
            no_monasteries = lose.add_condition(conditions.object_in_area)
            no_monasteries.inverted = True
            no_monasteries.player = p.value
            no_monasteries.amount_or_quantity = 1
            no_monasteries.object_list = buildings.monastery
            util_triggers.set_cond_area(no_monasteries, 0, 80, 79, 159)
            self._add_activate(rts.names.begin, name)
            self._add_activate(name, rts.names.cleanup)
            self._add_deactivate(rts.names.p1_wins, name)
            self._add_deactivate(rts.names.p2_wins, name)
            self._add_deactivate(name, other_name)
            for cond_name in r1_cond_names + r2_cond_names + r3_cond_names:
                self._add_deactivate(name, cond_name)
            if p == Player.ONE:
                self._add_effect_p2_score(lose, 100)
            else:
                self._add_effect_p1_score(lose, 100)

        # Cleanup removes units from player control.
        for p in (Player.ONE, Player.TWO):
            change_to_0 = rts.cleanup.add_effect(effects.change_ownership)
            change_to_0.player_source = p.value
            change_to_0.player_target = Player.GAIA.value
            util_triggers.set_effect_area(change_to_0, 0, 80, 79, 159)

        util_triggers.add_effect_modify_res(
            rts.cleanup, 0, util_triggers.ACC_ATTR_GOLD)


    def _add_daut_castle(self, index: int) -> None:
        """
        Adds the DauT Castle minigame at the given index.

        Checks the index is not 0 (cannot us a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        umgr = self._scn.object_manager.unit_manager

        prefix = f'[R{index}]' if index else '[T]'
        p1_wins_name = f'{prefix} Player 1 Wins Round'
        p1_builds_castle_name = f'{prefix} Player 1 Constructs Castle'
        p1_loses_army_name = f'{prefix} Player 1 Loses Army'
        p2_wins_name = f'{prefix} Player 2 Wins Round'
        p2_builds_castle_name = f'{prefix} Player 2 Constructs Castle'
        p2_loses_army_name = f'{prefix} Player 2 Loses Army'

        util_triggers.add_effect_modify_res(
            rts.init, 1300, util_triggers.ACC_ATTR_STONE)

        player_flags = defaultdict(set)
        for p in (Player.ONE, Player.TWO):
            for unit in umgr.get_units_in_area(0.0, 0.0, 80.0, 80.0,
                                               players=[p]):
                if unit.unit_id == UCONST_INVISIBLE_OBJECT:
                    continue
                if unit.unit_id == FLAG_A_UCONST:
                    player_flags[p].add(unit)
                self._create_unit_sequence(p, unit, rts)

        flag_positions = [
            (flag.x, flag.y)
            for flag in player_flags[Player.ONE] | player_flags[Player.TWO]
        ]
        # The min and max positions in which the Castle can be constructed.
        x1, y1 = (math.floor(pos) for pos in util.min_point(flag_positions))
        x2, y2 = (math.ceil(pos) for pos in util.max_point(flag_positions))
        # Adjusts positions to keep the Castle strictly inside the flags.
        x1 += 3
        y1 += 3
        x2 -= 3
        y2 -= 3

        # P1 constructs castle
        p1_builds_castle = self._add_trigger(p1_builds_castle_name)
        p1_builds_castle.enabled = False
        self._add_activate(rts.names.begin, p1_builds_castle_name)
        p1_c_cond = p1_builds_castle.add_condition(conditions.object_in_area)
        p1_c_cond.amount_or_quantity = 1
        p1_c_cond.player = 1
        p1_c_cond.object_list = buildings.castle
        util_triggers.set_cond_area(p1_c_cond, x1, y1, x2, y2)
        self._add_activate(p1_builds_castle_name, p1_wins_name)
        self._add_deactivate(p1_builds_castle_name, p1_loses_army_name)
        self._add_deactivate(p1_builds_castle_name, p2_builds_castle_name)
        self._add_deactivate(p1_builds_castle_name, p2_loses_army_name)
        p1_castle_var = p1_builds_castle.add_effect(effects.change_variable)
        p1_castle_var.quantity = 1
        p1_castle_var.operation = ChangeVarOp.set_op.value
        p1_castle_var.from_variable = self._var_ids['p1-castle-constructed']
        p1_castle_var.message = 'p1-castle-constructed'

        # P2 loses army
        p2_loses_army = self._add_trigger(p2_loses_army_name)
        p2_loses_army.enabled = False
        self._add_activate(rts.names.begin, p2_loses_army_name)
        util_triggers.add_cond_pop0(p2_loses_army, 2)
        self._add_activate(p2_loses_army_name, p1_wins_name)
        self._add_deactivate(p2_loses_army_name, p1_builds_castle_name)
        self._add_deactivate(p2_loses_army_name, p1_loses_army_name)
        self._add_deactivate(p2_loses_army_name, p2_builds_castle_name)

        # P1 wins
        self._add_effect_p1_score(rts.p1_wins, event.MAX_POINTS)

        # P2 constructs castle
        p2_builds_castle = self._add_trigger(p2_builds_castle_name)
        p2_builds_castle.enabled = False
        self._add_activate(rts.names.begin, p2_builds_castle_name)
        p2_c_cond = p2_builds_castle.add_condition(conditions.object_in_area)
        p2_c_cond.amount_or_quantity = 1
        p2_c_cond.player = 2
        p2_c_cond.object_list = buildings.castle
        util_triggers.set_cond_area(p2_c_cond, x1, y1, x2, y2)
        self._add_activate(p2_builds_castle_name, p2_wins_name)
        self._add_deactivate(p2_builds_castle_name, p2_loses_army_name)
        self._add_deactivate(p2_builds_castle_name, p1_builds_castle_name)
        self._add_deactivate(p2_builds_castle_name, p1_loses_army_name)
        p2_castle_var = p2_builds_castle.add_effect(effects.change_variable)
        p2_castle_var.quantity = 1
        p2_castle_var.operation = ChangeVarOp.set_op.value
        p2_castle_var.from_variable = self._var_ids['p2-castle-constructed']
        p2_castle_var.message = 'p2-castle-constructed'

        # P1 loses army
        p1_loses_army = self._add_trigger(p1_loses_army_name)
        p1_loses_army.enabled = False
        self._add_activate(rts.names.begin, p1_loses_army_name)
        util_triggers.add_cond_pop0(p1_loses_army, 1)
        self._add_activate(p1_loses_army_name, p2_wins_name)
        self._add_deactivate(p1_loses_army_name, p2_builds_castle_name)
        self._add_deactivate(p1_loses_army_name, p2_loses_army_name)
        self._add_deactivate(p1_loses_army_name, p1_builds_castle_name)

        # P2 wins
        self._add_effect_p2_score(rts.p2_wins, event.MAX_POINTS)

        # Cleanup removes units from player control.
        for p in (Player.ONE, Player.TWO):
            change_to_0 = rts.cleanup.add_effect(effects.change_ownership)
            change_to_0.player_source = p.value
            change_to_0.player_target = Player.GAIA.value
            # Don't include (0, 0), since P1's Invisible Object is there.
            util_triggers.set_effect_area(change_to_0, 1, 1, 79, 79)

        # Removes stone after round is over
        util_triggers.add_effect_modify_res(
            rts.cleanup, 0, util_triggers.ACC_ATTR_STONE)

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
        umgr = self._scn.object_manager.unit_manager

        util_triggers.add_effect_modify_res(
            rts.init, 650, util_triggers.ACC_ATTR_STONE)

        # Begin changes ownership
        for p in (Player.ONE, Player.TWO):
            ulst = umgr.get_units_in_area(80.0, 0.0, 160.0, 80.0, players=[p])
            for unit in ulst:
                self._create_unit_sequence(p, unit, rts)

        # P2 loses castle.
        p2_loses_castle = self._add_trigger(p2_loses_castle_name)
        p2_loses_castle.enabled = False
        p2_no_castle = p2_loses_castle.add_condition(conditions.object_in_area)
        p2_no_castle.inverted = True
        p2_no_castle.player = Player.TWO.value
        p2_no_castle.amount_or_quantity = 1
        p2_no_castle.object_list = buildings.castle
        util_triggers.set_cond_area(p2_no_castle, 80, 0, 159, 79)
        p2_castle_var = p2_loses_castle.add_effect(effects.change_variable)
        p2_castle_var.quantity = 1
        p2_castle_var.operation = ChangeVarOp.set_op.value
        p2_castle_var.from_variable = self._var_ids['p2-castle-destroyed']
        p2_castle_var.message = 'p2-castle-destroyed'
        self._add_activate(rts.names.begin, p2_loses_castle_name)
        self._add_activate(p2_loses_castle_name, rts.names.p1_wins)
        self._add_deactivate(p2_loses_castle_name, p2_loses_army_name)
        self._add_deactivate(p2_loses_castle_name, p1_loses_castle_name)
        self._add_deactivate(p2_loses_castle_name, p1_loses_army_name)

        # P2 loses army.
        p2_loses_army = self._add_trigger(p2_loses_army_name)
        p2_loses_army.enabled = False
        self._add_activate(rts.names.begin, p2_loses_army_name)
        util_triggers.add_cond_pop0(p2_loses_army, 2)
        self._add_activate(p2_loses_army_name, rts.names.p1_wins)
        self._add_deactivate(p2_loses_army_name, p1_loses_castle_name)
        self._add_deactivate(p2_loses_army_name, p1_loses_army_name)
        self._add_deactivate(p2_loses_army_name, p2_loses_castle_name)

        # P1 wins.
        rts.p1_wins.enabled = False
        self._add_effect_p1_score(rts.p1_wins, event.MAX_POINTS)

        # P1 loses castle.
        p1_loses_castle = self._add_trigger(p1_loses_castle_name)
        p1_loses_castle.enabled = False
        p1_no_castle = p1_loses_castle.add_condition(conditions.object_in_area)
        p1_no_castle.inverted = True
        p1_no_castle.player = Player.ONE.value
        p1_no_castle.amount_or_quantity = 1
        p1_no_castle.object_list = buildings.castle
        util_triggers.set_cond_area(p1_no_castle, 80, 0, 159, 79)
        p1_castle_var = p1_loses_castle.add_effect(effects.change_variable)
        p1_castle_var.quantity = 1
        p1_castle_var.operation = ChangeVarOp.set_op.value
        p1_castle_var.from_variable = self._var_ids['p1-castle-destroyed']
        p1_castle_var.message = 'p1-castle-destroyed'
        self._add_activate(rts.names.begin, p1_loses_castle_name)
        self._add_activate(p1_loses_castle_name, rts.names.p2_wins)
        self._add_deactivate(p1_loses_castle_name, p1_loses_army_name)
        self._add_deactivate(p1_loses_castle_name, p2_loses_castle_name)
        self._add_deactivate(p1_loses_castle_name, p2_loses_army_name)

        # P1 loses army.
        p1_loses_army = self._add_trigger(p1_loses_army_name)
        p1_loses_army.enabled = False
        self._add_activate(rts.names.begin, p1_loses_army_name)
        util_triggers.add_cond_pop0(p1_loses_army, 1)
        self._add_activate(p1_loses_army_name, rts.names.p2_wins)
        self._add_deactivate(p1_loses_army_name, p2_loses_castle_name)
        self._add_deactivate(p1_loses_army_name, p2_loses_army_name)
        self._add_deactivate(p1_loses_army_name, p1_loses_castle_name)

        # P2 wins
        rts.p2_wins.enabled = False
        self._add_effect_p2_score(rts.p2_wins, event.MAX_POINTS)

        # Cleanup removes units from player control.
        for p in (Player.ONE, Player.TWO):
            change_to_0 = rts.cleanup.add_effect(effects.change_ownership)
            change_to_0.player_source = p.value
            change_to_0.player_target = Player.GAIA.value
            util_triggers.set_effect_area(change_to_0, 80, 0, 159, 79)

        # Removes stone after round is over.
        util_triggers.add_effect_modify_res(
            rts.cleanup, 0, util_triggers.ACC_ATTR_STONE)

    def _add_regicide(self, index: int) -> None:
        """
        Adds the Regicide minigame at the given index.

        Checks index is not 0 (cannot use a minigame as the tiebreaker).
        """
        assert index
        rts = _RoundTriggers(self, index)
        umgr = self._scn.object_manager.unit_manager
        prefix = f'[R{index}]' if index else '[T]'
        stalemate_name = f'{prefix} Regicide Stalemate'

        for p in (Player.ONE, Player.TWO):
            # Leaves a small buffer to avoid selecting the units at the
            # very top of the map.
            ulst = umgr.get_units_in_area(160.0, 5.0, 235.0, 80.0, players=[p])
            uconsts = ({u.unit_id for u in ulst}
                       | {UCONST_GENGHIS_KHAN, UCONST_JOAN_OF_ARC})
            for unit in ulst:
                if unit.unit_id == units.king:
                    unit.unit_id = self._regicide_hero
                    kill_hero_name = f"{prefix} Player {p.value}'s Hero Killed"
                    kill_hero = self._add_trigger(kill_hero_name)
                    kill_hero.enabled = False
                    obj_area = kill_hero.add_condition(
                        conditions.object_in_area)
                    obj_area.inverted = True
                    obj_area.player = p.value
                    obj_area.amount_or_quantity = 1
                    obj_area.object_list = self._regicide_hero
                    util_triggers.set_cond_area(obj_area, 160, 5, 234, 79)
                    record_kill = kill_hero.add_effect(effects.change_variable)
                    record_kill.quantity = 1
                    record_kill.operation = ChangeVarOp.add.value
                    record_kill.from_variable = self._var_ids[
                        f'p{p.value}-hero-killed'
                    ]
                    for uconst in uconsts:
                        kill_unit = kill_hero.add_effect(effects.kill_object)
                        kill_unit.player_source = p.value
                        kill_unit.object_list_unit_id = uconst
                        util_triggers.set_effect_area(
                            kill_unit, 160, 5, 234, 79)
                    self._add_activate(rts.names.begin, kill_hero_name)
                    self._add_deactivate(rts.names.cleanup, kill_hero_name)
                self._create_unit_sequence(
                    p, unit, rts, True, self._regicide_buff)

            # Creates triggers for changing points.
            for k in range(100):
                name = f'{prefix} Regicide P{p.value} Pop Under {k}'
                pts = self._add_trigger(name)
                pts.enabled = False
                pop_under_k = pts.add_condition(conditions.accumulate_attribute)
                pop_under_k.inverted = True
                pop_under_k.amount_or_quantity = k + 1
                pop_under_k.player = p.value
                pop_under_k.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_POP_HEADROOM)
                self._add_effect_score(pts, other_player(p), 1)
                self._add_activate(rts.names.begin, name)
                self._add_deactivate(rts.names.cleanup, name)
                if self._regicide_hero == units.king:
                    self._add_deactivate(stalemate_name, name)
                self._add_deactivate(
                    rts.names.p1_wins if p is Player.ONE else rts.names.p2_wins,
                    name)

            # Cleanup removes units from player control.
            for uconst in uconsts:
                remove = rts.cleanup.add_effect(effects.remove_object)
                remove.object_list_unit_id = uconst
                remove.player_source = p.value
                util_triggers.set_effect_area(remove, 160, 0, 239, 79)

        # Stalemate possible only if the hero unit is a King.
        if self._regicide_hero == units.king:
            stalemate = self._add_trigger(stalemate_name)
            stalemate.enabled = False
            self._add_activate(rts.names.begin, stalemate_name)
            self._add_activate(stalemate_name, rts.names.cleanup)
            self._add_deactivate(stalemate_name, rts.names.p1_wins)
            self._add_deactivate(stalemate_name, rts.names.p2_wins)
            self._add_deactivate(rts.names.p1_wins, stalemate_name)
            self._add_deactivate(rts.names.p2_wins, stalemate_name)
            for p in (Player.ONE, Player.TWO):
                pop1 = stalemate.add_condition(conditions.accumulate_attribute)
                pop1.player = p.value
                pop1.amount_or_quantity = 1
                pop1.resource_type_or_tribute_list = (
                    util_triggers.ACC_ATTR_POP_HEADROOM)
                popnot2 = stalemate.add_condition(
                    conditions.accumulate_attribute)
                popnot2.player = p.value
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


    def _add_fight(self, index: int, f: Fight) -> None:
        """Adds the fight with the given index."""
        rts = _RoundTriggers(self, index)

        self._add_activate(rts.names.begin, rts.names.p1_wins)
        self._add_activate(rts.names.begin, rts.names.p2_wins)

        self._add_deactivate(rts.names.p1_wins, rts.names.p2_wins)
        self._add_effect_p1_score(rts.p1_wins, self._events[index].p1_bonus)
        util_triggers.add_cond_pop0(rts.p1_wins, Player.TWO.value)

        self._add_deactivate(rts.names.p2_wins, rts.names.p1_wins)
        self._add_effect_p2_score(rts.p2_wins, self._events[index].p2_bonus)
        util_triggers.add_cond_pop0(rts.p2_wins, Player.ONE.value)

        for p, ulst in ((Player.ONE, f.p1_units), (Player.TWO, f.p2_units)):
            self._add_fight_units(rts, index, p, ulst)

    def _add_fight_units(self, rts: _RoundTriggers, index: int, p: Player,
                         ulst: List[UnitStruct]) -> None:
        """
        Adds the units from the player's unit list to the scenario.
        `index` is the index of the fight in which the units participate.
        Checks that p is Player.ONE or Player.TWO.
        """
        assert p in (Player.ONE, Player.TWO)
        prefix = f'[R{index}]' if index else '[T]' # Index 0 is the Tiebreaker.
        for u in ulst:
            self._create_unit_sequence(p, u, rts, False)
        ucnts = Counter(u.unit_id for u in ulst)
        for uconst, cnt in ucnts.items():
            uname = units.unit_names[uconst]
            for k in range(cnt):
                pts_name = (
                    f'{prefix} P{p.value} {util.pretty_print_name(uname)} {k}'
                )
                pts = self._add_trigger(pts_name)
                pts.enabled = False
                obj_in_area = pts.add_condition(conditions.object_in_area)
                obj_in_area.inverted = True
                util_triggers.set_cond_area(obj_in_area, 80, 80, 159, 159)
                obj_in_area.amount_or_quantity = k + 1
                obj_in_area.player = p.value
                obj_in_area.object_list = uconst
                self._add_activate(rts.names.begin, pts_name)
                self._add_deactivate(
                    rts.names.p1_wins if p == Player.ONE else rts.names.p2_wins,
                    pts_name)
                self._add_effect_score(
                    pts,
                    Player.TWO if p == Player.ONE else Player.ONE,
                    self._events[index].points[uname])
        uconsts = {u.unit_id for u in ulst}
        for uconst in uconsts:
            remove = rts.cleanup.add_effect(effects.remove_object)
            remove.object_list_unit_id = uconst
            remove.player_source = p.value
            util_triggers.set_effect_area(remove, 80, 80, 159, 159)


def build_scenario(scenario_template: str = SCENARIO_TEMPLATE,
                   unit_template: str = UNIT_TEMPLATE,
                   event_json: str = event.DEFAULT_FILE,
                   xbow_template: str = XBOW_TEMPLATE,
                   arena_template: str = ARENA_TEMPLATE,
                   output: str = OUTPUT,
                   hero: int = REGICIDE_DEFAULT_HERO,
                   buff: bool = REGICIDE_DEFAULT_BUFF):
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
    scn_data = ScnData(scn, events, xbow_scn, arena_scn, hero, buff)
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
    hero = args.hero[0]
    buff = args.buff

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
    if hero not in (units.king, UCONST_JOAN_OF_ARC, UCONST_GENGHIS_KHAN):
        msg = (f'hero is {hero} but must be one of:\n'
               + f'  {units.king} - King\n'
               + f'  {UCONST_JOAN_OF_ARC} - Joan\n'
               + f'  {UCONST_GENGHIS_KHAN} - Khan')
        raise ValueError(msg)

    build_scenario(scenario_template=scenario_map, unit_template=units_scn,
                   event_json=event_json, output=out, hero=hero, buff=buff)


def build_publish_files(args):
    """
    Unpacks arguments from command line args and builds the files needed
    to upload the scenario as a mod.
    """
    raise AssertionError('Not implemented.')


def build_minigames(args): # pylint: disable=unused-argument
    """
    Builds each minigame as an individual file, as well as one file
    with all of the minigames.
    """
    # Individual minigames.
    for name, event_json in INDIVIDUAL_MINIGAME_EVENTS.items():
        build_scenario(SCENARIO_TEMPLATE, UNIT_TEMPLATE, event_json,
                       XBOW_TEMPLATE, ARENA_TEMPLATE, f'{name}.aoe2scenario')
    # All minigames.
    build_scenario(SCENARIO_TEMPLATE, UNIT_TEMPLATE, ALL_MINIGAMES_EVENTS,
                   XBOW_TEMPLATE, ARENA_TEMPLATE, ALL_MINIGAMES_OUTPUT)
    # Feudal
    build_scenario(SCENARIO_TEMPLATE, 'unit-feudal.aoe2scenario',
                   'events-feudal.json', XBOW_TEMPLATE, ARENA_TEMPLATE,
                   'Feudal Skirmishes.aoe2scenario')
    # Castle
    build_scenario(SCENARIO_TEMPLATE, 'unit-castle.aoe2scenario',
                   'events-castle.json', XBOW_TEMPLATE, ARENA_TEMPLATE,
                   'Castle Warfare.aoe2scenario')
    # Imperial
    build_scenario(SCENARIO_TEMPLATE, 'unit-imperial.aoe2scenario',
                   'events-imperial.json', XBOW_TEMPLATE, ARENA_TEMPLATE,
                   'Imperial Conquest.aoe2scenario')
    # Fights Only
    build_scenario(SCENARIO_TEMPLATE, UNIT_TEMPLATE, 'events-fights.json',
                   XBOW_TEMPLATE, ARENA_TEMPLATE, 'Fights Only.aoe2scenario')
    # Full
    build_scenario(SCENARIO_TEMPLATE, UNIT_TEMPLATE, 'events.json',
                   XBOW_TEMPLATE, ARENA_TEMPLATE, 'Full.aoe2scenario')


def scratch(args): # pylint: disable=unused-argument
    """Runs a simple test experiment."""
    # scratch_path = 'scratch.aoe2scenario'
    scn = AoE2Scenario(SCENARIO_TEMPLATE)
    umgr = scn.object_manager.unit_manager
    ulst = umgr.get_player_units(Player.TWO)
    for unit in ulst:
        if unit.unit_id == buildings.stone_wall:
            print(f'{unit.unit_id}: ({unit.x}, {unit.y}) - {unit.rotation}')


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
    parser_build.add_argument('--hero', nargs=1, type=int,
                              default=[REGICIDE_DEFAULT_HERO],
                              help=('The hero to use for the Regicide minigame:'
                                    + f'  {units.king} - King,'
                                    + f'  {UCONST_JOAN_OF_ARC} - Joan,'
                                    + f'  {UCONST_GENGHIS_KHAN} - Khan.'))

    parser_build.add_argument('--buff', action='store_true',
                              help='Pass this flag to buff the Regicide hero.')
    parser_build.add_argument(
        '--output', '-o', nargs=1, default=[OUTPUT],
        help='Filepath to which the output is written, must differ from all input files.' #pylint: disable=line-too-long
    )
    parser_build.set_defaults(func=call_build_scenario)

    parser_publish = subparsers.add_parser('publish',
                                           help='Creates mod upload files.')
    parser_publish.set_defaults(func=build_publish_files)

    parser_minigames = subparsers.add_parser('minigames',
                                             help='Creates minigame scenarios.')
    parser_minigames.set_defaults(func=build_minigames)

    parser_scratch = subparsers.add_parser('scratch', help='Runs a test.')
    parser_scratch.set_defaults(func=scratch)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
