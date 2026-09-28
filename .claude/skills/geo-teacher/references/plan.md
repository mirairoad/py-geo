# Python Geo Analytics API: Learning Plan

27 Sept 2026 · Leo

## Goal

In 7 working days, build a geo analytics API: sites (polygons), assets (points) and events (timestamped points with a value) in PostGIS, a Web Mercator pixel and tile system for maps, and an analytics overview, with JWT auth, four migrations and a test suite.

Pixel system: Web Mercator (EPSG:3857) world pixels and z/x/y tiles.

## Stack

| Concern | Pick | Why |
|---|---|---|
| Python | 3.14 | Leo's choice (plan said 3.13); uv pins it via .python-version |
| Package manager | uv | venv, lockfile and Python version in one tool |
| Task runner | make (Leo's choice over just) | uv has no npm-scripts equivalent |
| Server | FastAPI + uvicorn[standard] | Async, Pydantic validation, DI via Depends |
| Database | Postgres 17 + PostGIS 3.5 (postgis/postgis image) | Spatial types, GiST, MVT in SQL |
| Driver | psycopg v3 | One driver for async app and sync Alembic |
| ORM | SQLAlchemy 2.0 async | Typed `Mapped[]` models |
| Geo column types | geoalchemy2 | Geometry columns, Alembic helpers |
| Geometry in Python | shapely | WKB to/from GeoJSON |
| Analytics queries | SQLAlchemy Core + CTEs | Reports are SQL-shaped, not CRUD |
| Migrations | Alembic | |
| Validation | Pydantic v2 | Python's Zod |
| Config | pydantic-settings | Typed .env loading |
| Auth | PyJWT + pwdlib[argon2] | passlib is unmaintained |
| Lint/format | ruff | |
| Types | pyright strict | |
| Tests | pytest, pytest-asyncio, pytest-cov, httpx | Async tests against the real ASGI app |

Async trade-off: lazy-loading a relationship on an async session raises MissingGreenlet. Fix: explicit `selectinload()`.

## Project structure (Leo's layout, overrides the original plan)

Leo chose a single-project repo with a flat `src/` holding several top-level packages,
instead of the planned `api/src/api/` monorepo package. Respect it; review within it.

```
py-geo/
├── pyproject.toml, uv.lock, .python-version (3.14)
├── src/
│   ├── db/                # base.py, session.py, registry.py
│   ├── server/
│   │   ├── main.py        # run(): uvicorn.run("server.app:create_app", factory=True)
│   │   ├── app/           # __init__.py holds create_app()
│   │   ├── apis/public/<feature>/ , apis/private/<feature>/   # APIRouters
│   │   ├── services/<feature>/   # model, schema, service
│   │   ├── internals/
│   │   └── middlewares/
│   └── tests/             # testpaths = src/tests, --import-mode=importlib
```

Imports are `from db.session import ...`, `from server.services.users.service import ...` (no `api.` prefix).
Leo comes from a TS codebase using `name.api.ts` style files: watch for dotted module names like `health.api.py` (not importable).
Build: hatchling with `[tool.hatch.build.targets.wheel] packages = [...]`.

Known cost of this layout (mention when relevant, don't nag): each new top-level package
must be added by hand to hatch `packages` and pytest `--cov`; generic names like `db` / `server`
can clash with third-party modules.

Routing convention (Leo's choice): every package `__init__.py` under `apis/` aggregates its children into one `router`
(app → public/private → feature → endpoint files). Prefix `/api` set once in `create_app()`. Leo chose folder-mirrored URLs: `/api/public/...` and `/api/private/...`
(accepted trade-off: one resource has public read + private write URLs). Don't re-argue it.
Imports: absolute from `src/` across packages; `from . import x` allowed only for siblings (ruff TID252, ban-relative-imports = "parents").

PEP 8: snake_case modules/functions, PascalCase classes, UPPER_CASE constants. No dots in module names.

## Nine key patterns

1. **BaseService[M]** with create, get, find, find_one, update, remove. Session injected per request via Depends. Services only `flush()`; `get_session()` commits on success, rolls back on exception: one transaction per request.
2. **PATCH semantics**: update schemas all-optional, handler uses `model_dump(exclude_unset=True)`.
3. **Model registry**: `db/registry.py` imports every model; `migrations/env.py` imports it before reading `Base.metadata`.
4. **Cross-feature relationships**: model imports under `TYPE_CHECKING`, string annotations `Mapped["Site"]`.
5. **Feature dependency rule**: features talk through services only. auth calls UserService, never the User model. (import-linter optional.)
6. **HTTP at the edge**: services raise domain exceptions (NotFound, Forbidden); `internals/errors.py` maps them. Services never raise HTTPException. Auth is a router dependency, not middleware. Handlers stay thin.
7. **SRID discipline**: store SRID 4326. Transform to 3857 only in SQL (`ST_Transform`) for tiles/pixels. Metres: cast to geography. GiST on every geom. Bbox via `&&` + `ST_MakeEnvelope`. Mercator math in pure Python, cross-checked against PostGIS in a test.
8. **Analytics is SQL**: AnalyticsService does not extend BaseService. Core `select()` / `text()`, CTEs, window functions, returns Pydantic schemas never ORM objects. Heavy aggregates from a materialized view.
9. **Alembic + PostGIS**: first migration `CREATE EXTENSION IF NOT EXISTS postgis`; `include_object` filter to skip spatial_ref_sys/tiger; `geoalchemy2.alembic_helpers`; materialized views hand-written with `op.execute` incl. downgrade.

## Tooling and gate

Nothing gets ticked until `make check` passes: lint, format check, strict types, tests.

```toml
[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "ASYNC", "RUF"]

[tool.pyright]
typeCheckingMode = "strict"

[tool.pytest.ini_options]
testpaths = ["src/tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
addopts = "--import-mode=importlib --cov=server --cov=db --cov-report=term-missing"  # one --cov per top-level package
```

Makefile recipes: `dev`, `check` (ruff check, ruff format --check, pyright, pytest), `test`, `migrate`, `seed`, `refresh`.

Untyped geoalchemy2/shapely under strict pyright: silence at call site or `reportMissingTypeStubs = false`. Never drop strict globally.

## Test strategy

- Unit: no DB. Mercator known values (lng 0, lat 0, z 0 → (128, 128)), security helpers, schemas.
- Integration: real PostGIS `geo_test`, migrations once per session, per-test rollback (`join_transaction_mode="create_savepoint"`).
- Analytics: small fixture dataset with hand-computed answers, never the 200k seed.
- API: `httpx.AsyncClient(transport=ASGITransport(app=app))` + `dependency_overrides[get_session]`.

## Day-by-day checklist

**Day 0 Prep**: Docker allowed at EY, postgis image pullable, proxy/pip mirror, install uv, skim PEP 8.

**Day 1 Skeleton**: project init on Python 3.14; add deps + dev deps; tool config + Makefile; `create_app()` + `/health`; test /health; gate. (DONE. docker-compose, config.py + .env.example, and /ready running `SELECT postgis_version()` moved to Day 2 by Leo.)

**Day 2 Models + migrations**: FIRST the moved Day 1 items: docker-compose (geo + geo_test), `internals/config.py` + `.env.example`, `/ready` with `SELECT postgis_version()` + test. Then: Base with naming convention; users, sites (Polygon 4326), assets (Point 4326), events (Point, value numeric, occurred_at timestamptz); GiST on every geom, btree on occurred_at; TYPE_CHECKING relationships + registry; async session with `expire_on_commit=False`, commit/rollback `get_session()`; alembic env.py with registry, include_object, alembic_helpers; migration 1 with postgis extension; downgrade/upgrade round-trip, `alembic check` clean; SQL seed (~20 sites, ~500 assets via ST_GeneratePoints, ~200k events via generate_series); conftest migrate once + rollback; gate.

**Day 3 BaseService, CRUD, GeoJSON**: BaseService six methods, flush only; geojson.py Pydantic Point/Polygon via to_shape/from_shape + mapping/shape; sites + assets schemas/services, PATCH exclude_unset; deps.py factories; GET /sites, /sites/{id}, /assets?bbox=; tests: GeoJSON round-trip, invalid polygon rejected, every BaseService method, bbox, 404, bad bbox 422; gate.

**Day 4 Auth**: security.py hash/verify/create/decode (exp + sub); users + auth schema/service; POST /auth/register, /auth/login; current_user with OAuth2PasswordBearer; private POST/PATCH/DELETE sites + assets, POST /events batch, GET /me; ownership 403; asset point inside site (ST_Contains) else 422; errors.py handlers; tests: hash round-trip, expired/tampered token, 401/403/201/422; gate.

**Day 5 Spatial + pixels**: mercator.py test-first (lnglat_to_world_px, world_px_to_tile, tile_to_lnglat_bounds); KNN nearest with geography metres; events outside every site (LEFT JOIN ... IS NULL); MVT tiles (ST_TileEnvelope, ST_AsMVTGeom, ST_AsMVT, correct content type, Cache-Control); pixel heatmap 8x8 cells via ST_SnapToGrid in 3857; tests: mercator known values, Python vs PostGIS for 5 points, KNN order, stray event, MVT non-empty / 204 empty; gate.

**Day 6 Analytics**: Overview, TimeseriesPoint, SiteReport schemas; overview (totals, 7d vs prior 7d with FILTER, active assets, top 5 sites, p50/p95 percentile_cont); timeseries with generate_series LEFT JOIN zero-fill; site report (rank() OVER, 7-day rolling AVG, density per km² via geography area); migration 2 materialized view mv_site_daily + unique index; refresh script CONCURRENTLY; overview reads MV for full days + live for today; fixture-based tests; from>to 422, unknown site 404; gate.

**Day 7 Hardening**: request ID + timing middleware; EXPLAIN ANALYZE bbox/KNN/heatmap/overview on 200k seed; migration 3 composite (asset_id, occurred_at) if needed; migration 4 severity enum (nullable, backfill, NOT NULL); statement_timeout on analytics sessions; coverage ≥80% on services/ and internals/; gate.

**Stretch**: import-linter, pre-commit, GitHub Actions with PostGIS service, testcontainers, MapLibre client.
