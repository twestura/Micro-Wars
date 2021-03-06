"""
Tests utility functions.

GNU General Public License v3.0: See the LICENSE file.
"""


import math
import random
from nose.tools import assert_almost_equal, eq_, raises
from util import (
    flip_angle_h, pretty_print_name, min_point, max_point
)


@raises(ValueError)
def test_flip_angle_h_error0():
    flip_angle_h(-0.0000001)


@raises(ValueError)
def test_flip_angle_h_error1():
    flip_angle_h(math.tau)


def test_flip_angle_h_0():
    theta = 0.0
    phi = flip_angle_h(theta)
    expected = math.pi / 2.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_1():
    theta = math.pi / 4.0
    phi = flip_angle_h(theta)
    expected = math.pi / 4.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_2():
    theta = math.pi / 2.0
    phi = flip_angle_h(theta)
    expected = 0.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_3():
    theta = 3.0 * math.pi / 4.0
    phi = flip_angle_h(theta)
    expected = 7.0 * math.pi / 4.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_4():
    theta = 5.0 * math.pi / 4.0
    phi = flip_angle_h(theta)
    expected = 5.0 * math.pi / 4.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_5():
    theta = 7.0 * math.pi / 4.0
    phi = flip_angle_h(theta)
    expected = 3.0 * math.pi / 4.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_6():
    theta = math.pi
    phi = flip_angle_h(theta)
    expected = 3.0 * math.pi / 2.0
    assert_almost_equal(expected, phi)


def test_flip_angle_h_7():
    theta = 3.0 * math.pi / 2.0
    phi = flip_angle_h(theta)
    expected = math.pi
    assert_almost_equal(expected, phi)


def test_flip_angle_h_8():
    num_tests = 1000
    for __ in range(num_tests):
        theta = random.uniform(0.0, math.tau) % math.tau
        double_flip = flip_angle_h(flip_angle_h(theta))
        assert_almost_equal(theta, double_flip)


def test_pretty_name0():
    eq_('Militia', pretty_print_name('militia'))


def test_pretty_name1():
    eq_('Scout Cavalry', pretty_print_name('scout_cavalry'))


def test_pretty_name2():
    eq_('Elite Chu Ko Nu', pretty_print_name('elite_chu_ko_nu'))


def test_min_point0():
    eq_(None, min_point([]))


def test_min_point1():
    eq_((5, 7), min_point([(5, 7)]))


def test_min_point2():
    eq_((5, 6), min_point([(5, 7), (6, 6)]))


def test_min_point3():
    eq_((0, 3), min_point([(5, 7), (6, 6), (0, 11), (23, 3), (5, 5)]))


def test_max_point0():
    eq_(None, max_point([]))


def test_max_point1():
    eq_((5, 7), max_point([(5, 7)]))


def test_max_point2():
    eq_((6, 7), max_point([(5, 7), (6, 6)]))


def test_max_point3():
    eq_((23, 11), max_point([(5, 7), (6, 6), (0, 11), (23, 3), (5, 5)]))
