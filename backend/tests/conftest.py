"""Fixtures compartilhadas: banco SQLite temporário e cliente HTTP da API.

Os testes nunca usam o `moviestars.db` (constituição, seção 6).
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.cache import query_cache
from app.db.base import Base
from app.db.session import enable_sqlite_foreign_keys, get_db
from app.main import app


@pytest.fixture(autouse=True)
def clear_query_cache() -> None:
    """Esvazia o cache antes de cada teste: cada teste usa outro banco temporário (plan 101)."""

    query_cache.clear()


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """Engine assíncrona sobre um arquivo temporário, já com o esquema da aplicação."""

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Sessão para preparar dados e chamar serviços diretamente nos testes."""

    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP da aplicação usando o banco temporário no lugar do `get_db` real."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
