
"""
Utility functions for various operations with scenario files.

GNU General Public License v3.0: See the LICENSE file.
"""


from typing import Tuple
from AoE2ScenarioParser.aoe2_scenario import AoE2Scenario

# TODO don't access _parsed_data directly

def get_and_inc_unit_id(scn: AoE2Scenario) -> None:
    """Returns the scenarios next unit id and increments the unit id counter."""
    data_header = scn._parsed_data['DataHeaderPiece']
    unit_id = data_header.retrievers[0].data
    data_header.retrievers[0].data += 1
    return unit_id


def map_dimensions(scn: AoE2Scenario) -> Tuple[int, int]:
    """
    Returns a tuple (x, y), where x is the number of tiles along the
    x-dimension and y is the number of tiles along the y-dimension.
    """
    map_piece = scn._parsed_data['MapPiece']
    width = map_piece.retrievers[9].data
    height = map_piece.retrievers[10].data
    return width, height
