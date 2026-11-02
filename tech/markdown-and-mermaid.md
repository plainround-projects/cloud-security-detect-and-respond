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

### Every file and every diagram line, one by one

Every Markdown file that is part of the repository, outside this `tech/` folder, with the Markdown features it uses. (Markdown is plain text where a few marks decide how the page looks when shown: see the sections above.) Then every Mermaid diagram, line by line.

| File | Lines | Features used (count of lines) |
| --- | --- | --- |
| `ARCHITECTURE.md` | 86 | bold (13), bulleted list (19), code fence (2), heading (7), inline code (31), link (4), numbered list (7), table (21) |
| `CHANGELOG.md` | 16 | bulleted list (7), heading (3), inline code (2), link (1) |
| `README.md` | 158 | bold (11), bulleted list (7), code fence (8), heading (10), inline code (20), link (5), table (30) |
| `docs/DETECTIONS.md` | 26 | bold (5), bulleted list (5), heading (3), inline code (13), link (2), numbered list (3), table (7) |
| `docs/REHEARSAL_REVIEW.md` | 37 | bulleted list (6), heading (5), inline code (1), table (15) |
| `docs/RUNBOOK.md` | 91 | bold (7), bulleted list (5), code fence (6), heading (7), inline code (20), table (21) |
| `docs/adr/0001-detections-are-data-with-one-source-of-truth.md` | 23 | bold (2), bulleted list (5), heading (5), inline code (3) |
| `docs/adr/0002-the-archive-lives-in-another-account-with-object-lock.md` | 24 | bold (3), bulleted list (6), heading (5), inline code (4) |
| `docs/adr/0003-contain-sessions-not-only-the-key.md` | 23 | bold (2), bulleted list (5), heading (5), inline code (2) |

The features, each explained once, with the first place it appears:

- A **heading**: one to six `#` signs, a space, then the title. More signs mean a lower level. First in `ARCHITECTURE.md` line 1.
- A **table**: rows of cells separated by `|`; the second row (`| --- | --- |`) separates the header from the body. First in `ARCHITECTURE.md` line 7.
- A **fenced code block**: three backticks open it and three close it; the word after the opening ones names the language. First in `ARCHITECTURE.md` line 21.
- A **bulleted list**: each item starts with `-` (or `*`) and a space. First in `ARCHITECTURE.md` line 48.
- A **numbered list**: each item starts with a number and a dot. First in `ARCHITECTURE.md` line 38.
- **Inline code**: text between single backticks is shown in a fixed-width font and not interpreted. First in `ARCHITECTURE.md` line 3.
- **Bold**: text between double asterisks. First in `ARCHITECTURE.md` line 3.
- A **link**: the text in square brackets, then the address in round brackets. A relative address points at another file of the repository. First in `ARCHITECTURE.md` line 48.

**Mermaid diagrams.** Mermaid draws a diagram from text that sits in a code block marked `mermaid`. The page viewer (GitHub, for example) turns the text into a picture, so the diagram is plain text in the repository, shows in a diff and cannot go out of date as an image does. This repository has 1 diagram. Every line of each:

The diagram in `ARCHITECTURE.md`:

From `ARCHITECTURE.md` (line 21):

````text
```mermaid
````

The opening fence: three backticks and the word `mermaid`. Everything up to the closing fence is diagram text.

From `ARCHITECTURE.md` (line 22):

```text
flowchart LR
```

Starts a flowchart. `LR` means left to right: the first boxes are at the left and the arrows lead to the right.

From `ARCHITECTURE.md` (line 23):

```text
  drill["drill-user (attacker)"] -- "assume role" --> role["Broad role"]
```

Draws an arrow from `drill` (defined here as a box labelled "drill-user (attacker)") to `role` (defined here as a box labelled "Broad role"), with the label "assume role" written on it.

From `ARCHITECTURE.md` (line 24):

```text
  role -- "make public" --> data["Data bucket"]
```

Draws an arrow from `role` (defined earlier) to `data` (defined here as a box labelled "Data bucket"), with the label "make public" written on it.

From `ARCHITECTURE.md` (line 25):

```text
  role -- "every call" --> trail["Audit trail"]
```

Draws an arrow from `role` (defined earlier) to `trail` (defined here as a box labelled "Audit trail"), with the label "every call" written on it.

From `ARCHITECTURE.md` (line 26):

```text
  trail -- "log files + digests" --> archive["Log archive (security account, Object Lock)"]
```

Draws an arrow from `trail` (defined earlier) to `archive` (defined here as a box labelled "Log archive (security account, Object Lock)"), with the label "log files + digests" written on it.

From `ARCHITECTURE.md` (line 27):

```text
  trail -- "events" --> rules["Detection rules (EventBridge, per Region)"]
```

Draws an arrow from `trail` (defined earlier) to `rules` (defined here as a box labelled "Detection rules (EventBridge, per Region)"), with the label "events" written on it.

From `ARCHITECTURE.md` (line 28):

```text
  rules -- "D1, D2 matched" --> alert["Alert (email)"]
```

Draws an arrow from `rules` (defined earlier) to `alert` (defined here as a box labelled "Alert (email)"), with the label "D1, D2 matched" written on it.

From `ARCHITECTURE.md` (line 29):

```text
  alert -- "page" --> responder["Responder"]
```

Draws an arrow from `alert` (defined earlier) to `responder` (defined here as a box labelled "Responder"), with the label "page" written on it.

From `ARCHITECTURE.md` (line 30):

```text
  responder -- "contain: deny older sessions, deactivate key" --> role
```

Draws an arrow from `responder` (defined earlier) to `role` (defined earlier), with the label "contain: deny older sessions, deactivate key" written on it.

From `ARCHITECTURE.md` (line 31):

```text
  archive -- "synced out" --> tool["detect_respond: scan, timeline, measure, review"]
```

Draws an arrow from `archive` (defined earlier) to `tool` (defined here as a box labelled "detect_respond: scan, timeline, measure, review"), with the label "synced out" written on it.

From `ARCHITECTURE.md` (line 32):

```text
  files["detections/*.json"] -- "pattern, unchanged" --> rules
```

Draws an arrow from `files` (defined here as a box labelled "detections/*.json") to `rules` (defined earlier), with the label "pattern, unchanged" written on it.

From `ARCHITECTURE.md` (line 34):

````text
```
````

The closing fence.

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
