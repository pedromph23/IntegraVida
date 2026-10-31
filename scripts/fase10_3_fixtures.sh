#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

mkdir -p data/fixtures

cat > data/fixtures/README.md << 'EOF'
# Fixtures de migración piloto (Fase 10.3)

**Datos sintéticos**, no reales. Construidos a partir del schema de cada
repositorio origen (analizado en Fase 0 y Fase 8). Su propósito es
**demostrar el procedimiento de migración** (§16.1) sin exponer datos
reales ni requerir que el repo origen esté disponible en producción.

Cada archivo `.json` representa una exportación del sistema origen.

## Archivos

- `cobijo_vzla_refugios.json` — Refugios del sistema `cobijo_vzla`.
  Schema origen: `RefugioExistente` (`core/models.py`).
- `nutrilink_supplies.json` — Catálogo de insumos del sistema `NUTRILINK`.
  Schema origen: tabla `supplies` (migration `2026_09_07_000001`).

## Uso

```bash
python manage.py migrate_cobijo_vzla \
    --fixture=data/fixtures/cobijo_vzla_refugios.json \
    --organizacion=<uuid-de-org-destino>

python manage.py migrate_nutrilink \
    --fixture=data/fixtures/nutrilink_supplies.json \
    --organizacion=<uuid-de-org-destino>
EOF

cat > data/fixtures/cobijo_vzla_refugios.json << 'EOF'
[
{
"id": "REF-001",
"nombre": "Refugio Los Rosales",
"direccion": "Av. Principal Los Rosales, Caracas",
"capacidad_total": 120,
"capacidad_disponible": 30,
"servicios": ["agua", "cocina", "sanitarios"],
"operativo": true,
"telefono": "0212-1111111",
"horario": "24/7"
},
{
"id": "REF-002",
"nombre": "Refugio Catia La Mar",
"direccion": "Calle 5, Catia La Mar",
"capacidad_total": 200,
"capacidad_disponible": 200,
"servicios": ["agua", "sanitarios"],
"operativo": true,
"telefono": "0212-2222222",
"horario": "06:00-22:00"
},
{
"id": "REF-003",
"nombre": "Refugio Petare Norte",
"direccion": "Sector Petare Norte",
"capacidad_total": 80,
"capacidad_disponible": 80,
"servicios": ["agua"],
"operativo": false,
"telefono": "0212-3333333",
"horario": ""
}
]
EOF

cat > data/fixtures/nutrilink_supplies.json << 'EOF'
[
{
"id": 1,
"codigo": "ALI-001",
"nombre": "Arroz blanco",
"categoria": "alimento",
"subcategoria": "Granos",
"unidad_medida": "kg",
"es_perecedero": false,
"dias_vida_util_promedio": null
},
{
"id": 2,
"codigo": "ALI-002",
"nombre": "Leche en polvo",
"categoria": "alimento",
"subcategoria": "Lácteos",
"unidad_medida": "kg",
"es_perecedero": true,
"dias_vida_util_promedio": 365
},
{
"id": 3,
"codigo": "ALI-003",
"nombre": "Atún enlatado",
"categoria": "alimento",
"subcategoria": "Enlatados",
"unidad_medida": "cajas",
"es_perecedero": true,
"dias_vida_util_promedio": 730
},
{
"id": 4,
"codigo": "MED-001",
"nombre": "Paracetamol 500mg",
"categoria": "medico",
"subcategoria": "Analgésicos",
"unidad_medida": "unidades",
"es_perecedero": true,
"dias_vida_util_promedio": 1095
},
{
"id": 5,
"codigo": "MED-002",
"nombre": "Guantes de nitrilo (caja)",
"categoria": "medico",
"subcategoria": "Curación",
"unidad_medida": "cajas",
"es_perecedero": false,
"dias_vida_util_promedio": null
}
]
EOF

echo "OK: fixtures creados"
ls -la data/fixtures/
