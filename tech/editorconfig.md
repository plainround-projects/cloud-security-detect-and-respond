# EditorConfig

## What it is

EditorConfig is a tiny settings file, `.editorconfig`, that tells code editors how to treat files in a folder: spaces or tabs, how wide an indent, which line endings, whether to end the file with a newline. Most editors read it (some through a plugin). It does not run anything; it only guides the editor you type in.

## Why this repository uses it

A Makefile *requires* tab characters; Terraform and YAML use two-space indents; Python uses four. Without a shared file, each editor guesses and diffs fill up with whitespace noise. The file keeps everyone consistent.

## Where it appears

| Path | What it does |
| --- | --- |
| `.editorconfig` | the rules below |

## How it works underneath

An editor that supports EditorConfig looks for `.editorconfig` in the file's folder and each parent folder. It reads sections in order; a section header like `[*.md]` is a file-name pattern, and later sections override earlier ones for files they match. `root = true` stops the search going further up.

## Walkthrough of this repository's use

From `.editorconfig`:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4
```

- `root = true`: do not look in parent folders.
- `[*]` applies to every file. `charset = utf-8` is the text encoding. `end_of_line = lf` uses the Unix line ending (a single "line feed"), not the Windows pair. `insert_final_newline` ends each file with a newline. `trim_trailing_whitespace` removes spaces at the end of lines. The default indent is four spaces.

From `.editorconfig`:

```ini
[*.{yml,yaml,json,toml,tf,tfvars,hcl,rego}]
indent_size = 2
```

For these file types (a pattern with braces means "any of these endings") the indent is two spaces: the usual style for YAML ([yaml.md](yaml.md)), JSON ([json.md](json.md)), TOML ([toml.md](toml.md)), Terraform ([terraform.md](terraform.md)) and Rego ([opa-rego.md](opa-rego.md)).

From `.editorconfig`:

```ini
[Makefile]
indent_style = tab
```

A Makefile must indent commands with a tab character ([make.md](make.md)).

From `.editorconfig`:

```ini
[*.md]
trim_trailing_whitespace = false
```

In Markdown, two spaces at the end of a line mean "line break", so trimming would change the meaning.

## Try it yourself

```bash
grep -c "" .editorconfig
```

Expect `18`: the file is short.

```bash
grep -n "$(printf '\t')" Makefile | sed -n 1,2p
```

Expect Makefile lines that contain a tab, for example line 19, the `@grep -E` command of the `help` target.

```bash
grep -rn " $" --include='*.tf' infra | sed -n 1,3p
```

Expect no output: no Terraform line ends with a space.

## Mistakes people make

- Assuming EditorConfig is enforced. It only guides editors; the formatters ([ruff.md](ruff.md), `terraform fmt`) do the enforcing.
- Opening a Makefile in an editor without EditorConfig and inserting spaces, which breaks it.

## Check yourself

1. What does `root = true` mean? *Stop searching parent folders for more settings.*
2. Why does `[Makefile]` set tabs? *Make requires tabs before commands.*
3. Why does `[*.md]` keep trailing whitespace? *Two trailing spaces are a line break in Markdown.*
4. Does EditorConfig fail a build? *No; it only configures editors.*
5. What does `end_of_line = lf` do? *Uses Unix line endings.*

## Further reading

- EditorConfig: <https://editorconfig.org/> (specification and the list of supporting editors)
