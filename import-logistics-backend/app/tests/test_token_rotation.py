# app/tests/test_token_rotation.py
import asyncio

from app.core.token_rotation import consume_once


class FakeRedis:
    """Mimics SET NX EX: the check and the write cannot be interleaved (as in real Redis)."""

    def __init__(self):
        self.data = {}
        self.last_ttl = None

    async def set(self, key, value, nx=False, ex=None):
        await asyncio.sleep(0)            # yield, so concurrent callers really interleave
        if nx and key in self.data:
            return None
        self.data[key] = value
        self.last_ttl = ex
        return True


def run(coro):
    return asyncio.run(coro)


def test_exactly_one_of_many_simultaneous_refreshes_wins():
    async def scenario():
        redis = FakeRedis()
        results = await asyncio.gather(*[consume_once(redis, "bl:abc", 600) for _ in range(25)])
        assert results.count(True) == 1
        assert results.count(False) == 24
    run(scenario())


def test_a_token_cannot_be_used_twice_in_sequence():
    async def scenario():
        redis = FakeRedis()
        assert await consume_once(redis, "bl:abc", 600) is True
        assert await consume_once(redis, "bl:abc", 600) is False
    run(scenario())


def test_different_tokens_are_independent():
    async def scenario():
        redis = FakeRedis()
        assert await consume_once(redis, "bl:one", 60) is True
        assert await consume_once(redis, "bl:two", 60) is True
    run(scenario())


def test_ttl_is_at_least_one_second():
    async def scenario():
        redis = FakeRedis()
        await consume_once(redis, "bl:x", 0)
        assert redis.last_ttl == 1
    run(scenario())
