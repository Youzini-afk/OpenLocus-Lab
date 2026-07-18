#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd -- "$REPO_ROOT"

required_run_env() {
  local name
  for name in \
    OPENLOCUS_B4_PRIVATE_ROOT \
    OPENLOCUS_B4_CANDIDATE_CATALOG \
    OPENLOCUS_B4_HISTORY_B2 \
    OPENLOCUS_B4_HISTORY_B21 \
    OPENLOCUS_B4_HISTORY_B24 \
    OPENLOCUS_B4_HISTORY_B25 \
    OPENLOCUS_B4_HISTORY_B3 \
    OPENLOCUS_B4_EXCLUSION_REGISTRY \
    OPENLOCUS_B4_RUNTIME_PUBLIC \
    OPENLOCUS_B4_RUNTIME_PRIVATE \
    OPENLOCUS_B4_RUNTIME_SCRATCH \
    OPENLOCUS_B4_RUNTIME_PUBLICATION_CHECKPOINT \
    OPENLOCUS_B4_RUNTIME_PUBLICATION_CI_RUN_ID \
    OPENLOCUS_B4_READINESS \
    OPENLOCUS_B4_READINESS_CHECKPOINT \
    OPENLOCUS_B4_RUNS_DIR \
    OPENLOCUS_B4_PUBLIC_OUT \
    OPENLOCUS_B4_CLI \
    OPENLOCUS_B4_LOG \
    OPENLOCUS_B4_PID \
    OPENLOCUS_B4_EXIT; do
    if [[ -z "${!name:-}" ]]; then
      printf 'missing required B4 environment variable: %s\n' "$name" >&2
      return 1
    fi
  done
}

required_status_env() {
  local name
  for name in \
    OPENLOCUS_B4_PRIVATE_ROOT \
    OPENLOCUS_B4_RUNS_DIR \
    OPENLOCUS_B4_PUBLIC_OUT \
    OPENLOCUS_B4_PID \
    OPENLOCUS_B4_EXIT; do
    if [[ -z "${!name:-}" ]]; then
      printf 'missing required B4 status environment variable: %s\n' "$name" >&2
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
    raise SystemExit("private B4 control receipt already exists")
fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
temporary = Path(raw)
try:
    with os.fdopen(fd, "wb") as handle:
        handle.write((json.dumps(value, sort_keys=True) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    if os.path.lexists(resolved):
        raise SystemExit("private B4 control receipt appeared concurrently")
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
value = {
    "schema_version": "product_bakeoff_b4_private_worker_pid_identity.v1",
    "pid": pid,
    "boot_id": boot_id,
    "process_start_ticks": int(right[19]),
}
target.parent.mkdir(parents=True, exist_ok=True)
parent = target.parent.resolve(strict=True)
if os.path.lexists(target):
    raise SystemExit("B4 PID identity already exists")
fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
temporary = Path(raw)
try:
    with os.fdopen(fd, "wb") as handle:
        handle.write((json.dumps(value, sort_keys=True) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, target)
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

pid_identity_state() {
  local target="$1"
  python3 - "$target" <<'PY'
import json
from pathlib import Path
import sys

try:
    value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if value.get("schema_version") != "product_bakeoff_b4_private_worker_pid_identity.v1":
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

stop_prelaunch_worker() {
  local worker_pid="$1"
  if kill -0 "$worker_pid" 2>/dev/null; then
    kill -TERM -- "-$worker_pid" 2>/dev/null || true
    local attempt
    for ((attempt = 0; attempt < 40; attempt++)); do
      if ! kill -0 -- "-$worker_pid" 2>/dev/null; then
        break
      fi
      sleep 0.1
    done
    if kill -0 -- "-$worker_pid" 2>/dev/null; then
      kill -KILL -- "-$worker_pid" 2>/dev/null || true
    fi
  fi
  wait "$worker_pid" 2>/dev/null || true
}

remove_regular_file_if_present() {
  local target="$1"
  python3 - "$target" <<'PY'
import os
from pathlib import Path
import sys

path = Path(sys.argv[1])
if not os.path.lexists(path):
    raise SystemExit(0)
if path.is_symlink() or not path.is_file():
    raise SystemExit("B4 pre-boundary shell receipt is unsafe")
path.unlink()
PY
}

reset_prelaunch_state() {
  local started="$1"
  python3 eval/product_bakeoff_b4_cli.py reset-preboundary \
    --private-root "$OPENLOCUS_B4_PRIVATE_ROOT" \
    --runs-dir "$OPENLOCUS_B4_RUNS_DIR" \
    --public-out "$OPENLOCUS_B4_PUBLIC_OUT" \
    --confirm-worker-stopped >>"$OPENLOCUS_B4_LOG" 2>&1
  remove_regular_file_if_present "$started"
  remove_regular_file_if_present "$OPENLOCUS_B4_PID"
  remove_regular_file_if_present "$OPENLOCUS_B4_EXIT"
}

run_worker() {
  required_run_env
  write_json_exclusive \
    "$OPENLOCUS_B4_PRIVATE_ROOT/b4_private_worker_started.json" \
    '{"schema_version":"product_bakeoff_b4_private_worker_started.v1","worker_entered":true}'
  local keep=()
  if [[ "${OPENLOCUS_B4_KEEP_WORKTREES:-0}" == "1" ]]; then
    keep=(--keep-worktrees)
  fi
  set +e
  OPENLOCUS_CLI="$OPENLOCUS_B4_CLI" \
  python3 eval/product_bakeoff_b4_cli.py run \
    --private-root "$OPENLOCUS_B4_PRIVATE_ROOT" \
    --candidate-catalog "$OPENLOCUS_B4_CANDIDATE_CATALOG" \
    --history-b2 "$OPENLOCUS_B4_HISTORY_B2" \
    --history-b21 "$OPENLOCUS_B4_HISTORY_B21" \
    --history-b24 "$OPENLOCUS_B4_HISTORY_B24" \
    --history-b25 "$OPENLOCUS_B4_HISTORY_B25" \
    --history-b3 "$OPENLOCUS_B4_HISTORY_B3" \
    --exclusion-registry "$OPENLOCUS_B4_EXCLUSION_REGISTRY" \
    --runtime-public "$OPENLOCUS_B4_RUNTIME_PUBLIC" \
    --runtime-private "$OPENLOCUS_B4_RUNTIME_PRIVATE" \
    --runtime-scratch "$OPENLOCUS_B4_RUNTIME_SCRATCH" \
    --runtime-publication-checkpoint "$OPENLOCUS_B4_RUNTIME_PUBLICATION_CHECKPOINT" \
    --runtime-publication-ci-run-id "$OPENLOCUS_B4_RUNTIME_PUBLICATION_CI_RUN_ID" \
    --runtime-publication-ci-conclusion success \
    --cli "$OPENLOCUS_B4_CLI" \
    --readiness "$OPENLOCUS_B4_READINESS" \
    --runs-dir "$OPENLOCUS_B4_RUNS_DIR" \
    --public-out "$OPENLOCUS_B4_PUBLIC_OUT" \
    "${keep[@]}"
  local code=$?
  set -e
  local temporary="$OPENLOCUS_B4_EXIT.tmp.$$"
  printf '%s\n' "$code" >"$temporary"
  mv -f -- "$temporary" "$OPENLOCUS_B4_EXIT"
  return "$code"
}

run_handshake_probe_worker() {
  local started="$2"
  local admission="$3"
  local release="$4"
  local boundary="$5"
  local completed="$6"
  write_json_exclusive "$started" '{"worker_entered":true}'
  write_json_exclusive "$admission" '{"runner_admitted":true,"zero_treatment_observations":true}'
  local attempt
  for ((attempt = 0; attempt < 80; attempt++)); do
    if [[ -s "$release" ]]; then
      mkdir -p -- "$(dirname "$boundary")"
      write_json_exclusive "$boundary" '{"attempt_boundary_crossed":true}'
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
    command -v setsid >/dev/null
    probe_root="$(mktemp -d)"
    trap 'rm -rf -- "$probe_root"' EXIT
    script_path="$(resolved_self "$0")"
    started="$probe_root/started.json"
    admission="$probe_root/admission.json"
    release="$probe_root/release.json"
    boundary="$probe_root/boundary.json"
    completed="$probe_root/completed.json"
    nohup bash "$script_path" --handshake-probe-worker \
      "$started" "$admission" "$release" "$boundary" "$completed" \
      >"$probe_root/probe.log" 2>&1 &
    probe_pid=$!
    wait_for_gate "$probe_pid" "$started" 80
    wait_for_gate "$probe_pid" "$admission" 80
    [[ ! -e "$boundary" ]]
    write_json_exclusive "$release" '{"release":true,"launch_release_alone_consumes_attempt":false}'
    wait_for_gate "$probe_pid" "$boundary" 80
    wait_for_gate "$probe_pid" "$completed" 80
    wait "$probe_pid"
    pid_file="$probe_root/pid.json"
    write_pid_identity "$pid_file" "$$"
    [[ "$(pid_identity_state "$pid_file")" == "alive" ]]
    printf '{"checks_passed":12,"checks_total":12,"status":"passed"}\n'
    ;;
  --launch)
    required_run_env
    script_path="$(resolved_self "$0")"
    started="$OPENLOCUS_B4_PRIVATE_ROOT/b4_private_worker_started.json"
    admission="$OPENLOCUS_B4_PRIVATE_ROOT/b4_private_runner_admission.json"
    release="$OPENLOCUS_B4_PRIVATE_ROOT/b4_private_launch_release.json"
    boundary="$OPENLOCUS_B4_RUNS_DIR/private/b4_private_attempt_boundary.json"
    for target in \
      "$started" "$admission" "$release" "$boundary" \
      "$OPENLOCUS_B4_PID" "$OPENLOCUS_B4_EXIT" "$OPENLOCUS_B4_PUBLIC_OUT"; do
      if [[ -e "$target" || -L "$target" ]]; then
        printf 'B4 launch target already exists; fail closed\n' >&2
        exit 1
      fi
    done
    mkdir -p -- "$(dirname "$OPENLOCUS_B4_LOG")" "$(dirname "$OPENLOCUS_B4_PID")"
    nohup setsid bash "$script_path" --worker >>"$OPENLOCUS_B4_LOG" 2>&1 &
    worker_pid=$!
    if ! write_pid_identity "$OPENLOCUS_B4_PID" "$worker_pid"; then
      stop_prelaunch_worker "$worker_pid"
      if ! reset_prelaunch_state "$started"; then
        printf 'B4 pre-boundary cleanup failed; user action required\n' >&2
        exit 1
      fi
      printf 'B4 worker PID identity could not be frozen; no attempt consumed\n' >&2
      exit 1
    fi
    if ! wait_for_gate "$worker_pid" "$started" 80; then
      stop_prelaunch_worker "$worker_pid"
      if ! reset_prelaunch_state "$started"; then
        printf 'B4 pre-boundary cleanup failed; user action required\n' >&2
        exit 1
      fi
      printf 'B4 worker did not enter; no attempt consumed\n' >&2
      exit 1
    fi
    if ! wait_for_gate "$worker_pid" "$admission" 2400; then
      stop_prelaunch_worker "$worker_pid"
      if ! reset_prelaunch_state "$started"; then
        printf 'B4 pre-boundary cleanup failed; user action required\n' >&2
        exit 1
      fi
      printf 'B4 runner admission did not pass; no attempt consumed\n' >&2
      exit 1
    fi
    [[ ! -e "$boundary" ]]
    release_json="$(python3 - \
      "$OPENLOCUS_B4_PRIVATE_ROOT/b4_private_launch_authorization.json" \
      "$OPENLOCUS_B4_READINESS_CHECKPOINT" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle)
if value["readiness_checkpoint"] != sys.argv[2]:
    raise SystemExit("B4 readiness checkpoint environment drifted")
print(json.dumps({
    "schema_version": "product_bakeoff_b4_private_launch_release.v1",
    "formal_attempt_number": 1,
    "readiness_checkpoint": value["readiness_checkpoint"],
    "launch_authorization_digest": value["launch_authorization_digest"],
    "release": True,
    "launch_release_alone_consumes_attempt": False,
}, sort_keys=True))
PY
)"
    write_json_exclusive "$release" "$release_json"
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" 2>/dev/null || true
      printf 'B4 worker stopped immediately after release; inspect safe status\n' >&2
      exit 1
    fi
    printf '{"attempt_boundary_crossed":false,"launch_release_issued":true,"launched":true,"private_paths_printed":false,"runner_admitted":true,"worker_entered":true}\n'
    ;;
  --status)
    required_status_env
    python3 - \
      "$OPENLOCUS_B4_PRIVATE_ROOT" \
      "$OPENLOCUS_B4_RUNS_DIR" \
      "$OPENLOCUS_B4_PUBLIC_OUT" \
      "$OPENLOCUS_B4_PID" \
      "$OPENLOCUS_B4_EXIT" <<'PY'
import json
from pathlib import Path
import sys
sys.path.insert(0, "eval")
import product_bakeoff_b4_control as control

private_root, runs_dir, public_out, pid_path, exit_path = map(Path, sys.argv[1:])
status = control.aggregate_status(
    private_root=private_root, runs_dir=runs_dir, public_closeout_path=public_out
)
identity = "absent"
alive = False
try:
    value = json.loads(pid_path.read_text(encoding="utf-8"))
    pid = int(value["pid"])
    boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    right = stat.rsplit(")", 1)[1].strip().split()
    alive = boot == value["boot_id"] and int(right[19]) == int(value["process_start_ticks"])
    identity = "alive" if alive else "not_alive"
except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError):
    if pid_path.exists():
        identity = "invalid"
exit_code = ""
if exit_path.is_file():
    exit_code = "".join(ch for ch in exit_path.read_text() if ch in "-0123456789")
status.update({"worker_alive": alive, "worker_identity_state": identity, "exit_code": exit_code})
print(json.dumps(status, sort_keys=True))
PY
    ;;
  --closeout-interrupted)
    required_status_env
    identity="absent"
    if [[ -s "$OPENLOCUS_B4_PID" ]]; then
      identity="$(pid_identity_state "$OPENLOCUS_B4_PID")"
    fi
    if [[ "$identity" == "alive" ]]; then
      printf 'B4 worker is still alive; interrupted closeout forbidden\n' >&2
      exit 1
    fi
    if [[ "${OPENLOCUS_B4_CONFIRM_WORKER_STOPPED:-}" != "YES" ]]; then
      printf 'B4 interrupted closeout requires explicit stopped confirmation\n' >&2
      exit 1
    fi
    python3 eval/product_bakeoff_b4_cli.py closeout-interrupted \
      --private-root "$OPENLOCUS_B4_PRIVATE_ROOT" \
      --runs-dir "$OPENLOCUS_B4_RUNS_DIR" \
      --public-out "$OPENLOCUS_B4_PUBLIC_OUT" \
      --confirm-worker-stopped
    ;;
  --reset-preboundary)
    required_status_env
    identity="absent"
    if [[ -s "$OPENLOCUS_B4_PID" ]]; then
      identity="$(pid_identity_state "$OPENLOCUS_B4_PID")"
    fi
    if [[ "$identity" == "alive" ]]; then
      printf 'B4 worker is still alive; pre-boundary reset forbidden\n' >&2
      exit 1
    fi
    if [[ "${OPENLOCUS_B4_CONFIRM_WORKER_STOPPED:-}" != "YES" ]]; then
      printf 'B4 pre-boundary reset requires explicit stopped confirmation\n' >&2
      exit 1
    fi
    reset_prelaunch_state "$OPENLOCUS_B4_PRIVATE_ROOT/b4_private_worker_started.json"
    ;;
  --worker)
    run_worker
    ;;
  --handshake-probe-worker)
    run_handshake_probe_worker "$@"
    ;;
  *)
    printf 'usage: %s --self-test|--launch|--status|--closeout-interrupted|--reset-preboundary\n' "$0" >&2
    exit 2
    ;;
esac
