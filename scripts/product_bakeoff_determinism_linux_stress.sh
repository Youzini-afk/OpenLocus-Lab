#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"

require_uint() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]] || (( value < 1 )); then
    printf '%s must be a positive integer\n' "$name" >&2
    exit 2
  fi
}

run_stress() {
  local file_count="$1"
  local rrf_spans="$2"
  local process_iterations="$3"
  local profile_flag=()
  if [[ "${OPENLOCUS_DETERMINISM_STRESS_RELEASE:-1}" == "1" ]]; then
    profile_flag=(--release)
  fi

  cd "$repo_root"
  local iteration
  for ((iteration = 1; iteration <= process_iterations; iteration++)); do
    printf 'synthetic determinism process iteration %d/%d\n' \
      "$iteration" "$process_iterations"
    OPENLOCUS_DETERMINISM_STRESS_FILES="$file_count" \
      cargo test --quiet --locked "${profile_flag[@]}" -p openlocus-index \
        persistent_bm25_large_equal_score_boundary_stress -- \
        --ignored --test-threads=1
    OPENLOCUS_DETERMINISM_STRESS_FILES="$file_count" \
      cargo test --quiet --locked "${profile_flag[@]}" -p openlocus-retrieval \
        bm25_large_equal_score_boundary_stress -- \
        --ignored --test-threads=1
    OPENLOCUS_DETERMINISM_STRESS_RRF_SPANS="$rrf_spans" \
      cargo test --quiet --locked "${profile_flag[@]}" -p openlocus-retrieval \
        rrf_large_ambiguous_overlap_conserves_score_without_positional_bias -- \
        --ignored --test-threads=1
  done

  printf '{"schema_version":"product_bakeoff_determinism_linux_stress.v1",'
  printf '"synthetic_only":true,"private_input_read":false,'
  printf '"file_count":%d,"rrf_span_count":%d,' "$file_count" "$rrf_spans"
  printf '"process_iterations":%d,"passed":true}\n' "$process_iterations"
}

case "$mode" in
  --self-test)
    [[ "$(uname -s)" == "Linux" ]]
    command -v cargo >/dev/null
    OPENLOCUS_DETERMINISM_STRESS_RELEASE=0 run_stress 64 128 1
    ;;
  --run)
    [[ "$(uname -s)" == "Linux" ]]
    command -v cargo >/dev/null
    file_count="${OPENLOCUS_DETERMINISM_STRESS_FILES:-20000}"
    rrf_spans="${OPENLOCUS_DETERMINISM_STRESS_RRF_SPANS:-4096}"
    process_iterations="${OPENLOCUS_DETERMINISM_STRESS_PROCESSES:-3}"
    require_uint OPENLOCUS_DETERMINISM_STRESS_FILES "$file_count"
    require_uint OPENLOCUS_DETERMINISM_STRESS_RRF_SPANS "$rrf_spans"
    require_uint OPENLOCUS_DETERMINISM_STRESS_PROCESSES "$process_iterations"
    run_stress "$file_count" "$rrf_spans" "$process_iterations"
    ;;
  *)
    printf 'usage: %s --self-test|--run\n' "$0" >&2
    exit 2
    ;;
esac
