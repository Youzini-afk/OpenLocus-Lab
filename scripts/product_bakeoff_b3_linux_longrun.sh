#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd -- "$REPO_ROOT"

required_run_env() {
  local name
  for name in \
    OPENLOCUS_B3_PRIVATE_ROOT \
    OPENLOCUS_B3_CANDIDATE_PLAN \
    OPENLOCUS_B3_HISTORY_B2 \
    OPENLOCUS_B3_HISTORY_B21 \
    OPENLOCUS_B3_HISTORY_B24 \
    OPENLOCUS_B3_HISTORY_B25 \
    OPENLOCUS_B3_EXCLUSION_REGISTRY \
    OPENLOCUS_B3_RUNTIME_PUBLIC \
    OPENLOCUS_B3_RUNTIME_PRIVATE \
    OPENLOCUS_B3_RUNTIME_SCRATCH \
    OPENLOCUS_B3_RUNTIME_PUBLICATION_CHECKPOINT \
    OPENLOCUS_B3_RUNTIME_PUBLICATION_CI_RUN_ID \
    OPENLOCUS_B3_READINESS \
    OPENLOCUS_B3_READINESS_CHECKPOINT \
    OPENLOCUS_B3_RUNS_DIR \
    OPENLOCUS_B3_PUBLIC_OUT \
    OPENLOCUS_B3_CLI \
    OPENLOCUS_B3_LOG \
    OPENLOCUS_B3_PID \
    OPENLOCUS_B3_EXIT; do
    if [[ -z "${!name:-}" ]]; then
      printf 'missing required B3 environment variable: %s\n' "$name" >&2
      return 1
    fi
  done
}

required_status_env() {
  local name
  for name in \
    OPENLOCUS_B3_PRIVATE_ROOT \
    OPENLOCUS_B3_RUNS_DIR \
    OPENLOCUS_B3_PUBLIC_OUT \
    OPENLOCUS_B3_PID \
    OPENLOCUS_B3_EXIT; do
    if [[ -z "${!name:-}" ]]; then
      printf 'missing required B3 status environment variable: %s\n' "$name" >&2
      return 1
    fi
  done
}

resolved_self() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=True))
PY
}

write_json_exclusive() {
  local target="$1"
  local payload="$2"
  python3 - "$target" "$payload" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

target = Path(sys.argv[1])
value = json.loads(sys.argv[2])
target.parent.mkdir(parents=True, exist_ok=True)
parent = target.parent.resolve(strict=True)
resolved = parent / target.name
if os.path.lexists(resolved):
    raise SystemExit("private B3 control receipt already exists")
fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
temporary = Path(raw)
try:
    with os.fdopen(fd, "wb") as handle:
        handle.write((json.dumps(value, sort_keys=True) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    if os.path.lexists(resolved):
        raise SystemExit("private B3 control receipt appeared concurrently")
    os.replace(temporary, resolved)
    directory = os.open(parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
finally:
    if temporary.exists():
        temporary.unlink()
PY
}

wait_for_gate() {
  local worker_pid="$1"
  local target="$2"
  local attempts="$3"
  local attempt
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if [[ -s "$target" ]]; then
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

write_pid_identity() {
  local target="$1"
  local pid="$2"
  python3 - "$target" "$pid" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

target = Path(sys.argv[1])
pid = int(sys.argv[2])
boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
right = stat.rsplit(")", 1)[1].strip().split()
start_ticks = int(right[19])
value = {
    "schema_version": "product_bakeoff_b3_private_worker_pid_identity.v1",
    "pid": pid,
    "boot_id": boot_id,
    "process_start_ticks": start_ticks,
}
target.parent.mkdir(parents=True, exist_ok=True)
parent = target.parent.resolve(strict=True)
resolved = parent / target.name
if os.path.lexists(resolved):
    raise SystemExit("B3 PID identity already exists")
fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
temporary = Path(raw)
try:
    with os.fdopen(fd, "wb") as handle:
        handle.write((json.dumps(value, sort_keys=True) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, resolved)
finally:
    if temporary.exists():
        temporary.unlink()
PY
}

pid_identity_state() {
  local target="$1"
  python3 - "$target" <<'PY'
import json
from pathlib import Path
import sys

try:
    value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if value.get("schema_version") != "product_bakeoff_b3_private_worker_pid_identity.v1":
        raise KeyError
    pid = int(value["pid"])
    boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
except (OSError, ValueError, KeyError, json.JSONDecodeError):
    print("invalid")
    raise SystemExit(0)
if boot != value["boot_id"]:
    print("not_alive")
    raise SystemExit(0)
try:
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    right = stat.rsplit(")", 1)[1].strip().split()
    same_start = int(right[19]) == int(value["process_start_ticks"])
except (OSError, ValueError, IndexError):
    print("not_alive")
    raise SystemExit(0)
print("alive" if same_start else "not_alive")
PY
}

pid_identity_alive() {
  [[ "$(pid_identity_state "$1")" == "alive" ]]
}

run_worker() {
  required_run_env
  local worker_started="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_worker_started.json"
  write_json_exclusive \
    "$worker_started" \
    '{"schema_version":"product_bakeoff_b3_private_worker_started.v1","worker_entered":true}'
  local keep=()
  if [[ "${OPENLOCUS_B3_KEEP_WORKTREES:-0}" == "1" ]]; then
    keep=(--keep-worktrees)
  fi
  set +e
  python3 eval/product_bakeoff_b3_cli.py run \
    --private-root "$OPENLOCUS_B3_PRIVATE_ROOT" \
    --candidate-plan "$OPENLOCUS_B3_CANDIDATE_PLAN" \
    --history-b2 "$OPENLOCUS_B3_HISTORY_B2" \
    --history-b21 "$OPENLOCUS_B3_HISTORY_B21" \
    --history-b24 "$OPENLOCUS_B3_HISTORY_B24" \
    --history-b25 "$OPENLOCUS_B3_HISTORY_B25" \
    --exclusion-registry "$OPENLOCUS_B3_EXCLUSION_REGISTRY" \
    --runtime-public "$OPENLOCUS_B3_RUNTIME_PUBLIC" \
    --runtime-private "$OPENLOCUS_B3_RUNTIME_PRIVATE" \
    --runtime-scratch "$OPENLOCUS_B3_RUNTIME_SCRATCH" \
    --runtime-publication-checkpoint "$OPENLOCUS_B3_RUNTIME_PUBLICATION_CHECKPOINT" \
    --runtime-publication-ci-run-id "$OPENLOCUS_B3_RUNTIME_PUBLICATION_CI_RUN_ID" \
    --runtime-publication-ci-conclusion success \
    --cli "$OPENLOCUS_B3_CLI" \
    --readiness "$OPENLOCUS_B3_READINESS" \
    --runs-dir "$OPENLOCUS_B3_RUNS_DIR" \
    --public-out "$OPENLOCUS_B3_PUBLIC_OUT" \
    "${keep[@]}"
  local code=$?
  set -e
  local temporary="$OPENLOCUS_B3_EXIT.tmp.$$"
  printf '%s\n' "$code" >"$temporary"
  mv -f -- "$temporary" "$OPENLOCUS_B3_EXIT"
  return "$code"
}

run_handshake_probe_worker() {
  local worker_started="$2"
  local admission="$3"
  local release="$4"
  local boundary="$5"
  local completed="$6"
  write_json_exclusive "$worker_started" '{"worker_entered":true}'
  write_json_exclusive "$admission" '{"runner_admitted":true,"zero_observation":true}'
  local attempt
  for ((attempt = 0; attempt < 80; attempt++)); do
    if [[ -s "$release" ]]; then
      sleep 1
      mkdir -p -- "$(dirname "$boundary")/cells"
      printf '{}\n' >"$(dirname "$boundary")/cells/s0__probe.json"
      write_json_exclusive "$boundary" '{"attempt_boundary_crossed":true,"first_durable_observation":true}'
      write_json_exclusive "$completed" '{"completed":true}'
      return 0
    fi
    sleep 0.1
  done
  return 1
}

mode="${1:-}"
case "$mode" in
  --self-test)
    command -v python3 >/dev/null
    command -v nohup >/dev/null
    command -v find >/dev/null
    probe_root="$(mktemp -d)"
    trap 'rm -rf -- "$probe_root"' EXIT
    script_path="$(resolved_self "$0")"
    probe_worker="$probe_root/worker.json"
    probe_admission="$probe_root/admission.json"
    probe_release="$probe_root/release.json"
    probe_boundary="$probe_root/runs/private/boundary.json"
    probe_completed="$probe_root/completed.json"
    nohup bash "$script_path" \
      --handshake-probe-worker \
      "$probe_worker" \
      "$probe_admission" \
      "$probe_release" \
      "$probe_boundary" \
      "$probe_completed" \
      >"$probe_root/probe.log" 2>&1 &
    probe_pid=$!
    wait_for_gate "$probe_pid" "$probe_worker" 80
    wait_for_gate "$probe_pid" "$probe_admission" 80
    [[ ! -e "$probe_boundary" ]]
    write_json_exclusive "$probe_release" '{"release":true,"launch_release_alone_consumes_attempt":false}'
    [[ ! -e "$probe_boundary" ]]
    wait_for_gate "$probe_pid" "$probe_boundary" 80
    wait_for_gate "$probe_pid" "$probe_completed" 80
    wait "$probe_pid"
    [[ -s "$(dirname "$probe_boundary")/cells/s0__probe.json" ]]
    probe_pid_identity="$probe_root/pid.json"
    write_pid_identity "$probe_pid_identity" "$$"
    pid_identity_alive "$probe_pid_identity"
    python3 - "$probe_pid_identity" <<'PY'
import json
from pathlib import Path
import sys
path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
value["boot_id"] = "00000000-0000-0000-0000-000000000000"
path.write_text(json.dumps(value) + "\n", encoding="utf-8")
PY
    if pid_identity_alive "$probe_pid_identity"; then
      printf 'B3 PID identity accepted a boot-id mismatch\n' >&2
      exit 1
    fi
    [[ "$(pid_identity_state "$probe_pid_identity")" == "not_alive" ]]
    printf '{"checks_passed":13,"checks_total":13,"status":"passed"}\n'
    ;;
  --launch)
    required_run_env
    script_path="$(resolved_self "$0")"
    worker_started="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_worker_started.json"
    admission="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_runner_admission.json"
    release="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_launch_release.json"
    boundary="$OPENLOCUS_B3_RUNS_DIR/private/b3_private_attempt_boundary.json"
    for target in \
      "$worker_started" \
      "$admission" \
      "$release" \
      "$boundary" \
      "$OPENLOCUS_B3_PID" \
      "$OPENLOCUS_B3_EXIT" \
      "$OPENLOCUS_B3_PUBLIC_OUT"; do
      if [[ -e "$target" || -L "$target" ]]; then
        printf 'B3 launch target already exists; fail closed\n' >&2
        exit 1
      fi
    done
    mkdir -p -- "$(dirname "$OPENLOCUS_B3_LOG")" "$(dirname "$OPENLOCUS_B3_PID")"
    nohup bash "$script_path" --worker >>"$OPENLOCUS_B3_LOG" 2>&1 &
    worker_pid=$!
    if ! write_pid_identity "$OPENLOCUS_B3_PID" "$worker_pid"; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B3 worker PID identity could not be frozen; no attempt consumed\n' >&2
      exit 1
    fi
    if ! wait_for_gate "$worker_pid" "$worker_started" 80; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B3 worker did not enter; no attempt consumed\n' >&2
      exit 1
    fi
    if ! wait_for_gate "$worker_pid" "$admission" 480; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B3 runner admission did not pass; no attempt consumed\n' >&2
      exit 1
    fi
    if [[ -e "$boundary" ]]; then
      stop_prelaunch_worker "$worker_pid"
      printf 'B3 attempt boundary appeared before release\n' >&2
      exit 1
    fi
    authorization_digest="$(python3 - "$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_launch_authorization.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle)
print(value["launch_authorization_digest"])
PY
)"
    release_json="$(printf \
      '{"launch_authorization_digest":"%s","launch_release_alone_consumes_attempt":false,"readiness_checkpoint":"%s","release":true,"schema_version":"product_bakeoff_b3_private_launch_release.v1","tournament_attempt_number":1}' \
      "$authorization_digest" \
      "$OPENLOCUS_B3_READINESS_CHECKPOINT")"
    write_json_exclusive "$release" "$release_json"
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" 2>/dev/null || true
      printf 'B3 worker stopped immediately after release; inspect safe status\n' >&2
      exit 1
    fi
    printf '{"attempt_boundary_crossed":false,"launch_release_issued":true,"launched":true,"private_paths_printed":false,"runner_admitted":true,"worker_entered":true}\n'
    ;;
  --status)
    required_status_env
    worker_entered=false
    runner_admitted=false
    launch_released=false
    boundary_receipt=false
    worker_alive=false
    worker_identity_state="absent"
    worker_started="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_worker_started.json"
    admission="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_runner_admission.json"
    release="$OPENLOCUS_B3_PRIVATE_ROOT/b3_private_launch_release.json"
    boundary="$OPENLOCUS_B3_RUNS_DIR/private/b3_private_attempt_boundary.json"
    [[ -s "$worker_started" ]] && worker_entered=true
    [[ -s "$admission" ]] && runner_admitted=true
    [[ -s "$release" ]] && launch_released=true
    [[ -s "$boundary" ]] && boundary_receipt=true
    logical_records=0
    if [[ -d "$OPENLOCUS_B3_RUNS_DIR/private/cells" ]]; then
      normal_count="$(find "$OPENLOCUS_B3_RUNS_DIR/private/cells" -maxdepth 1 -type f -name '*.json' | wc -l)"
      logical_records=$((logical_records + normal_count))
    fi
    if [[ -d "$OPENLOCUS_B3_RUNS_DIR/private/terminal_support" ]]; then
      terminal_count="$(find "$OPENLOCUS_B3_RUNS_DIR/private/terminal_support" -maxdepth 1 -type f -name '*.json' | wc -l)"
      logical_records=$((logical_records + terminal_count))
    fi
    attempt_boundary_crossed=false
    if [[ "$boundary_receipt" == true || "$logical_records" -gt 0 ]]; then
      attempt_boundary_crossed=true
    fi
    exit_code=""
    if [[ -s "$OPENLOCUS_B3_PID" ]]; then
      worker_identity_state="$(pid_identity_state "$OPENLOCUS_B3_PID")"
      if [[ "$worker_identity_state" == "alive" ]]; then
        worker_alive=true
      fi
    fi
    if [[ -s "$OPENLOCUS_B3_EXIT" ]]; then
      exit_code="$(tr -cd '0-9-' <"$OPENLOCUS_B3_EXIT")"
    fi
    completed_groups=$((logical_records / 30))
    if [[ -s "$OPENLOCUS_B3_PUBLIC_OUT" ]]; then
      state="public_closeout_ready"
    elif [[ "$worker_alive" == true && "$attempt_boundary_crossed" == true ]]; then
      state="running_after_attempt_boundary"
    elif [[ "$worker_alive" == true && "$launch_released" == true ]]; then
      state="released_waiting_first_durable_observation"
    elif [[ "$worker_alive" == true && "$runner_admitted" == true ]]; then
      state="admitted_waiting_release"
    elif [[ "$worker_alive" == true ]]; then
      state="prelaunch_validating"
    elif [[ "$worker_identity_state" == "invalid" ]]; then
      state="worker_identity_invalid_manual_review"
    elif [[ "$attempt_boundary_crossed" == true ]]; then
      state="stopped_after_attempt_boundary"
    elif [[ -n "$exit_code" ]]; then
      state="preboundary_stopped_no_attempt"
    else
      state="not_started"
    fi
    printf '{"attempt_boundary_crossed":%s,"completed_group_count":%s,"exit_code":"%s","launch_release_issued":%s,"logical_record_count":%s,"runner_admitted":%s,"state":"%s","worker_alive":%s,"worker_entered":%s,"worker_identity_state":"%s"}\n' \
      "$attempt_boundary_crossed" \
      "$completed_groups" \
      "$exit_code" \
      "$launch_released" \
      "$logical_records" \
      "$runner_admitted" \
      "$state" \
      "$worker_alive" \
      "$worker_entered" \
      "$worker_identity_state"
    ;;
  --closeout-interrupted)
    required_status_env
    identity_state="absent"
    if [[ -s "$OPENLOCUS_B3_PID" ]]; then
      identity_state="$(pid_identity_state "$OPENLOCUS_B3_PID")"
    fi
    if [[ "$identity_state" == "alive" ]]; then
      printf 'B3 worker is still alive; interrupted closeout forbidden\n' >&2
      exit 1
    fi
    confirm=()
    if [[ "$identity_state" == "invalid" || "$identity_state" == "absent" ]]; then
      if [[ "${OPENLOCUS_B3_CONFIRM_WORKER_STOPPED:-}" != "YES" ]]; then
        printf 'B3 worker identity is not trustworthy; explicit stopped confirmation required\n' >&2
        exit 1
      fi
      confirm=(--confirm-worker-stopped)
    fi
    if [[ -s "$OPENLOCUS_B3_EXIT" ]]; then
      exit_code="$(tr -cd '0-9-' <"$OPENLOCUS_B3_EXIT")"
    else
      exit_code=255
    fi
    python3 eval/product_bakeoff_b3_cli.py closeout-interrupted \
      --private-root "$OPENLOCUS_B3_PRIVATE_ROOT" \
      --runs-dir "$OPENLOCUS_B3_RUNS_DIR" \
      --public-out "$OPENLOCUS_B3_PUBLIC_OUT" \
      --worker-exit-code "$exit_code" \
      --worker-pid-identity "$OPENLOCUS_B3_PID" \
      "${confirm[@]}"
    ;;
  --audit-preboundary)
    if [[ -z "${OPENLOCUS_B3_RUNS_DIR:-}" ]]; then
      printf 'missing required B3 audit environment variable: OPENLOCUS_B3_RUNS_DIR\n' >&2
      exit 1
    fi
    python3 eval/product_bakeoff_b3_cli.py audit-preboundary \
      --runs-dir "$OPENLOCUS_B3_RUNS_DIR"
    ;;
  --worker)
    run_worker
    ;;
  --handshake-probe-worker)
    run_handshake_probe_worker "$@"
    ;;
  *)
    printf 'usage: %s --self-test|--launch|--status|--closeout-interrupted|--audit-preboundary\n' "$0" >&2
    exit 2
    ;;
esac
