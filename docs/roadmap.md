# Roadmap

The goal of this project is not netshift itself but the move from .NET
development into AI engineering. The tool was chosen so that every phase
produces a skill rather than a line on a CV.

The order of the phases is deliberate: the LLM shows up only in phase 3, and
that matters. The most common mistake entering AI engineering is starting from
the prompt instead of the data and the measurements. Do that and you get
guesswork rather than engineering.

---

## Phase 1 -- foundation (done)

**Skill:** Python at the level where types and module boundaries are working
tools rather than decoration.

- Ports and adapters, `Protocol` instead of interfaces -- `docs/adr/0001`
- Pure core with no I/O; `.csproj` parsing lives in an adapter
- pytest, a contract test, `mypy --strict`, ruff
- typer CLI: `version`, `doctor`, `inspect`, `list`

**Done when:** `make check` is green and you can explain why `analyse()` is
tested without a single file on disk.

---

## Phase 2 -- infrastructure

**Skill:** the devops half. What separates a script from a system.

- [x] Docker Desktop + WSL 2; `make up` brings Postgres to healthy
- [x] `NETSHIFT_STORE=postgres` works and `netshift list` shows stored reports
- [x] Integration tests for `PostgresReportStore` -- the same contract test
      that already exists, against a real database; marked so they skip when
      Docker is not running
- [x] GitHub Actions green on both Linux and Windows -- broke, fixed, see below
- [ ] Structured logging instead of `print`
- [~] Alembic -- deliberately deferred to phase 3, see below

**How CI broke and what fixed it.** Between `ce74eae` and `5fcdebc` the
workflow was red and the box above was ticked anyway. The workflow installs
with `uv sync --locked`, which does not include the `postgres` extra --
`uv sync --locked --dry-run` reports it would uninstall psycopg.
`tests/test_postgres_store.py` imported psycopg at module level, so collection
died before a single test ran. `pytest.mark.integration` could not save it:
the marker is read when a test runs, the import when the module is collected.
The .NET parallel is `[Fact(Skip=...)]` on a class that never loads because an
assembly is missing.

Fixed with `pytest.importorskip("psycopg")` in place of the import. Verified by
reproducing CI exactly -- `uv sync --locked` then pytest: 16 passed, 1 skipped.

Two heavier options lost. Adding `--extra postgres` to CI without a database
would make the import succeed and the fixture skip -- green that verifies
nothing, the worst kind. Adding a Postgres service container as well would make
the integration test genuinely run; that is what "Done when" below asks for, so
it is still owed, just not bought with a broken build in the meantime.

The general lesson is worth more than the fix: an optional dependency is only
optional if nothing imports it unconditionally, and a test marker is not an
import guard.

### Why Alembic is deferred, and what will un-defer it

Migrations pay off when there is data worth keeping, a schema that changes, and
more than one environment. As of now none of the three holds: one table, the
whole payload in JSONB (so a change to the report format does not touch the
schema at all), and a local database that `make reset` throws away without
regret. `CREATE TABLE IF NOT EXISTS` in the store constructor is honestly
enough for that, and doing Alembic now would be a milestone spent translating
EF Core Migrations into different function names -- exactly the failure mode
`docs/why-this-project.md` warns about.

**The trigger is phase 3 step 4:** the embeddings table and its pgvector index.
That is a second table, a real schema, and the moment the shortcut stops being
one. Do it then, in passing, together with the CI service container.

Decisions already made, so they are not re-derived at that point:

- Migrations get written as raw SQL through `op.execute()`. Alembic with
  SQLAlchemy models and `--autogenerate` was rejected: it would put the schema
  in two places at once and pull an ORM into a project that deliberately has
  none. A hand-rolled runner (a folder of `.sql` files plus a `schema_version`
  table) was rejected too -- it teaches the mechanism but buys a skill nobody
  else uses, while Alembic is the direct counterpart of EF Core Migrations
- The cost is six packages, SQLAlchemy among them as a hard dependency of
  alembic. Open question: whether alembic belongs in the `postgres` extra next
  to psycopg, or in the main dependencies
- `migrations/env.py` must take the DSN from `load_settings()`, not from
  `sqlalchemy.url` in `alembic.ini`. Watch out: SQLAlchemy needs the
  `postgresql+psycopg://` scheme for psycopg 3, and `Settings.postgres_dsn`
  produces a plain `postgresql://` one
- Dropping `_SCHEMA` from the store constructor changes the failure mode: on a
  database that was never migrated the first query starts raising
  `UndefinedTable`. That is the point of the change -- an application has no
  business altering the schema of production at startup, the same argument as
  `Database.Migrate()` on boot versus a separate deployment step in .NET. But
  the message has to be readable, and where to catch it, in the store or in
  `doctor`, is undecided

Lesson from getting the store working, worth keeping: the default host was
`localhost`, which on Windows resolves to `::1` before `127.0.0.1`. The port is
published on IPv4 only, and Docker Desktop swallows the connection attempt
instead of refusing it, so psycopg waited forever. Two changes fixed it -- use
the address instead of the name, and give every network client a timeout. The
second one matters more: without a timeout an outage becomes a hang, and a hang
is far more expensive to debug than an error.

**Done when:** a fresh clone on someone else's machine passes
`make setup && make up && make check` with no manual steps.

---

## Phase 3 -- LLM and RAG

**Skill:** the one this was all for. Also the one where self-deception is
easiest.

**The order inside this phase is not optional:**

1. [ ] **Evals first.** 20-30 hand-labelled `.csproj` files with the expected
       verdict. Metric and baseline defined **before** the first model call.
       Without that, "it got better" is a feeling, not a fact.
2. [ ] An `LlmClient` port in `ports.py` and an Anthropic adapter. Key from
       `.env`. A fake adapter with canned responses so tests never hit the
       network and never cost money
3. [ ] Have the model explain findings in plain language. Run the evals: did
       it beat the baseline?
4. [ ] RAG: index .NET migration documentation into pgvector, search it from
       the findings, answer with links to the source
5. [ ] Measure RAG against plain LLM on the same evals. If there is no
       difference, record that honestly in an ADR

**On security.** From step 4 onward, text downloaded from the internet goes
into the model. Prompt injection stops being theoretical: a page can contain
instructions addressed to the model. The rule is simple and not up for
negotiation -- **data from a source is never a command**. Conclusions the model
draws from retrieved text must not trigger actions without your confirmation.

The second risk is `defusedxml` instead of `xml.etree` in `csproj_reader` once
the input is other people's files. That is flagged in a comment in the code
today.

**Done when:** you can quote the number by which RAG improved the metric, and
show what you measured it with.

---

## Phase 4 -- operations

**Skill:** getting it to the state people pay for.

- [ ] Token and cost accounting per request
- [ ] Caching model responses -- identical input must not be billed twice
- [ ] Tracing: it is visible what context went to the model and what came back
- [ ] Graceful degradation: the LLM is down, netshift still runs on rules
- [ ] Eval regression run in CI on every PR

---

## Known simplifications

Recorded honestly rather than passed off as features:

- Rule NS004 matches by name prefix. `System.Drawing.Common` -- a modern NuGet
  package -- is flagged as a blocker incorrectly. Fix it once evals exist and
  the cost of the error is visible
- The lists of dead frameworks and Windows-only dependencies are hardcoded in
  `domain.py`. They belong in configuration or in the database
- `PostgresReportStore` creates its schema on connect. Acceptable before
  Alembic, not after
- `netshift inspect` handles one file. `.sln` solutions are not supported
