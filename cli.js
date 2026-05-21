#!/usr/bin/env node
const { spawnSync } = require('child_process');

/** Try a list of Python executable names and return the first one that exists. */
function findPython(candidates) {
  const { existsSync } = require('fs');
  const { sep } = require('path');
  for (const exe of candidates) {
    // On Unix, shell can resolve PATH; on Windows we also check common locations
    const result = spawnSync(exe, ['--version'], { stdio: 'pipe' });
    if (result.status === 0) return exe;
    // Also check full paths for common locations
    const fullPaths = [
      `${process.env.LOCALAPPDATA || ''}${sep}Programs${sep}Python${sep}python3.exe`,
      `C:${sep}Python313${sep}python.exe`,
      `C:${sep}Python312${sep}python.exe`,
      `/usr/bin/${exe}`,
      `/usr/local/bin/${exe}`,
    ].filter(p => p.includes(exe));
    for (const fp of fullPaths) {
      if (existsSync(fp)) {
        const r = spawnSync(fp, ['--version'], { stdio: 'pipe' });
        if (r.status === 0) return fp;
      }
    }
  }
  return null;
}

const candidates = process.platform === 'win32'
  ? ['python3', 'python', 'py']
  : ['python3', 'python'];

const python = findPython(candidates);
if (!python) {
  console.error('ERROR: Python 3 not found. Install Python 3.10+ from https://python.org');
  process.exit(1);
}

const args = ['-m', 'configdrift.cli', ...process.argv.slice(2)];
const result = spawnSync(python, args, { stdio: 'inherit' });
process.exit(result.status != null ? result.status : 1);
