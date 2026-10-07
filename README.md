# Proton ARM64 MappingFix

Custom Valve Proton 11 ARM64 builds for DroidDeck, with a generic fix for the ARM64EC emulator-stack mapping leak during thread exit.

Download **Proton-11-ARM64-MappingFix.tar.xz** and its checksum from [Releases](https://github.com/NargaFRZ/proton-arm64-mappingfix/releases/latest).

## Current release

| Item | Value |
| --- | --- |
| Display name | Proton 11 ARM64 MappingFix |
| Proton base | `proton-11.0-2c` / `5b89db940e0ebe3a137a6009a3589232fe084c09` |
| Valve Wine base | `dc26e61847081a1b5cb0733dc30feba6ee575482` |
| Build target | `--target-arch=arm64` |
| SDK | Valve Steam Runtime 4 ARM64 LLVM, `4.0.20260331.220802-2` |
| Archive size | 335.11 MiB (351,383,864 bytes) |
| Archive root | `Proton 11 ARM64 MappingFix/` |
| Validation | 127 native ELF files are AArch64; layout, launcher permissions and XZ integrity passed |

SHA-256:

```text
d0ad2c1c8816a2272ef6391810da3a82c39df4f687accedb412f023f2e217ae6
```

The archive contains the complete Proton redistributable, including its launcher, manifests, ARM64 Wine, FEX integration and Windows compatibility libraries. Windows PE modules use the architectures required by the ARM64 Proton stack.

## Install in DroidDeck

Copy the archive to the phone's Download folder. In the DroidDeck Linux environment, run:

```bash
droiddeck-proton-extra \
  /root/.local/share/Steam \
  /root/Storage/Download/Proton-11-ARM64-MappingFix.tar.xz
```

Fully restart DroidDeck and Steam. Select:

**Fate/stay night REMASTERED → Properties → Compatibility → Force the use of a specific Steam Play compatibility tool → Proton 11 ARM64 MappingFix**

The same compatibility tool can be selected for other games. The fix applies to thread cleanup generally.

The archive has one top-level directory containing `toolmanifest.vdf`, `compatibilitytool.vdf`, `proton`, `version` and `files/`. The directory uses spaces because DroidDeck derives the display name from the extracted folder. The normal ARM64 layout includes `files/bin-arm64/` and `files/lib/wine/aarch64-unix/`.

## Mapping fix

Wine places `ChpeV2CpuAreaInfo` one `kernel_stack_guard_size` beyond the emulator-stack allocation base. Passing that offset pointer to `NtFreeVirtualMemory(..., MEM_RELEASE)` fails to release the allocation.

The patch changes `virtual_free_teb()` to subtract the guard size, release the allocation through a local base pointer and clear `ChpeV2CpuAreaInfo`. It preserves the rest of the pinned Valve Wine source.

References:

- [GameNative PR 42](https://github.com/GameNative/proton-wine/pull/42)
- [GameNative PR 43](https://github.com/GameNative/proton-wine/pull/43)
- [GameNative PR 44](https://github.com/GameNative/proton-wine/pull/44)
- [Valve Proton](https://github.com/ValveSoftware/Proton)
- [DroidDeck](https://github.com/Droid-Deck/DroidDeck)

## Build

Use a native Linux AArch64 host with Docker, Git, Make, Python 3, rsync, file, binutils and xz-utils. The Valve SDK supplies the compilers and build dependencies. Allow several hours and at least 100 GB of working disk space.

```bash
git clone https://github.com/NargaFRZ/proton-arm64-mappingfix.git
cd proton-arm64-mappingfix
bash scripts/build.sh
```

The script fetches the pinned Proton revision and its exact submodules, restores FEX tags required by its build, applies the Wine patch, configures Valve's SDK with `--target-arch=arm64`, and runs the full `make redist` build. The packaged archive and checksum are written to `output/`.

The individual stages are `sources`, `configure`, `compile` and `package`, run in that order. Build logs and submodule revisions are written to `logs/`.

The **Build Proton ARM64 MappingFix** workflow runs the same stages on `ubuntu-24.04-arm`. Start it manually from the repository's Actions page. Its completed archive, checksum and build evidence are available as workflow artifacts.

## Validation and limits

`scripts/validate.py` checks the source fix, executable launcher, manifests, ARM64 native ELF headers, archive root and unwanted source/build metadata. The actual source copied into the Wine build was compared with the patched source. Disassembly of the released `ntdll.so` confirmed the 4 KiB subtraction and pointer clear in `virtual_free_teb()`.

The optional x64 thread-churn test warms up with 2,048 thread exits, then attempts 64,000 more exits while sampling `/proc/<wine-pid>/maps`. The original test attempt timed out without mapping measurements. Runtime mapping stability and Android/Fate gameplay remain unverified. The optional runtime workflow reports an unavailable test as a failed verification, rather than a pass.

Start **Verify ARM64EC thread cleanup** manually with the run ID of a completed build from this repository. Results and stderr are uploaded as runtime evidence.

The release contains all 8,836 entries from the complete compiled output. Every file payload, permission, timestamp and link is compared with the original build archive before publication. This package replaces the earlier incomplete local repack.

The build recipe is pinned; a later rebuild has fresh timestamps and may have a different archive checksum. `build-info.json` records the provenance and checksum of the released binary. The release retains the original upstream redistributable license files.
