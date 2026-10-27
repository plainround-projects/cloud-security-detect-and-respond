# Markdown and Mermaid

## What it is

**Markdown** is a way to write formatted text in a plain file: `#` makes a heading, `-` a list item, `|` builds a table, backticks mark code. GitHub shows `.md` files formatted. **Mermaid** is a small language, written inside a Markdown code block marked `mermaid`, that GitHub draws as a diagram.

## Why this repository uses it

Everything a reader needs is documentation: the README, the architecture, the catalog of detections, the runbook, the incident review and the decision records. Markdown is readable in a terminal and on GitHub. The incident review is **blameless** and every claim in it cites an event id, so it is written by the tool from the logs, not typed by hand. The diagram in `ARCHITECTURE.md` is Mermaid, so the picture lives in the same file as the text and changes with it.

## Where it appears

| Path | What it holds |
| --- | --- |
| `README.md`, `ARCHITECTURE.md`, `CHANGELOG.md` | the main documents |
| `ARCHITECTURE.md` | the data-flow diagram, written in Mermaid |
| `docs/DETECTIONS.md` | the catalog of detections |
| `docs/REHEARSAL_REVIEW.md` | the review of the rehearsal drill, **generated** by the tool; do not edit by hand |
| `docs/RUNBOOK.md`, `docs/adr/*.md` | account steps; decision records |
| `src/detect_respond/interfaces/render.py` | the code that writes the review's Markdown |

## How it works underneath

Markdown is just text. A viewer converts it to formatted output when you look at it. A table is lines with `|` between cells and a separator row of `---`. A Mermaid block is not drawn by the file itself: the viewer (GitHub) runs a diagram renderer on the block's text.

## Walkthrough of this repository's use

From `ARCHITECTURE.md`:

````text
```mermaid
flowchart LR
  drill["drill-user (attacker)"] -- "assume role" --> role["Broad role"]
  role -- "make public" --> data["Data bucket"]
````

- The opening fence names the language `mermaid`.
- `flowchart LR` draws boxes and arrows left to right.
- `drill["drill-user (attacker)"]` defines a box with an id (`drill`) and a label.
- `drill -- "assume role" --> role` draws an arrow with a label on it, from the box `drill` to the box `role`. A line that starts with an id already defined (`role -- "make public" --> data`) adds one more arrow from the same box.

**A generated review.** `render.py` builds `docs/REHEARSAL_REVIEW.md` from the tool's results: a title, a timeline table with one row per call, the measured times, what was prevented and only recorded, and the changes that would stop the weakness recurring. `make review` regenerates it and `make validate` compares the committed file with a fresh one (`review --check`), so a stale review fails the build.

From `src/detect_respond/interfaces/render.py`:

```python
def review_markdown(drill: Drill, detections: dict[str, tuple[str, str]]) -> str:
```

The function takes the rebuilt drill and returns one long string of Markdown. Because it is a pure function of its inputs, the same archive always gives the same file.

## Try it yourself

```bash
grep -c '^| [0-9][0-9]:' docs/REHEARSAL_REVIEW.md
```

Expect `8`: one table row for each call in the timeline (rows that start with a clock time).

```bash
.venv/bin/python -m detect_respond review --archive fixtures/drill --alerts fixtures/drill/alerts.json --check docs/REHEARSAL_REVIEW.md
```

Expect `docs/REHEARSAL_REVIEW.md is current`.

```bash
grep -n "mermaid" ARCHITECTURE.md
```

Expect `21:```mermaid`: the opening fence of the diagram.

## Mistakes people make

- Editing a generated file by hand. The next `make review` overwrites it, and `make validate` fails until they match.
- Forgetting the blank line before a table, so it renders as plain text.
- A Mermaid label containing quotes or brackets without quoting the label.
- Writing a review claim without an event id. The review's rule is that every sentence can be checked in the log.

## Check yourself

1. What marks a Mermaid diagram in Markdown? *A code fence whose language is `mermaid`.*
2. Who draws the diagram? *The viewer (such as GitHub), not the file.*
3. Why is `docs/REHEARSAL_REVIEW.md` not edited by hand? *It is generated from the archive, and `make validate` checks it is current.*
4. What does `flowchart LR` mean? *A flowchart drawn from left to right.*
5. What does "blameless" mean in the review? *It states what the role allowed and what the logs show, not who is at fault.*

## Further reading

- CommonMark specification: <https://spec.commonmark.org/>
- GitHub Flavored Markdown (tables): <https://github.github.com/gfm/>
- Mermaid flowcharts: <https://mermaid.js.org/syntax/flowchart.html>
