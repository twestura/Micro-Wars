
"""
Utility functions for various operations with technologies.

GNU General Public License v3.0: See the LICENSE file.
"""


from AoE2ScenarioParser.datasets import techs


def is_tech(tech_name: str) -> bool:
    """Returns True if tech_name is a valid technology name, False otherwise."""
    return tech_name in techs.tech_names.inverse
