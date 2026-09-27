"""Cache em memória das consultas do catálogo e dos gêneros (feature 101).

Guarda resultados por um tempo (TTL) e até um limite de entradas, descartando a
menos usada recentemente (LRU). Toda escrita da aplicação chama `clear()`.
"""

import time
from collections import OrderedDict
from collections.abc import Callable

from app.core.config import get_settings

# Sentinela para "não há valor guardado": None pode ser um valor legítimo.
MISSING = object()


class QueryCache:
    """Cache com TTL, limite de entradas (LRU) e contador de geração (plan 101, DEC-1, DEC-4).

    Os atributos são públicos para que os testes os troquem com `monkeypatch`.
    Nenhum método tem `await`: num único laço de eventos, nenhum é interrompido
    no meio, então não é preciso trava.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        ttl_seconds: float = 300,
        max_entries: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        # chave → (momento em que foi guardado, valor); a ordem é a de uso.
        self._entries: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._generation = 0

    @property
    def generation(self) -> int:
        """Muda a cada `clear()`; usada para não guardar resultados velhos (DEC-4)."""
        return self._generation

    def get(self, key: str) -> object:
        """Valor guardado, ou `MISSING` se não existe ou expirou."""

        entry = self._entries.get(key)
        if entry is None:
            return MISSING
        stored_at, value = entry
        if self.clock() >= stored_at + self.ttl_seconds:
            del self._entries[key]
            return MISSING
        self._entries.move_to_end(key)  # passa a ser a mais usada
        return value

    def set(self, key: str, value: object, generation: int) -> None:
        """Guarda o valor, a não ser que o cache tenha sido limpo depois de `generation`."""

        if generation != self._generation:
            # Uma escrita aconteceu durante a consulta: o resultado pode estar velho.
            return
        self._entries[key] = (self.clock(), value)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)  # a menos usada recentemente

    def clear(self) -> None:
        """Esvazia o cache e muda a geração."""

        self._entries.clear()
        self._generation += 1

    def __len__(self) -> int:
        return len(self._entries)


_settings = get_settings()
# Instância única da aplicação: o router lê e o serviço limpa (plan 101, DEC-10).
query_cache = QueryCache(
    enabled=_settings.cache_enabled,
    ttl_seconds=_settings.cache_ttl_seconds,
    max_entries=_settings.cache_max_entries,
)
