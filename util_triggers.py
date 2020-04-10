"""
Utility functions for interacting with triggers.

GNU General Public License v3.0: See the LICENSE file.
"""


from AoE2ScenarioParser.datasets import conditions, effects
from AoE2ScenarioParser.objects.trigger_obj import TriggerObject


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
