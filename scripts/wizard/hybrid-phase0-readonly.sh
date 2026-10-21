#!/usr/bin/env bash
# Hybrid H6 Phase-0 inventory. Strictly read-only; not a start/retire authorization.
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "$0")/../.." && pwd -P)"
MODEL_ROOT="$ROOT_DIR/models"
if [[ -v QWEN38_PHASE0_MODELS_ROOT ]]; then MODEL_ROOT="$QWEN38_PHASE0_MODELS_ROOT"; fi
blocked() {
  printf 'HYBRID_PHASE0_READONLY=BLOCKED reason=%s\n' "$1" >&2
  exit 2
}
trap 'rc=$?; printf "HYBRID_PHASE0_READONLY=BLOCKED command_failed_rc=%s\n" "$rc" >&2' ERR
(( $# == 0 )) || blocked "unexpected_arguments"
[[ "$MODEL_ROOT" = /* && -d "$MODEL_ROOT" && ! -L "$MODEL_ROOT" ]] ||
  blocked "model_root_missing_or_symlinked"
printf '=== SOURCE ===\n'
git -C "$ROOT_DIR" rev-parse HEAD
dirty="$(git -C "$ROOT_DIR" status --porcelain=v1 --untracked-files=all)"
[[ -z "$dirty" ]] || blocked "dirty_checkout"
printf '=== MANAGED HOST IDLE ===\n'
python3 -B "$ROOT_DIR/scripts/diagnostics/verify-managed-idle.py"
base="$MODEL_ROOT/qwen3.8-flash-next-orcarouter"
h3="$MODEL_ROOT/qwen3.8-hybrid-quant-layout"
h4="$MODEL_ROOT/qwen3.8-h4-orca-all"
h5="$MODEL_ROOT/qwen3.8-h5-neutral-input-scale"
h6="$MODEL_ROOT/qwen3.8-h6-modelopt-w4a16"
for stage in "$base" "$h3" "$h4" "$h5" "$h6"; do
  [[ -d "$stage" && ! -L "$stage" ]] ||
    blocked "missing_or_symlinked_stage:$(basename -- "$stage")"
done
printf '=== H6 RUNTIME-ONLY VALIDATION ===\n'
python3 -B "$ROOT_DIR/scripts/model/validate-orcarouter-hybrid.py" \
  --runtime-only --base-dir "$base" --h3-dir "$h3" \
  --h4-dir "$h4" --h5-dir "$h5" --model-dir "$h6"
printf '=== METADATA HASHES (NO TENSOR CONTENT HASHES) ===\n'
for stage in "$base" "$h3" "$h4" "$h5" "$h6"; do
  count=0
  for file in .qwen38-model-manifest.json .qwen38-hybrid-manifest.json; do
    metadata="$stage/$file"
    if [[ -e "$metadata" || -L "$metadata" ]]; then
      [[ -f "$metadata" && ! -L "$metadata" ]] ||
        blocked "invalid_manifest_object:$(basename -- "$stage")/$file"
      sha256sum -- "$metadata"
      count=$((count + 1))
    fi
  done
  (( count > 0 )) || blocked "missing_manifest:$(basename -- "$stage")"
  index="$stage/model.safetensors.index.json"
  if [[ -e "$index" || -L "$index" ]]; then
    [[ -f "$index" && ! -L "$index" ]] ||
      blocked "invalid_index_object:$(basename -- "$stage")"
    sha256sum -- "$index"
  fi
done
printf '=== ACTUAL BLOCK ALLOCATION AND LINK COUNTS ===\n'
df -B1 -- "$MODEL_ROOT"
df -i -- "$MODEL_ROOT"
for stage in "$base" "$h3" "$h4" "$h5" "$h6"; do
  du -s -B1 -- "$stage"
  printf 'STAGE=%s SYMLINK_ENTRIES=' "$(basename -- "$stage")"
  find "$stage" -type l -printf '.\n' | wc -l
  printf 'STAGE=%s MULTILINK_REGULAR_FILES=' "$(basename -- "$stage")"
  find "$stage" -type f -links +1 -printf '.\n' | wc -l
done
printf 'STAGE_DU_VALUES_MAY_DOUBLE_COUNT_SHARED_BLOCKS=YES\n'
printf '=== PROJECT ASSETS ===\n'
bash "$ROOT_DIR/scripts/manage-models.sh" assets
printf '=== ALL DOCKER CONTAINERS AND MOUNTS ===\n'
docker ps -a --no-trunc --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}'
ids="$(docker ps -aq --no-trunc)"
while IFS= read -r id; do
  [[ -n "$id" ]] || continue
  [[ "$id" =~ ^[[:xdigit:]]{64}$ ]] || blocked "invalid_docker_id"
  docker inspect --format '{{.Id}} {{json .Mounts}}' "$id"
done <<< "$ids"
printf 'HYBRID_BENCH_AUTHORIZED=NO\n'
printf 'HYBRID_STAGE_DELETION_AUTHORIZED=NO\n'
printf 'EXTERNAL_H7_H20_RELEASE_DEPENDENCIES=NOT_YET_QUALIFIED\n'
printf 'HYBRID_PHASE0_READONLY=PASS_STATIC_INVENTORY_ONLY\n'
