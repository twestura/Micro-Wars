"""Creates files for the Micro Wars scenario."""


import argparse


# Relative path to the template scenario file.
SCENARIO_TEMPLATE = 'scenario-template.aoe2scenario'


# Relative path to the unit scenario file.
UNIT_TEMPLATE = 'unit-template.aoe2scenario'


# Default output scenario name.
OUTPUT = 'Micro Wars.aoe2scenario'


def build_scenario(scenario_template=SCENARIO_TEMPLATE,
                   unit_template=UNIT_TEMPLATE, output=OUTPUT):
    """
    Builds the scenario.

    Parameters:
        scenario_template: The source of the map, players, and scenario
            objectives. The units are copied to this scenario, and triggers
            are added to it.
        unit_template: A template of unit formations to copy for fights.
        output: The output path to which the resulting scenario is written.
    """
    pass


def main():
    print('Building Micro Wars.')


if __name__ == '__main__':
    main()
