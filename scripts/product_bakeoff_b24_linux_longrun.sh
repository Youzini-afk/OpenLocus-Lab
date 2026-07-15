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

resolved_self() {
  local script_dir
  script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
  printf '%s/%s\n' "$script_dir" "$(basename -- "$0")"
}

write_private_receipt() {
  local path="$1"
  local value="$2"
  local temporary="${path}.tmp.$$"
  safe_target "$path"
  printf '%s\n' "$value" >"$temporary"
  chmod 600 "$temporary"
  mv "$temporary" "$path"
}

wait_for_gate() {
  local worker_pid="$1"
  local gate_path="$2"
  local attempts="$3"
  local attempt
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if [[ -s "$gate_path" ]]; then
      return 0
    fi
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" 2>/dev/null || true
      return 1
    fi
    sleep 0.25
  done
  return 1
}

stop_prelaunch_worker() {
  local worker_pid="$1"
  if kill -0 "$worker_pid" 2>/dev/null; then
    kill "$worker_pid" 2>/dev/null || true
  fi
  wait "$worker_pid" 2>/dev/null || true
}

run_worker() {
  required_env
  umask 077
  cd "$OPENLOCUS_B24_CHECKOUT"
  ulimit -n 65535
  safe_target "$OPENLOCUS_B24_LOG"
  safe_target "$OPENLOCUS_B24_EXIT"
  worker_started="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_worker_started.json"
  safe_target "$worker_started"
  if [[ -e "$worker_started" ]]; then
    printf 'B2.4 worker-start receipt already exists\n' >&2
    return 1
  fi
  write_private_receipt \
    "$worker_started" \
    '{"schema_version":"product_bakeoff_b24_private_worker_started.v1","worker_entered":true}'
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

run_handshake_probe_worker() {
  local worker_started="${2:-}"
  local runner_admission="${3:-}"
  local launch_release="${4:-}"
  local completed="${5:-}"
  if [[ -z "$worker_started" || -z "$runner_admission" || -z "$launch_release" || -z "$completed" ]]; then
    return 2
  fi
  umask 077
  write_private_receipt "$worker_started" '{"worker_entered":true}'
  sleep 0.1
  write_private_receipt "$runner_admission" '{"runner_admitted":true}'
  local attempt
  for ((attempt = 0; attempt < 80; attempt++)); do
    if [[ -s "$launch_release" ]]; then
      write_private_receipt "$completed" '{"release_consumed":true}'
      return 0
    fi
    sleep 0.05
  done
  return 1
}

case "$mode" in
  --self-test)
    [[ "$(uname -s)" == "Linux" ]]
    command -v nohup >/dev/null
    command -v grep >/dev/null
    script_path="$(resolved_self)"
    [[ -r "$script_path" ]]
    [[ ! -x "$script_path" ]]
    probe_root="$(mktemp -d)"
    probe_pid=""
    cleanup_probe() {
      if [[ -n "${probe_pid:-}" ]] && kill -0 "$probe_pid" 2>/dev/null; then
        kill "$probe_pid" 2>/dev/null || true
        wait "$probe_pid" 2>/dev/null || true
      fi
      rm -rf "$probe_root"
    }
    trap cleanup_probe EXIT
    probe_started="$probe_root/started.json"
    probe_admission="$probe_root/admission.json"
    probe_release="$probe_root/release.json"
    probe_completed="$probe_root/completed.json"
    nohup bash "$script_path" \
      --handshake-probe-worker \
      "$probe_started" \
      "$probe_admission" \
      "$probe_release" \
      "$probe_completed" \
      >"$probe_root/probe.log" 2>&1 &
    probe_pid=$!
    wait_for_gate "$probe_pid" "$probe_started" 80
    wait_for_gate "$probe_pid" "$probe_admission" 80
    write_private_receipt \
      "$probe_release" \
      '{"readiness_checkpoint":"0000000000000000000000000000000000000000","release":true,"schema_version":"product_bakeoff_b24_private_launch_release.v1","tournament_attempt_number":1}'
    wait "$probe_pid"
    probe_pid=""
    [[ -s "$probe_completed" ]]
    cleanup_probe
    trap - EXIT
    printf '{"checks_passed":8,"checks_total":8,"status":"passed"}\n'
    ;;
  --launch)
    required_env
    umask 077
    worker_started="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_worker_started.json"
    runner_admission="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_runner_admission.json"
    launch_release="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_launch_release.json"
    for target in \
      "$OPENLOCUS_B24_PID" \
      "$OPENLOCUS_B24_LOG" \
      "$OPENLOCUS_B24_EXIT" \
      "$worker_started" \
      "$runner_admission" \
      "$launch_release" \
      "$OPENLOCUS_B24_RUNS_DIR" \
      "$OPENLOCUS_B24_PUBLIC_OUT"
    do
      safe_target "$target"
      if [[ -e "$target" ]]; then
        printf 'B2.4 launch target already exists\n' >&2
        exit 1
      fi
    done
    : >"$OPENLOCUS_B24_LOG"
    chmod 600 "$OPENLOCUS_B24_LOG"
    script_path="$(resolved_self)"
    nohup bash "$script_path" --worker >>"$OPENLOCUS_B24_LOG" 2>&1 &
    worker_pid=$!
    pid_tmp="${OPENLOCUS_B24_PID}.tmp.$$"
    printf '%s\n' "$worker_pid" >"$pid_tmp"
    mv "$pid_tmp" "$OPENLOCUS_B24_PID"
    if ! wait_for_gate "$worker_pid" "$worker_started" 80; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B2.4 worker did not enter before the launch boundary\n' >&2
      exit 1
    fi
    if ! wait_for_gate "$worker_pid" "$runner_admission" 480; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B2.4 runner admission did not pass before the launch boundary\n' >&2
      exit 1
    fi
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" 2>/dev/null || true
      printf 'B2.4 worker stopped before the launch boundary\n' >&2
      exit 1
    fi
    readiness_checkpoint="$(git -C "$OPENLOCUS_B24_CHECKOUT" rev-parse HEAD)"
    if [[ ! "$readiness_checkpoint" =~ ^[0-9a-f]{40}$ ]]; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B2.4 readiness checkpoint could not be verified\n' >&2
      exit 1
    fi
    release_json="$(printf \
      '{"readiness_checkpoint":"%s","release":true,"schema_version":"product_bakeoff_b24_private_launch_release.v1","tournament_attempt_number":1}' \
      "$readiness_checkpoint")"
    write_private_receipt "$launch_release" "$release_json"
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" 2>/dev/null || true
      printf 'B2.4 worker stopped after the launch boundary\n' >&2
      exit 1
    fi
    printf '{"attempt_boundary_crossed":true,"launched":true,"private_paths_printed":false,"runner_admitted":true,"worker_entered":true}\n'
    ;;
  --status)
    required_env
    state="not_started"
    progress="none"
    exit_code="none"
    worker_entered=false
    runner_admitted=false
    attempt_boundary_crossed=false
    worker_started="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_worker_started.json"
    runner_admission="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_runner_admission.json"
    launch_release="$OPENLOCUS_B24_PRIVATE_ROOT/b24_private_launch_release.json"
    [[ -s "$worker_started" ]] && worker_entered=true
    [[ -s "$runner_admission" ]] && runner_admitted=true
    [[ -s "$launch_release" ]] && attempt_boundary_crossed=true
    if [[ -f "$OPENLOCUS_B24_PID" ]]; then
      worker_pid="$(tr -cd '0-9' <"$OPENLOCUS_B24_PID")"
      if [[ -n "$worker_pid" ]] && kill -0 "$worker_pid" 2>/dev/null; then
        if [[ "$attempt_boundary_crossed" == true ]]; then
          state="running"
        elif [[ "$runner_admitted" == true ]]; then
          state="admitted_waiting_release"
        elif [[ "$worker_entered" == true ]]; then
          state="prelaunch_validating"
        else
          state="starting"
        fi
      else
        if [[ "$attempt_boundary_crossed" == true ]]; then
          state="stopped_after_attempt_boundary"
        else
          state="prelaunch_stopped_no_attempt"
        fi
      fi
    fi
    if [[ -f "$OPENLOCUS_B24_EXIT" ]]; then
      exit_code="$(tr -cd '0-9' <"$OPENLOCUS_B24_EXIT")"
      if [[ "$exit_code" == "0" ]]; then
        state="completed_success"
      elif [[ "$attempt_boundary_crossed" == true ]]; then
        state="completed_failed_closed"
      else
        state="prelaunch_failed_no_attempt"
      fi
    fi
    if [[ -f "$OPENLOCUS_B24_LOG" ]]; then
      progress="$(grep -E 'B2\.1 group [0-9]+/[0-9]+ complete; logical_records=[0-9]+' "$OPENLOCUS_B24_LOG" | tail -n 1 || true)"
      if [[ -z "$progress" ]]; then
        progress="none"
      fi
    fi
    printf '{"attempt_boundary_crossed":%s,"exit_code":"%s","progress":"%s","runner_admitted":%s,"state":"%s","worker_entered":%s}\n' \
      "$attempt_boundary_crossed" \
      "$exit_code" \
      "$progress" \
      "$runner_admitted" \
      "$state" \
      "$worker_entered"
    ;;
  --worker)
    run_worker
    ;;
  --handshake-probe-worker)
    run_handshake_probe_worker "$@"
    ;;
  *)
    printf 'usage: %s --self-test|--launch|--status\n' "$0" >&2
    exit 2
    ;;
esac
