# Third-party software & assets

Every library, copied snippet (>5 lines), dataset, image, font or icon used in this repo (CLAUDE.md §7).

| Name | URL | Licence | Where used |
|---|---|---|---|
| xrpl-py | https://github.com/XRPLF/xrpl-py | ISC | ledger/: XRPL client, tx models, websocket subscribe |
| FastAPI | https://github.com/fastapi/fastapi | MIT | app/: HTTP API |
| Uvicorn | https://github.com/encode/uvicorn | BSD-3-Clause | cli: ASGI server for the API |
| SQLAlchemy | https://github.com/sqlalchemy/sqlalchemy | MIT | store/: ORM / Postgres access |
| psycopg | https://github.com/psycopg/psycopg | LGPL-3.0 | store/: Postgres driver (used as unmodified library) |
| redis-py | https://github.com/redis/redis-py | MIT | store/, flows/: job queue and pub/sub |
| PyJWT | https://github.com/jpadilla/pyjwt | MIT | app/: JWT auth |
| argon2-cffi | https://github.com/hynek/argon2-cffi | MIT | app/: password hashing |
| Ruff | https://github.com/astral-sh/ruff | MIT | dev: lint and format |
| pytest | https://github.com/pytest-dev/pytest | MIT | dev: tests |
| pytest-asyncio | https://github.com/pytest-dev/pytest-asyncio | Apache-2.0 | dev: async tests |
