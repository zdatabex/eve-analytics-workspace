#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

COMMAND="${1:-}"
TICKET="${2:-}"
SLUG="${3:-}"

usage() {
  echo "Usage:"
  echo "  $0 create <TICKET-ID> <slug>"
  echo "  $0 list"
  echo "  $0 remove <TICKET-ID> <slug>"
  exit 1
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | \
    sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
}

case "$COMMAND" in
  create)
    [[ -n "$TICKET" && -n "$SLUG" ]] || usage

    SLUG="$(slugify "$SLUG")"
    NAME="${TICKET}-${SLUG}"
    PATH_TO_WORKTREE="$ROOT/.worktrees/$NAME"
    BRANCH="ticket/$NAME"

    if [[ -e "$PATH_TO_WORKTREE" ]]; then
      echo "Worktree already exists: $PATH_TO_WORKTREE"
      exit 1
    fi

    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      echo "Branch already exists: $BRANCH"
      exit 1
    fi

    git worktree add -b "$BRANCH" "$PATH_TO_WORKTREE" HEAD

    echo
    echo "Worktree created:"
    echo "$PATH_TO_WORKTREE"
    echo
    echo "Start working:"
    echo "cd \"$PATH_TO_WORKTREE\""
    ;;

  list)
    git worktree list
    ;;

  remove)
    [[ -n "$TICKET" && -n "$SLUG" ]] || usage

    SLUG="$(slugify "$SLUG")"
    NAME="${TICKET}-${SLUG}"
    PATH_TO_WORKTREE="$ROOT/.worktrees/$NAME"

    git worktree remove "$PATH_TO_WORKTREE"
    echo "Removed: $PATH_TO_WORKTREE"
    ;;

  *)
    usage
    ;;
esac
