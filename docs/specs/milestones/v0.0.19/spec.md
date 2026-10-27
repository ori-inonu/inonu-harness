# v0.0.19 — Credential-pattern guard for decision packets

The gap matrix in [the v0.0.10 research](../v0.0.10/research.md) lists "redaction of secrets in packets" as the caller's job. `decisions context` and `decisions packet` print free text (questions, constraints, evidence, a task prompt) that the owner then hands to an agent, so a pasted credential would travel with it. This milestone adds an opt-in guard that refuses to print a packet containing credential-like text. It changes no default behavior and no database. The scope was decided by Jev without consensus ([decisions.md](decisions.md)).

## Requirements

- R1 A new module `inonu_harness/secret_scan.py` exposes `scan(value) -> list[dict]`. It walks a JSON-like value (dicts, lists, strings; other types are ignored) and returns findings `{"rule": str, "path": str}` sorted by path then rule, with no duplicates. Both dict keys and string values are scanned.
- R2 Rules, with these exact names and deliberately narrow patterns (a pattern list is an aid, not proof that text is free of secrets):
  - `private_key_block`: a PEM header `-----BEGIN` followed by an optional algorithm word and `PRIVATE KEY-----`.
  - `aws_access_key_id`: `AKIA` or `ASIA` followed by 16 upper-case letters or digits, on word boundaries.
  - `github_token`: `ghp_`, `gho_`, `ghu_`, `ghs_` or `ghr_` followed by 36 or more letters or digits; `github_pat_` followed by 22 or more letters, digits or underscores.
  - `slack_token`: `xoxb-`, `xoxa-`, `xoxp-`, `xoxr-` or `xoxs-` followed by 10 or more letters, digits or hyphens.
  - `google_api_key`: `AIza` followed by 35 letters, digits, `_` or `-`.
  - `stripe_live_key`: `sk_live_` or `rk_live_` followed by 16 or more letters or digits.
  - `anthropic_key`: `sk-ant-` followed by 20 or more letters, digits, `_` or `-`.
  - `openai_style_key`: `sk-` followed by 32 or more letters or digits (an optional `proj-` segment may follow `sk-`).
  - `jwt`: three base64url segments of 10 or more characters separated by dots, the first starting `eyJ`.
  - `bearer_token`: the word `Bearer`, one space, and 20 or more token characters.
  - `credential_assignment`: a name containing `api_key`, `apikey`, `secret`, `token`, `password`, `passwd` or `private_key` (case-insensitive, separators `_` or `-` allowed), then `:` or `=` with optional spaces and optional quotes, then 16 or more characters of letters, digits and `_-/+=.`.
  Every pattern is anchored by a literal prefix or keyword and matches in a single pass with open-ended minimum counts, so scanning is expected to be linear on realistic input; a one-megabyte near-miss string finishes within two seconds in the tests. A string under a dict key is also checked as `key: value` against the `credential_assignment` rule.
- R3 Paths contain only list indices and dict keys that are plain lowercase identifiers up to 40 characters (`[a-z_][a-z0-9_]*`); any other key is shown as `*`, and so is a key that shares eight or more consecutive characters with the matched text. A matched value, any part of it and any odd key text never appear in a finding.
- R4 `decisions context` and `decisions packet` accept `--refuse-secret-patterns`. With it, the command scans exactly the object it would print (including a packet's task prompt). On a finding it prints nothing to stdout, writes one line to stderr naming only the rule names and paths (sorted, no values), and exits 2. The requested `--ids` are scanned first, so an unknown token-shaped id is refused instead of echoed by the lookup error. With no finding the output is byte-identical to the output without the flag. Without the flag, behavior and output are unchanged even when text matches a rule.
- R5 Tests build every synthetic credential at run time from fragments, so no credential-looking string is committed to the public repository. They cover:
  - each rule matches its synthetic value;
  - near-misses do not match (a token one character short, a `sk-` prefix that is too short, a keyword with a short value, the word "password" in prose, a base64 blob without the `eyJ` start);
  - paths for nested findings, list indices and odd keys;
  - key scanning;
  - no matched value or substring of at least 8 characters in stdout, stderr or the error message;
  - the linear-time bound;
  - the flag on `context` and `packet`: refusal exit 2 with empty stdout; clean data byte-identical with and without the flag; secret-bearing data unchanged without the flag;
  - a secret in the packet task prompt and in a decision field;
  - determinism.
- R6 Docs: CHANGELOG 0.0.19, README, a short Portuguese paragraph in `docs/sdd-workflow.md`, and a skill bullet. They say the guard is opt-in, that callers who attach the output to an agent should pass it, that it catches only the listed formats (it does not catch passwords in prose, custom tokens or most credential formats) and can raise false positives, and that matched values are never printed. Version 0.0.19 in `__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the tests.

## Out of scope

Redaction, refusing by default, scanning the decision database or arbitrary files, entropy-based detection, and any network lookup of a suspected credential.
