import pytest

from app.settings import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgres://user:pass@db:5432/launchscope", "postgresql+psycopg://user:pass@db:5432/launchscope"),
        ("postgresql://user:pass@db:5432/launchscope", "postgresql+psycopg://user:pass@db:5432/launchscope"),
        ("postgresql+psycopg://user:pass@db:5432/launchscope", "postgresql+psycopg://user:pass@db:5432/launchscope"),
    ],
)
def test_database_url_uses_psycopg_driver(database_url: str, expected: str) -> None:
    assert Settings(database_url=database_url).database_url == expected