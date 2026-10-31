#!/usr/bin/env bash
# Runner de pruebas E2E. Arranca Django en background si no está,
# ejecuta Playwright, y limpia.
set -e
cd "$(dirname "$0")/.."

echo "▶ Ejecutando Playwright..."
if [ "$1" = "--update-snapshots" ]; then
    npx playwright test --update-snapshots
else
    npx playwright test
fi

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ E2E: TODOS LOS TESTS PASARON"
else
    echo "❌ E2E: ALGUNOS TESTS FALLARON (exit $EXIT_CODE)"
    echo ""
    echo "Ver reporte HTML:"
    echo "  npx playwright show-report"
fi
exit $EXIT_CODE
