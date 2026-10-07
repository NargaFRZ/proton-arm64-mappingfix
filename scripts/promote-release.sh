#!/usr/bin/env bash
set -euo pipefail

task_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$task_root"

mapfile -t release_fields < <(python3 - <<'PY'
import json
with open('build-info.json') as stream:
    data = json.load(stream)
original = data['original_build']
release = data['release']
for value in (original['repository'], original['artifact_id'], original['artifact_zip_sha256'],
              original['archive_sha256'], original['archive_root'], data['archive_name'],
              data['archive_root'], release['sha256'], release['size_bytes']):
    print(value)
PY
)
source_repo=${release_fields[0]}
source_artifact_id=${release_fields[1]}
zip_checksum=${release_fields[2]}
original_checksum=${release_fields[3]}
source_tree=${release_fields[4]}
archive_name=${release_fields[5]}
tool_tree=${release_fields[6]}
release_checksum=${release_fields[7]}
release_size=${release_fields[8]}

promote_dir="$task_root/.promotion"
test ! -e "$promote_dir"
mkdir -p "$promote_dir/input" "$promote_dir/staging" output logs
gh api --method GET "repos/$source_repo/actions/artifacts/$source_artifact_id/zip" > "$promote_dir/input.zip"
printf '%s  %s\n' "$zip_checksum" "$promote_dir/input.zip" | sha256sum -c -
unzip -tq "$promote_dir/input.zip"
unzip -q "$promote_dir/input.zip" -d "$promote_dir/input"
printf '%s  %s\n' "$original_checksum" "$promote_dir/input/$archive_name" | sha256sum -c -

tar --same-permissions --no-same-owner -xJf "$promote_dir/input/$archive_name" -C "$promote_dir/staging"
mv "$promote_dir/staging/$source_tree" "$promote_dir/staging/$tool_tree"
python3 scripts/validate.py tree "$promote_dir/staging/$tool_tree" | tee logs/release-tree-validation.json

tar --sort=name --owner=0 --group=0 --numeric-owner -C "$promote_dir/staging" -cf - "$tool_tree" | \
    xz -T4 -6 > "output/$archive_name"
sha256sum "output/$archive_name" | tee logs/release-checksum.txt
printf '%s  %s\n' "$release_checksum" "output/$archive_name" | sha256sum -c -
test "$(stat -c %s "output/$archive_name")" = "$release_size"
xz --test "output/$archive_name"
python3 scripts/validate.py archive "output/$archive_name" | tee logs/release-archive-validation.json
tar -tJf "output/$archive_name" > logs/release-archive-contents.txt
(cd output && sha256sum "$archive_name" > "$archive_name.sha256")
