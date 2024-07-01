import random


def get_random_delay() -> float:
    # Each endpoint should have a random short delay between 0.1 and 1 second.
    return random.randint(100, 1_000) / 1_000
