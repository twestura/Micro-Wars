"""
Various utility functions used in building Micro Wars!

GNU General Public License v3.0: See the LICENSE file.
"""


import math
from typing import List, Tuple


def flip_angle_h(theta: float) -> float:
    """
    Returns an angle phi, where phi equals theta mirrored across the
    horizontal axis that runs parallel to math.pi / 4.0.

    Note that 0.0 radians points Northeast, so an eighth of a turn around
    the circle gives the line running West to East.

    Raises:
        ValueError if theta does not satisfy 0.0 <= theta < math.tau.
    """
    if theta < 0.0 or theta >= math.tau:
        raise ValueError(f'theta {theta} must be in [0, tau).')

    if theta < 3.0 * math.pi / 4.0:
        phi = (theta + 2.0 * (math.pi / 4.0 - theta)) % math.tau
    elif theta < 7.0 * math.pi / 4.0:
        phi = theta + 2.0 * (5.0 * math.pi / 4.0 - theta)
    else:
        phi = math.tau - theta + math.pi / 2.0

    assert 0.0 <= phi < math.tau, f'theta: {theta}, phi: {phi}'
    return phi


def pretty_print_name(name: str) -> str:
    """
    Returns a pretty-printed version of the name string.
    Replaces all underscores with spaces and capitalizes the first letter
    of each word.
    For example, elite_chu_ko_nu -> Elite Chu Ko Nu.
    """
    return ' '.join(s[0].upper() + s[1:] for s in name.split('_'))


def min_point(points: List[Tuple[int, int]]) -> Tuple[int, int]:
    """
    Returns the component-wise (min(x), min(y)) of the list of points,
    or None if the list of points is empty.
    """
    if not points:
        return None
    x = min(a for a, __ in points)
    y = min(b for __, b in points)
    return x, y


def max_point(points: List[Tuple[int, int]]) -> Tuple[int, int]:
    """
    Returns the component-wise maximum (max(x), max(y)) of the
    list of points, or None if the list of points is empty.
    """
    if not points:
        return None
    x = max(a for a, __ in points)
    y = max(b for __, b in points)
    return x, y
