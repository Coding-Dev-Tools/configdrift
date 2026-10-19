#!/usr/bin/env node
const { spawnSync } = require('child_process');

// Find python3 or python
const python = process.platform === 'win32' ? 'python' : 'python3';
const args = ['-m', 'configdrift.cli', ...process.argv.slice(2)];
const result = spawnSync(python, args, { stdio: 'inherit' });
process.exit(typeof result.status === 'number' ? result.status : 1);
