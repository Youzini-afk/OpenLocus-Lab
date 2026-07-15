#!/usr/bin/env python3
"""Qualify a constrained Linux long-run runner before private input is read.

The production qualification has three layers:

1. a closed cgroup/tool/local-scratch/idle-noise profile gate;
2. a bounded sequential I/O gate; and
3. three consecutive synthetic xlarge split-plot groups using the real six
   adapters, process-isolated lifecycle hooks, 600-second phase timeout, and
   frozen arm rotation.

Exact hardware and scratch details stay in a private receipt.  The only public
output is a closed aggregate report containing thresholds, booleans, counts,
canonical failure codes, and a self-digest.  The qualifier accepts no holdout
argument, so passing it cannot accidentally read future private tasks.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import ctypes
import dataclasses
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b2_runner as b2r  # noqa: E402
import product_bakeoff_b21_runner as b21r  # noqa: E402
from product_bakeoff_b1_adapters import (  # noqa: E402
    enforce_wsr_inventory,
    write_index_seal,
)
from product_bakeoff_b1_spec import adapter_supports_support  # noqa: E402
from product_bakeoff_b2_adapters import B2_ADAPTERS  # noqa: E402
from product_bakeoff_conformance import (  # noqa: E402
    EpisodeRegistry,
    require_scoreable,
    stable_target_id,
)
from product_bakeoff_b23_protocol import (  # noqa: E402
    B23_IO_QUALIFICATION,
    B23_RUNNER_CLASS,
    B23_STRESS_QUALIFICATION,
    b23_source_bundle_digest,
    b23_spec_digest,
)


B23_QUALIFICATION_VERSION = "product_bakeoff_b23_runner_qualification.v1"
B23_PUBLIC_SCHEMA = "product_bakeoff_b23_runner_qualification_public.v1"
B23_PRIVATE_SCHEMA = "product_bakeoff_b23_runner_qualification_private.v1"
PUBLIC_STATUS_PASS = "product_bakeoff_b23_runner_qualified_no_private_input_read"
PUBLIC_STATUS_FAIL = "product_bakeoff_b23_runner_not_qualified_no_private_input_read"
PROFILE_FAILURE_CODES = frozenset(
    {
        "runner_os_mismatch",
        "runner_architecture_mismatch",
        "cgroup_cpu_limit_unavailable",
        "effective_cpu_quota_below_minimum",
        "cgroup_memory_limit_unavailable",
        "cgroup_memory_below_minimum",
        "cgroup_available_memory_below_minimum",
        "active_swap_nonzero",
        "idle_cgroup_cpu_above_maximum",
        "open_file_soft_limit_below_minimum",
        "python_version_below_minimum",
        "scratch_free_space_below_minimum",
        "scratch_not_nonrotational_local_block_storage",
        "scratch_not_outside_checkout",
        "runner_profile_recheck_failed",
        "runner_profile_drift_during_qualification",
        "git_unavailable",
        "rustc_unavailable",
        "rustc_version_mismatch",
        "cargo_unavailable",
        "cargo_version_mismatch",
        "openlocus_unavailable",
    }
)
STRESS_FAILURE_CODES = frozenset(
    {
        "stress_normal_record_rejected",
        "stress_two_step_parent_unavailable",
        "stress_support_status_mismatch",
        "stress_support_relation_missing",
        "stress_wall_clock_cap_exceeded",
        "stress_harness_failure",
        "stress_aggregate_gate_failed",
    }
)
ALL_PUBLIC_FAILURE_CODES = (
    PROFILE_FAILURE_CODES | STRESS_FAILURE_CODES | {"io_qualification_failed"}
)

STABLE_PROFILE_KEYS = (
    "os",
    "architecture",
    "cgroup_version",
    "logical_cpu_count_visible",
    "cpuset_cpu_count",
    "cpu_quota_count",
    "effective_cpu_quota_count",
    "finite_cgroup_cpu_limit",
    "memory_cgroup_version",
    "cgroup_memory_limit_bytes",
    "finite_cgroup_memory_limit",
    "active_swap_total_bytes",
    "scratch_mount_device_major_minor",
    "scratch_mount_root_length",
    "scratch_filesystem_type",
    "scratch_mount_source",
    "scratch_block_rotational",
    "scratch_nonrotational_local_block_storage",
    "scratch_outside_checkout",
    "open_file_soft_limit",
    "open_file_hard_limit",
    "python_version",
    "python_version_major",
    "python_version_minor",
    "python_version_micro",
    "git_available",
    "git_version",
    "rustc_available",
    "rustc_version",
    "cargo_available",
    "cargo_version",
    "openlocus_available",
    "openlocus_version",
    "openlocus_bytes",
    "openlocus_sha256",
)


class B23QualificationError(RuntimeError):
    """Fail-closed qualification error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_version(command: Sequence[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            list(command), capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, type(exc).__name__
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return completed.returncode == 0, (text[0][:160] if text else "empty")


def _host_memory_bytes() -> tuple[int, int, int]:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise B23QualificationError("GlobalMemoryStatusEx failed")
        return int(status.ullTotalPhys), int(status.ullAvailPhys), 0
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            if rest.strip().endswith("kB"):
                values[key] = int(rest.strip().split()[0]) * 1024
        if "MemTotal" in values and "MemAvailable" in values:
            return (
                values["MemTotal"],
                values["MemAvailable"],
                values.get("SwapTotal", 0),
            )
    raise B23QualificationError("physical memory could not be measured")


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_int(path: Path) -> int | None:
    raw = _read_text(path)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _cpuset_count(raw: str | None) -> int | None:
    if raw is None or not raw.strip():
        return None
    values: set[int] = set()
    try:
        for chunk in raw.split(","):
            left, separator, right = chunk.strip().partition("-")
            if separator:
                values.update(range(int(left), int(right) + 1))
            else:
                values.add(int(left))
    except ValueError:
        return None
    return len(values)


def _cpu_limit_profile(cgroup_root: Path = Path("/sys/fs/cgroup")) -> dict[str, Any]:
    logical = int(os.cpu_count() or 0)
    finite = False
    quota_count: float | None = None
    cpuset = None
    version = "none"
    cpu_max = _read_text(cgroup_root / "cpu.max")
    if cpu_max is not None:
        version = "v2"
        parts = cpu_max.split()
        if len(parts) == 2 and parts[0] != "max":
            try:
                quota = int(parts[0])
                period = int(parts[1])
                if quota > 0 and period > 0:
                    quota_count = quota / period
                    finite = True
            except ValueError:
                pass
        cpuset = _cpuset_count(
            _read_text(cgroup_root / "cpuset.cpus.effective")
            or _read_text(cgroup_root / "cpuset.cpus")
        )
    else:
        quota = _read_int(cgroup_root / "cpu" / "cpu.cfs_quota_us")
        period = _read_int(cgroup_root / "cpu" / "cpu.cfs_period_us")
        if quota is not None or period is not None:
            version = "v1"
        if quota is not None and period is not None and quota > 0 and period > 0:
            quota_count = quota / period
            finite = True
        cpuset = _cpuset_count(_read_text(cgroup_root / "cpuset" / "cpuset.cpus"))
    candidates = [logical]
    if cpuset is not None:
        candidates.append(cpuset)
    if quota_count is not None:
        candidates.append(int(quota_count))
    effective = min(candidates) if candidates and all(value > 0 for value in candidates) else 0
    return {
        "cgroup_version": version,
        "logical_cpu_count_visible": logical,
        "cpuset_cpu_count": cpuset,
        "cpu_quota_count": quota_count,
        "effective_cpu_quota_count": effective,
        "finite_cgroup_cpu_limit": finite,
    }


def _memory_limit_profile(cgroup_root: Path = Path("/sys/fs/cgroup")) -> dict[str, Any]:
    host_total, host_available, host_swap_total = _host_memory_bytes()
    version = "none"
    limit: int | None = None
    current: int | None = None
    raw_max = _read_text(cgroup_root / "memory.max")
    if raw_max is not None:
        version = "v2"
        if raw_max != "max":
            try:
                limit = int(raw_max)
            except ValueError:
                pass
        current = _read_int(cgroup_root / "memory.current")
    else:
        limit = _read_int(cgroup_root / "memory" / "memory.limit_in_bytes")
        current = _read_int(cgroup_root / "memory" / "memory.usage_in_bytes")
        if limit is not None or current is not None:
            version = "v1"
    finite = (
        isinstance(limit, int)
        and limit > 0
        and limit < (1 << 60)
    )
    available = max(0, int(limit) - int(current or 0)) if finite else host_available
    return {
        "memory_cgroup_version": version,
        "host_total_memory_bytes": host_total,
        "host_available_memory_bytes": host_available,
        "cgroup_memory_limit_bytes": limit,
        "cgroup_memory_current_bytes": current,
        "cgroup_available_memory_bytes": available,
        "finite_cgroup_memory_limit": finite,
        "active_swap_total_bytes": host_swap_total,
    }


def _cgroup_cpu_usage_ns(cgroup_root: Path = Path("/sys/fs/cgroup")) -> int | None:
    cpu_stat = _read_text(cgroup_root / "cpu.stat")
    if cpu_stat is not None:
        for line in cpu_stat.splitlines():
            key, _, raw = line.partition(" ")
            if key == "usage_usec":
                try:
                    return int(raw.strip()) * 1000
                except ValueError:
                    return None
    return _read_int(cgroup_root / "cpuacct" / "cpuacct.usage")


def _idle_cpu_millicores(*, seconds: float = 3.0) -> int | None:
    before = _cgroup_cpu_usage_ns()
    if before is None:
        return None
    started = time.perf_counter()
    time.sleep(seconds)
    elapsed = time.perf_counter() - started
    after = _cgroup_cpu_usage_ns()
    if after is None or after < before:
        return None
    cpu_seconds = (after - before) / 1_000_000_000
    return int(round(cpu_seconds / max(elapsed, 1e-9) * 1000))


def _mount_profile(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    selected: tuple[int, str, str, str] | None = None
    mountinfo = Path("/proc/self/mountinfo")
    if mountinfo.is_file():
        for line in mountinfo.read_text(encoding="utf-8").splitlines():
            left, separator, right = line.partition(" - ")
            if not separator:
                continue
            fields = left.split()
            after = right.split()
            if len(fields) < 5 or len(after) < 2:
                continue
            mountpoint = fields[4].replace("\\040", " ")
            try:
                resolved.relative_to(Path(mountpoint))
            except ValueError:
                continue
            candidate = (len(mountpoint), fields[2], after[0], after[1])
            if selected is None or candidate[0] > selected[0]:
                selected = candidate
    major_minor = f"{os.major(resolved.stat().st_dev)}:{os.minor(resolved.stat().st_dev)}"
    block = Path("/sys/dev/block") / major_minor
    rotational = None
    if block.exists():
        rotational = _read_int(block.resolve() / "queue" / "rotational")
    return {
        "scratch_mount_device_major_minor": major_minor,
        "scratch_mount_root_length": selected[0] if selected else None,
        "scratch_filesystem_type": selected[2] if selected else None,
        "scratch_mount_source": selected[3] if selected else None,
        "scratch_block_rotational": rotational,
        "scratch_nonrotational_local_block_storage": bool(
            selected
            and selected[2] not in {"overlay", "tmpfs", "fuse", "fuseblk", "nfs", "nfs4"}
            and selected[3].startswith("/dev/")
            and rotational == 0
        ),
    }


def _open_file_limits() -> tuple[int, int]:
    if os.name == "nt":
        return 0, 0
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    return int(soft), int(hard)


def _is_reparse_or_link(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        info = os.lstat(path)
    except OSError:
        return True
    return bool((getattr(info, "st_file_attributes", 0) or 0) & 0x400)


def _outside_checkout(repo_root: Path, scratch_root: Path) -> bool:
    repo = repo_root.resolve(strict=True)
    scratch = scratch_root.resolve(strict=False)
    try:
        scratch.relative_to(repo)
        return False
    except ValueError:
        pass
    try:
        repo.relative_to(scratch)
        return False
    except ValueError:
        return True


def collect_runner_profile(
    *, repo_root: Path, scratch_root: Path, cli_path: Path
) -> dict[str, Any]:
    if _is_reparse_or_link(repo_root):
        raise B23QualificationError("checkout root is missing or unsafe")
    repo_root = repo_root.resolve(strict=True)
    if not repo_root.is_dir() or _is_reparse_or_link(repo_root):
        raise B23QualificationError("checkout root is missing or unsafe")
    if os.path.lexists(scratch_root) and _is_reparse_or_link(scratch_root):
        raise B23QualificationError("scratch root is a link or reparse point")
    scratch_root = scratch_root.resolve(strict=False)
    if not _outside_checkout(repo_root, scratch_root):
        outside = False
    else:
        outside = True
    scratch_root.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_link(scratch_root):
        raise B23QualificationError("scratch root is a link or reparse point")
    if _is_reparse_or_link(cli_path):
        raise B23QualificationError("OpenLocus CLI is missing or unsafe")
    cli_path = cli_path.resolve(strict=True)
    if _is_reparse_or_link(cli_path) or not cli_path.is_file():
        raise B23QualificationError("OpenLocus CLI is missing or unsafe")
    cpu = _cpu_limit_profile()
    memory = _memory_limit_profile()
    mount = _mount_profile(scratch_root)
    nofile_soft, nofile_hard = _open_file_limits()
    idle_millicores = _idle_cpu_millicores()
    disk = shutil.disk_usage(scratch_root)
    git_ok, git_version = _run_version(("git", "--version"))
    rustc_ok, rustc_version = _run_version(("rustc", "--version"))
    cargo_ok, cargo_version = _run_version(("cargo", "--version"))
    cli_ok, cli_version = _run_version((str(cli_path), "--version"))
    machine = platform.machine().casefold()
    architecture = "x64" if machine in {"amd64", "x86_64", "x64"} else machine
    python_version = sys.version_info
    return {
        "os": "windows" if os.name == "nt" else platform.system().casefold(),
        "architecture": architecture,
        **cpu,
        **memory,
        "scratch_free_bytes": int(disk.free),
        **mount,
        "scratch_outside_checkout": outside,
        "active_idle_cgroup_cpu_millicores": idle_millicores,
        "open_file_soft_limit": nofile_soft,
        "open_file_hard_limit": nofile_hard,
        "python_version": platform.python_version(),
        "python_version_major": int(python_version.major),
        "python_version_minor": int(python_version.minor),
        "python_version_micro": int(python_version.micro),
        "git_available": git_ok,
        "git_version": git_version,
        "rustc_available": rustc_ok,
        "rustc_version": rustc_version,
        "cargo_available": cargo_ok,
        "cargo_version": cargo_version,
        "openlocus_available": cli_ok,
        "openlocus_version": cli_version,
        "openlocus_bytes": cli_path.stat().st_size,
        "openlocus_sha256": _file_sha256(cli_path),
    }


def validate_runner_profile(profile: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if profile.get("os") != B23_RUNNER_CLASS["required_os"]:
        failures.append("runner_os_mismatch")
    if profile.get("architecture") != B23_RUNNER_CLASS["required_architecture"]:
        failures.append("runner_architecture_mismatch")
    if profile.get("finite_cgroup_cpu_limit") is not True:
        failures.append("cgroup_cpu_limit_unavailable")
    if profile.get("finite_cgroup_memory_limit") is not True:
        failures.append("cgroup_memory_limit_unavailable")
    numeric_gates = (
        (
            "effective_cpu_quota_count",
            "minimum_effective_cpu_quota_count",
            "effective_cpu_quota_below_minimum",
        ),
        (
            "cgroup_memory_limit_bytes",
            "minimum_cgroup_memory_limit_bytes",
            "cgroup_memory_below_minimum",
        ),
        (
            "cgroup_available_memory_bytes",
            "minimum_cgroup_available_memory_bytes_at_start",
            "cgroup_available_memory_below_minimum",
        ),
        (
            "scratch_free_bytes",
            "minimum_free_local_scratch_bytes_at_start",
            "scratch_free_space_below_minimum",
        ),
    )
    for observed_key, required_key, code in numeric_gates:
        observed = profile.get(observed_key)
        if not isinstance(observed, int) or isinstance(observed, bool):
            failures.append(code)
        elif observed < int(B23_RUNNER_CLASS[required_key]):
            failures.append(code)
    if profile.get("active_swap_total_bytes") != 0:
        failures.append("active_swap_nonzero")
    idle = profile.get("active_idle_cgroup_cpu_millicores")
    if not isinstance(idle, int) or isinstance(idle, bool) or idle > int(
        B23_RUNNER_CLASS["maximum_idle_cgroup_cpu_millicores"]
    ):
        failures.append("idle_cgroup_cpu_above_maximum")
    nofile = profile.get("open_file_soft_limit")
    if not isinstance(nofile, int) or isinstance(nofile, bool) or nofile < int(
        B23_RUNNER_CLASS["minimum_open_file_soft_limit"]
    ):
        failures.append("open_file_soft_limit_below_minimum")
    python_major = profile.get("python_version_major")
    python_minor = profile.get("python_version_minor")
    if (
        not isinstance(python_major, int)
        or isinstance(python_major, bool)
        or not isinstance(python_minor, int)
        or isinstance(python_minor, bool)
        or (python_major, python_minor)
        < (
            int(B23_RUNNER_CLASS["minimum_python_major"]),
            int(B23_RUNNER_CLASS["minimum_python_minor"]),
        )
    ):
        failures.append("python_version_below_minimum")
    if profile.get("scratch_nonrotational_local_block_storage") is not True:
        failures.append("scratch_not_nonrotational_local_block_storage")
    if profile.get("scratch_outside_checkout") is not True:
        failures.append("scratch_not_outside_checkout")
    for tool in ("git", "rustc", "cargo", "openlocus"):
        if profile.get(f"{tool}_available") is not True:
            failures.append(f"{tool}_unavailable")
    if profile.get("rustc_available") is True and not str(
        profile.get("rustc_version") or ""
    ).startswith(str(B23_RUNNER_CLASS["required_rustc_version_prefix"])):
        failures.append("rustc_version_mismatch")
    if profile.get("cargo_available") is True and not str(
        profile.get("cargo_version") or ""
    ).startswith(str(B23_RUNNER_CLASS["required_cargo_version_prefix"])):
        failures.append("cargo_version_mismatch")
    return sorted(set(failures))


def stable_runner_profile_changes(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> list[str]:
    """Return exact stable-field names that changed during qualification.

    The returned names are private receipt material.  Public output exposes only
    the closed drift failure code, never the field names or observed values.
    """

    return [key for key in STABLE_PROFILE_KEYS if before.get(key) != after.get(key)]


def run_io_qualification(scratch_root: Path) -> dict[str, Any]:
    path = scratch_root / "b23_io_qualification.bin"
    if path.exists():
        raise B23QualificationError("I/O qualification target already exists")
    target = int(B23_IO_QUALIFICATION["file_bytes"])
    chunk = hashlib.sha256(b"openlocus-b23-io").digest() * (8 * 1024 * 1024 // 32)
    digest = hashlib.sha256()
    try:
        started = time.perf_counter()
        with path.open("xb", buffering=0) as handle:
            remaining = target
            while remaining:
                block = chunk[: min(len(chunk), remaining)]
                handle.write(block)
                digest.update(block)
                remaining -= len(block)
            os.fsync(handle.fileno())
        write_seconds = time.perf_counter() - started
        expected_hash = digest.hexdigest()
        observed = hashlib.sha256()
        started = time.perf_counter()
        with path.open("rb", buffering=0) as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                observed.update(block)
        read_seconds = time.perf_counter() - started
    finally:
        if path.exists():
            path.unlink()
    write_bps = int(target / max(write_seconds, 1e-9))
    read_bps = int(target / max(read_seconds, 1e-9))
    hash_valid = observed.hexdigest() == expected_hash
    passed = (
        write_bps
        >= int(B23_IO_QUALIFICATION["minimum_sequential_write_bytes_per_second"])
        and read_bps
        >= int(B23_IO_QUALIFICATION["minimum_sequential_read_bytes_per_second"])
        and hash_valid
    )
    return {
        "passed": passed,
        "bytes": target,
        "write_seconds": write_seconds,
        "read_seconds": read_seconds,
        "write_bytes_per_second": write_bps,
        "read_bytes_per_second": read_bps,
        "content_hash_valid": hash_valid,
    }


def _write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


def _initialize_fixture_git(root: Path) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "OpenLocus Qualification",
            "GIT_AUTHOR_EMAIL": "qualification@invalid.example",
            "GIT_COMMITTER_NAME": "OpenLocus Qualification",
            "GIT_COMMITTER_EMAIL": "qualification@invalid.example",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
    )

    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-c", "core.longpaths=true", *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if completed.returncode != 0:
            raise B23QualificationError(
                f"synthetic fixture git command failed: {args[0]}"
            )
        return completed.stdout.strip()

    run("init", "--quiet")
    run("config", "core.autocrlf", "false")
    run("add", "--all")
    run("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "b23 qualification fixture")
    commit = run("rev-parse", "HEAD")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise B23QualificationError("synthetic fixture commit id malformed")
    if run("status", "--porcelain=v1", "--untracked-files=no"):
        raise B23QualificationError("synthetic fixture checkout is dirty")
    return commit


def _fixture_anchor_files() -> dict[str, bytes]:
    return {
        "src/qualification_literal.ts": (
            "export const B23QualificationLiteral45 = "
            '"B23 qualification literal error 45";\n'
        ).encode("utf-8"),
        "src/a_qualification_target.ts": (
            "export function B23QualificationTarget46(value: number): number {\n"
            "  return value + 46;\n"
            "}\n"
        ).encode("utf-8"),
        "src/z_qualification_support.ts": (
            'import "./a_qualification_target";\n'
            "export function B23QualificationCaller46(value: number): number {\n"
            "  return value + 4600;\n"
            "}\n"
        ).encode("utf-8"),
        "config/qualification_config.ts": (
            "export const b23QualificationConfig47 = {\n"
            '  mode: "self_hosted",\n'
            "  enabled: true,\n"
            "};\n"
        ).encode("utf-8"),
    }


def generate_fixture(
    *, root: Path, target_bytes: int, file_count: int, repo_slot: str
) -> tuple[dict[str, Any], tuple[b2c.B2PublicTask, ...]]:
    if root.exists():
        raise B23QualificationError("fixture root already exists")
    root.mkdir(parents=True)
    anchors = _fixture_anchor_files()
    if file_count <= len(anchors):
        raise B23QualificationError("fixture file count too small")
    for rel, raw in anchors.items():
        _write_bytes(root / rel, raw)
    remaining_bytes = target_bytes - sum(len(raw) for raw in anchors.values())
    remaining_files = file_count - len(anchors)
    if remaining_bytes <= remaining_files * 256:
        raise B23QualificationError("fixture target bytes too small")
    for index in range(remaining_files):
        files_left = remaining_files - index
        target = remaining_bytes // files_left
        base = (
            f"export function B23QualificationFiller{index:05d}(value: number): number {{\n"
            f"  const stable = value + {index % 997};\n"
            "  return stable;\n"
            "}\n"
        ).encode("ascii")
        overhead = len(b"/*") + len(b"*/\n")
        pad = max(0, target - len(base) - overhead)
        raw = base + b"/*" + (b"q" * pad) + b"*/\n"
        _write_bytes(root / "src" / "fixture" / f"fixture_{index:05d}.ts", raw)
        remaining_bytes -= len(raw)
    commit = _initialize_fixture_git(root)
    records = b2c.scan_repository(root)
    if len(records) != file_count:
        raise B23QualificationError("fixture file count drift")
    b2c.validate_visible_band("typescript", repo_slot.rsplit("_", 1)[1], records)
    visible_bytes = sum(row.bytes for row in records)
    if visible_bytes != target_bytes:
        raise B23QualificationError("fixture byte count drift")
    repo_row = {
        "repo_slot": repo_slot,
        "language": "typescript",
        "size_band": repo_slot.rsplit("_", 1)[1],
        "source": {
            "type": "qualification_synthetic",
            "repo": "qualification/synthetic-typescript",
            "clone_root": str(root.resolve()),
        },
        "commit": commit,
        "license": {"detected": ["MIT"], "expected": "MIT"},
        "visible": {
            "file_count": len(records),
            "bytes": visible_bytes,
            "manifest_digest": b2c.visible_manifest_digest(records),
            "files": [row.to_dict() for row in records],
        },
    }
    queries = {
        "direct": "B23 qualification literal error 45",
        "relational": "B23QualificationTarget46",
        "workflow": "b23QualificationConfig47",
        "restraint": "B23QualificationDefinitelyAbsent48",
    }
    tasks: list[b2c.B2PublicTask] = []
    slots = [slot for slot in b2p.build_task_slots() if slot.repo_slot == repo_slot]
    if len(slots) != 4:
        raise B23QualificationError("fixture repo slot does not own four tasks")
    for slot in slots:
        query = queries[slot.role]
        number = int(slot.slot_id.rsplit("_", 1)[1])
        suffix = hashlib.sha256(
            f"{slot.slot_id}|{query}|b23-qualification".encode("utf-8")
        ).hexdigest()[:12]
        tasks.append(
            b2c.B2PublicTask(
                slot_id=slot.slot_id,
                task_slug=f"b2_t{number:02d}_{suffix}",
                repo_slot=slot.repo_slot,
                language=slot.language,
                size_band=slot.size_band,
                role=slot.role,
                task_family=slot.task_family,
                interaction_mode=slot.interaction_mode,
                query=query,
            ).validate()
        )
    return repo_row, tuple(tasks)


def _record_counts(result: b21r.B21RunResult) -> dict[str, int]:
    failures = Counter(
        record.failure_category or "none" for record in result.records
    )
    return {
        "logical_record_count": result.logical_record_count,
        "normal_record_count": len(result.records),
        "terminal_support_record_count": len(result.terminal_support_cells),
        "normal_accepted_count": sum(r.status == "accepted" for r in result.records),
        "normal_rejected_count": sum(r.status != "accepted" for r in result.records),
        "timeout_count": sum(
            (r.failure_category or "")
            in {"adapter_timeout", "lifecycle_timeout:prepare", "lifecycle_timeout:index"}
            for r in result.records
        ),
        "parent_receipt_count": len(result.parent_receipts),
        "parent_receipt_error_count": len(result.parent_receipt_failures),
        "provider_network_call_count": sum(
            int(receipt["provider_network_call_count"])
            for receipt in (*result.parent_receipts, *result.terminal_parent_receipts)
        ),
        "distinct_failure_category_count": len(
            [key for key in failures if key != "none"]
        ),
    }


_FROZEN_MAKE_B2_REQUEST = b2r.make_b2_request


def _make_b23_longrun_request(**kwargs: Any) -> Any:
    request = _FROZEN_MAKE_B2_REQUEST(**kwargs)
    run_spec = dataclasses.replace(
        request.run_spec,
        timeout_seconds=float(B23_STRESS_QUALIFICATION["same_phase_timeout_seconds"]),
    ).validate()
    return dataclasses.replace(request, run_spec=run_spec).validate()


@contextlib.contextmanager
def _longrun_timeout_override() -> Any:
    if b2r.make_b2_request is not _FROZEN_MAKE_B2_REQUEST:
        raise B23QualificationError("B2 request factory is already overridden")
    b2r.make_b2_request = _make_b23_longrun_request
    try:
        yield
    finally:
        b2r.make_b2_request = _FROZEN_MAKE_B2_REQUEST


def _run_sustained_stress_impl(
    *,
    repo_row: Mapping[str, Any],
    tasks: Sequence[b2c.B2PublicTask],
    group_count: int,
    run_root: Path,
    wall_clock_cap_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if run_root.exists():
        raise B23QualificationError("stress run root already exists")
    private_root = run_root / "private"
    work_root = run_root / "work"
    private_root.mkdir(parents=True)
    work_root.mkdir()
    result = b21r.B21RunResult(runs_dir=str(run_root.resolve()))
    adapter_map = {
        adapter_id: (descriptor_factory(), hooks_factory())
        for adapter_id, descriptor_factory, hooks_factory in B2_ADAPTERS
    }
    task_by_slot = {task.slot_id: task for task in tasks}
    rows = [
        row
        for row in b2p.build_execution_schedule()
        if row.slot_id in task_by_slot and row.repetition <= group_count
    ]
    groups = b2r._schedule_groups(rows)
    if len(groups) != group_count:
        raise B23QualificationError("stress schedule group count drift")
    started = time.perf_counter()
    completed_groups = 0
    failure_codes: list[str] = []
    private_failure_types: list[str] = []
    try:
        for group_index, (_, repetition, group_rows) in enumerate(groups, start=1):
            group_root = work_root / f"g{group_index:02d}_r{repetition}"
            group_root.mkdir()
            try:
                cell_map = b2r._create_repo_rep_cells(
                    group_root=group_root,
                    private_root=private_root,
                    repo_row=repo_row,
                    repetition=repetition,
                )
                for row in group_rows:
                    task = task_by_slot[row.slot_id]
                    episode_id = b21r._request_token("b23q_ep", task, repetition)
                    context_id = b21r._request_token("b23q_ctx", task, repetition)
                    support_id = b21r._request_token("b23q_sup", task, repetition)
                    contexts: dict[str, b2r.B2CellResult] = {}
                    row_failed = False
                    for adapter_id in row.arm_order:
                        descriptor, hooks = adapter_map[adapter_id]
                        cell_root, snapshot, visible_path = cell_map[adapter_id]
                        request = b2r.make_b2_request(
                            task=task,
                            snapshot=snapshot,
                            repo_visible_digest=repo_row["visible"]["manifest_digest"],
                            adapter_id=adapter_id,
                            repetition=repetition,
                            cache_state=row.cache_state,
                            operation="context",
                            episode_id=episode_id,
                            request_id=context_id,
                        )
                        cell = b2r._run_cell(
                            hooks=hooks,
                            descriptor=descriptor,
                            request=request,
                            snapshot=snapshot,
                            cell_root=cell_root,
                            visible_manifest_path=visible_path,
                            episode_registry=None,
                            materialize_step=1,
                        )
                        if row.cache_state == "cold" and cell.record.status == "accepted":
                            write_index_seal(cell_root)
                        b21r._append_normal(result, cell, descriptor, private_root)
                        contexts[adapter_id] = cell
                        if cell.record.status != "accepted":
                            row_failed = True
                    if row_failed:
                        failure_codes.append("stress_normal_record_rejected")
                        raise B23QualificationError("stress context record rejected")
                    for context in contexts.values():
                        require_scoreable(context.record, context.capture)
                    if task.interaction_mode != "two_step":
                        continue
                    for adapter_id in row.arm_order:
                        descriptor, hooks = adapter_map[adapter_id]
                        cell_root, snapshot, visible_path = cell_map[adapter_id]
                        context = contexts[adapter_id]
                        target = b21r._own_parent_target(context)
                        if target is None:
                            failure_codes.append("stress_two_step_parent_unavailable")
                            raise B23QualificationError("synthetic stress parent unavailable")
                        output = context.capture.output
                        if output is None:
                            raise B23QualificationError("stress context capture missing")
                        bound_target_id = stable_target_id(target)
                        registry = EpisodeRegistry()
                        registered = registry.register(
                            result_id=context_id,
                            target=target,
                            snapshot=snapshot,
                            request=context.request,
                            episode_estimate_used=(
                                output.pack.budget_usage.episode_estimate_used
                            ),
                            parent_step=1,
                        )
                        if registered != bound_target_id:
                            raise B23QualificationError("stress target id drift")
                        b21r._write_lineage_receipt(
                            cell_root,
                            support_id,
                            context_id,
                            bound_target_id,
                            target.path,
                            target.start_line,
                            target.end_line,
                            snapshot.manifest_digest,
                            context.record.canonical_result_hash or "",
                            context.record.canonical_pack_hash or "",
                        )
                        request = b2r.make_b2_request(
                            task=task,
                            snapshot=snapshot,
                            repo_visible_digest=repo_row["visible"]["manifest_digest"],
                            adapter_id=adapter_id,
                            repetition=repetition,
                            cache_state=row.cache_state,
                            operation="support",
                            episode_id=episode_id,
                            request_id=support_id,
                            parent_result_id=context_id,
                            bound_target_id=bound_target_id,
                        )
                        support = b2r._run_cell(
                            hooks=hooks,
                            descriptor=descriptor,
                            request=request,
                            snapshot=snapshot,
                            cell_root=cell_root,
                            visible_manifest_path=visible_path,
                            episode_registry=registry,
                            materialize_step=2,
                        )
                        b21r._append_normal(result, support, descriptor, private_root)
                        require_scoreable(support.record, support.capture)
                        support_output = support.capture.output
                        if support_output is None:
                            raise B23QualificationError("stress support capture missing")
                        expected = (
                            "ready"
                            if adapter_supports_support(adapter_id)
                            else "no_evidence"
                        )
                        if support_output.pack.pack_status != expected:
                            failure_codes.append("stress_support_status_mismatch")
                            raise B23QualificationError("stress support status mismatch")
                        if expected == "ready" and not support_output.pack.support:
                            failure_codes.append("stress_support_relation_missing")
                            raise B23QualificationError("stress support relation missing")
                        b21r._clear_lineage_receipt(cell_root)
                for cell_root, _, _ in cell_map.values():
                    enforce_wsr_inventory(cell_root, expected_index_sealed=True)
                completed_groups += 1
            finally:
                if group_root.exists():
                    shutil.rmtree(group_root)
            if time.perf_counter() - started > wall_clock_cap_seconds:
                failure_codes.append("stress_wall_clock_cap_exceeded")
                raise B23QualificationError("stress wall clock cap exceeded")
    except Exception as exc:  # noqa: BLE001 - exact detail stays private
        private_failure_types.append(type(exc).__name__)
        if not failure_codes:
            failure_codes.append("stress_harness_failure")
    elapsed = time.perf_counter() - started
    counts = _record_counts(result)
    expected_logical = group_count * 30
    stress_passed = (
        not failure_codes
        and completed_groups == group_count
        and counts["logical_record_count"] == expected_logical
        and counts["normal_record_count"] == expected_logical
        and counts["normal_accepted_count"] == expected_logical
        and counts["normal_rejected_count"] == 0
        and counts["timeout_count"] == 0
        and counts["terminal_support_record_count"] == 0
        and counts["parent_receipt_count"] == expected_logical
        and counts["parent_receipt_error_count"] == 0
        and counts["provider_network_call_count"] == 0
        and elapsed <= wall_clock_cap_seconds
    )
    if not stress_passed and not failure_codes:
        failure_codes.append("stress_aggregate_gate_failed")
    public = {
        "executed": True,
        "passed": stress_passed,
        "completed_group_count": completed_groups,
        "logical_record_count": counts["logical_record_count"],
        "normal_record_count": counts["normal_record_count"],
        "normal_accepted_count": counts["normal_accepted_count"],
        "normal_rejected_count": counts["normal_rejected_count"],
        "timeout_count": counts["timeout_count"],
        "terminal_support_record_count": counts["terminal_support_record_count"],
        "parent_receipt_count": counts["parent_receipt_count"],
        "parent_receipt_error_count": counts["parent_receipt_error_count"],
        "provider_network_call_count": counts["provider_network_call_count"],
        "wall_clock_cap_met": elapsed <= wall_clock_cap_seconds,
        "failure_codes": sorted(set(failure_codes)),
    }
    private = {
        **public,
        "elapsed_seconds": elapsed,
        "private_failure_types": private_failure_types,
        "fixture_manifest_digest": repo_row["visible"]["manifest_digest"],
        "fixture_visible_bytes": repo_row["visible"]["bytes"],
        "fixture_file_count": repo_row["visible"]["file_count"],
    }
    return public, private


def run_sustained_stress(
    *,
    repo_row: Mapping[str, Any],
    tasks: Sequence[b2c.B2PublicTask],
    group_count: int,
    run_root: Path,
    wall_clock_cap_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with _longrun_timeout_override():
        return _run_sustained_stress_impl(
            repo_row=repo_row,
            tasks=tasks,
            group_count=group_count,
            run_root=run_root,
            wall_clock_cap_seconds=wall_clock_cap_seconds,
        )


def _empty_stress() -> dict[str, Any]:
    return {
        "executed": False,
        "passed": False,
        "completed_group_count": 0,
        "logical_record_count": 0,
        "normal_record_count": 0,
        "normal_accepted_count": 0,
        "normal_rejected_count": 0,
        "timeout_count": 0,
        "terminal_support_record_count": 0,
        "parent_receipt_count": 0,
        "parent_receipt_error_count": 0,
        "provider_network_call_count": 0,
        "wall_clock_cap_met": False,
        "failure_codes": [],
    }


def build_public_report(
    *,
    profile_admission_passed: bool,
    profile_revalidation_executed: bool,
    profile_passed: bool,
    profile_failure_codes: Sequence[str],
    io_public: Mapping[str, Any] | None,
    stress_public: Mapping[str, Any],
) -> dict[str, Any]:
    io_executed = io_public is not None
    io_passed = bool(io_public and io_public.get("passed"))
    stress_passed = bool(stress_public.get("passed"))
    passed = (
        profile_admission_passed
        and profile_revalidation_executed
        and profile_passed
        and io_passed
        and stress_passed
    )
    failure_codes = set(profile_failure_codes)
    if io_executed and not io_passed:
        failure_codes.add("io_qualification_failed")
    failure_codes.update(stress_public.get("failure_codes") or [])
    report = {
        "schema_version": B23_PUBLIC_SCHEMA,
        "qualification_version": B23_QUALIFICATION_VERSION,
        "status": PUBLIC_STATUS_PASS if passed else PUBLIC_STATUS_FAIL,
        "claim_level": "runner_qualification_only_no_private_input_no_tournament",
        "b23_spec_digest": b23_spec_digest(),
        "b23_source_bundle_digest": b23_source_bundle_digest(),
        "runner_class": copy.deepcopy(B23_RUNNER_CLASS),
        "profile_gate": {
            "admission_passed": profile_admission_passed,
            "post_stress_revalidation_executed": profile_revalidation_executed,
            "passed": profile_passed,
            "exact_observed_profile_public": False,
            "failure_codes": sorted(set(profile_failure_codes)),
        },
        "io_gate": {
            "executed": io_executed,
            "passed": io_passed,
            "file_bytes": int(B23_IO_QUALIFICATION["file_bytes"]),
            "minimum_write_bytes_per_second": int(
                B23_IO_QUALIFICATION["minimum_sequential_write_bytes_per_second"]
            ),
            "minimum_read_bytes_per_second": int(
                B23_IO_QUALIFICATION["minimum_sequential_read_bytes_per_second"]
            ),
            "exact_observed_throughput_public": False,
        },
        "stress_gate": {
            "source_kind": B23_STRESS_QUALIFICATION["source_kind"],
            "source_file_count": B23_STRESS_QUALIFICATION["source_file_count"],
            "source_visible_bytes": B23_STRESS_QUALIFICATION["source_visible_bytes"],
            "required_group_count": B23_STRESS_QUALIFICATION["consecutive_group_count"],
            "required_logical_record_count": B23_STRESS_QUALIFICATION["logical_record_count"],
            "phase_timeout_seconds": B23_STRESS_QUALIFICATION["same_phase_timeout_seconds"],
            "wall_clock_cap_seconds": B23_STRESS_QUALIFICATION["maximum_wall_clock_seconds"],
            **dict(stress_public),
        },
        "privacy": {
            "private_input_read": False,
            "repository_or_task_identity_public": False,
            "exact_hardware_profile_public": False,
            "runner_name_or_machine_identifier_public": False,
            "scratch_location_public": False,
            "only_aggregate_qualification_output": True,
        },
        "decision": {
            "runner_qualified": passed,
            "future_holdout_authoring_authorized": passed,
            "future_tournament_execution_authorized": False,
            "failure_codes": sorted(failure_codes),
        },
        "qualification_digest": "",
    }
    digest_payload = dict(report)
    digest_payload.pop("qualification_digest")
    report["qualification_digest"] = _prefixed_digest("b23qual_", digest_payload)
    return report


def validate_public_report(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "qualification_version",
        "status",
        "claim_level",
        "b23_spec_digest",
        "b23_source_bundle_digest",
        "runner_class",
        "profile_gate",
        "io_gate",
        "stress_gate",
        "privacy",
        "decision",
        "qualification_digest",
    }:
        return ["public qualification report has non-closed shape"]
    errors = list(b2p.scan_public_report(value))
    if value.get("schema_version") != B23_PUBLIC_SCHEMA:
        errors.append("public schema mismatch")
    if value.get("qualification_version") != B23_QUALIFICATION_VERSION:
        errors.append("qualification version mismatch")
    if value.get("b23_spec_digest") != b23_spec_digest():
        errors.append("B2.3 spec digest mismatch")
    if value.get("b23_source_bundle_digest") != b23_source_bundle_digest():
        errors.append("B2.3 source bundle digest mismatch")
    payload = dict(value)
    declared = payload.pop("qualification_digest", None)
    if declared != _prefixed_digest("b23qual_", payload):
        errors.append("qualification digest mismatch")
    profile_raw = value.get("profile_gate")
    io_gate_raw = value.get("io_gate")
    stress_raw = value.get("stress_gate")
    privacy_raw = value.get("privacy")
    decision_raw = value.get("decision")
    profile = profile_raw if isinstance(profile_raw, dict) else {}
    io_gate = io_gate_raw if isinstance(io_gate_raw, dict) else {}
    stress = stress_raw if isinstance(stress_raw, dict) else {}
    privacy = privacy_raw if isinstance(privacy_raw, dict) else {}
    decision = decision_raw if isinstance(decision_raw, dict) else {}
    if value.get("runner_class") != B23_RUNNER_CLASS:
        errors.append("runner class drift")
    expected_nested_keys = {
        "profile_gate": {
            "admission_passed",
            "post_stress_revalidation_executed",
            "passed",
            "exact_observed_profile_public",
            "failure_codes",
        },
        "io_gate": {
            "executed",
            "passed",
            "file_bytes",
            "minimum_write_bytes_per_second",
            "minimum_read_bytes_per_second",
            "exact_observed_throughput_public",
        },
        "stress_gate": {
            "source_kind",
            "source_file_count",
            "source_visible_bytes",
            "required_group_count",
            "required_logical_record_count",
            "phase_timeout_seconds",
            "wall_clock_cap_seconds",
            "executed",
            "passed",
            "completed_group_count",
            "logical_record_count",
            "normal_record_count",
            "normal_accepted_count",
            "normal_rejected_count",
            "timeout_count",
            "terminal_support_record_count",
            "parent_receipt_count",
            "parent_receipt_error_count",
            "provider_network_call_count",
            "wall_clock_cap_met",
            "failure_codes",
        },
        "privacy": {
            "private_input_read",
            "repository_or_task_identity_public",
            "exact_hardware_profile_public",
            "runner_name_or_machine_identifier_public",
            "scratch_location_public",
            "only_aggregate_qualification_output",
        },
        "decision": {
            "runner_qualified",
            "future_holdout_authoring_authorized",
            "future_tournament_execution_authorized",
            "failure_codes",
        },
    }
    for key, expected_keys in expected_nested_keys.items():
        child = value.get(key)
        if not isinstance(child, dict) or set(child) != expected_keys:
            errors.append(f"{key} has non-closed shape")
    failure_lists: dict[str, list[str]] = {}
    for label, child, vocabulary in (
        ("profile", profile, PROFILE_FAILURE_CODES),
        ("stress", stress, STRESS_FAILURE_CODES),
        ("decision", decision, ALL_PUBLIC_FAILURE_CODES),
    ):
        raw_codes = child.get("failure_codes")
        if not isinstance(raw_codes, list) or not all(
            isinstance(code, str) for code in raw_codes
        ):
            errors.append(f"{label} failure codes must be a string list")
            failure_lists[label] = []
            continue
        failure_lists[label] = raw_codes
        if raw_codes != sorted(set(raw_codes)):
            errors.append(f"{label} failure codes must be sorted and unique")
        if not set(raw_codes) <= vocabulary:
            errors.append(f"{label} failure code vocabulary drift")
    expected_io = {
        "file_bytes": int(B23_IO_QUALIFICATION["file_bytes"]),
        "minimum_write_bytes_per_second": int(
            B23_IO_QUALIFICATION["minimum_sequential_write_bytes_per_second"]
        ),
        "minimum_read_bytes_per_second": int(
            B23_IO_QUALIFICATION["minimum_sequential_read_bytes_per_second"]
        ),
    }
    for key, expected in expected_io.items():
        if io_gate.get(key) != expected:
            errors.append(f"I/O gate {key} drift")
    expected_stress = {
        "source_kind": B23_STRESS_QUALIFICATION["source_kind"],
        "source_file_count": B23_STRESS_QUALIFICATION["source_file_count"],
        "source_visible_bytes": B23_STRESS_QUALIFICATION["source_visible_bytes"],
        "required_group_count": B23_STRESS_QUALIFICATION["consecutive_group_count"],
        "required_logical_record_count": B23_STRESS_QUALIFICATION["logical_record_count"],
        "phase_timeout_seconds": B23_STRESS_QUALIFICATION["same_phase_timeout_seconds"],
        "wall_clock_cap_seconds": B23_STRESS_QUALIFICATION["maximum_wall_clock_seconds"],
    }
    for key, expected in expected_stress.items():
        if stress.get(key) != expected:
            errors.append(f"stress gate {key} drift")
    for key in (
        "completed_group_count",
        "logical_record_count",
        "normal_record_count",
        "normal_accepted_count",
        "normal_rejected_count",
        "timeout_count",
        "terminal_support_record_count",
        "parent_receipt_count",
        "parent_receipt_error_count",
        "provider_network_call_count",
    ):
        observed = stress.get(key)
        if not isinstance(observed, int) or isinstance(observed, bool) or observed < 0:
            errors.append(f"stress gate {key} must be nonnegative int")
    if profile.get("exact_observed_profile_public") is not False:
        errors.append("exact runner profile must remain private")
    for key in (
        "admission_passed",
        "post_stress_revalidation_executed",
        "passed",
    ):
        if not isinstance(profile.get(key), bool):
            errors.append(f"profile gate {key} must be bool")
    if profile.get("passed") is not (not bool(failure_lists.get("profile"))):
        errors.append("profile gate decision mismatch")
    for key in ("executed", "passed"):
        if not isinstance(io_gate.get(key), bool):
            errors.append(f"I/O gate {key} must be bool")
    for key in ("executed", "passed", "wall_clock_cap_met"):
        if not isinstance(stress.get(key), bool):
            errors.append(f"stress gate {key} must be bool")
    for key in (
        "runner_qualified",
        "future_holdout_authoring_authorized",
        "future_tournament_execution_authorized",
    ):
        if not isinstance(decision.get(key), bool):
            errors.append(f"decision {key} must be bool")
    if io_gate.get("exact_observed_throughput_public") is not False:
        errors.append("exact I/O throughput must remain private")
    if privacy.get("private_input_read") is not False:
        errors.append("qualification may not read private input")
    expected_privacy = {
        "private_input_read": False,
        "repository_or_task_identity_public": False,
        "exact_hardware_profile_public": False,
        "runner_name_or_machine_identifier_public": False,
        "scratch_location_public": False,
        "only_aggregate_qualification_output": True,
    }
    if privacy != expected_privacy:
        errors.append("qualification privacy contract drift")
    passed = (
        profile.get("admission_passed") is True
        and profile.get("post_stress_revalidation_executed") is True
        and profile.get("passed") is True
        and io_gate.get("passed") is True
        and stress.get("passed") is True
    )
    if decision.get("runner_qualified") is not passed:
        errors.append("runner qualification decision mismatch")
    expected_status = PUBLIC_STATUS_PASS if passed else PUBLIC_STATUS_FAIL
    if value.get("status") != expected_status:
        errors.append("qualification status mismatch")
    if decision.get("future_holdout_authoring_authorized") is not passed:
        errors.append("future holdout authorization mismatch")
    if decision.get("future_tournament_execution_authorized") is not False:
        errors.append("runner qualification cannot authorize tournament execution")
    expected_failure_codes = set(failure_lists.get("profile", []))
    expected_failure_codes.update(failure_lists.get("stress", []))
    if io_gate.get("executed") is True and io_gate.get("passed") is False:
        expected_failure_codes.add("io_qualification_failed")
    if decision.get("failure_codes") != sorted(expected_failure_codes):
        errors.append("decision failure code union mismatch")
    if io_gate.get("executed") is False and io_gate.get("passed") is not False:
        errors.append("unexecuted I/O gate cannot pass")
    if stress.get("executed") is False and stress.get("logical_record_count") != 0:
        errors.append("unexecuted stress carries records")
    if stress.get("executed") is False and stress.get("passed") is not False:
        errors.append("unexecuted stress cannot pass")
    if profile.get("admission_passed") is False and io_gate.get("executed") is not False:
        errors.append("failed admission profile must short-circuit I/O")
    if profile.get("admission_passed") is False and profile.get("passed") is not False:
        errors.append("failed admission profile cannot pass")
    if io_gate.get("passed") is False and stress.get("executed") is not False:
        errors.append("failed or skipped I/O must short-circuit stress")
    if stress.get("executed") is True and profile.get(
        "post_stress_revalidation_executed"
    ) is not True:
        errors.append("executed stress must be followed by profile revalidation")
    if profile.get("post_stress_revalidation_executed") is True and (
        profile.get("admission_passed") is not True
        or io_gate.get("executed") is not True
        or stress.get("executed") is not True
    ):
        errors.append("profile revalidation execution order mismatch")
    if stress.get("passed") is True:
        if (
            stress.get("completed_group_count")
            != B23_STRESS_QUALIFICATION["consecutive_group_count"]
            or stress.get("logical_record_count")
            != B23_STRESS_QUALIFICATION["logical_record_count"]
            or stress.get("normal_record_count")
            != B23_STRESS_QUALIFICATION["logical_record_count"]
            or stress.get("normal_accepted_count")
            != B23_STRESS_QUALIFICATION["logical_record_count"]
            or stress.get("normal_rejected_count") != 0
            or stress.get("timeout_count") != 0
            or stress.get("terminal_support_record_count") != 0
            or stress.get("parent_receipt_count")
            != B23_STRESS_QUALIFICATION["logical_record_count"]
            or stress.get("parent_receipt_error_count") != 0
            or stress.get("provider_network_call_count") != 0
            or stress.get("wall_clock_cap_met") is not True
            or stress.get("failure_codes") != []
        ):
            errors.append("passing stress aggregate does not meet frozen gates")
    if not isinstance(decision.get("failure_codes"), list):
        errors.append("decision failure codes malformed")
    return sorted(set(errors))


def _private_receipt(
    *,
    profile_before: Mapping[str, Any],
    profile_after: Mapping[str, Any] | None,
    profile_recheck_error: str | None,
    stable_profile_changes: Sequence[str],
    profile_failures: Sequence[str],
    io_private: Mapping[str, Any] | None,
    stress_private: Mapping[str, Any] | None,
    public_digest: str,
) -> dict[str, Any]:
    receipt = {
        "schema_version": B23_PRIVATE_SCHEMA,
        "qualification_version": B23_QUALIFICATION_VERSION,
        "b23_spec_digest": b23_spec_digest(),
        "b23_source_bundle_digest": b23_source_bundle_digest(),
        "profile_before": dict(profile_before),
        "profile_after": dict(profile_after) if profile_after is not None else None,
        "profile_recheck_error": profile_recheck_error,
        "stable_profile_changes": list(stable_profile_changes),
        "profile_failure_codes": list(profile_failures),
        "io": dict(io_private) if io_private is not None else None,
        "stress": dict(stress_private) if stress_private is not None else None,
        "public_qualification_digest": public_digest,
        "private_receipt_digest": "",
    }
    receipt["private_receipt_digest"] = _prefixed_digest("b23qpriv_", receipt)
    return receipt


def write_json(path: Path, value: Any) -> None:
    """Write one new JSON artifact atomically without following a target link."""

    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B23QualificationError("qualification output already exists")
    raw = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        if os.path.lexists(target):
            raise B23QualificationError("qualification output appeared concurrently")
        os.replace(temporary, target)
        if os.name != "nt":
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_output_boundaries(
    *,
    repo_root: Path,
    scratch_root: Path,
    private_receipt_path: Path,
    public_out_path: Path,
) -> None:
    resolved_repo = repo_root.resolve(strict=True)
    resolved_scratch = scratch_root.resolve(strict=False)
    resolved_private = private_receipt_path.resolve(strict=False)
    resolved_public = public_out_path.resolve(strict=False)
    if resolved_private == resolved_scratch:
        raise B23QualificationError("private qualification receipt must be a file")
    for output in (private_receipt_path, public_out_path):
        if os.path.lexists(output):
            raise B23QualificationError("qualification output path must be new")
    try:
        resolved_private.relative_to(resolved_scratch)
    except ValueError as exc:
        raise B23QualificationError(
            "private qualification receipt must stay under scratch root"
        ) from exc
    try:
        resolved_public.relative_to(resolved_scratch)
        raise B23QualificationError(
            "public qualification aggregate must be outside private scratch root"
        )
    except ValueError:
        pass
    try:
        resolved_public.relative_to(resolved_repo)
        raise B23QualificationError(
            "public qualification aggregate must not be written into the checkout"
        )
    except ValueError:
        pass


def qualify_runner(
    *,
    repo_root: Path,
    scratch_root: Path,
    cli_path: Path,
    private_receipt_path: Path,
    public_out_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_output_boundaries(
        repo_root=repo_root,
        scratch_root=scratch_root,
        private_receipt_path=private_receipt_path,
        public_out_path=public_out_path,
    )
    profile_before = collect_runner_profile(
        repo_root=repo_root, scratch_root=scratch_root, cli_path=cli_path
    )
    admission_profile_failures = validate_runner_profile(profile_before)
    profile_failures = list(admission_profile_failures)
    profile_after: dict[str, Any] | None = None
    profile_recheck_error: str | None = None
    profile_revalidation_executed = False
    stable_changes: list[str] = []
    io_private: dict[str, Any] | None = None
    stress_private: dict[str, Any] | None = None
    stress_public = _empty_stress()
    if not admission_profile_failures:
        io_private = run_io_qualification(scratch_root)
        if io_private["passed"]:
            fixture_root = scratch_root / "b23_synthetic_fixture"
            run_root = scratch_root / "b23_sustained_stress"
            repo_row, tasks = generate_fixture(
                root=fixture_root,
                target_bytes=int(B23_STRESS_QUALIFICATION["source_visible_bytes"]),
                file_count=int(B23_STRESS_QUALIFICATION["source_file_count"]),
                repo_slot="b2_repo_typescript_xlarge",
            )
            try:
                stress_public, stress_private = run_sustained_stress(
                    repo_row=repo_row,
                    tasks=tasks,
                    group_count=int(B23_STRESS_QUALIFICATION["consecutive_group_count"]),
                    run_root=run_root,
                    wall_clock_cap_seconds=int(
                        B23_STRESS_QUALIFICATION["maximum_wall_clock_seconds"]
                    ),
                )
            finally:
                if fixture_root.exists():
                    shutil.rmtree(fixture_root)
                if run_root.exists():
                    shutil.rmtree(run_root)
            try:
                profile_revalidation_executed = True
                profile_after = collect_runner_profile(
                    repo_root=repo_root,
                    scratch_root=scratch_root,
                    cli_path=cli_path,
                )
            except Exception as exc:  # noqa: BLE001 - exact type stays private
                profile_recheck_error = type(exc).__name__
                profile_failures.append("runner_profile_recheck_failed")
            else:
                profile_failures.extend(validate_runner_profile(profile_after))
                stable_changes = stable_runner_profile_changes(
                    profile_before, profile_after
                )
                if stable_changes:
                    profile_failures.append(
                        "runner_profile_drift_during_qualification"
                    )
    profile_failures = sorted(set(profile_failures))
    public = build_public_report(
        profile_admission_passed=not admission_profile_failures,
        profile_revalidation_executed=profile_revalidation_executed,
        profile_passed=not profile_failures,
        profile_failure_codes=profile_failures,
        io_public=io_private,
        stress_public=stress_public,
    )
    errors = validate_public_report(public)
    if errors:
        raise B23QualificationError("public qualification report validation failed")
    private = _private_receipt(
        profile_before=profile_before,
        profile_after=profile_after,
        profile_recheck_error=profile_recheck_error,
        stable_profile_changes=stable_changes,
        profile_failures=profile_failures,
        io_private=io_private,
        stress_private=stress_private,
        public_digest=public["qualification_digest"],
    )
    write_json(private_receipt_path, private)
    write_json(public_out_path, public)
    return public, private


def run_micro_test(*, scratch_root: Path, cli_path: Path) -> dict[str, Any]:
    if scratch_root.exists():
        raise B23QualificationError("micro-test scratch root already exists")
    scratch_root.mkdir(parents=True)
    os.environ["OPENLOCUS_CLI"] = str(cli_path.resolve(strict=True))
    fixture = scratch_root / "fixture"
    run_root = scratch_root / "stress"
    repo_row, tasks = generate_fixture(
        root=fixture,
        target_bytes=512 * 1024,
        file_count=64,
        repo_slot="b2_repo_typescript_small",
    )
    public, _ = run_sustained_stress(
        repo_row=repo_row,
        tasks=tasks,
        group_count=1,
        run_root=run_root,
        wall_clock_cap_seconds=20 * 60,
    )
    result = {
        "passed": public["passed"],
        "completed_group_count": public["completed_group_count"],
        "logical_record_count": public["logical_record_count"],
        "timeout_count": public["timeout_count"],
        "provider_network_call_count": public["provider_network_call_count"],
        "failure_codes": public["failure_codes"],
    }
    return result


def _mock_profile(**overrides: Any) -> dict[str, Any]:
    profile = {
        "os": "linux",
        "architecture": "x64",
        "cgroup_version": "v1",
        "logical_cpu_count_visible": 96,
        "cpuset_cpu_count": 96,
        "cpu_quota_count": 12.0,
        "effective_cpu_quota_count": 12,
        "finite_cgroup_cpu_limit": True,
        "memory_cgroup_version": "v1",
        "host_total_memory_bytes": 384 * 1024**3,
        "host_available_memory_bytes": 320 * 1024**3,
        "cgroup_memory_limit_bytes": 40 * 1024**3,
        "cgroup_memory_current_bytes": 512 * 1024**2,
        "cgroup_available_memory_bytes": 39 * 1024**3,
        "finite_cgroup_memory_limit": True,
        "active_swap_total_bytes": 0,
        "scratch_free_bytes": 350 * 1024**3,
        "scratch_mount_device_major_minor": "9:0",
        "scratch_mount_root_length": 17,
        "scratch_filesystem_type": "xfs",
        "scratch_mount_source": "/dev/md0",
        "scratch_block_rotational": 0,
        "scratch_nonrotational_local_block_storage": True,
        "scratch_outside_checkout": True,
        "active_idle_cgroup_cpu_millicores": 25,
        "open_file_soft_limit": 65_535,
        "open_file_hard_limit": 1_048_576,
        "python_version": "3.10.8",
        "python_version_major": 3,
        "python_version_minor": 10,
        "python_version_micro": 8,
        "git_available": True,
        "git_version": "git version test",
        "rustc_available": True,
        "rustc_version": "rustc 1.95.0 (mock)",
        "cargo_available": True,
        "cargo_version": "cargo 1.95.0 (mock)",
        "openlocus_available": True,
        "openlocus_version": "openlocus test",
        "openlocus_bytes": 123,
        "openlocus_sha256": "1" * 64,
    }
    profile.update(overrides)
    return profile


def _mock_stress(*, passed: bool = True) -> dict[str, Any]:
    return {
        "executed": True,
        "passed": passed,
        "completed_group_count": 3 if passed else 2,
        "logical_record_count": 90 if passed else 60,
        "normal_record_count": 90 if passed else 60,
        "normal_accepted_count": 90 if passed else 60,
        "normal_rejected_count": 0,
        "timeout_count": 0,
        "terminal_support_record_count": 0,
        "parent_receipt_count": 90 if passed else 60,
        "parent_receipt_error_count": 0,
        "provider_network_call_count": 0,
        "wall_clock_cap_met": True,
        "failure_codes": [] if passed else ["stress_aggregate_gate_failed"],
    }


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    checks.append(("cpuset_parser", _cpuset_count("0-3,8,10-11") == 7))
    with tempfile.TemporaryDirectory(prefix="openlocus-b23-cgroup-") as tmp:
        root = Path(tmp)
        (root / "cpu").mkdir()
        (root / "cpuset").mkdir()
        (root / "memory").mkdir()
        (root / "cpu" / "cpu.cfs_quota_us").write_text("1200000\n", encoding="utf-8")
        (root / "cpu" / "cpu.cfs_period_us").write_text("100000\n", encoding="utf-8")
        (root / "cpuset" / "cpuset.cpus").write_text("0-95\n", encoding="utf-8")
        (root / "memory" / "memory.limit_in_bytes").write_text(
            str(40 * 1024**3), encoding="utf-8"
        )
        (root / "memory" / "memory.usage_in_bytes").write_text(
            str(512 * 1024**2), encoding="utf-8"
        )
        cpu_v1 = _cpu_limit_profile(root)
        memory_v1 = _memory_limit_profile(root)
        checks.append(("cgroup_v1_cpu_quota", cpu_v1["cpu_quota_count"] == 12.0))
        checks.append((
            "cgroup_v1_effective_cpu_minimum",
            cpu_v1["effective_cpu_quota_count"]
            == min(int(os.cpu_count() or 0), 96, 12),
        ))
        checks.append(("cgroup_v1_cpu_finite", cpu_v1["finite_cgroup_cpu_limit"] is True))
        checks.append(("cgroup_v1_memory_finite", memory_v1["finite_cgroup_memory_limit"] is True))
        checks.append((
            "cgroup_v1_memory_available",
            memory_v1["cgroup_available_memory_bytes"] == 40 * 1024**3 - 512 * 1024**2,
        ))
    with tempfile.TemporaryDirectory(prefix="openlocus-b23-cgroup2-") as tmp:
        root = Path(tmp)
        (root / "cpu.max").write_text("800000 100000\n", encoding="utf-8")
        (root / "cpuset.cpus.effective").write_text("0-15\n", encoding="utf-8")
        (root / "memory.max").write_text(str(32 * 1024**3), encoding="utf-8")
        (root / "memory.current").write_text(str(1024**3), encoding="utf-8")
        cpu_v2 = _cpu_limit_profile(root)
        memory_v2 = _memory_limit_profile(root)
        checks.append(("cgroup_v2_cpu_quota", cpu_v2["cpu_quota_count"] == 8.0))
        checks.append((
            "cgroup_v2_effective_cpu_minimum",
            cpu_v2["effective_cpu_quota_count"]
            == min(int(os.cpu_count() or 0), 16, 8),
        ))
        checks.append(("cgroup_v2_memory_finite", memory_v2["finite_cgroup_memory_limit"] is True))
    profile = _mock_profile()
    checks.append(("constrained_profile_passes", not validate_runner_profile(profile)))
    checks.append((
        "stable_profile_unchanged",
        not stable_runner_profile_changes(profile, copy.deepcopy(profile)),
    ))
    checks.append((
        "stable_profile_drift_detected",
        stable_runner_profile_changes(
            profile, _mock_profile(effective_cpu_quota_count=10)
        )
        == ["effective_cpu_quota_count"],
    ))
    checks.append((
        "weak_cpu_rejected",
        "effective_cpu_quota_below_minimum"
        in validate_runner_profile(_mock_profile(effective_cpu_quota_count=4)),
    ))
    checks.append((
        "weak_memory_rejected",
        "cgroup_memory_below_minimum"
        in validate_runner_profile(_mock_profile(cgroup_memory_limit_bytes=16 * 1024**3)),
    ))
    checks.append((
        "unbounded_cpu_rejected",
        "cgroup_cpu_limit_unavailable"
        in validate_runner_profile(_mock_profile(finite_cgroup_cpu_limit=False)),
    ))
    checks.append((
        "busy_container_rejected",
        "idle_cgroup_cpu_above_maximum"
        in validate_runner_profile(_mock_profile(active_idle_cgroup_cpu_millicores=500)),
    ))
    checks.append((
        "low_nofile_rejected",
        "open_file_soft_limit_below_minimum"
        in validate_runner_profile(_mock_profile(open_file_soft_limit=1024)),
    ))
    checks.append((
        "old_python_rejected",
        "python_version_below_minimum"
        in validate_runner_profile(
            _mock_profile(python_version="3.9.19", python_version_minor=9)
        ),
    ))
    checks.append((
        "wrong_rust_rejected",
        "rustc_version_mismatch"
        in validate_runner_profile(_mock_profile(rustc_version="rustc 1.94.0 (mock)")),
    ))
    checks.append((
        "weak_disk_rejected",
        "scratch_free_space_below_minimum"
        in validate_runner_profile(_mock_profile(scratch_free_bytes=80 * 1024**3)),
    ))
    io_pass = {
        "passed": True,
        "bytes": B23_IO_QUALIFICATION["file_bytes"],
        "write_seconds": 1.0,
        "read_seconds": 1.0,
        "write_bytes_per_second": 512 * 1024**2,
        "read_bytes_per_second": 512 * 1024**2,
        "content_hash_valid": True,
    }
    public = build_public_report(
        profile_admission_passed=True,
        profile_revalidation_executed=True,
        profile_passed=True,
        profile_failure_codes=[],
        io_public=io_pass,
        stress_public=_mock_stress(),
    )
    checks.append(("public_pass_valid", not validate_public_report(public)))
    checks.append(("public_pass_decision", public["decision"]["runner_qualified"] is True))
    failed_public = build_public_report(
        profile_admission_passed=False,
        profile_revalidation_executed=False,
        profile_passed=False,
        profile_failure_codes=["cgroup_memory_below_minimum"],
        io_public=None,
        stress_public=_empty_stress(),
    )
    checks.append(("public_fail_valid", not validate_public_report(failed_public)))
    checks.append(("profile_failure_short_circuits_io", failed_public["io_gate"]["executed"] is False))
    checks.append(("profile_failure_short_circuits_stress", failed_public["stress_gate"]["executed"] is False))
    checks.append(("private_input_never_read", failed_public["privacy"]["private_input_read"] is False))
    original_factory = b2r.make_b2_request
    with _longrun_timeout_override():
        override_active = b2r.make_b2_request is _make_b23_longrun_request
    checks.append(("longrun_timeout_override_active", override_active))
    checks.append(("frozen_request_factory_restored", b2r.make_b2_request is original_factory))
    with tempfile.TemporaryDirectory(prefix="openlocus-b23-boundary-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        scratch = root / "scratch"
        public = root / "public" / "aggregate.json"
        repo.mkdir()
        scratch.mkdir()
        try:
            validate_output_boundaries(
                repo_root=repo,
                scratch_root=scratch,
                private_receipt_path=scratch / "private.json",
                public_out_path=public,
            )
            valid_boundaries = True
        except B23QualificationError:
            valid_boundaries = False
        checks.append(("valid_output_boundaries", valid_boundaries))
        try:
            validate_output_boundaries(
                repo_root=repo,
                scratch_root=scratch,
                private_receipt_path=root / "outside-private.json",
                public_out_path=public,
            )
            private_escape_rejected = False
        except B23QualificationError:
            private_escape_rejected = True
        checks.append(("private_receipt_escape_rejected", private_escape_rejected))
        try:
            validate_output_boundaries(
                repo_root=repo,
                scratch_root=scratch,
                private_receipt_path=scratch / "private.json",
                public_out_path=scratch / "public.json",
            )
            public_in_private_rejected = False
        except B23QualificationError:
            public_in_private_rejected = True
        checks.append(("public_inside_private_rejected", public_in_private_rejected))
        atomic = root / "atomic" / "report.json"
        write_json(atomic, {"passed": True})
        checks.append((
            "atomic_json_complete",
            json.loads(atomic.read_text(encoding="utf-8")) == {"passed": True},
        ))
        try:
            write_json(atomic, {"passed": False})
            existing_output_rejected = False
        except B23QualificationError:
            existing_output_rejected = True
        checks.append(("existing_output_rejected", existing_output_rejected))
    forbidden = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
    }
    checks.append(("author_or_scorer_import_boundary", not bool(forbidden & set(sys.modules))))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    io_pass = {
        "passed": True,
        "bytes": B23_IO_QUALIFICATION["file_bytes"],
        "write_seconds": 1.0,
        "read_seconds": 1.0,
        "write_bytes_per_second": 512 * 1024**2,
        "read_bytes_per_second": 512 * 1024**2,
        "content_hash_valid": True,
    }
    base = build_public_report(
        profile_admission_passed=True,
        profile_revalidation_executed=True,
        profile_passed=True,
        profile_failure_codes=[],
        io_public=io_pass,
        stress_public=_mock_stress(),
    )
    checks: list[tuple[str, bool]] = []

    def rejected(name: str, mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_public_report(value))))

    rejected("unknown_key", lambda value: value.__setitem__("extra", True))
    rejected("digest_drift", lambda value: value.__setitem__("qualification_digest", "b23qual_" + "0" * 64))
    rejected("spec_drift", lambda value: value.__setitem__("b23_spec_digest", "drift"))
    rejected("private_input_read", lambda value: value["privacy"].__setitem__("private_input_read", True))
    rejected("hardware_profile_public", lambda value: value["profile_gate"].__setitem__("exact_observed_profile_public", True))
    rejected("throughput_public", lambda value: value["io_gate"].__setitem__("exact_observed_throughput_public", True))
    rejected("profile_revalidation_missing", lambda value: value["profile_gate"].__setitem__("post_stress_revalidation_executed", False))
    rejected("decision_drift", lambda value: value["decision"].__setitem__("runner_qualified", False))
    rejected("execution_overauthorized", lambda value: value["decision"].__setitem__("future_tournament_execution_authorized", True))
    rejected("status_drift", lambda value: value.__setitem__("status", PUBLIC_STATUS_FAIL))
    rejected("unexecuted_with_records", lambda value: (value["stress_gate"].__setitem__("executed", False), value["stress_gate"].__setitem__("logical_record_count", 90)))
    rejected("nested_unknown_key", lambda value: value["profile_gate"].__setitem__("extra", True))
    rejected("unknown_failure_code", lambda value: value["decision"].__setitem__("failure_codes", ["unknown_failure"]))
    rejected("malformed_failure_codes", lambda value: value["profile_gate"].__setitem__("failure_codes", 1))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.3 self-hosted runner qualifier")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--micro-test", action="store_true")
    mode.add_argument("--qualify", action="store_true")
    mode.add_argument("--validate-public", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--scratch-root", type=Path)
    parser.add_argument("--openlocus", type=Path)
    parser.add_argument("--private-receipt", type=Path)
    parser.add_argument("--public-out", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.fault_test:
        result = run_fault_test()
        print(json.dumps(result, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.validate_public:
        value = json.loads(args.validate_public.read_text(encoding="utf-8"))
        errors = validate_public_report(value)
        print(json.dumps({"passed": not errors, "errors": errors}, sort_keys=True))
        return 0 if not errors else 1
    if args.micro_test:
        if args.scratch_root is None or args.openlocus is None:
            raise SystemExit("--micro-test requires --scratch-root and --openlocus")
        os.environ["OPENLOCUS_CLI"] = str(args.openlocus.resolve(strict=True))
        result = run_micro_test(
            scratch_root=args.scratch_root,
            cli_path=args.openlocus,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["passed"] else 1
    required = (
        args.repo_root,
        args.scratch_root,
        args.openlocus,
        args.private_receipt,
        args.public_out,
    )
    if any(value is None for value in required):
        raise SystemExit(
            "--qualify requires --repo-root, --scratch-root, --openlocus, "
            "--private-receipt, and --public-out"
        )
    os.environ["OPENLOCUS_CLI"] = str(args.openlocus.resolve(strict=True))
    public, _ = qualify_runner(
        repo_root=args.repo_root,
        scratch_root=args.scratch_root,
        cli_path=args.openlocus,
        private_receipt_path=args.private_receipt,
        public_out_path=args.public_out,
    )
    print(
        json.dumps(
            {
                "runner_qualified": public["decision"]["runner_qualified"],
                "failure_codes": public["decision"]["failure_codes"],
                "qualification_digest": public["qualification_digest"],
                "private_input_read": public["privacy"]["private_input_read"],
            },
            sort_keys=True,
        )
    )
    return 0 if public["decision"]["runner_qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "collect_runner_profile",
    "validate_runner_profile",
    "stable_runner_profile_changes",
    "generate_fixture",
    "run_sustained_stress",
    "build_public_report",
    "validate_public_report",
    "validate_output_boundaries",
    "qualify_runner",
    "run_micro_test",
]
