#!/usr/bin/env python3
"""Verify redistributable payloads across top-level renaming and owner normalization."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import PurePosixPath
import tarfile


def relative_name(name):
    parts = PurePosixPath(name).parts
    if not parts or '..' in parts or name.startswith('/'):
        raise ValueError(f'Unsafe archive path: {name}')
    return '/'.join(parts[1:])


def manifest(path):
    entries = {}
    hardlinks = {}
    with tarfile.open(path, 'r|xz') as archive:
        for member in archive:
            name = relative_name(member.name)
            if name in entries:
                raise ValueError(f'Duplicate archive member: {member.name}')
            item = {'mode': member.mode, 'mtime': member.mtime}
            if member.isfile():
                digest = hashlib.sha256()
                size = 0
                with archive.extractfile(member) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                        size += len(block)
                if size != member.size:
                    raise ValueError(f'Truncated file: {member.name}')
                item.update(kind='file', size=size, sha256=digest.hexdigest())
            elif member.isdir():
                item.update(kind='directory')
            elif member.issym():
                item.update(kind='symlink', target=member.linkname)
            elif member.islnk():
                item.update(kind='hardlink')
                hardlinks[name] = relative_name(member.linkname)
            else:
                raise ValueError(f'Unexpected member type: {member.name}')
            entries[name] = item

    def resolve(name, seen):
        if name in seen:
            raise ValueError(f'Hardlink cycle: {name}')
        entry = entries[name]
        if entry['kind'] == 'hardlink':
            target = resolve(hardlinks[name], seen | {name})
            if target['kind'] != 'file':
                raise ValueError(f'Hardlink target is not a file: {name}')
            entry.update(kind='file', size=target['size'], sha256=target['sha256'])
        return entry

    for name in hardlinks:
        resolve(name, set())
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original')
    parser.add_argument('release')
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=2) as pool:
        original, release = pool.map(manifest, (args.original, args.release))
    differences = [name for name in sorted(set(original) | set(release))
                   if original.get(name) != release.get(name)]
    report = {'original_entries': len(original), 'release_entries': len(release),
              'payloads_permissions_timestamps_and_links_match': not differences,
              'different_entries': len(differences), 'examples': differences[:10]}
    print(json.dumps(report))
    if differences:
        raise SystemExit('Redistributable differs from the complete compiled build')


if __name__ == '__main__':
    main()
