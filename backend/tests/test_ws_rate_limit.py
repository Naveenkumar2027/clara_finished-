import unittest

from backend.security.rate_limit import BoundedKeyedRateLimiter, TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTokenBucket(unittest.TestCase):
    def test_normal_traffic_and_threshold(self) -> None:
        clock = FakeClock()
        bucket = TokenBucket(3, 1, clock)
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())
        clock.advance(1)
        self.assertTrue(bucket.allow())

    def test_keys_are_isolated(self) -> None:
        clock = FakeClock()
        limiter = BoundedKeyedRateLimiter(1, 1, clock=clock)
        self.assertTrue(limiter.allow("connection-a"))
        self.assertFalse(limiter.allow("connection-a"))
        self.assertTrue(limiter.allow("connection-b"))

    def test_stale_buckets_expire_without_sleep(self) -> None:
        clock = FakeClock()
        limiter = BoundedKeyedRateLimiter(1, 1, stale_after_seconds=10, clock=clock)
        limiter.allow("old-ip")
        clock.advance(10)
        self.assertEqual(limiter.entry_count(), 0)

    def test_map_is_bounded(self) -> None:
        clock = FakeClock()
        limiter = BoundedKeyedRateLimiter(1, 1, max_entries=2, clock=clock)
        limiter.allow("a")
        clock.advance(1)
        limiter.allow("b")
        clock.advance(1)
        limiter.allow("c")
        self.assertEqual(limiter.entry_count(), 2)

    def test_new_connection_has_fresh_connection_budget(self) -> None:
        clock = FakeClock()
        first = TokenBucket(1, 1, clock)
        self.assertTrue(first.allow())
        self.assertFalse(first.allow())
        reconnected = TokenBucket(1, 1, clock)
        self.assertTrue(reconnected.allow())

    def test_ip_budget_survives_reconnect(self) -> None:
        clock = FakeClock()
        limiter = BoundedKeyedRateLimiter(1, 1, clock=clock)
        self.assertTrue(limiter.allow("203.0.113.8"))
        self.assertFalse(limiter.allow("203.0.113.8"))


if __name__ == "__main__":
    unittest.main()
