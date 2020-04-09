"""
Tests the representation of unit fights.

GNU General Public License v3.0: See the LICENSE file.
"""


from nose.tools import eq_, raises
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


def test_start_tile0():
    eq_((0, 0), get_start_tile(0))


def test_start_tile1():
    eq_((20, 0), get_start_tile(1))


def test_start_tile2():
    eq_((40, 0), get_start_tile(2))


def test_start_tile5():
    eq_((100, 0), get_start_tile(5))


def test_start_tile6():
    eq_((0, 20), get_start_tile(6))


def test_start_tile7():
    eq_((20, 20), get_start_tile(7))


def test_start_tile8():
    eq_((40, 20), get_start_tile(8))


def test_start_tile35():
    eq_((100, 100), get_start_tile(35))
