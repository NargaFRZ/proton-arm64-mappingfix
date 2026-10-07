Full native ARM64 Proton 11 redistributable for DroidDeck, with the generic ARM64EC emulator-stack mapping leak fix.

- Proton: `proton-11.0-2c` (`5b89db940e0ebe3a137a6009a3589232fe084c09`).
- Valve Wine: `dc26e61847081a1b5cb0733dc30feba6ee575482`, plus the allocation-base release fix in `virtual_free_teb()`.
- Built with Valve's Steam Runtime 4 ARM64 LLVM SDK and `--target-arch=arm64`.
- Size: **349,301,768 bytes (333.12 MiB)**.
- Structure, executable launcher and XZ integrity verified; **127 native ELF files are AArch64**.
- The fix was verified in the patched source and compiled `ntdll.so`.

Download `Proton-11-ARM64-MappingFix.tar.xz` and its `.sha256` file below. The archive has one normal Proton tool directory, `Proton 11 ARM64 MappingFix/`.

SHA-256:

```text
bb5ab7257ce0eddffa031b50acc373989682243b07b0abff418df8486c28e341
```

Install after copying the archive to the phone's Download folder:

```bash
droiddeck-proton-extra \
  /root/.local/share/Steam \
  /root/Storage/Download/Proton-11-ARM64-MappingFix.tar.xz
```

Fully restart DroidDeck and Steam, then choose:

**Fate/stay night REMASTERED → Properties → Compatibility → Force the use of a specific Steam Play compatibility tool → Proton 11 ARM64 MappingFix**

The optional thread stress test timed out without mapping measurements. Runtime mapping stability and Android/Fate gameplay remain unverified.
