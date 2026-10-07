#!/usr/bin/env bash
set -euo pipefail

export PROTON_REVISION=5b89db940e0ebe3a137a6009a3589232fe084c09
export WINE_REVISION=dc26e61847081a1b5cb0733dc30feba6ee575482
export PROTON_SDK=registry.gitlab.steamos.cloud/proton/steamrt4/sdk/arm64-llvm:4.0.20260331.220802-2
export BUILD_DISPLAY_NAME='Proton 11 ARM64 MappingFix'
export TOOL_NAME=Proton-11-ARM64-MappingFix
export PROTON_TREE_NAME='Proton 11 ARM64 MappingFix'

task_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$task_root"
mkdir -p logs output
test "$(uname -m)" = aarch64
stage=${1:-all}
case "$stage" in all|sources|configure|compile|package) ;; *) exit 2 ;; esac

if [[ $stage == sources || $stage == all ]]; then
docker info > logs/docker-info.txt
df -h .
git clone --depth=1 --branch proton_11.0 --single-branch https://github.com/ValveSoftware/Proton.git proton-source
git -C proton-source fetch --depth=1 origin "$PROTON_REVISION"
git -C proton-source checkout --detach "$PROTON_REVISION"
git -C proton-source submodule update --init --recursive --depth=1 --jobs=4
git -C proton-source/FEX fetch --unshallow --tags origin
git -C proton-source/FEX describe --abbrev=7
test "$(git -C proton-source rev-parse HEAD)" = "$PROTON_REVISION"
test "$(git -C proton-source/wine rev-parse HEAD)" = "$WINE_REVISION"
git -C proton-source/wine apply --check "$task_root/patches/arm64ec-mapping-base.patch"
git -C proton-source/wine apply "$task_root/patches/arm64ec-mapping-base.patch"
git -C proton-source/wine diff --check
git -C proton-source/wine diff -- dlls/ntdll/unix/virtual.c > logs/applied-wine.patch
git -C proton-source submodule status --recursive > logs/submodule-revisions.txt

python3 scripts/validate.py source proton-source/wine
fi

if [[ $stage == configure || $stage == all ]]; then
mkdir proton-build
cd proton-build
../proton-source/configure.sh --target-arch=arm64 \
    --build-name="$BUILD_DISPLAY_NAME" --container-engine=docker \
    --proton-sdk-image="$PROTON_SDK" 2>&1 | tee ../logs/configure.log
cd "$task_root"
fi

if [[ $stage == compile || $stage == all ]]; then
cd proton-build
make -j"$(nproc)" "BUILD_NAME=$BUILD_DISPLAY_NAME" "INTERNAL_TOOL_NAME=$TOOL_NAME" \
    ENABLE_CCACHE=0 redist 2>&1 | tee ../logs/build.log
cd "$task_root"
fi

if [[ $stage == package || $stage == all ]]; then
python3 scripts/validate.py source proton-build/src-wine
cmp proton-source/wine/dlls/ntdll/unix/virtual.c proton-build/src-wine/dlls/ntdll/unix/virtual.c
docker image inspect "$PROTON_SDK" > logs/sdk-image.json
python3 scripts/validate.py tree proton-build/redist
mv proton-build/redist "output/$PROTON_TREE_NAME"
tar --sort=name --owner=0 --group=0 --numeric-owner -C output -cf - "$PROTON_TREE_NAME" | \
    xz -T4 -6 > "output/$TOOL_NAME.tar.xz"
xz --test "output/$TOOL_NAME.tar.xz"
python3 scripts/validate.py archive "output/$TOOL_NAME.tar.xz"
tar -tf "output/$TOOL_NAME.tar.xz" > logs/archive-contents.txt
head -100 logs/archive-contents.txt
cd output
sha256sum "$TOOL_NAME.tar.xz" > "$TOOL_NAME.tar.xz.sha256"
sha256sum -c "$TOOL_NAME.tar.xz.sha256"
stat -c '%n: %s bytes' "$TOOL_NAME.tar.xz"
fi
