# v0.23.0 decisions

## D1 — Scope (set by the owner; no Jev call)

The owner said the Jev judge must decide from the project's context and needs a specification document for that. The question "should it" was settled by that instruction, so no Jev call was made for the scope. What the judge sees, and the limits that shape the command, are in [v0.22.0 decisions](../v0.22.0/decisions.md) D4, verified against the judge's source and with the free `consensus_plan`.

## D2 — Design choices and why

- Verbatim chunks, not a model-written summary. A summary by the coordinator would put the same unchecked paraphrase back between the document and the judge. The only edit is whitespace collapsing, so that the text can be compared with the document.
- A command that prints the spec, not one that calls Jev. The docs record that the CLI has no portable Jev transport; the coordinator already passes the object to the MCP tools. The output is compact so that it can be passed as is.
- At least one document is required. The rule "no Jev call without a document" is then a failing exit code instead of a habit.
- Provenance is a fact. The path and a 16-digit digest of each document are part of `facts`, so they are covered by the receipt's spec hash and the decision record can name the exact document.
- No truncation, ever. Over the fact limit the command fails and says so, because a silently shortened document would give the judge a false picture of the context.
- Reuse the existing validator. The limits and the sensitive-content scan stay in one place, `_validate_spec`.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
