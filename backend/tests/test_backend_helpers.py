from backend.helpers import overs_str_from_balls


def test_overs_str_from_balls_zero():
    assert overs_str_from_balls(0) == "0.0"


def test_overs_str_from_balls_full_over():
    assert overs_str_from_balls(6) == "1.0"


def test_overs_str_from_balls_mixed():
    assert overs_str_from_balls(13) == "2.1"


def test_overs_str_from_balls_coerce_int_like():
    # Accept int-like float but coerce to int
    assert overs_str_from_balls(int(7.0)) == "1.1"
