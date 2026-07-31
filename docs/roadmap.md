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
- [ ] Alembic: the schema stops being created on the fly. The .NET equivalent
      is EF Core Migrations
- [ ] GitHub Actions green on both Linux and Windows -- was true, is not any
      more. See "CI is red" below
- [ ] Structured logging instead of `print`

**CI is red since `ce74eae`, and the box above was unticked because of it.**
The workflow installs with `uv sync --locked`, which does not include the
`postgres` extra -- `uv sync --locked --dry-run` reports it would uninstall
psycopg. `tests/test_postgres_store.py` imports psycopg at module level, so
collection fails before any test runs. `pytest.mark.integration` does not help:
the marker is evaluated when a test runs, the import when the module is
collected. The .NET parallel is `[Fact(Skip=...)]` on a class that cannot be
loaded because an assembly is missing.

Three ways out, none picked yet:

- `pytest.importorskip("psycopg")` in the test module -- one line, CI green
  everywhere, workflow untouched
- `--extra postgres` in CI without a database -- the import succeeds and the
  fixture skips, so the test still never executes. Green that verifies
  nothing; the worst kind
- `--extra postgres` plus a Postgres service container -- the integration test
  actually runs. This is what the "Done when" below asks for, and it is the
  natural moment to add `alembic upgrade head` to CI as well

Current thinking: the one-line fix now as its own commit, the service container
together with the Alembic work.

### Next session: Alembic

Decided before starting, so the reasoning is not re-derived:

- Migrations are written as raw SQL through `op.execute()`. Alembic with
  SQLAlchemy models and `--autogenerate` was rejected: it would put the schema
  in two places at once and pull an ORM into a project that deliberately has
  none. A hand-rolled runner (a folder of `.sql` files plus a `schema_version`
  table) was also rejected -- it teaches the mechanism but buys a skill nobody
  else uses, while Alembic is the direct counterpart of EF Core Migrations
- The cost is six packages, SQLAlchemy among them as a hard dependency of
  alembic. Open question: whether alembic belongs in the `postgres` extra next
  to psycopg, or in the main dependencies
- `migrations/env.py` must take the DSN from `load_settings()`, not from
  `sqlalchemy.url` in `alembic.ini`. Watch out: SQLAlchemy needs the
  `postgresql+psycopg://` scheme for psycopg 3, and `Settings.postgres_dsn`
  produces a plain `postgresql://` one
- Dropping `_SCHEMA` from the store constructor changes the failure mode: on a
  database that was never migrated the first query now raises `UndefinedTable`.
  That is the point of the change, but the message has to be a readable one --
  where to catch it, in the store or in `doctor`, is undecided

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
