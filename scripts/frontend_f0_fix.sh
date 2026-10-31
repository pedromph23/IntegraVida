#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Quitar djlint del package.json (es Python, va por pip)"
python3 - << 'PY'
import json
from pathlib import Path
p = Path("package.json")
data = json.loads(p.read_text(encoding="utf-8"))
dev = data.get("devDependencies", {})
dev.pop("djlint", None)
data["devDependencies"] = dev
data["scripts"]["lint:templates"] = "djlint --check ./templates --profile=django"
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("OK: djlint removido de package.json")
PY

echo ""
echo "▶ 2. Añadir djlint a requirements-dev.txt"
if [ ! -f requirements-dev.txt ]; then
    cat > requirements-dev.txt << 'EOF'
# Herramientas de desarrollo y CI (no van a producción)
djlint==1.34.1
EOF
    echo "OK: requirements-dev.txt creado"
else
    if ! grep -q "^djlint" requirements-dev.txt; then
        echo "djlint==1.34.1" >> requirements-dev.txt
        echo "OK: djlint añadido a requirements-dev.txt existente"
    else
        echo "ya aplicado: djlint en requirements-dev.txt"
    fi
fi

echo ""
echo "▶ 3. Actualizar .gitignore para node_modules y dist"
if ! grep -q "^node_modules/" .gitignore 2>/dev/null; then
    cat >> .gitignore << 'EOF'

# Frontend — node_modules no va al repo, dist SÍ
node_modules/
.npm/
npm-debug.log*
EOF
    echo "OK: .gitignore actualizado"
else
    echo "ya aplicado: .gitignore"
fi

echo ""
echo "▶ 4. Reinstalar limpio"
npm install

echo ""
echo "▶ 5. Verificar build determinista"
npm run build

echo ""
echo "▶ 6. Re-verificar anti-CDN"
bash scripts/check-no-cdn.sh
