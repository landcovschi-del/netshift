# netshift

Inspects `.csproj` files from legacy .NET Framework projects and reports what
stands in the way of moving to modern .NET: out-of-support frameworks,
Windows-only dependencies, unpinned package versions.

A learning project. The goal is a move from .NET development into AI
engineering with devops skills; the phased plan is in
[docs/roadmap.md](docs/roadmap.md). Instructions for Claude Code are in
[CLAUDE.md](CLAUDE.md).

## Quick start

You need only [uv](https://docs.astral.sh/uv/) and git. No Docker at this
stage, no LLM keys either.

```powershell
.\make.ps1 setup
.\make.ps1 check
.\make.ps1 demo
```

On WSL 2, Linux and macOS the same targets run as `make setup`, `make check`,
`make demo`.

If PowerShell refuses to run the script, allow local scripts for your user --
this is a one-time thing:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Usage

```powershell
uv run netshift doctor                          # environment report
uv run netshift inspect samples/Legacy.csproj   # inspect a project
uv run netshift inspect samples/Legacy.csproj --save
uv run netshift list                            # what has been stored
```

`inspect` exits 1 when blockers are found and 0 when there are none, so the
command can sit in a pipeline and honestly fail it.

## Layout

```
src/netshift/
  domain.py            types and analysis rules. No I/O whatsoever
  ports.py             boundaries with the outside world: Protocol, no impls
  config.py            settings from .env via pydantic-settings
  cli.py               composition root: implementations are chosen here
  adapters/
    csproj_reader.py   reads .csproj from disk (both formats)
    memory_store.py    in-memory store -- the default
    postgres_store.py  Postgres store -- needs Docker
tests/                 pytest: rules, adapter, port contract
samples/               three .csproj files to experiment with
docs/adr/              architecture decisions and the reasoning behind them
```

The architecture is ports and adapters. Dependencies point inward: `adapters`
knows about `domain`, `domain` knows nothing about `adapters`. Why `Protocol`
rather than abstract base classes:
[docs/adr/0001](docs/adr/0001-ports-and-adapters.md).

## Rules

| Code | Severity | Meaning |
|---|---|---|
| NS001 | warning | Old csproj format -- worth moving to SDK-style |
| NS002 | blocker | Target framework could not be determined |
| NS003 | blocker | Framework is out of support (net45 and older) |
| NS004 | blocker | Dependency is tied to Windows and .NET Framework |
| NS005 | warning | NuGet package has no version -- build is not reproducible |

Known simplifications in these rules are listed at the end of
[docs/roadmap.md](docs/roadmap.md). They are there deliberately, not forgotten.

## Postgres (phase 2)

Requires Docker Desktop. Once it is installed:

```powershell
.\make.ps1 up          # starts Postgres and waits until it is healthy
```

Then set `NETSHIFT_STORE=postgres` in `.env` and add the driver:

```powershell
uv sync --extra postgres
```

## Secrets

Keys live in `.env`, which is excluded from git. The template is
`.env.example`. Keys never appear in code: a secret that reaches git is
compromised permanently, because the history stays with everyone who cloned
the repository.

## Targets

`.\make.ps1 help` (or `make help`) lists them all: `setup`, `up`, `down`,
`reset`, `test`, `cov`, `lint`, `fmt`, `typecheck`, `check`, `doctor`, `demo`,
`clean`.
