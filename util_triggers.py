"""
Utility functions for interacting with triggers.

GNU General Public License v3.0: See the LICENSE file.
"""


from AoE2ScenarioParser.datasets import conditions, effects
from AoE2ScenarioParser.objects.condition_obj import ConditionObject
from AoE2ScenarioParser.objects.effect_obj import EffectObject
from AoE2ScenarioParser.objects.trigger_obj import TriggerObject


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


def add_cond_timer(trigger: TriggerObject, num_seconds: int) -> None:
    """Adds a timer condition to trigger to wait num_seconds seconds."""
    timer = trigger.add_condition(conditions.timer)
    timer.timer = num_seconds


def add_effect_activate(source: TriggerObject, target: int) -> None:
    """Adds an effect to source to activate the trigger with index target."""
    activate = source.add_effect(effects.activate_trigger)
    activate.trigger_id = target


def add_effect_deactivate(source: TriggerObject, target: int) -> None:
    """Adds an effect to source to dectivate the trigger with index target."""
    deactivate = source.add_effect(effects.deactivate_trigger)
    deactivate.trigger_id = target


def add_effect_delcare_victory(trigger: TriggerObject, player: int) -> None:
    """Adds to trigger an effect to Declare Victory to the player."""
    declare_victory = trigger.add_effect(effects.declare_victory)
    declare_victory.player_source = player


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
    # TODO find out what force research technology does
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
