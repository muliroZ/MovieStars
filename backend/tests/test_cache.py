"""Testes unitários do `QueryCache` (feature 101), com um relógio falso."""

import pytest
from pydantic import ValidationError

from app.core.cache import MISSING, QueryCache
from app.core.config import Settings


class FakeClock:
    """Relógio controlado pelo teste: `now` só avança quando o teste manda."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_cache(clock: FakeClock, **kwargs: float) -> QueryCache:
    return QueryCache(clock=clock, **kwargs)


# --- guardar e ler (CA-1) ---


def test_get_without_value_returns_missing(clock: FakeClock) -> None:
    assert make_cache(clock).get("a") is MISSING


def test_set_and_get(clock: FakeClock) -> None:
    cache = make_cache(clock)
    cache.set("a", {"total": 1}, cache.generation)
    assert cache.get("a") == {"total": 1}
    assert len(cache) == 1


def test_none_is_a_valid_value(clock: FakeClock) -> None:
    cache = make_cache(clock)
    cache.set("a", None, cache.generation)
    assert cache.get("a") is None


# --- expiração (CA-13) ---


def test_entry_expires_after_ttl(clock: FakeClock) -> None:
    cache = make_cache(clock, ttl_seconds=300)
    cache.set("a", 1, cache.generation)

    clock.now += 299.5  # valores exatos em binário: sem erro de arredondamento
    assert cache.get("a") == 1
    clock.now += 0.5  # exatamente 300 s depois
    assert cache.get("a") is MISSING
    assert len(cache) == 0


def test_reading_does_not_extend_ttl(clock: FakeClock) -> None:
    cache = make_cache(clock, ttl_seconds=300)
    cache.set("a", 1, cache.generation)
    clock.now += 200
    assert cache.get("a") == 1
    clock.now += 100
    assert cache.get("a") is MISSING


# --- limite de entradas (CA-14) ---


def test_least_recently_used_is_dropped(clock: FakeClock) -> None:
    cache = make_cache(clock, max_entries=2)
    cache.set("a", 1, cache.generation)
    cache.set("b", 2, cache.generation)
    cache.set("c", 3, cache.generation)

    assert cache.get("a") is MISSING
    assert (cache.get("b"), cache.get("c")) == (2, 3)


def test_get_makes_entry_most_recently_used(clock: FakeClock) -> None:
    cache = make_cache(clock, max_entries=2)
    cache.set("a", 1, cache.generation)
    cache.set("b", 2, cache.generation)
    cache.get("a")
    cache.set("c", 3, cache.generation)

    assert cache.get("b") is MISSING
    assert (cache.get("a"), cache.get("c")) == (1, 3)


def test_setting_same_key_replaces_and_refreshes(clock: FakeClock) -> None:
    cache = make_cache(clock, max_entries=2)
    cache.set("a", 1, cache.generation)
    cache.set("b", 2, cache.generation)
    cache.set("a", 10, cache.generation)
    cache.set("c", 3, cache.generation)

    assert cache.get("b") is MISSING
    assert (cache.get("a"), cache.get("c")) == (10, 3)
    assert len(cache) == 2


# --- limpeza e geração (CA-10, CA-12) ---


def test_clear_empties_and_changes_generation(clock: FakeClock) -> None:
    cache = make_cache(clock)
    cache.set("a", 1, cache.generation)
    before = cache.generation

    cache.clear()

    assert cache.get("a") is MISSING
    assert len(cache) == 0
    assert cache.generation == before + 1


def test_set_with_old_generation_is_ignored(clock: FakeClock) -> None:
    cache = make_cache(clock)
    generation = cache.generation  # a consulta começa
    cache.clear()  # uma escrita termina durante a consulta
    cache.set("a", "resultado velho", generation)

    assert cache.get("a") is MISSING
    assert len(cache) == 0


# --- configuração (CA-16) ---


def test_settings_cache_defaults() -> None:
    settings = Settings(_env_file=None)  # sem o .env do desenvolvedor
    assert (settings.cache_enabled, settings.cache_ttl_seconds, settings.cache_max_entries) == (
        True,
        300,
        256,
    )


@pytest.mark.parametrize("field", ["cache_ttl_seconds", "cache_max_entries"])
def test_settings_reject_non_positive_cache_values(field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        Settings(_env_file=None, **{field: 0})
