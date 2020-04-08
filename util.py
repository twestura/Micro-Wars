"""
Various utility functions used in building Micro Wars!

GNU General Public License v3.0: See the LICENSE file.
"""


import math


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
