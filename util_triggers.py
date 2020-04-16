"""
Utility functions for interacting with triggers.

GNU General Public License v3.0: See the LICENSE file.
"""


from enum import Enum
from AoE2ScenarioParser.datasets import conditions, effects
from AoE2ScenarioParser.objects.condition_obj import ConditionObject
from AoE2ScenarioParser.objects.effect_obj import EffectObject
from AoE2ScenarioParser.objects.trigger_obj import TriggerObject


# Index of stone in the accumulate attribute condition list.
ACC_ATTR_STONE = 2


# Index of population headroom in the accumulate attribute condition list.
ACC_ATTR_POP_HEADROOM = 11


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


def add_cond_destroy_obj(trigger: TriggerObject, unit_id: int) -> None:
    """
    Adds a condition to trigger that the unit with id unit_id is destroyed.
    """
    destroy_obj = trigger.add_condition(conditions.destroy_object)
    destroy_obj.unit_object = unit_id


def add_cond_gaia_defeated(trigger: TriggerObject) -> None:
    """
    Adds a condition to trigger that the gaia player is defeated.

    This condition will never be True. It can be used to ensure that
    objectives are never checked off.
    """
    gaia_defeated = trigger.add_condition(conditions.player_defeated)
    gaia_defeated.player = 0


def add_cond_hp0(trigger: TriggerObject, uid: int) -> None:
    """
    Adds a condition to trigger that the unit with id number uid
    has 0 Hit Points.

    This condition essentially is the same as a Destroy Object condition,
    but it is satisfied at the beginning of a destruction animation,
    rather than at the end.
    """
    hp0 = trigger.add_condition(conditions.object_hp)
    hp0.amount_or_quantity = 0
    hp0.comparison = VarValComp.equal.value
    hp0.unit_object = uid


def add_cond_pop0(trigger: TriggerObject, player: int) -> None:
    """Adds a condition to trigger that the player has population 0."""
    pop0 = trigger.add_condition(conditions.accumulate_attribute)
    pop0.player = player
    pop0.amount_or_quantity = 1
    pop0.resource_type_or_tribute_list = ACC_ATTR_POP_HEADROOM
    pop0.inverted = True


def add_cond_timer(trigger: TriggerObject, num_seconds: int) -> None:
    """Adds a timer condition to trigger to wait num_seconds seconds."""
    timer = trigger.add_condition(conditions.timer)
    timer.timer = num_seconds


def add_effect_activate(source: TriggerObject, target: int) -> None:
    """Adds an effect to source to activate the trigger with index target."""
    activate = source.add_effect(effects.activate_trigger)
    activate.trigger_id = target

def add_effect_change_own_unit(trigger: TriggerObject, source: int, target: int,
                               uid: int) -> None:
    """
    Adds an effect to trigger to change the ownership of the unit with
    id uid from player source to player target.
    """
    change_own = trigger.add_effect(effects.change_ownership)
    change_own.player_source = source
    change_own.player_target = target
    change_own.selected_object_id = uid
    change_own.number_of_units_selected = 1

def add_effect_deactivate(source: TriggerObject, target: int) -> None:
    """Adds an effect to source to dectivate the trigger with index target."""
    deactivate = source.add_effect(effects.deactivate_trigger)
    deactivate.trigger_id = target


def add_effect_delcare_victory(trigger: TriggerObject, player: int) -> None:
    """Adds to trigger an effect to Declare Victory to the player."""
    declare_victory = trigger.add_effect(effects.declare_victory)
    declare_victory.player_source = player


def add_effect_modify_res(trigger: TriggerObject, player: int, quantity: int,
                          tribute_list: int) -> None:
    """
    Adds an effect to trigger to set the player's resource at the
    index given by tribute_list to quantity.
    """
    modify_res = trigger.add_effect(effects.modify_resource)
    modify_res.player_source = player
    modify_res.quantity = quantity
    modify_res.tribute_list = tribute_list
    modify_res.item_id = -1
    modify_res.operation = ChangeVarOp.set_op.value


def add_effect_remove_obj(trigger: TriggerObject, unit_id: int,
                          player: int) -> None:
    """
    Adds to trigger an effect to remove the unit with it unit_id.
    The number of the player who owns the unit is given by player.
    """
    remove_obj = trigger.add_effect(effects.remove_object)
    remove_obj.number_of_units_selected = 1
    remove_obj.player_source = player
    remove_obj.selected_object_id = unit_id


def add_effect_research_tech(trigger: TriggerObject, tech_id: int,
                             player: int) -> None:
    """
    Adds to trigger an effect to research the technology given by tech_id
    for the indicated player.
    """
    res_tech = trigger.add_effect(effects.research_technology)
    res_tech.player_source = player
    res_tech.technology = tech_id
    res_tech.force_research_technology = True


def add_effect_teleport(trigger: TriggerObject, unit_id: int,
                        x: int, y: int, player: int) -> None:
    """
    Adds to trigger an effect to teleport the unit specificed by unit_id
    to the tile (x, y). The unit must belong to the player given by
    the int player.
    """
    teleport = trigger.add_effect(effects.teleport_object)
    teleport.number_of_units_selected = 1
    teleport.player_source = player
    teleport.selected_object_id = unit_id
    teleport.location_x = x
    teleport.location_y = y


def set_cond_area(cond: ConditionObject,
                  x1: int, y1: int, x2: int, y2: int) -> None:
    """
    Sets the area selected by cond to minimum (x1, y1) and maximum (x2, y2).
    """
    cond.area_1_x = x1
    cond.area_1_y = y1
    cond.area_2_x = x2
    cond.area_2_y = y2


def set_effect_area(effect: EffectObject,
                    x1: int, y1: int, x2: int, y2: int) -> None:
    """
    Sets the area selected by effect to minimum (x1, y1) and maximum (x2, y2).
    """
    effect.area_1_x = x1
    effect.area_1_y = y1
    effect.area_2_x = x2
    effect.area_2_y = y2
