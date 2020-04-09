"""
Represents unit fights for Micro Wars.

GNU General Public License v3.0: See the LICENSE file.
"""

import json
import util_techs
import util_units


# Default filepath from which to load fight data.
DEFAULT_FILE = 'fights.json'


def load_fights(filepath=DEFAULT_FILE):
    """
    TODO specify
    """
    with open(filepath) as json_file:
        loaded = json.loads(json_file.read())
    return [FightData(dct['techs'], dct['points']) for dct in loaded]


class FightData:
    """An instance represents a fight in the middle of the map."""

    def __init__(self, techs, points):
        """
        Initializes a new FightData object.

        Arguments:
            techs: The names of the technologies researched at the start of
                the fight.
            points: A map from unit name to the number of points killing that
                unit is worth.
        Raises:
            ValueError:
                * An element of techs is not a valid technology name.
                * A key in points is not a valid unit name.
                * A value in points is nonpositive.
        """
        self.techs = techs
        self.points = points
        for tech_name in self.techs:
            if not util_techs.is_tech(tech_name):
                raise ValueError(f'{tech_name} is not a valid tech name.')
        for unit_name, point_value in self.points.items():
            if not util_units.is_unit(unit_name):
                raise ValueError(f'{unit_name} is not a valid unit name.')
            if point_value <= 0:
                msg = f'{unit_name}: {point_value} must have a positive value.'
                raise ValueError(msg)

    def __str__(self):
        return json.dumps({'techs': self.techs, 'points': self.points})

    @staticmethod
    def from_json(s: str):
        """Returns a FightData object that is represented by json string s."""
        loaded = json.loads(s)
        return FightData(loaded['techs'], loaded['points'])
