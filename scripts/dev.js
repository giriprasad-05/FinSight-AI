#!/usr/bin/env node
/**
 * dev.js
 * ------
 * Cross-platform unified development runner for FinSight AI.
 * Starts all 3 core services concurrently with colored, prefixed logs:
 *   1. ML Service (FastAPI / Uvicorn on http://127.0.0.1:8000)
 *   2. Backend API (Node.js / Express on http://localhost:5000)
 *   3. Frontend (React / Vite on http://localhost:5173)
 *
 * Automatically terminates all processes on Ctrl+C (SIGINT / SIGTERM).
 */

import { spawn, execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

const isWin = process.platform === 'win32';

// ANSI Colors
const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  gray: '\x1b[90m',
};

const services = [
  {
    name: 'ML-Service',
    color: colors.magenta,
    cwd: path.join(ROOT_DIR, 'ml-service'),
    command: 'python',
    args: ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
  },
  {
    name: 'Backend   ',
    color: colors.green,
    cwd: path.join(ROOT_DIR, 'backend'),
    command: 'node',
    args: ['--watch', 'src/server.js'],
  },
  {
    name: 'Frontend  ',
    color: colors.cyan,
    cwd: path.join(ROOT_DIR, 'Frontend'),
    command: isWin ? 'npm.cmd' : 'npm',
    args: ['run', 'dev'],
  },
];

// Clean up stale processes on core ports before launching
function freePort(port) {
  try {
    if (isWin) {
      const output = execSync(`netstat -ano | findstr :${port}`, {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      });
      const lines = output.trim().split(/\r?\n/);
      const pids = new Set();
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        if (parts.length >= 5 && parts[1].endsWith(`:${port}`) && parts[3] === 'LISTENING') {
          const pid = parseInt(parts[4], 10);
          if (pid && pid !== process.pid) {
            pids.add(pid);
          }
        }
      }
      for (const pid of pids) {
        try {
          execSync(`taskkill /pid ${pid} /T /F`, { stdio: 'ignore' });
        } catch {}
      }
    } else {
      execSync(`fuser -k ${port}/tcp`, { stdio: 'ignore' });
    }
  } catch {}
}

for (const p of [8000, 5000, 5173, 5174]) {
  freePort(p);
}

console.log(`${colors.bold}${colors.blue}`);
console.log('===========================================================');
console.log('       FinSight AI — Development Stack Launcher           ');
console.log('===========================================================');
console.log(`${colors.reset}`);
console.log(`  ${colors.magenta}[ML-Service]${colors.reset}  FastAPI   -> http://127.0.0.1:8000`);
console.log(`  ${colors.green}[Backend]   ${colors.reset}  Express   -> http://localhost:5000`);
console.log(`  ${colors.cyan}[Frontend]  ${colors.reset}  React/Vite-> http://localhost:5173`);
console.log(`  ${colors.yellow}[Local LLM] ${colors.reset}  LM Studio -> http://localhost:1234/v1`);
console.log(`${colors.gray}-----------------------------------------------------------${colors.reset}\n`);

const children = [];

function prefixLines(prefix, data, color) {
  const text = data.toString();
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() || i < lines.length - 1) {
      process.stdout.write(`${color}[${prefix}]${colors.reset} ${lines[i]}\n`);
    }
  }
}

function killProcessTree(child) {
  if (!child || !child.pid) return;
  try {
    if (isWin) {
      execSync(`taskkill /pid ${child.pid} /T /F`, { stdio: 'ignore' });
    } else {
      process.kill(-child.pid, 'SIGKILL');
    }
  } catch {
    // Process might already be dead
    try {
      child.kill('SIGKILL');
    } catch {}
  }
}

let isShuttingDown = false;

function shutdown() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log(`\n${colors.yellow}[Launcher] Shutting down all FinSight AI services...${colors.reset}`);
  for (const child of children) {
    killProcessTree(child);
  }
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
process.on('exit', shutdown);

// Launch all services
for (const svc of services) {
  try {
    const child = spawn(svc.command, svc.args, {
      cwd: svc.cwd,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: isWin && svc.command.includes('npm'),
      detached: !isWin,
      env: { ...process.env },
    });

    children.push(child);

    child.stdout.on('data', (data) => prefixLines(svc.name, data, svc.color));
    child.stderr.on('data', (data) => prefixLines(svc.name, data, svc.color));

    child.on('error', (err) => {
      console.error(`${svc.color}[${svc.name}]${colors.reset} Failed to start: ${err.message}`);
    });

    child.on('close', (code) => {
      if (!isShuttingDown && code !== 0 && code !== null) {
        console.warn(`${svc.color}[${svc.name}]${colors.reset} exited with code ${code}`);
      }
    });
  } catch (err) {
    console.error(`${svc.color}[${svc.name}]${colors.reset} Launch error: ${err.message}`);
  }
}
