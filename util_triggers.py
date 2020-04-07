"""Utility functions for various operations with triggers."""


from typing import Dict
from bidict import bidict
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario
from AoE2ScenarioParser.datasets import conditions, effects


class TriggerUtil:
    """
    Wraps a scenario file to provide convenience methods for interacting
    with triggers (I miss OCaml functors).
    """

    def __init__(self, scn: AoE2Scenario):
        """Initializes a new TriggerUtil that wraps scn."""
        self.scn = scn
        self.obj_mgr = scn.object_manager
        self.trigger_mgr = self.obj_mgr.get_trigger_object()
        # Maps a variable name to it's index in the list of trigger variables.
        self.var_index = bidict()
        # TODO map trigger name to trigger index?

    def add_header(self, name: str) -> None:
        """
        Adds a section header with title `name`.

        This trigger serves no functional purpose, but allows
        the trigger list to be broken so it is more
        human-readable in the editor.
        """
        self.trigger_mgr.add_trigger(f'-- {name} --')

    def initialize_variables(self, var_value: Dict[str, int]) -> None:
        var_init_trigger = self.trigger_mgr.add_trigger(
            f'[I] Initializes scenario variables.')
        for name, value in var_value.items():
            index = len(self.var_index)
            self.var_index[name] = index
            set_var = var_init_trigger.add_effect(effects.change_variable)
            set_var.from_variable = index
            set_var.operation = 1 # Set # TODO enum for the operation
            set_var.quantity = value
            set_var.message = f'{name}\x00'
            # TODO how to set variable name (end of file)
        print(self.trigger_mgr.get_trigger_as_string(
            trigger_id=var_init_trigger.trigger_id))
