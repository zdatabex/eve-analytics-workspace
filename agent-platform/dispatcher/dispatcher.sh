#!/usr/bin/env bash
set -euo pipefail

STATUS_LABELS=(
  status:needs-spec
  status:spec-review
  status:ready
  status:in-progress
  status:review
  status:blocked
)

usage() {
  echo "Usage:"
  echo "  $0 create-labels"
  echo "  $0 set <issue> <status:label>"
  exit 1
}

require_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh is required."
    exit 1
  fi
}

is_status_label() {
  local label="$1"
  local known
  for known in "${STATUS_LABELS[@]}"; do
    if [[ "$label" == "$known" ]]; then
      return 0
    fi
  done
  return 1
}

COMMAND="${1:-}"

case "$COMMAND" in
  create-labels)
    require_gh
    for label in "${STATUS_LABELS[@]}"; do
      gh label create "$label" --force --description "Issue workflow status"
    done
    ;;

  set)
    ISSUE="${2:-}"
    LABEL="${3:-}"
    [[ -n "$ISSUE" && -n "$LABEL" ]] || usage
    if ! is_status_label "$LABEL"; then
      echo "Unknown status label: $LABEL"
      exit 1
    fi
    require_gh

    while IFS= read -r existing; do
      if [[ "$existing" == status:* && "$existing" != "$LABEL" ]]; then
        gh issue edit "$ISSUE" --remove-label "$existing"
      fi
    done < <(gh issue view "$ISSUE" --json labels --jq '.labels[].name')

    gh issue edit "$ISSUE" --add-label "$LABEL"
    gh issue comment "$ISSUE" --body "dispatcher set \`$LABEL\`."
    echo "Set $ISSUE to $LABEL"
    ;;

  *)
    usage
    ;;
esac
