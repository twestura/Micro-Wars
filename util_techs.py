
"""
Utility functions for various operations with technologies.

GNU General Public License v3.0: See the LICENSE file.
"""


from bidict import bidict
from AoE2ScenarioParser.datasets import techs


# Bidirectional map between technology names and ids.
TECH_IDS = bidict()
for x in techs.__dict__:
    if '__' not in x and 'get_tech_id_by_string' not in x:
        TECH_IDS[x] = techs.get_tech_id_by_string(x)


def is_tech(tech_name: str) -> bool:
    """Returns True if tech_name is a valid technology name, False otherwise."""
    return tech_name in TECH_IDS
