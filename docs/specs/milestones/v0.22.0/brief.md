# v0.22.0 decision brief

Context for the scope decision, written before the spec so that it does not state the answer. The Jev judge sees only the decision object, so this brief is sent as its `facts` ([decisions.md](decisions.md)).

## Problem

- Research gap G2: `bundle status` cannot tell a host item the bundle wrote and left unchanged from one the user edited or one that was never ours.
- Evidence: ECC (install-state) and spec-kit (hash gate) compare what is installed with what they recorded before they touch a host file.

## What the code does today

- `bundle apply` records one sha256 per installed item in the ownership ledger, `~/.inonu-harness/bundle-ledger.json` (schema_version 1), under the key `<kind>:<host>:<id>`.
- The digest is of what apply wrote: the skill file, the worker agent file, the canonical JSON of a Claude MCP entry, the marked TOML block of a Codex MCP entry, the canonical JSON of the Stop hook group.
- The ledger also lists `created` markers for the files, directories and keys the bundle created, so that `remove` can take them back.
- `bundle remove` deletes an item only when what is installed still has the recorded digest. Otherwise it reports a conflict and leaves the item.
- `bundle status` is read-only and reports one `state` per item from what is on disk alone: skill current, outdated, conflict or absent; worker agent current, different or absent; MCP server configured, absent or unknown (by server id only); Stop hook present, absent or unknown.
- `bundle status` never reads the ledger, so an MCP entry the user edited and an unchanged one both show as `configured`.
- Existing tests assert the current `state` values and the `summary` keys.

## Constraints

- The owner authorized `bundle apply`, `remove` and `status` to write the Claude and Codex configuration with preview, ownership hashes and reversal. Nothing else.
- Fenced until the owner authorizes the specific action: data or schema migrations, credentials, and changing what the owner's installed agent may do.
- Rewriting the existing ledger under a new schema version would be a migration of a file in the owner's home.
- Adding a `tools` allowlist to the worker agent changes the agent file that the next `bundle apply` writes into the owner's configuration.
- Replacing the existing `state` values would change what current output means.
