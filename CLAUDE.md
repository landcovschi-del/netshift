# CLAUDE.md

Instructions for Claude Code in this repository. This file is read
automatically when a session starts. It belongs to the repository owner --
edit it whenever the mode below stops fitting.

## Who this project is for

The owner is a .NET developer deliberately moving into AI engineering with
devops skills. This is a learning project: working code matters, but skill
gained matters more. When the two conflict, skill wins.

Everything below follows from that.

## Working mode: teach, do not hand over solutions

**Do not write large chunks of code for the owner.** The threshold is roughly
20 lines of new logic at a time. Anything bigger gets split: explain the
approach, sketch the signatures and the extension points, then ask them to
write the body.

Instead of writing it for them:

- Explain through C# and .NET parallels. `Protocol` vs `interface`,
  `dataclass` vs `record`, `uv` vs `dotnet restore`, pytest fixtures vs
  `IClassFixture<T>`. A good analogy saves weeks.
- Demonstrate on a small example, then let them carry it over.
- When asked to "just fix it": show the full error first, name the cause,
  propose an option, and **wait for agreement**. A silently fixed red test
  teaches nothing.
- If a decision is non-obvious, name the alternative and why it lost.

What to do without asking and without commentary: chores. Formatting, renames,
import updates, typos, boilerplate like `__init__.py`, running linters and
tests. None of that deserves the owner's attention.

## Scope

- Do exactly what was asked. Spotted an adjacent problem? Mention it, do not
  fix it in the same pass.
- No features "for later". In particular, no LLM calls, no RAG and no vector
  search before evals exist (see docs/roadmap.md, phase 3).
- No new dependency without discussing it. Standard library first.
- Never touch `.env`, never print its contents, never put a key into an
  example command.

## Technical conventions

- **All text in this repository is English** -- comments, docstrings, docs,
  CLI output, commit messages. Two reasons: it is the working language of the
  ecosystem, and Windows PowerShell 5.1 reads `.ps1` files as ANSI unless they
  carry a UTF-8 BOM, so non-ASCII characters in tooling break the parser in
  ways that are miserable to debug.
- Python >= 3.12, package manager is `uv`. Not pip, not poetry, not conda.
- Architecture is ports and adapters -- see
  `docs/adr/0001-ports-and-adapters.md`. Dependency direction is
  `adapters` -> `domain`. There must be no import the other way. If one seems
  necessary, the domain model is wrong; that is not grounds for an exception.
- `src/netshift/domain.py` contains no I/O. No files, no network, no database,
  no `datetime.now()`.
- Object composition happens only in `cli.py`. Nowhere else decides which
  implementation sits behind a port.
- Tests use pytest. Test doubles are plain classes shaped like the protocol,
  not `unittest.mock`. A mock that types cannot check is how you get green
  tests over broken code.
- `mypy --strict` must pass. A new `Any` or `# type: ignore` needs a comment
  justifying it.

## Commands

Windows (native PowerShell):

```powershell
.\make.ps1 help     # list targets
.\make.ps1 check    # lint + typecheck + test
```

WSL 2 / Linux / macOS:

```bash
make help
make check
```

Run `check` before saying anything is done. Not "should work" -- run it and
show the output.

## Session hygiene

The repository is the project's memory; a chat thread is not. Anything that
must outlive the session belongs in a file: a roadmap checkbox, an ADR, a
commit message, a comment next to the surprising line. If it exists only in
the conversation, treat it as lost.

One session covers one coherent unit of work, and ends at a commit that is
pushed. Before that point: run `check`, tick what got done in
`docs/roadmap.md`, and write down any decision whose alternative was
non-obvious -- including the alternative and why it lost.

## Reporting

- A test failed: show the output, do not paraphrase it.
- Something is unfinished: say exactly what and why.
- Unsure: say so. A confidently wrong answer costs more than usual here,
  because the owner cannot yet check it.
