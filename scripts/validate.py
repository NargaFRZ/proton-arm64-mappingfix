#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import tarfile

TOOL_NAME = 'Proton 11 ARM64 MappingFix'
CORE_ELFS = (
    'files/bin-arm64/wine',
    'files/bin-arm64/wineserver',
    'files/lib/wine/aarch64-unix/ntdll.so',
)
REQUIRED = ('proton', 'toolmanifest.vdf', 'compatibilitytool.vdf', 'version')
FORBIDDEN = {'.git', '.gitmodules', '.github', 'CMakeCache.txt', 'compile_commands.json', 'autom4te.cache'}


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def check_source(root):
    source = root / 'dlls/ntdll/unix/virtual.c'
    text = source.read_text()
    start = text.index('void virtual_free_teb( TEB *teb )')
    end = text.index('\n}\n', start)
    function = text[start:end]
    expected = '''    if (teb->ChpeV2CpuAreaInfo)
    {
        void *base = (char *)teb->ChpeV2CpuAreaInfo - kernel_stack_guard_size;
        size = 0;
        NtFreeVirtualMemory( GetCurrentProcess(), &base, &size, MEM_RELEASE );
        teb->ChpeV2CpuAreaInfo = NULL;
    }'''
    require(expected in function, 'CPU-area allocation-base release is missing')
    require('(void **)&teb->ChpeV2CpuAreaInfo' not in function, 'Offset pointer is still passed to MEM_RELEASE')
    allocation = (root / 'dlls/ntdll/unix/thread.c').read_text()
    require('cpu_area = (CHPE_V2_CPU_AREA_INFO *)((char*)stack.DeallocationStack + kernel_stack_guard_size);' in allocation,
            'CPU-area allocation has changed: review the subtraction before building')
    print(json.dumps({'source': str(source), 'mapping_fix': True,
                      'virtual_c_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))


def elf_arch(data, name):
    require(data[:4] == b'\x7fELF', f'{name}: expected ELF binary')
    require(len(data) >= 20 and data[4] == 2 and data[5] == 1, f'{name}: expected 64-bit little-endian ELF')
    machine = struct.unpack_from('<H', data, 18)[0]
    require(machine == 183, f'{name}: expected AArch64 (183), found {machine}')


def check_tree(root):
    for name in REQUIRED:
        require((root / name).is_file(), f'Missing {name}')
    require((root / 'files').is_dir(), 'Missing files directory')
    require(os.access(root / 'proton', os.X_OK), 'proton launcher is not executable')
    manifest = (root / 'compatibilitytool.vdf').read_text()
    require(re.search(r'"display_name"\s+"Proton 11 ARM64 MappingFix"', manifest), 'Incorrect Steam display name')
    require('bin-arm64' in (root / 'proton').read_text(), 'Proton launcher is missing ARM64 support')
    elfs = []
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        require(not (set(relative.parts) & FORBIDDEN), f'Build/source metadata found: {relative}')
        require(not any(part.startswith(('src-', 'obj-', 'dst-')) for part in relative.parts), f'Build directory found: {relative}')
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as stream:
                header = stream.read(20)
            if header[:4] == b'\x7fELF':
                elf_arch(header, str(relative))
                elfs.append(str(relative))
    for name in CORE_ELFS:
        path = root / name
        require(path.is_file(), f'Missing ARM64 core binary: {name}')
        with path.open('rb') as stream:
            elf_arch(stream.read(20), name)
    require(elfs, 'No ARM64 ELF binaries found')
    print(json.dumps({'tree': str(root), 'architecture': 'AArch64', 'elf_count': len(elfs),
                      'launcher_executable': True, 'source_metadata_absent': True, 'core_binaries': list(CORE_ELFS)}))


def check_archive(path):
    with tarfile.open(path, 'r:xz') as archive:
        members = archive.getmembers()
        names = {m.name.rstrip('/'): m for m in members}
        tops = set()
        for member in members:
            require(not member.name.startswith('/'), f'Absolute archive path: {member.name}')
            relative = PurePosixPath(member.name)
            require('..' not in relative.parts, f'Unsafe archive path: {member.name}')
            require(not (set(relative.parts) & FORBIDDEN), f'Source metadata in archive: {member.name}')
            tops.add(relative.parts[0])
        require(tops == {TOOL_NAME}, f'Expected exactly one top-level directory: found {tops}')
        require(names[TOOL_NAME].isdir(), 'Top-level entry is not a directory')
        for name in REQUIRED:
            member = names.get(f'{TOOL_NAME}/{name}')
            require(member is not None and member.isfile(), f'Archive missing {name}')
        require(names[f'{TOOL_NAME}/proton'].mode & 0o111, 'Archive launcher lacks execute permission')
        require(names.get(f'{TOOL_NAME}/files') is not None and names[f'{TOOL_NAME}/files'].isdir(), 'Archive missing files directory')
        for name in CORE_ELFS:
            member = archive.getmember(f'{TOOL_NAME}/{name}')
            with archive.extractfile(member) as stream:
                elf_arch(stream.read(20), name)
    print(json.dumps({'archive': str(path), 'size_bytes': path.stat().st_size, 'top_level': TOOL_NAME,
                      'structure_passed': True, 'core_architecture_passed': True}))


if __name__ == '__main__':
    require(len(sys.argv) == 3, 'usage: validate.py source|tree|archive PATH')
    functions = {'source': check_source, 'tree': check_tree, 'archive': check_archive}
    require(sys.argv[1] in functions, 'Invalid validation mode')
    functions[sys.argv[1]](Path(sys.argv[2]))
