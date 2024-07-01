from demo_app.utils import get_random_delay


def test_get_random_delay():
    """
        GIVEN
        WHEN call 1000 time the get_random_delay() function
        THEN every time the result is between 0.1 and 1
    """
    for _ in range(1_000):
        assert 0.1 <= get_random_delay() <= 1
