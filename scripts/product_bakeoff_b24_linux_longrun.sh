#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"

required_env() {
  local name
  for name in \
    OPENLOCUS_B24_CHECKOUT \
    OPENLOCUS_B24_PYTHON \
    OPENLOCUS_B24_PRIVATE_ROOT \
    OPENLOCUS_B24_CANDIDATE_PLAN \
    OPENLOCUS_B24_B2_LOCK \
    OPENLOCUS_B24_B21_LOCK \
    OPENLOCUS_B24_EXCLUSIONS \
    OPENLOCUS_B24_QUALIFICATION_REPORT \
    OPENLOCUS_B24_QUALIFICATION_PRIVATE_RECEIPT \
    OPENLOCUS_B24_READINESS_REPORT \
    OPENLOCUS_B24_RUNS_DIR \
    OPENLOCUS_B24_OPENLOCUS \
    OPENLOCUS_B24_PUBLIC_OUT \
    OPENLOCUS_B24_LOG \
    OPENLOCUS_B24_PID \
    OPENLOCUS_B24_EXIT
  do
    if [[ -z "${!name:-}" ]]; then
      printf 'missing required B2.4 environment variable\n' >&2
      return 1
    fi
  done
}

safe_target() {
  local path="$1"
  if [[ -L "$path" ]]; then
    printf 'unsafe symbolic-link target\n' >&2
    return 1
  fi
}

run_worker() {
  required_env
  umask 077
  cd "$OPENLOCUS_B24_CHECKOUT"
  ulimit -n 65535
  safe_target "$OPENLOCUS_B24_LOG"
  safe_target "$OPENLOCUS_B24_EXIT"
  set +e
  PYTHONUNBUFFERED=1 "$OPENLOCUS_B24_PYTHON" \
    eval/product_bakeoff_b24_cli.py \
    --full-run \
    --candidate-plan "$OPENLOCUS_B24_CANDIDATE_PLAN" \
    --private-root "$OPENLOCUS_B24_PRIVATE_ROOT" \
    --excluded-b2-repo-lock "$OPENLOCUS_B24_B2_LOCK" \
    --excluded-b21-repo-lock "$OPENLOCUS_B24_B21_LOCK" \
    --repository-exclusions "$OPENLOCUS_B24_EXCLUSIONS" \
    --qualification-report "$OPENLOCUS_B24_QUALIFICATION_REPORT" \
    --qualification-private-receipt "$OPENLOCUS_B24_QUALIFICATION_PRIVATE_RECEIPT" \
    --readiness-report "$OPENLOCUS_B24_READINESS_REPORT" \
    --runs-dir "$OPENLOCUS_B24_RUNS_DIR" \
    --openlocus "$OPENLOCUS_B24_OPENLOCUS" \
    --public-out "$OPENLOCUS_B24_PUBLIC_OUT"
  code=$?
  set -e
  exit_tmp="${OPENLOCUS_B24_EXIT}.tmp.$$"
  printf '%s\n' "$code" >"$exit_tmp"
  mv "$exit_tmp" "$OPENLOCUS_B24_EXIT"
  exit "$code"
}

case "$mode" in
  --self-test)
    [[ "$(uname -s)" == "Linux" ]]
    command -v nohup >/dev/null
    command -v grep >/dev/null
    printf '{"checks_passed":3,"checks_total":3,"status":"passed"}\n'
    ;;
  --launch)
    required_env
    umask 077
    safe_target "$OPENLOCUS_B24_PID"
    safe_target "$OPENLOCUS_B24_LOG"
    safe_target "$OPENLOCUS_B24_EXIT"
    if [[ -f "$OPENLOCUS_B24_PID" ]]; then
      existing_pid="$(tr -cd '0-9' <"$OPENLOCUS_B24_PID")"
      if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
        printf 'B2.4 worker is already running\n' >&2
        exit 1
      fi
    fi
    if [[ -e "$OPENLOCUS_B24_EXIT" ]]; then
      printf 'B2.4 exit receipt already exists\n' >&2
      exit 1
    fi
    : >"$OPENLOCUS_B24_LOG"
    chmod 600 "$OPENLOCUS_B24_LOG"
    nohup "$0" --worker >>"$OPENLOCUS_B24_LOG" 2>&1 &
    worker_pid=$!
    pid_tmp="${OPENLOCUS_B24_PID}.tmp.$$"
    printf '%s\n' "$worker_pid" >"$pid_tmp"
    mv "$pid_tmp" "$OPENLOCUS_B24_PID"
    printf '{"launched":true,"private_paths_printed":false}\n'
    ;;
  --status)
    required_env
    state="not_started"
    progress="none"
    exit_code="none"
    if [[ -f "$OPENLOCUS_B24_PID" ]]; then
      worker_pid="$(tr -cd '0-9' <"$OPENLOCUS_B24_PID")"
      if [[ -n "$worker_pid" ]] && kill -0 "$worker_pid" 2>/dev/null; then
        state="running"
      else
        state="stopped"
      fi
    fi
    if [[ -f "$OPENLOCUS_B24_EXIT" ]]; then
      exit_code="$(tr -cd '0-9' <"$OPENLOCUS_B24_EXIT")"
      if [[ "$exit_code" == "0" ]]; then
        state="completed_success"
      else
        state="completed_failed_closed"
      fi
    fi
    if [[ -f "$OPENLOCUS_B24_LOG" ]]; then
      progress="$(grep -E 'B2\.1 group [0-9]+/[0-9]+ complete; logical_records=[0-9]+' "$OPENLOCUS_B24_LOG" | tail -n 1 || true)"
      if [[ -z "$progress" ]]; then
        progress="none"
      fi
    fi
    printf '{"state":"%s","progress":"%s","exit_code":"%s"}\n' \
      "$state" "$progress" "$exit_code"
    ;;
  --worker)
    run_worker
    ;;
  *)
    printf 'usage: %s --self-test|--launch|--status\n' "$0" >&2
    exit 2
    ;;
esac
