// HACK: serves the official validation set as static files until GET /api/scenarios/validation exists.
// Copies ../Scam_Shield_Public_Kit/validation_set/*.json → public/validation/ (gitignored).
import { cpSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, '..', 'Scam_Shield_Public_Kit', 'validation_set');
const dst = join(root, 'public', 'validation');
if (existsSync(src)) {
  mkdirSync(dst, { recursive: true });
  cpSync(src, dst, { recursive: true });
  console.log(`validation set copied to ${dst}`);
} else {
  console.warn(`validation set not found at ${src}`);
}
