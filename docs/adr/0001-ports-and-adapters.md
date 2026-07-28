# ADR 0001. Ports and adapters, built on Protocol

- **Status:** accepted
- **Date:** 2026-07-28

## Context

netshift reads `.csproj` files from disk, and will later read them from git
repositories and archives, store reports in Postgres, and call an LLM. Every
one of those is the outside world: slow, unreliable, and needing infrastructure
to be up.

If the analysis rules depend on how a file is read, you cannot check a rule
without a file, and you cannot check it against Postgres without Docker. The
author comes from .NET, where Clean Architecture and Dependency Inversion solve
the same problem, and those instincts are worth carrying over rather than
discarding.

## Decision

Split the code into three layers:

```
domain.py     the core: types and rules. Knows nothing external.
ports.py      what the core needs from outside. Protocol, no implementations.
adapters/     implementations of the ports: files, database, network.
cli.py        composition root: the one place that picks an implementation.
```

Ports are declared with `typing.Protocol`, not `abc.ABC`.

## Why Protocol and not ABC

`ABC` gives nominal typing: a class is compatible if it **declares** the
inheritance. That is exactly `interface` semantics in C#.

`Protocol` gives structural typing: a class is compatible if it **has** the
right methods. Nothing to declare, nothing to inherit.

What that changes in practice:

1. **A test double is an ordinary class.** `FakeStore` in
   `tests/test_ports.py` imports no adapter and inherits no protocol. Ten lines
   instead of a mocking library.

2. **A third-party class fits with no wrapper.** If some library object already
   has a method of the right shape, it *is* an adapter. With `ABC` you would
   write a shim.

3. **The core does not know adapters exist.** `adapters/` imports `domain` and
   there is no import back. With `ABC` the adapter must at least import the
   base class -- a weaker coupling, but a real one. With `Protocol` the edge is
   physically absent.

The price: only the static analyser verifies protocol conformance. Forget a
method and mypy tells you, not the interpreter at import time. That is why
`mypy --strict` is part of the contract in this project rather than a nicety.
The protocols are additionally marked `@runtime_checkable`, which enables
`isinstance()` -- but that only checks that methods exist, not their
signatures, and is no substitute for type checking.

## When ABC is the right call

When subclasses need shared behaviour: a template method, a common `__init__`,
validation in the constructor. `Protocol` cannot express any of that. There is
no shared behaviour between these adapters, so the question does not arise.

## Consequences

- Core tests run with no Docker, no network and no temp files: `analyse()` is a
  pure function over data.
- Changing the store is one branch in `build_store()` in `cli.py`.
- The contract test (`test_store_contract_holds_for_both_implementations`)
  applies one set of expectations to every implementation of a port. A new
  adapter is added to the list and is covered immediately.
- It imposes discipline: every new external source needs a port first, then an
  adapter. That is slower than calling `psycopg.connect()` from business logic,
  and that is the entire point.
