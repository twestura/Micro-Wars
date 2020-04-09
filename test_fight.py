"""
Tests the representation of unit fights.

GNU General Public License v3.0: See the LICENSE file.
"""


from nose.tools import * # pylint: disable=wildcard-import,unused-wildcard-import
from fight import * # pylint: disable=wildcard-import,unused-wildcard-import


def test_load0():
    s = '{ "techs": ["drill"], "points": { "bombard_cannon": 20 } }'
    fd = FightData.from_json(s)
    eq_(['drill'], fd.techs)
    eq_({'bombard_cannon': 20}, fd.points)

@raises(ValueError)
def test_load1():
    s = '{ "techs": ["invalid-name"], "points": { "bombard_cannon": 20 } }'
    FightData.from_json(s)


@raises(ValueError)
def test_load2():
    s = '{ "techs": ["drill"], "points": { "invalid-name": 20 } }'
    FightData.from_json(s)


@raises(ValueError)
def test_load3():
    s = '{ "techs": ["drill"], "points": { "bombard_cannon": 0 } }'
    FightData.from_json(s)


@raises(ValueError)
def test_load4():
    s = '{ "techs": ["drill"], "points": { "bombard_cannon": -1 } }'
    FightData.from_json(s)
