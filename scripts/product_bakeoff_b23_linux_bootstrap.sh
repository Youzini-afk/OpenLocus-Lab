#!/usr/bin/env bash
set -euo pipefail

parse_sha256_file() {
  awk 'NR == 1 {print $1}' "$1"
}

if [[ "${1:-}" == "--self-test" ]]; then
  sample="$(printf 'a%.0s' {1..64})"
  observed="$(parse_sha256_file <(printf '%s *./rustup-init\n' "$sample"))"
  [[ "$observed" == "$sample" ]]
  printf 'B2.3 bootstrap self-test passed\n'
  exit 0
fi

# Idempotent bootstrap for the inspected quota-limited Ubuntu 22.04 container.
# It installs the pinned Rust toolchain on the paid data volume and deliberately
# does not register a GitHub runner or read any private B2.3 input.

umask 077

: "${OPENLOCUS_B23_DATA_ROOT:?set OPENLOCUS_B23_DATA_ROOT to the private data-volume path}"
DATA_ROOT="$OPENLOCUS_B23_DATA_ROOT"
PYTHON_REQUESTED="${OPENLOCUS_B23_PYTHON:-python3}"
RUSTUP_VERSION="1.29.0"
RUST_TOOLCHAIN="1.95.0"
RUST_TARGET="x86_64-unknown-linux-gnu"

case "$DATA_ROOT" in
  /*) ;;
  *) echo "OPENLOCUS_B23_DATA_ROOT must be absolute" >&2; exit 2 ;;
esac
if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "B2.3 bootstrap requires Linux x86_64" >&2
  exit 2
fi
for command_name in awk curl git readlink sha256sum; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "B2.3 bootstrap dependency is unavailable: $command_name" >&2
    exit 2
  fi
done
if ! PYTHON_BIN="$(command -v "$PYTHON_REQUESTED")"; then
  echo "B2.3 Python interpreter is unavailable" >&2
  exit 2
fi
PYTHON_BIN="$(readlink -f "$PYTHON_BIN")"
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 2)'; then
  echo "B2.3 requires Python 3.10 or newer" >&2
  exit 2
fi

mkdir -p "$DATA_ROOT"
DATA_ROOT="$(readlink -f "$DATA_ROOT")"
if [[ "$DATA_ROOT" == "/" || "$DATA_ROOT" == "/root" ]]; then
  echo "refusing unsafe B2.3 data root" >&2
  exit 2
fi

managed_directories=(
  "$DATA_ROOT/checkout"
  "$DATA_ROOT/logs"
  "$DATA_ROOT/public"
  "$DATA_ROOT/runner"
  "$DATA_ROOT/scratch"
  "$DATA_ROOT/toolchains/cargo"
  "$DATA_ROOT/toolchains/rustup"
  "$DATA_ROOT/toolchains/target"
)
mkdir -p "${managed_directories[@]}"
chmod 700 "$DATA_ROOT" "${managed_directories[@]}"

export CARGO_HOME="$DATA_ROOT/toolchains/cargo"
export RUSTUP_HOME="$DATA_ROOT/toolchains/rustup"
export CARGO_TARGET_DIR="$DATA_ROOT/toolchains/target"
export PATH="$CARGO_HOME/bin:$PATH"
export OPENLOCUS_B23_DATA_ROOT="$DATA_ROOT"
export OPENLOCUS_B23_SCRATCH_ROOT="$DATA_ROOT/scratch"
export OPENLOCUS_B23_PYTHON="$PYTHON_BIN"

if [[ ! -x "$CARGO_HOME/bin/rustup" ]]; then
  installer="$DATA_ROOT/toolchains/rustup-init"
  checksum="$installer.sha256"
  base="https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/${RUST_TARGET}/rustup-init"
  curl --fail --location --proto '=https' --tlsv1.2 --silent --show-error \
    "$base" --output "$installer"
  curl --fail --location --proto '=https' --tlsv1.2 --silent --show-error \
    "$base.sha256" --output "$checksum"
  expected="$(parse_sha256_file "$checksum")"
  observed="$(sha256sum "$installer" | awk '{print $1}')"
  if [[ ! "$expected" =~ ^[0-9a-f]{64}$ || "$observed" != "$expected" ]]; then
    echo "rustup-init checksum verification failed" >&2
    rm -f "$installer" "$checksum"
    exit 2
  fi
  chmod 700 "$installer"
  "$installer" -y --no-modify-path --profile minimal --default-toolchain "$RUST_TOOLCHAIN"
  rm -f "$installer" "$checksum"
else
  "$CARGO_HOME/bin/rustup" toolchain install "$RUST_TOOLCHAIN" --profile minimal
  "$CARGO_HOME/bin/rustup" default "$RUST_TOOLCHAIN"
fi

observed_rustup="$("$CARGO_HOME/bin/rustup" --version | awk 'NR == 1 {print $2}')"
if [[ "$observed_rustup" != "$RUSTUP_VERSION" ]]; then
  echo "rustup version does not match the frozen B2.3 version" >&2
  exit 2
fi
observed_rustc="$(rustc --version)"
observed_cargo="$(cargo --version)"
if [[ "$observed_rustc" != "rustc ${RUST_TOOLCHAIN} "* ]]; then
  echo "rustc version does not match the frozen B2.3 toolchain" >&2
  exit 2
fi
if [[ "$observed_cargo" != "cargo ${RUST_TOOLCHAIN} "* ]]; then
  echo "cargo version does not match the frozen B2.3 toolchain" >&2
  exit 2
fi

env_file="$DATA_ROOT/b23-env.sh"
{
  printf 'export OPENLOCUS_B23_DATA_ROOT=%q\n' "$DATA_ROOT"
  printf 'export OPENLOCUS_B23_SCRATCH_ROOT=%q\n' "$DATA_ROOT/scratch"
  printf 'export OPENLOCUS_B23_PYTHON=%q\n' "$PYTHON_BIN"
  printf 'export CARGO_HOME=%q\n' "$CARGO_HOME"
  printf 'export RUSTUP_HOME=%q\n' "$RUSTUP_HOME"
  printf 'export CARGO_TARGET_DIR=%q\n' "$CARGO_TARGET_DIR"
  printf 'export PATH=%q:$PATH\n' "$CARGO_HOME/bin"
  printf 'ulimit -n 65535\n'
} > "$env_file"
chmod 600 "$env_file"

ulimit -n 65535
"$PYTHON_BIN" --version
git --version
rustc --version
cargo --version
printf 'B2.3 bootstrap ready at %s\n' "$DATA_ROOT"
