"""Splitting the value of a purchase with several items (spec, rule 4). Values worked out by hand."""
from decimal import Decimal

from src.purchase_history import item_values, split_total

D = Decimal


def test_split_proportional_to_list_price():
    # R$ 30.00 between games of R$ 60 and R$ 20: 3/4 and 1/4
    assert split_total(D("30.00"), [D("60"), D("20")]) == [D("22.50"), D("7.50")]


def test_split_never_loses_cents():
    # R$ 10.00 in 3: 3.333... each; the leftover cent goes to the largest remainder
    parts = split_total(D("10.00"), [1, 1, 1])
    assert parts == [D("3.34"), D("3.33"), D("3.33")]
    assert sum(parts) == D("10.00")


def test_bundle_with_games_of_different_prices():
    # Games 1 (R$ 100), 2 (R$ 50) and 3 (R$ 50) in a R$ 47.99 bundle: 1/2, 1/4, 1/4.
    # 4799 cents -> 2399.5 / 1199.75 / 1199.75; floors sum 4797; the 2 leftover cents go to
    # the largest remainders (0.75 and 0.75): 2399 / 1200 / 1200
    values = item_values(D("47.99"), [1, 2, 3], {1: D("100"), 2: D("50"), 3: D("50")})
    assert values == [D("23.99"), D("12.00"), D("12.00")]
    assert sum(values) == D("47.99")


def test_free_game_in_a_bundle_gets_zero():
    # A free game has list price 0, so it gets no part of the money
    assert item_values(D("40.00"), [1, 2], {1: D("80"), 2: D("0")}) == [D("40.00"), D("0.00")]


def test_bundle_with_a_game_without_list_price_is_split_equally():
    assert item_values(D("40.00"), [1, 2], {1: D("80"), 2: None}) == [D("20.00"), D("20.00")]


def test_items_of_the_same_game_split_its_part_equally():
    # Game 1 (2 items) and game 2 (1 item), same price: R$ 30 each game, R$ 15 each item of game 1
    assert item_values(D("60.00"), [1, 1, 2], {1: D("10"), 2: D("10")}) == [D("15.00"), D("15.00"), D("30.00")]


def test_single_item_gets_the_whole_total():
    assert item_values(D("19.96"), [1], {1: None}) == [D("19.96")]
