"""
Utility functions for interacting with triggers.

GNU General Public License v3.0: See the LICENSE file.
"""


from AoE2ScenarioParser.datasets import conditions


# TODO annotate type of trigger
def add_cond_gaia_defeated(trigger) -> None:
    """
    Adds a condition to trigger that the gaia player is defeated.

    This condition will never be True. It can be used to ensure that
    objectives are never checked off.
    """
    gaia_defeated = trigger.add_condition(conditions.player_defeated)
    gaia_defeated.player = 0
