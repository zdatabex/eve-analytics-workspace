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

PROMPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/prompts"

usage() {
  echo "Usage:"
  echo "  $0 create-labels"
  echo "  $0 set <issue> <status:label>"
  echo "  $0 next [issue]"
  echo "  $0 run [issue]"
  echo "  $0 watch [seconds]"
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

set_label() {
  local issue="$1" label="$2" existing
  require_gh
  if ! is_status_label "$label"; then
    echo "Unknown status label: $label" >&2
    exit 1
  fi
  while IFS= read -r existing; do
    if [[ "$existing" == status:* && "$existing" != "$label" ]]; then
      gh issue edit "$issue" --repo "$REPO" --remove-label "$existing"
    fi
  done < <(gh issue view "$issue" --repo "$REPO" --json labels --jq '.labels[].name')
  gh issue edit "$issue" --repo "$REPO" --add-label "$label"
  gh issue comment "$issue" --repo "$REPO" --body "dispatcher set \`$label\`."
  echo "Set $issue to $label"
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | \
    sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
}

fill_template() {
  local file="$1" text
  text="$(cat "$file")"
  text="${text//\{\{ISSUE_URL\}\}/$ISSUE_URL}"
  text="${text//\{\{TICKET\}\}/$TICKET}"
  text="${text//\{\{AGENT\}\}/$AGENT}"
  text="${text//\{\{PR_URL\}\}/$PR_URL}"
  text="${text//\{\{BRANCH\}\}/$BRANCH}"
  text="${text//\{\{WORKTREE\}\}/$WORKTREE}"
  text="${text//\{\{SLUG\}\}/$SLUG}"
  printf '%s\n' "$text"
}

load_repo() {
  require_gh
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required." >&2
    exit 1
  fi
  REPO="${GH_REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
  ISSUES_JSON="$(gh issue list --repo "$REPO" --state all --limit 200 \
    --json number,title,state,labels)"
  PRS_JSON="$(gh pr list --repo "$REPO" --state all --limit 100 \
    --json number,state,headRefName,url,mergedAt)"
}

classify_pr() {
  local number="$1" file
  file="$(mktemp)"
  gh pr view "$number" --repo "$REPO" \
    --json reviews,comments,commits,statusCheckRollup,state,url,headRefName \
    >"$file" || exit 1
  python3 - "$file" <<'PY' || exit 1
import json
import sys
from datetime import datetime

def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def line_kind(text):
    if not text:
        return None
    for line in text.splitlines():
        line = line.strip().rstrip(".")
        if line == "Blocking findings remain":
            return "blocking"
        if line == "No blocking findings remain":
            return "clear"
    return None

data = json.load(open(sys.argv[1]))
events = []
for review in data.get("reviews") or []:
    kind = line_kind(review.get("body"))
    when = parse_time(review.get("submittedAt"))
    if kind and when:
        events.append((when, "review", kind))
for comment in data.get("comments") or []:
    body = (comment.get("body") or "").strip()
    when = parse_time(comment.get("createdAt"))
    if not when:
        continue
    kind = line_kind(body)
    if kind:
        events.append((when, "review", kind))
    elif body.rstrip(".") == "allow one more revision":
        events.append((when, "allow", None))
commits = []
for commit in data.get("commits") or []:
    when = parse_time(commit.get("committedDate"))
    if when:
        commits.append(when)
events.sort(key=lambda item: item[0])
reviews = [event for event in events if event[1] == "review"]
latest_kind = reviews[-1][2] if reviews else "none"
latest_time = reviews[-1][0] if reviews else None
blocking_count = sum(1 for event in reviews if event[2] == "blocking")
commit_after = "yes" if latest_time and any(item > latest_time for item in commits) else "no"
allow_after = "yes" if latest_time and any(
    event[1] == "allow" and event[0] > latest_time for event in events
) else "no"
rollup = data.get("statusCheckRollup") or []
if isinstance(rollup, dict):
    rollup = [rollup]
pending = {"QUEUED", "IN_PROGRESS", "PENDING", "WAITING", "REQUESTED"}
failed = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
checks = "passed"
for item in rollup:
    status = (item.get("status") or "").upper()
    conclusion = (item.get("conclusion") or item.get("state") or "").upper()
    if conclusion in failed or status in failed:
        checks = "failed"
        break
    if status in pending or conclusion in pending:
        checks = "pending"
        break
print(data.get("state") or "")
print(data.get("url") or "")
print(data.get("headRefName") or "")
print(latest_kind)
print(commit_after)
print(allow_after)
print(checks)
print(blocking_count)
PY
  rm -f "$file"
}

choose_owner() {
  local named
  named="$(printf '%s\n' "$ISSUE_BODY" | python3 -c '
import re, sys
title = sys.argv[1]
body = sys.stdin.read()
match = re.search(r"Agent:\**\s*([A-Za-z0-9_-]+)", body)
known = {"data-engineer", "analytics-engineer", "analyst"}
if match and match.group(1) in known:
    print(match.group(1))
    raise SystemExit
text = f"{title}\n{body}".lower()
if "source schema" in text or "data generation" in text or "ingestion" in text:
    print("data-engineer")
elif "dbt" in text or "warehouse" in text:
    print("analytics-engineer")
elif "hex" in text or "omni" in text:
    print("analyst")
else:
    print("data-engineer")
' "$ISSUE_TITLE")" || exit 1
  printf '%s\n' "$named"
}

dependencies_closed() {
  printf '%s\n' "$ISSUE_BODY" | python3 -c '
import json, re, sys
body = sys.stdin.read()
issues = json.loads(sys.argv[1])
deps = re.findall(r"Depends On:\**\s*(DATA-\d+)", body)
by_ticket = {}
for issue in issues:
    match = re.match(r"(DATA-\d+)", issue["title"])
    if match:
        by_ticket[match.group(1)] = issue["state"]
for dep in deps:
    if by_ticket.get(dep) != "CLOSED":
        raise SystemExit(1)
' "$ISSUES_JSON"
}

find_pr_number() {
  local phase="$1"
  python3 - "$phase" "$TICKET" "$PRS_JSON" <<'PY' || exit 1
import json
import sys
phase, ticket, raw = sys.argv[1:]
prefix = f"{phase}/{ticket}-"
pulls = [
    item for item in json.loads(raw)
    if item["headRefName"].startswith(prefix)
]
opens = [item for item in pulls if item["state"] == "OPEN"]
merged = [item for item in pulls if item["state"] == "MERGED"]
pick = (opens or merged or [None])[0]
print("" if pick is None else pick["number"])
PY
}

use_branch() {
  local phase="$1"
  if [[ -n "${PR_BRANCH:-}" ]]; then
    BRANCH="$PR_BRANCH"
    WORKTREE=".worktrees/${PR_BRANCH//\//-}"
  else
    BRANCH="${phase}/${TICKET}-${SLUG}"
    WORKTREE=".worktrees/${phase}-${TICKET}-${SLUG}"
  fi
}

load_prompt() {
  local action="$1"
  if [[ -f "$PROMPT_DIR/${action}.txt" ]]; then
    PROMPT="$(fill_template "$PROMPT_DIR/${action}.txt")"
  fi
}

phase_decision() {
  local phase="$1" review_action="$2" revise_action="$3" number
  number="$(find_pr_number "$phase")"
  [[ -n "$number" ]] || return 1
  local result state kind commit_after allow_after checks blocking
  result="$(classify_pr "$number")"
  state="$(sed -n '1p' <<<"$result")"
  PR_URL="$(sed -n '2p' <<<"$result")"
  PR_BRANCH="$(sed -n '3p' <<<"$result")"
  kind="$(sed -n '4p' <<<"$result")"
  commit_after="$(sed -n '5p' <<<"$result")"
  allow_after="$(sed -n '6p' <<<"$result")"
  checks="$(sed -n '7p' <<<"$result")"
  blocking="$(sed -n '8p' <<<"$result")"
  PR="$number"
  use_branch "$phase"
  if [[ "$state" == "MERGED" && "$phase" == "spec" && "$STATUS" == "status:spec-review" ]]; then
    ACTION="launch-implement"
    TRIGGER="specification pull request #${number} is merged and the issue is still status:spec-review"
    AGENT="$(choose_owner)"
    PR_BRANCH=""
    PR_URL=""
    use_branch impl
    load_prompt "$ACTION"
    return 0
  fi
  if [[ "$state" == "MERGED" && "$phase" == "impl" ]]; then
    if [[ "$checks" == "passed" ]]; then
      ACTION="ask-close"
      TRIGGER="implementation pull request #${number} is merged and the required checks have passed"
      PROMPT="Required checks passed for ${TICKET}. Close ${ISSUE_URL}."
    else
      ACTION="wait"
      TRIGGER="implementation pull request #${number} is merged and checks have not passed"
      AGENT=""
      PROMPT=""
      return 0
    fi
    AGENT="human"
    return 0
  fi
  [[ "$state" == "OPEN" ]] || return 1
  case "$kind" in
    none)
      ACTION="$review_action"
      TRIGGER="${phase} pull request #${number} is open and has no decision review"
      AGENT="reviewer"
      ;;
    clear)
      ACTION="ask-merge"
      TRIGGER="the latest review on pull request #${number} says no blocking findings remain"
      AGENT="human"
      PROMPT="No blocking findings remain on ${TICKET}. Merge ${PR_URL}."
      ;;
    blocking)
      if [[ "$commit_after" == "yes" ]]; then
        ACTION="$review_action"
        TRIGGER="a new commit on pull request #${number} follows a blocking review"
        AGENT="reviewer"
      elif [[ "$allow_after" == "yes" || "$blocking" == "1" ]]; then
        ACTION="$revise_action"
        if [[ "$allow_after" == "yes" ]]; then
          TRIGGER="allow one more revision was commented on pull request #${number}"
        else
          TRIGGER="the first review on pull request #${number} says blocking findings remain"
        fi
        AGENT="$(choose_owner)"
      else
        ACTION="ask-decide"
        TRIGGER="a later review on pull request #${number} still says blocking findings remain"
        AGENT="human"
        PROMPT="A blocking finding remains on ${PR_URL}. Comment \`allow one more revision\` on the pull request to allow one more pass, or close it and set status:blocked."
      fi
      ;;
    *)
      return 1
      ;;
  esac
  if [[ "$ACTION" == launch-* ]]; then
    load_prompt "$ACTION"
  fi
  return 0
}

decide_issue() {
  local number="$1" json
  json="$(gh issue view "$number" --repo "$REPO" --json number,title,body,state,labels,url)"
  ISSUE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["number"])' <<<"$json")"
  ISSUE_TITLE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["title"])' <<<"$json")"
  ISSUE_BODY="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["body"] or "")' <<<"$json")"
  ISSUE_STATE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])' <<<"$json")"
  ISSUE_URL="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' <<<"$json")"
  TICKET="$(python3 -c 'import re,sys; m=re.match(r"(DATA-\d+)", sys.argv[1]); print(m.group(1) if m else "")' "$ISSUE_TITLE")"
  STATUS="$(python3 -c 'import json,sys; labels=json.load(sys.stdin)["labels"]; print(next((item["name"] for item in labels if item["name"].startswith("status:")), ""))' <<<"$json")"
  SLUG="$(slugify "${ISSUE_TITLE#${TICKET}}")"
  ACTION="wait"
  TRIGGER="no matching row"
  AGENT=""
  PR=""
  PR_URL=""
  PR_BRANCH=""
  BRANCH=""
  WORKTREE=""
  PROMPT=""
  [[ -n "$TICKET" ]] || return 0
  if [[ "$ISSUE_STATE" == "CLOSED" ]]; then
    return 0
  fi
  if [[ "$STATUS" == "status:blocked" ]]; then
    TRIGGER="issue is status:blocked"
    return 0
  fi
  if [[ "$STATUS" == "status:needs-spec" ]]; then
    if dependencies_closed; then
      ACTION="launch-spec"
      TRIGGER="issue is status:needs-spec and its dependencies are closed"
      AGENT="$(choose_owner)"
      use_branch spec
      load_prompt "$ACTION"
    else
      TRIGGER="issue is status:needs-spec and a dependency is open"
    fi
    return 0
  fi
  if [[ "$STATUS" == "status:spec-review" ]]; then
    phase_decision spec launch-review-spec launch-revise-spec || true
    return 0
  fi
  if [[ "$STATUS" == "status:ready" || "$STATUS" == "status:in-progress" ]]; then
    TRIGGER="implementation was already started"
    return 0
  fi
  if phase_decision impl launch-review-impl launch-revise-impl; then
    if [[ "$ACTION" == "ask-close" || "$STATUS" == "status:review" ]]; then
      return 0
    fi
  fi
  ACTION="wait"
  TRIGGER="no matching row"
  PROMPT=""
}

print_row() {
  printf 'issue: %s\n' "$ISSUE"
  printf 'ticket: %s\n' "$TICKET"
  printf 'trigger: %s\n' "$TRIGGER"
  printf 'action: %s\n' "$ACTION"
  printf 'agent: %s\n' "$AGENT"
  printf 'pr: %s\n' "$PR"
  printf 'prompt: |\n'
  printf '%s\n' "$PROMPT"
}

needs_spec_successor() {
  python3 - "$ISSUES_JSON" <<'PY'
import json
import re
import sys
issues = []
for issue in json.loads(sys.argv[1]):
    match = re.match(r"DATA-(\d+)", issue["title"])
    if not match:
        continue
    status = next((item["name"] for item in issue["labels"] if item["name"].startswith("status:")), "")
    issues.append((int(match.group(1)), issue["number"], issue["state"], status, match.group(0)))
issues.sort()
by_number = {item[0]: item for item in issues}
for number, issue_number, state, status, ticket in issues:
    if state != "CLOSED":
        continue
    nxt = by_number.get(number + 1)
    if nxt and nxt[2] == "OPEN" and not nxt[3]:
        print(nxt[1])
        raise SystemExit
print("")
PY
}

select_issue() {
  local requested="${1:-}" number
  ACTION="wait"
  TRIGGER="no matching row"
  AGENT=""
  PR=""
  PROMPT=""
  TICKET=""
  ISSUE=""
  if [[ -n "$requested" ]]; then
    decide_issue "$requested"
    if [[ "$ISSUE_STATE" == "CLOSED" && "$ACTION" == "wait" ]]; then
      number="$(needs_spec_successor)"
      if [[ -n "$number" ]]; then
        decide_issue "$number"
        ACTION="ask-needs-spec"
        TRIGGER="the previous DATA issue is closed and this issue has no status label"
        AGENT="human"
        PROMPT="Set status:needs-spec on ${ISSUE_URL} (${TICKET})."
      fi
    fi
    return 0
  fi
  local candidate
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    decide_issue "$candidate"
    if [[ "$ACTION" != "wait" ]]; then
      return 0
    fi
  done < <(python3 - "$ISSUES_JSON" <<'PY'
import json
import re
import sys
rows = []
for issue in json.loads(sys.argv[1]):
    match = re.match(r"DATA-(\d+)", issue["title"])
    if match and issue["state"] == "OPEN":
        rows.append((int(match.group(1)), issue["number"]))
for _, number in sorted(rows):
    print(number)
PY
)
  number="$(needs_spec_successor)"
  if [[ -n "$number" ]]; then
    decide_issue "$number"
    ACTION="ask-needs-spec"
    TRIGGER="the previous DATA issue is closed and this issue has no status label"
    AGENT="human"
    PROMPT="Set status:needs-spec on ${ISSUE_URL} (${TICKET})."
    return 0
  fi
  ACTION="wait"
  TRIGGER="no matching row"
  PROMPT=""
}

next_cmd() {
  load_repo
  select_issue "${1:-}"
  print_row
}

run_cmd() {
  load_repo
  select_issue "${1:-}"
  if [[ "$ACTION" == "wait" ]]; then
    return 0
  fi
  if [[ "$ACTION" == "launch-implement" ]]; then
    set_label "$ISSUE" "status:ready"
  fi
  if [[ "$ACTION" == ask-* ]]; then
    printf '%s\n' "$PROMPT"
    if [[ -n "${DISPATCHER_NOTIFY:-}" ]]; then
      printf '%s\n' "$PROMPT" | "${DISPATCHER_NOTIFY}"
    fi
    return 0
  fi
  print_row
  if [[ -n "${DISPATCHER_AGENT_CMD:-}" ]]; then
    local prompt_file
    prompt_file="$(mktemp)"
    printf '%s\n' "$PROMPT" >"$prompt_file"
    "${DISPATCHER_AGENT_CMD}" "$AGENT" "$prompt_file"
  fi
}

watch_cmd() {
  local seconds="${1:-60}"
  while true; do
    run_cmd "" || true
    sleep "$seconds"
  done
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
    load_repo
    [[ -n "${2:-}" && -n "${3:-}" ]] || usage
    set_label "$2" "$3"
    ;;

  next)
    next_cmd "${2:-}"
    ;;

  run)
    run_cmd "${2:-}"
    ;;

  watch)
    watch_cmd "${2:-60}"
    ;;

  *)
    usage
    ;;
esac
