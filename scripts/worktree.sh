#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

COMMAND="${1:-}"
PHASE="${2:-}"
TICKET="${3:-}"
SLUG="${4:-}"

usage() {
  echo "Usage:"
  echo "  $0 create <spec|impl> <DATA-ID> <slug>"
  echo "  $0 list"
  echo "  $0 remove <spec|impl> <DATA-ID> <slug>"
  exit 1
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | \
    sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
}

require_phase() {
  case "$PHASE" in
    spec|impl) ;;
    *) usage ;;
  esac
  [[ -n "$TICKET" && -n "$SLUG" ]] || usage
}

case "$COMMAND" in
  create)
    require_phase

    SLUG="$(slugify "$SLUG")"
    NAME="${TICKET}-${SLUG}"
    PATH_TO_WORKTREE="$ROOT/.worktrees/${PHASE}-${NAME}"
    BRANCH="${PHASE}/${NAME}"

    if [[ -e "$PATH_TO_WORKTREE" ]]; then
      echo "Worktree already exists:"
      echo "$PATH_TO_WORKTREE"
      echo
      echo "Start working:"
      echo "cd \"$PATH_TO_WORKTREE\""
      exit 0
    fi

    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git worktree add "$PATH_TO_WORKTREE" "$BRANCH"
      echo
      echo "Worktree attached to existing branch:"
      echo "$PATH_TO_WORKTREE"
    else
      git fetch origin main
      git worktree add -b "$BRANCH" "$PATH_TO_WORKTREE" origin/main
      echo
      echo "Worktree created:"
      echo "$PATH_TO_WORKTREE"
    fi

    echo
    echo "Branch:"
    echo "$BRANCH"
    echo
    echo "Start working:"
    echo "cd \"$PATH_TO_WORKTREE\""
    ;;

  list)
    git worktree list
    ;;

  remove)
    require_phase

    SLUG="$(slugify "$SLUG")"
    NAME="${TICKET}-${SLUG}"
    PATH_TO_WORKTREE="$ROOT/.worktrees/${PHASE}-${NAME}"

    git worktree remove "$PATH_TO_WORKTREE"
    echo "Removed: $PATH_TO_WORKTREE"
    ;;

  *)
    usage
    ;;
esac
