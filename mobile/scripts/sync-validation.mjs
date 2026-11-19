import { readdirSync, readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, '..', 'Scam_Shield_Public_Kit', 'validation_set');
const outDir = join(root, 'src', 'data');
const outFile = join(outDir, 'validationSet.json');

if (existsSync(src)) {
  const files = readdirSync(src)
    .filter((f) => f.endsWith('.json'))
    .sort();
  const items = files.map((f) => JSON.parse(readFileSync(join(src, f), 'utf8')));
  mkdirSync(outDir, { recursive: true });
  writeFileSync(outFile, JSON.stringify(items, null, 2) + '\n', 'utf8');
  console.log(`Synced ${items.length} validation scenarios to ${outFile}`);
} else {
  console.warn(`Validation set not found at ${src}`);
}
