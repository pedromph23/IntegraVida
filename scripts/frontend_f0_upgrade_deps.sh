#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Bump a versiones que resuelven los 4 advisories"
echo "   esbuild 0.24.0 → >=0.25.0  (advisory GHSA-67mh-4wv8-2f99)"
echo "   postcss 8.4.49 → >=8.5.32  (4 CVEs, y arregla peer deps con cssnano)"
echo "   playwright 1.49.0 → >=1.55.1 (GHSA-7mvr-c777-76hp)"

npm install -D \
  "esbuild@>=0.25.0" \
  "postcss@>=8.5.32" \
  "@playwright/test@>=1.55.1"

echo ""
echo "▶ 2. npm audit (esperado 0 vulnerabilidades)"
npm audit || true

echo ""
echo "▶ 3. Verificar build con nuevas versiones"
npm run build

echo ""
echo "▶ 4. Tamaños finales"
echo "CSS gzip: $(gzip -c static/css/dist/main.css | wc -c) bytes"
echo "JS gzip:  $(gzip -c static/js/dist/main.js  | wc -c) bytes"

echo ""
echo "▶ 5. Re-verificar anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 6. Versiones finales de package.json"
python3 -c "
import json
d = json.load(open('package.json'))
print('devDependencies:')
for k, v in sorted(d['devDependencies'].items()):
    print(f'  {k:24} {v}')
print('dependencies:')
for k, v in sorted(d['dependencies'].items()):
    print(f'  {k:24} {v}')
"
