# Security policy

## Scope

This repository ships a Claude Code plugin: Markdown instructions plus a small
set of standalone Python scripts and one POSIX shell script. The scripts are
stdlib-only, have no third-party dependencies, and make no network calls. They
do read and write files on the machine that runs them — the ledger, critic
reports, and a copy of the project under review in a scratchpad directory — so
path handling and the disclosure filters in `copy-project.sh` and
`cleanup-scratchpad.py` are the parts most worth scrutiny.

## Reporting a vulnerability

Report privately through GitHub's private vulnerability reporting on this
repository ("Security" tab, "Report a vulnerability"). Please do not open a
public issue for a suspected vulnerability.

## What to expect

This is a solo-maintained project. Reports are handled on a best-effort basis
and there is no response-time commitment. If a report is accepted, the fix goes
out in the next release and the report is credited unless the reporter asks
otherwise.

## Supported versions

Only the latest release receives fixes. Older releases are not patched.
