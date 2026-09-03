#!/bin/sh
# copy-project.sh — stage-2 copy of the project under review into the
# scratchpad, for critics to read. It also writes the manifest the
# scratchpad cleanup script later reads.
#
# Three steps, only the first depends on the filesystem:
#   STEP1-CLONE     whole-tree copy-on-write clone in STRICT mode
#                   (macOS `cp -Rc`, Linux `cp -R --reflink=always`).
#                   The permissive `auto` reflink mode is FORBIDDEN and appears
#                   nowhere below: it silently degrades to a full copy, so a
#                   clone becomes indistinguishable from copying tens of
#                   gigabytes. Strict mode fails loudly instead, and that
#                   failure is exactly the signal to move to step 2. The clone
#                   necessarily brings `.git` along; without
#                   --with-git-history it is removed from the copy again and
#                   listed as `EXCLUDED:`, as in steps 2-3.
#                   The clone runs ONLY when git reports no ignored content
#                   under --src. It copies everything on disk while steps 2-3
#                   copy what git knows, so on a tree that mixes the project
#                   with ignored runtime state it would WIDEN the copy in
#                   silence. That pre-flight gate is fail-closed and has no
#                   opt-out.
#   STEP2-FILELIST  fallback when the clone is impossible: copy the files git
#                   knows about (tracked + untracked-not-ignored); `.git`
#                   itself only with --with-git-history.
#   STEP3-NARROWED  fallback when step 2 does not fit: copy only --object-only
#                   and its immediate surroundings; everything left out is
#                   listed on stdout as `EXCLUDED:` lines (never silent).
#
# Symlinks are copied AS LINKS, never dereferenced: otherwise files that
# physically live outside the project (a shared key store the project links
# to) would land in the copy and in the critic's field of view.
#
# Disclosure minimisation runs on EVERY step, not only when space is short:
# secret-class files (.env*, *.pem, *.key, id_*, .netrc, credential dirs) are
# removed from the copy and listed as `EXCLUDED:`.
#
# ONE copy per invocation. How many copies a round makes is the orchestrator's
# call — one clone per critic when cloning is available AND the step-1
# pre-flight allows it, one shared copy otherwise (the ordinary case on a real
# repository, which almost always carries ignored content), with the number of
# simultaneous clones equal to the agent budget, at most 12 — and this script
# neither counts nor enforces that budget.
#
# Usage:
#   copy-project.sh --src <project root> --dest <scratchpad run dir>
#                   [--with-git-history] [--object-only <path>]
#                   [--run-id <id>]
#
#   --src           absolute path of the project under review (a git work tree)
#   --dest          absolute path of the scratchpad run directory. NO DEFAULT:
#                   the scratchpad root is passed in by the orchestrator, an
#                   environment variable is never the source. cleanup-scratchpad.py
#                   refuses (its condition 4) to remove a run directory fewer
#                   than 3 levels below the scratchpad root, so the run
#                   directory is placed deeper than that.
#   --run-id        run identifier written to the manifest. It MUST equal the
#                   basename of --dest and defaults to it: cleanup-scratchpad.py
#                   compares the two (its condition 7), so a divergent id — a
#                   lens suffix, say — makes the copy unremovable by the
#                   cleanup script. A divergence is refused here.
#
# Exit: 0 copy made; 2 bad arguments / refused precondition; 3 all steps failed.
# Stdout: STEP<n>-<NAME>, DURATION-SEC, DF-BEFORE/DF-AFTER, EXCLUDED:, NOTICE:.

set -u

PROG=copy-project.sh
MANIFEST_NAME=critic-ledger-manifest.json
MANIFEST_VERSION="critic-ledger/scratchpad-manifest@1"

die() { printf '%s: ERROR: %s\n' "$PROG" "$*" >&2; exit 2; }
# No step produced a copy: leave nothing half-copied behind, and say so.
fail_copy() {
  printf '%s: ERROR: %s\n' "$PROG" "$*" >&2
  reset_dest
  printf 'NOTICE: no copy was made; %s is left empty\n' "$DEST_R" >&2
  exit 3
}
note() { printf 'NOTICE: %s\n' "$*"; }

usage() {
  printf 'usage: %s --src <project root> --dest <scratchpad run dir>\n' "$PROG" >&2
  printf '            [--with-git-history] [--object-only <path>] [--run-id <id>]\n' >&2
}

# ---------------------------------------------------------------- arguments --
SRC=; DEST=; WITH_GIT=0; OBJECT_ONLY=; RUN_ID=
while [ $# -gt 0 ]; do
  case "$1" in
    --src)         [ $# -ge 2 ] || { usage; die "--src needs a value"; }; SRC=$2; shift 2 ;;
    --dest)        [ $# -ge 2 ] || { usage; die "--dest needs a value"; }; DEST=$2; shift 2 ;;
    --object-only) [ $# -ge 2 ] || { usage; die "--object-only needs a value"; }; OBJECT_ONLY=$2; shift 2 ;;
    --run-id)      [ $# -ge 2 ] || { usage; die "--run-id needs a value"; }; RUN_ID=$2; shift 2 ;;
    --with-git-history) WITH_GIT=1; shift ;;
    -h|--help)     usage; exit 0 ;;
    *)             usage; die "unknown argument: $1" ;;
  esac
done

[ -n "$SRC" ]  || { usage; die "--src is required"; }
[ -n "$DEST" ] || { usage; die "--dest is required (no default: the scratchpad root comes from the orchestrator)"; }

# Paths must be absolute, free of `..`, and free of newlines: a newline in a
# path would break every line-oriented list this script builds, so it is
# refused rather than mishandled.
NL=$(printf '\nx'); NL=${NL%x}
check_path() { # <label> <path>
  case "$2" in
    /*) ;;
    *) die "$1 must be an absolute path: $2" ;;
  esac
  case "$2" in
    *..*) die "$1 must not contain '..': $2" ;;
  esac
  case "$2" in
    *"$NL"*) die "$1 must not contain a newline" ;;
  esac
}
check_path "--src" "$SRC"
check_path "--dest" "$DEST"

[ -d "$SRC" ] || die "--src is not an existing directory: $SRC"

# Resolve both paths physically (no symlinked segments left) before comparing.
SRC_R=$(cd "$SRC" && pwd -P) || die "cannot resolve --src: $SRC"
DEST_PARENT=$(dirname "$DEST")
[ -d "$DEST_PARENT" ] || die "parent of --dest does not exist: $DEST_PARENT"
DEST_PARENT_R=$(cd "$DEST_PARENT" && pwd -P) || die "cannot resolve parent of --dest: $DEST_PARENT"
DEST_R="$DEST_PARENT_R/$(basename "$DEST")"
if [ -d "$DEST" ]; then
  DEST_R=$(cd "$DEST" && pwd -P) || die "cannot resolve --dest: $DEST"
fi

[ "$DEST_R" != "$SRC_R" ] || die "--dest is the same directory as --src: $DEST_R"
case "$DEST_R/" in "$SRC_R"/*) die "--dest lies inside --src: $DEST_R" ;; esac
case "$SRC_R/" in "$DEST_R"/*) die "--src lies inside --dest: $SRC_R" ;; esac

# --dest may exist only if it is empty; a non-empty directory is never
# written into (a half-merged copy is worse than no copy).
if [ -e "$DEST_R" ]; then
  [ -d "$DEST_R" ] || die "--dest exists and is not a directory: $DEST_R"
  if [ -n "$(ls -A "$DEST_R" 2>/dev/null)" ]; then
    die "--dest exists and is not empty: $DEST_R"
  fi
fi

# git is mandatory for the project under review: steps 2 and 3 are defined
# in terms of the file list git knows.
git -C "$SRC_R" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
  die "--src is not a git work tree: $SRC_R (run 'git init' there first)"

[ ! -e "$SRC_R/$MANIFEST_NAME" ] ||
  die "--src already contains $MANIFEST_NAME; the copy manifest would collide with it"

if [ -n "$OBJECT_ONLY" ]; then
  case "$OBJECT_ONLY" in
    /*) case "$OBJECT_ONLY/" in
          "$SRC_R"/*) OBJECT_REL=${OBJECT_ONLY#"$SRC_R"/} ;;
          *) die "--object-only is outside --src: $OBJECT_ONLY" ;;
        esac ;;
    *)  OBJECT_REL=$OBJECT_ONLY ;;
  esac
  case "$OBJECT_REL" in *..*) die "--object-only must not contain '..': $OBJECT_ONLY" ;; esac
  OBJECT_REL=${OBJECT_REL%/}
  [ -e "$SRC_R/$OBJECT_REL" ] || die "--object-only does not exist inside --src: $OBJECT_REL"
else
  OBJECT_REL=
fi

# The manifest's run_id is what cleanup-scratchpad.py compares against the
# basename of the directory it is asked to remove (its condition 7). An id that
# differs from that basename — a lens suffix appended to the run id, as
# happened in the field — leaves a copy the cleanup script refuses to remove
# unless every later caller remembers to repeat the id by hand. The divergence
# is refused at copy time instead of being discovered at teardown.
DEST_BASE=$(basename "$DEST_R")
if [ -n "$RUN_ID" ]; then
  [ "$RUN_ID" = "$DEST_BASE" ] ||
    die "--run-id must equal the basename of --dest ('$DEST_BASE'), got '$RUN_ID': cleanup-scratchpad.py compares the two (condition 7) and would refuse to remove this copy"
else
  RUN_ID=$DEST_BASE
fi

# ------------------------------------------------------------------- set-up --
umask 077                       # run dir and manifest: owner of the process only
TMPD=$(mktemp -d) || die "cannot create a temp dir"
trap 'rm -rf "$TMPD"' EXIT INT HUP TERM

mkdir -p "$DEST_R" || die "cannot create --dest: $DEST_R"
chmod 700 "$DEST_R" || die "cannot chmod 700 --dest: $DEST_R"

T_START=$(date +%s)
DF_BEFORE=$(df -m "$DEST_R" | tail -n 1)

# Empties the destination between failed steps. Only ever called on $DEST_R,
# which this run created or verified empty.
reset_dest() {
  depth=$(printf '%s' "$DEST_R" | tr -cd '/' | wc -c | tr -d ' ')
  [ "$depth" -ge 2 ] || die "refusing to reset a top-level --dest: $DEST_R"
  # The copy is being destroyed whole, so restoring write permission across it
  # is safe here in a way it is not while a copy is being KEPT: a clone brings
  # the source's modes along, and a read-only directory inside the copy would
  # otherwise leave a half-emptied destination behind.
  chmod -R u+w "$DEST_R" 2>/dev/null
  find "$DEST_R" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null
}

# ----------------------------------------------------------- excluded list ----
# Every omission from the copy, one `<path> | class=<class>` line. The step-1
# pre-flight below is its earliest writer. `reset_excluded` re-seeds the list
# after a step's copy is discarded: the pre-flight lines describe --src and
# survive that, everything a discarded step contributed does not.
EXCLUDED_LIST="$TMPD/excluded.txt"
PREFLIGHT_LIST="$TMPD/preflight.txt"
: >"$PREFLIGHT_LIST"
reset_excluded() { cat "$PREFLIGHT_LIST" >"$EXCLUDED_LIST"; }
reset_excluded

# --------------------------------------- step 1 pre-flight: scope of the copy --
# Step 1 and steps 2-3 do not mean the same thing by "the project": the strict
# clone takes EVERYTHING under --src, steps 2-3 take what git knows. On a tree
# where the project is mixed with ignored runtime state the clone WIDENS the
# copy in silence — the disclosure sweep further down removes only
# secret-class paths, so private-but-not-secret state would reach the critics
# unannounced. The clone therefore runs only when git reports no ignored
# content at all; the predicate is exact by construction, being the same source
# of truth step 2 defines the project by.
#
# Fail-closed on BOTH conditions, not one: non-empty output, OR a non-zero exit
# code. Empty stdout with a non-zero code is a refusal, never "nothing is
# ignored" (there is no `set -e` here, so the code is checked explicitly, as
# for every other git call in this script). No opt-out flag is offered on
# purpose: an opt-out would be reached for out of habit and the gate would be
# decorative.
PREFLIGHT_OK=1
git -C "$SRC_R" ls-files -z --others --ignored --exclude-standard --directory \
  >"$TMPD/ignored.z" 2>"$TMPD/ignored.err"
PREFLIGHT_RC=$?
if [ "$PREFLIGHT_RC" -ne 0 ]; then
  PREFLIGHT_OK=0
  note "step 1 (strict clone) not run: the git pre-flight failed (exit $PREFLIGHT_RC): $(tr '\n' ' ' <"$TMPD/ignored.err")"
  printf 'git pre-flight | class=git-preflight-failed (git ls-files --ignored exit %s)\n' \
    "$PREFLIGHT_RC" >>"$PREFLIGHT_LIST"
elif [ -s "$TMPD/ignored.z" ]; then
  PREFLIGHT_OK=0
  tr '\0' '\n' <"$TMPD/ignored.z" >"$TMPD/ignored.txt"
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    printf '%s | class=git-ignored\n' "$p" >>"$PREFLIGHT_LIST"
  done <"$TMPD/ignored.txt"
  note "step 1 (strict clone) not run: --src carries git-ignored content ($(wc -l <"$TMPD/ignored.txt" | tr -d ' ') top-level entries listed as EXCLUDED); the copy is built from the git-known file list instead"
fi
reset_excluded

# ------------------------------------------------------ step 1: strict clone --
STEP=
OS=$(uname -s)
CLONE_RC=1
CLONE_GIT_EXCLUDED=0
: >"$TMPD/cp.err"
if [ "$PREFLIGHT_OK" -eq 1 ]; then
  case "$OS" in
    Darwin) cp -Rc "$SRC_R/." "$DEST_R" >"$TMPD/cp.err" 2>&1; CLONE_RC=$? ;;
    Linux)  cp -R --reflink=always -T "$SRC_R" "$DEST_R" >"$TMPD/cp.err" 2>&1; CLONE_RC=$? ;;
    *)      printf 'no strict clone mode known for %s\n' "$OS" >"$TMPD/cp.err"; CLONE_RC=1 ;;
  esac
fi

if [ "$CLONE_RC" -eq 0 ]; then
  STEP=STEP1-CLONE
  # A whole-tree clone necessarily brings .git along. Unless a lens asked for
  # the history, remove it again so that step 1 obeys the same
  # git-history-on-demand contract as steps 2-3. What is removed is the copy
  # this run just created inside its own destination — guarded by the same
  # depth check reset_dest uses, and never touching $SRC_R.
  if [ "$WITH_GIT" -eq 0 ] && [ -e "$DEST_R/.git" ]; then
    depth=$(printf '%s' "$DEST_R" | tr -cd '/' | wc -c | tr -d ' ')
    [ "$depth" -ge 2 ] || die "refusing to remove .git under a top-level --dest: $DEST_R"
    rm -rf -- "$DEST_R/.git" || die "cannot remove .git from the copy: $DEST_R/.git"
    CLONE_GIT_EXCLUDED=1
  fi
elif [ "$PREFLIGHT_OK" -eq 1 ]; then
  note "strict clone unavailable (cp exit $CLONE_RC): $(tr '\n' ' ' <"$TMPD/cp.err")"
  reset_dest
fi

# ------------------------------------------------ secret-class path matching --
# Common patterns for environment files and local secrets.
is_secret_base() { # <basename> -> echoes the matched class, or nothing
  case "$1" in
    .env|.env.*|.envrc)              printf '.env*' ;;
    *.pem)                           printf '*.pem' ;;
    *.key)                           printf '*.key' ;;
    id_*)                            printf 'id_*' ;;
    .netrc)                          printf '.netrc' ;;
    .ssh|.gnupg|.aws|.azure|.kube|.docker|.npmrc|credentials)
                                     printf 'credentials-store' ;;
    *)                               ;;
  esac
}

# True when <relative path> is the object under check or lies inside it.
is_object() { # <relative path>
  [ -n "$OBJECT_REL" ] || return 1
  [ "$1" = "$OBJECT_REL" ] && return 0
  case "$1/" in "$OBJECT_REL"/*) return 0 ;; esac
  return 1
}

# ------------------------------------------------ git file list (steps 2, 3) --
# Builds "$TMPD/list.txt": newline-separated paths relative to $SRC_R, tracked
# plus untracked-not-ignored, minus deleted-from-the-worktree, minus
# secret-class files. Refuses (rather than mishandles) filenames with newlines.
# `$EXCLUDED_LIST` itself is created before step 1, which already writes to it.

# Step 1 removed the .git it had cloned (no lens asked for the history): record
# it in the same class wording steps 2-3 use.
[ "$CLONE_GIT_EXCLUDED" -eq 0 ] ||
  printf '.git | class=git-history (not requested by any lens)\n' >>"$EXCLUDED_LIST"

build_file_list() {
  : >"$TMPD/all.z"
  git -C "$SRC_R" ls-files -z >>"$TMPD/all.z" || return 1
  git -C "$SRC_R" ls-files -z --others --exclude-standard >>"$TMPD/all.z" || return 1
  nul=$(tr -dc '\0' <"$TMPD/all.z" | wc -c | tr -d ' ')
  tr '\0' '\n' <"$TMPD/all.z" >"$TMPD/all.txt"
  lines=$(wc -l <"$TMPD/all.txt" | tr -d ' ')
  [ "$nul" = "$lines" ] || die "the git file list contains a filename with a newline; refusing"
  {
    while IFS= read -r p; do
      [ -n "$p" ] || continue
      if [ ! -e "$SRC_R/$p" ] && [ ! -L "$SRC_R/$p" ]; then
        note "skipped (tracked but missing from the work tree): $p" >&2
        continue
      fi
      cls=$(is_secret_base "$(basename "$p")")
      if [ -n "$cls" ] && ! is_object "$p"; then
        printf '%s | class=%s\n' "$p" "$cls" >>"$EXCLUDED_LIST"
        continue
      fi
      [ -z "$cls" ] || note "kept $p: it is the object under check, secret-class exclusion not applied" >&2
      printf '%s\n' "$p"
    done
  } <"$TMPD/all.txt" >"$TMPD/list.txt"
  return 0
}

# Copies "$1" (a newline-separated list file, paths relative to $SRC_R) into
# $DEST_R with tar: symlinks stay symlinks, directories are created on the way.
copy_by_list() { # <list file>
  [ -s "$1" ] || { note "the file list is empty"; return 1; }
  ( cd "$SRC_R" && tar -c -f - -T "$1" ) 2>"$TMPD/tar.err" |
    ( cd "$DEST_R" && tar -x -f - ) 2>>"$TMPD/tar.err"
  trc=$?
  want=$(wc -l <"$1" | tr -d ' ')
  got=$(find "$DEST_R" \( -type f -o -type l \) | wc -l | tr -d ' ')
  if [ "$trc" -ne 0 ] || [ "$got" -lt "$want" ]; then
    note "list copy incomplete (tar exit $trc, $got of $want entries): $(tr '\n' ' ' <"$TMPD/tar.err")"
    return 1
  fi
  return 0
}

copy_git_dir() {
  [ "$WITH_GIT" -eq 1 ] || return 0
  [ -e "$SRC_R/.git" ] || { note ".git not present in --src, nothing to copy"; return 0; }
  cp -R "$SRC_R/.git" "$DEST_R/.git" 2>"$TMPD/git.err" || {
    note "copying .git failed: $(tr '\n' ' ' <"$TMPD/git.err")"
    return 1
  }
  return 0
}

# --------------------------------------------------- step 2: git file list ---
if [ -z "$STEP" ]; then
  if build_file_list && copy_by_list "$TMPD/list.txt" && copy_git_dir; then
    STEP=STEP2-FILELIST
    [ "$WITH_GIT" -eq 1 ] || printf '.git | class=git-history (not requested by any lens)\n' >>"$EXCLUDED_LIST"
  else
    note "step 2 (git file list) did not fit"
    reset_dest
    reset_excluded
  fi
fi

# ------------------------------------------------------ step 3: narrowed ------
# The object under check plus its immediate surroundings: the object itself,
# and the non-directory entries sitting next to it in its parent directory.
if [ -z "$STEP" ]; then
  [ -n "$OBJECT_REL" ] ||
    fail_copy "steps 1 and 2 failed and --object-only was not given, so there is nothing to narrow to"
  build_file_list || fail_copy "cannot build the git file list for the narrowed copy"
  PARENT_REL=$(dirname "$OBJECT_REL")
  : >"$TMPD/narrow.txt"
  {
    while IFS= read -r p; do
      keep=0
      if is_object "$p"; then
        keep=1
      else
        d=$(dirname "$p")
        [ "$d" = "$PARENT_REL" ] && keep=1
      fi
      if [ "$keep" -eq 1 ]; then
        printf '%s\n' "$p" >>"$TMPD/narrow.txt"
      else
        printf '%s | class=narrowed-out (step 3)\n' "$p" >>"$EXCLUDED_LIST"
      fi
    done
  } <"$TMPD/list.txt"
  copy_by_list "$TMPD/narrow.txt" || fail_copy "the narrowed copy failed as well"
  copy_git_dir || fail_copy "the narrowed copy failed while copying .git"
  STEP=STEP3-NARROWED
  [ "$WITH_GIT" -eq 1 ] || printf '.git | class=git-history (not requested by any lens)\n' >>"$EXCLUDED_LIST"
fi

# ------------------------------------- disclosure minimisation over the copy --
# Runs on every step: after a clone, secret-class files are physically in the
# copy and are removed here; after steps 2-3 they were already filtered out,
# and this sweep is the second line of defence.
find "$DEST_R" -mindepth 1 \( -name '.env' -o -name '.env.*' -o -name '.envrc' \
  -o -name '*.pem' -o -name '*.key' -o -name 'id_*' -o -name '.netrc' \
  -o -name '.ssh' -o -name '.gnupg' -o -name '.aws' -o -name '.azure' \
  -o -name '.kube' -o -name '.docker' -o -name '.npmrc' -o -name 'credentials' \) \
  -print0 >"$TMPD/hits.z" 2>/dev/null
hnul=$(tr -dc '\0' <"$TMPD/hits.z" | wc -c | tr -d ' ')
tr '\0' '\n' <"$TMPD/hits.z" >"$TMPD/hits.txt"
hlines=$(wc -l <"$TMPD/hits.txt" | tr -d ' ')
[ "$hnul" = "$hlines" ] || die "the copy contains a filename with a newline; refusing to sweep it blindly"
while IFS= read -r hit; do
  [ -n "$hit" ] || continue
  case "$hit" in "$DEST_R"/*) ;; *) die "sweep produced a path outside --dest: $hit" ;; esac
  rel=${hit#"$DEST_R"/}
  cls=$(is_secret_base "$(basename "$hit")")
  [ -n "$cls" ] || continue
  if is_object "$rel"; then
    note "kept $rel: it is the object under check, secret-class exclusion not applied"
    continue
  fi
  # A refusal here is not a `die`: `die` would leave a HALF-cleaned copy on
  # disk, with the secret still readable in it and no manifest by which
  # cleanup-scratchpad.py could find it. Restore write permission on what is
  # being removed and retry once; if it still refuses, the copy cannot be
  # trusted at all — destroy it whole and report "no copy was made" (exit 3).
  if ! rm -rf -- "$hit" 2>/dev/null; then
    chmod -R u+w "$hit" 2>/dev/null
    rm -rf -- "$hit" 2>/dev/null ||
      fail_copy "cannot remove $rel from the copy even after chmod -R u+w; the copy would keep a secret-class path"
  fi
  printf '%s | class=%s\n' "$rel" "$cls" >>"$EXCLUDED_LIST"
done <"$TMPD/hits.txt"

# Deduplicate: list-filter and sweep can report the same path.
sort -u "$EXCLUDED_LIST" >"$TMPD/excluded.sorted" && mv "$TMPD/excluded.sorted" "$EXCLUDED_LIST"
while IFS= read -r line; do
  [ -n "$line" ] || continue
  printf 'EXCLUDED: %s\n' "$line"
done <"$EXCLUDED_LIST"

# ------------------------------------------------------------------ manifest --
# Format: absolute path, run id, time, list of what was created and volume,
# with field names and JSON shape as fixed by the cleanup script that reads it — `critic-ledger-manifest.json`, mode 0600,
# `manifest_version` "critic-ledger/scratchpad-manifest@1", required fields
# absolute_path (condition 6), run_id (condition 7), created_at (ISO 8601 WITH
# a timezone offset), project_root (condition 8), created, size_bytes. The
# extra fields below (step, with_git_history, object_only, excluded) are the
# copy's own record and are ignored by the cleanup script.
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

# Apparent size in bytes: GNU du where available, per-file stat otherwise.
if du -s --apparent-size --block-size=1 "$DEST_R" >/dev/null 2>&1; then
  SIZE_BYTES=$(du -s --apparent-size --block-size=1 "$DEST_R" | awk '{print $1}')
else
  SIZE_BYTES=$(find "$DEST_R" -type f -exec stat -f '%z' {} + 2>/dev/null |
    awk '{s+=$1} END{print s+0}')
fi
[ -n "$SIZE_BYTES" ] || SIZE_BYTES=0

# ISO 8601 with an explicit offset: "+0000" is turned into "+00:00" so that
# every reader of the format parses it, not just the newest ones.
TZOFF=$(date +%z)
case "$TZOFF" in
  [+-][0-9][0-9][0-9][0-9]) TZOFF="${TZOFF%??}:${TZOFF#???}" ;;
  *) TZOFF="+00:00" ;;
esac
CREATED_AT="$(date +%Y-%m-%dT%H:%M:%S)$TZOFF"
MANIFEST="$DEST_R/$MANIFEST_NAME"

{
  printf '{\n'
  printf '  "manifest_version": "%s",\n' "$MANIFEST_VERSION"
  printf '  "created_by": "critic-ledger/templates/%s",\n' "$PROG"
  printf '  "created_at": "%s",\n' "$CREATED_AT"
  printf '  "run_id": "%s",\n' "$(json_escape "$RUN_ID")"
  printf '  "absolute_path": "%s",\n' "$(json_escape "$DEST_R")"
  printf '  "project_root": "%s",\n' "$(json_escape "$SRC_R")"
  printf '  "step": "%s",\n' "$STEP"
  printf '  "with_git_history": %s,\n' "$([ "$WITH_GIT" -eq 1 ] && echo true || echo false)"
  printf '  "object_only": "%s",\n' "$(json_escape "$OBJECT_REL")"
  printf '  "size_bytes": %s,\n' "$SIZE_BYTES"
  printf '  "created": ['
  first=1
  for e in "$DEST_R"/* "$DEST_R"/.[!.]* "$DEST_R"/..?*; do
    [ -e "$e" ] || continue
    b=$(basename "$e")
    [ "$b" = "$MANIFEST_NAME" ] && continue
    [ $first -eq 1 ] || printf ','
    printf '\n    "%s"' "$(json_escape "$b")"
    first=0
  done
  [ $first -eq 1 ] || printf '\n  '
  printf '],\n'
  printf '  "excluded": ['
  first=1
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    [ $first -eq 1 ] || printf ','
    printf '\n    "%s"' "$(json_escape "$line")"
    first=0
  done <"$EXCLUDED_LIST"
  [ $first -eq 1 ] || printf '\n  '
  printf ']\n'
  printf '}\n'
} >"$MANIFEST" || die "cannot write the manifest: $MANIFEST"
chmod 600 "$MANIFEST" || die "cannot chmod 600 the manifest: $MANIFEST"

# ------------------------------------------------------------ measurements ---
T_END=$(date +%s)
DF_AFTER=$(df -m "$DEST_R" | tail -n 1)

printf '%s\n' "$STEP"
printf 'SRC: %s\n' "$SRC_R"
printf 'DEST: %s\n' "$DEST_R"
printf 'RUN-ID: %s\n' "$RUN_ID"
printf 'MANIFEST: %s\n' "$MANIFEST"
printf 'SIZE-BYTES: %s\n' "$SIZE_BYTES"
printf 'DURATION-SEC: %s\n' "$((T_END - T_START))"
printf 'DF-BEFORE: %s\n' "$DF_BEFORE"
printf 'DF-AFTER: %s\n' "$DF_AFTER"
exit 0
