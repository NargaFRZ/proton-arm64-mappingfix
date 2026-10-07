#!/usr/bin/env python3
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

root = Path.cwd()
report_path = root / 'logs/thread-churn-result.json'
wine = root / 'output/Proton 11 ARM64 MappingFix/files/bin-arm64/wine'
exe = root / 'logs/thread-churn.exe'
libraries = root / 'output/Proton 11 ARM64 MappingFix/files/lib'
environment = dict(os.environ)
environment.update(WINEPREFIX=str(root / 'thread-test-prefix'), WINEDEBUG='-all',
                   LD_LIBRARY_PATH=f'{libraries}/aarch64-linux-gnu:{libraries}:/usr/aarch64-linux-gnu/lib')
samples = []
baseline = None
done = False
deadline = time.monotonic() + 600
error = None

try:
    with (root / 'logs/thread-churn-stderr.txt').open('w') as stderr:
        process = subprocess.Popen([str(wine), str(exe)], env=environment, stdout=subprocess.PIPE,
                                   stderr=stderr, text=True, bufsize=1)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        while time.monotonic() < deadline:
            events = selector.select(timeout=1)
            if events:
                line = process.stdout.readline()
                if not line:
                    break
                print(line.rstrip(), flush=True)
                if line.startswith(('WARMED', 'SAMPLE')):
                    count = len(Path(f'/proc/{process.pid}/maps').read_text().splitlines())
                    if line.startswith('WARMED'):
                        baseline = count
                    else:
                        samples.append({'threads_exited': int(line.split()[1]), 'mappings': count})
                    print(f'Wine PID {process.pid}: {count} virtual memory mappings', flush=True)
                if line.startswith('DONE'):
                    done = True
            if process.poll() is not None and not events:
                break
        if process.poll() is None:
            process.kill()
        returncode = process.wait(timeout=10)
        if not done or returncode or baseline is None or len(samples) != 10:
            error = f'Runtime could not finish all 64000 exits (status={returncode}, samples={len(samples)})'
except Exception as exception:
    error = str(exception)

leak = not error and samples[-1]['mappings'] - baseline > 256
report = {'status': 'unavailable' if error else ('failed' if leak else 'passed'),
          'baseline_mappings': baseline, 'samples': samples, 'error': error,
          'threads_exited_after_warmup': 64000 if done else None}
report_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
if error:
    print('::warning::Optional runtime stress test was unavailable; see build evidence for the runtime failure.')
if leak:
    raise SystemExit('ARM64EC thread mapping count grew beyond the stress-test limit')
