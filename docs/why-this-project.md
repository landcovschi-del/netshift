# Why this project, and how it gets you to AI engineering

Read this first in a new session. `docs/roadmap.md` says *what* comes next;
this file says *why*, and what the plan is deliberately not doing.

Written 2026-07-29, two days into the project.

## The starting position

A .NET developer moving into AI engineering with devops skills. That starting
point is not a blank slate, and the plan is built around what it already
covers.

**Already there, do not re-learn:** dependency inversion and layering, typed
interfaces, migrations as a concept, CI, containers as a concept, testing
discipline, reading a stack trace, caring about reproducible builds. Every one
of those transfers. What changes is syntax and tool names.

**Genuinely missing:** Python as a working language, the Linux-shaped half of
the toolchain, and everything model-related.

This split matters because time spent on the first list is close to wasted.
Alembic is EF Core Migrations with different function names; learning it as a
phase would be a week spent translating a concept you already hold.

## Why netshift, and not a chatbot

netshift reads a legacy `.csproj` and reports what blocks migration to modern
.NET. Three reasons that is a better learning vehicle than the usual demo:

1. **The domain is yours.** You can tell a correct verdict from a wrong one
   without looking anything up. That is the prerequisite for the next point.
2. **It admits evals.** Twenty hand-labelled project files with expected
   verdicts give a number. "Did the model improve this?" becomes a measurement
   instead of an impression. With a general chatbot you cannot answer that
   question at all, which is why so many portfolio projects quietly avoid it.
3. **RAG has a real job here.** Microsoft's migration documentation is large,
   changes, and is exactly what a human would go look up. That is retrieval
   solving a real problem, not retrieval demonstrated for its own sake.

## What "AI engineer" actually means

Not model training. In practice the role is: build reliable systems around
models you did not train. That decomposes into

- **Software and ops.** Serving, containers, CI, observability, cost. You are
  strong here already; this is the part most people entering from data science
  are missing, and it is why your direction of travel is an advantage rather
  than a handicap.
- **Model mechanics.** Tokens, context windows, embeddings, chunking, sampling
  parameters. Not "how to call the API" but what happens inside and why the
  answer changed.
- **Measurement.** Evals, regression suites, cost and latency budgets. The
  skill that separates engineering from prompt-tinkering.
- **Retrieval and orchestration.** RAG, tool use, agent loops, and the failure
  modes each brings.
- **Security under untrusted input.** Prompt injection stops being theoretical
  the moment retrieved text reaches the model.

The roadmap phases map onto this: phase 1 bought Python fluency, phase 2 buys
the ops half in Python-flavoured form, phase 3 is where the actual subject
begins.

## Honest assessment of the plan

Recorded so the same mistake is not repeated.

**The pacing was wrong at first.** The original roadmap put four phases in
order and left the LLM until the third. Defensible on paper, but it meant the
first stretch of work sat squarely in the half already covered by .NET
experience. Phase 2 should be compressed to what is genuinely new — Docker and
Postgres reached from Python — and the rest (Alembic, structured logging) done
in passing when a real need appears, not as milestones.

**The plan is still missing things.** As of writing it does not cover:

- Async Python. LLM calls take seconds; without concurrency an application
  stalls. Syntactically close to C# `async/await`, semantically different in
  unpleasant places.
- Model mechanics as a topic in its own right, rather than something absorbed
  while wiring up an API client.
- Running inference locally: quantisation, GPU, memory. Not required for every
  role, but "never ran a model myself" is a visible limit.

**One rule that stays.** Evals before the first model call. The common failure
mode entering this field is starting from the prompt and then improving it by
feeling for six months.

## Caveats

The reasoning above is about typical requirements for AI engineering roles, not
about a specific job market or employer. If the target turns out to be MLOps
or research rather than product-facing AI engineering, the priorities shift and
this file should be rewritten rather than quietly stretched to fit.
