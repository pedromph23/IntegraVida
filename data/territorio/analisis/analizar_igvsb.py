#!/usr/bin/env python3
"""Analiza atributos de la capa municipal IGVSB directamente desde el ZIP.

El script es de solo lectura respecto de la fuente. Al ejecutarse, escribe un
informe JSON en data/territorio/analisis/informes/. No conecta con PostgreSQL,
no importa entidades y no modifica el ZIP original.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ZIP_PATH = (
    ROOT
    / "data"
    / "territorio"
    / "original"
    / "Limites_municipales_de_venezuela_IGVSB_WGS84.zip"
)
ZIP_MEMBER = (
    "Limites_municipales_de_venezuela_IGVSB_WGS84/"
    "Limites_municipales_de_venezuela_IGVSB_WGS84.shp"
)
LAYER_NAME = "Limites_municipales_de_venezuela_IGVSB_WGS84"
EXPECTED_SHA256 = "f5c9712ef77a7e4c2692a7c967f7436533b359a4a22cb280e2763b910671991f"
OUT = ROOT / "data" / "territorio" / "analisis" / "informes" / "calidad_igvsb_2016.json"

CLASS_DESCRIPTIONS = {
    "1": "Registros candidatos de la capa; no equivale a certificación administrativa vigente.",
    "3": "Registros descritos durante la inspección como zonas de sobreposición de límites entre municipios.",
    "4": "Registros descritos durante la inspección como zonas sin jurisdicción territorial entre municipios.",
    "null": "Clasificación ausente.",
}

FIELDS_OF_INTEREST = (
    "id_0",
    "dm_bst",
    "nam",
    "ngov",
    "nm3",
    "nm4",
    "sag",
    "txt",
    "dm_acc",
    "ara",
    "dm_cent",
    "dm_cmun",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalized_status(value: Any) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return "null"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"unexpected:{value}"
    if not math.isfinite(number):
        return "null"
    if number.is_integer():
        return str(int(number))
    return f"unexpected:{value}"


def display_id(value: Any) -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
        if math.isfinite(number) and number.is_integer():
            return str(int(number))
    except (TypeError, ValueError):
        pass
    return str(value)


def run_ogr2ogr(vsi_path: str) -> dict[str, Any]:
    command = ["ogr2ogr", "-f", "GeoJSON", "/vsistdout/", vsi_path]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "sin detalle"
        raise RuntimeError(f"Falló ogr2ogr (código {result.returncode}): {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "ogr2ogr no devolvió GeoJSON válido. "
            f"Salida inicial: {result.stdout[:500]!r}; stderr: {result.stderr[:500]!r}"
        ) from exc


def feature_summary(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    summary = {field: properties.get(field) for field in FIELDS_OF_INTEREST}
    summary["id_0"] = display_id(summary.get("id_0"))
    summary["geometry_type"] = geometry.get("type")
    return summary


def main() -> int:
    if not ZIP_PATH.is_file():
        print(f"ERROR: no se encontró el ZIP original: {ZIP_PATH}", file=sys.stderr)
        return 2
    if shutil.which("ogr2ogr") is None:
        print("ERROR: no se encontró ogr2ogr. Instala GDAL y verifica el PATH.", file=sys.stderr)
        return 2

    source_sha256 = sha256_file(ZIP_PATH)
    vsi_path = f"/vsizip/{ZIP_PATH.resolve()}/{ZIP_MEMBER}"

    try:
        dataset = run_ogr2ogr(vsi_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    features = dataset.get("features")
    if not isinstance(features, list):
        print("ERROR: la salida GeoJSON no contiene una lista 'features'.", file=sys.stderr)
        return 2

    summaries = [feature_summary(feature) for feature in features]
    status_counts = Counter(normalized_status(row.get("dm_bst")) for row in summaries)
    code_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    missing_code_ids: list[str | None] = []
    missing_name_ids: list[str | None] = []

    for row in summaries:
        state_code = normalized_text(row.get("dm_cent"))
        municipality_code = normalized_text(row.get("dm_cmun"))
        row_status = normalized_status(row.get("dm_bst"))
        if row_status == "1":
            if state_code is None or municipality_code is None:
                missing_code_ids.append(row.get("id_0"))
            else:
                # Los valores se conservan como texto para preservar ceros iniciales.
                code_groups[(state_code, municipality_code)].append(row)
            if normalized_text(row.get("nam")) is None:
                missing_name_ids.append(row.get("id_0"))

    duplicate_groups = []
    for (state_code, municipality_code), rows in sorted(code_groups.items()):
        if len(rows) > 1:
            duplicate_groups.append(
                {
                    "dm_cent": state_code,
                    "dm_cmun": municipality_code,
                    "composite_source_code": f"{state_code}-{municipality_code}",
                    "record_count": len(rows),
                    "records": sorted(rows, key=lambda row: (row.get("id_0") or "")),
                    "warning": (
                        "Colisión de código de la fuente; no asumir que estos campos "
                        "son códigos administrativos oficiales ni descartar registros automáticamente."
                    ),
                }
            )

    null_class_records = [
        row for row in summaries if normalized_status(row.get("dm_bst")) == "null"
    ]
    special_class_records = [
        row
        for row in summaries
        if normalized_status(row.get("dm_bst")) in {"3", "4"}
    ]
    unexpected_class_records = [
        row
        for row in summaries
        if normalized_status(row.get("dm_bst")) not in {"1", "3", "4", "null"}
    ]

    warnings = [
        "El análisis automático cubre atributos y geometrías GeoJSON; no certifica vigencia administrativa.",
        "dm_cent y dm_cmun se tratan como códigos de la fuente, no como códigos oficiales verificados.",
        "id_0 se trata como identificador de registro de la fuente, no como código administrativo oficial.",
        "No se infieren unidades ni metodología del campo ara.",
        "No se importan ni modifican datos de PostgreSQL.",
        "Las comprobaciones ST_IsValid, ST_Intersects y áreas en EPSG:6933 se documentan como consultas manuales separadas; este script no las vuelve a ejecutar.",
    ]
    if source_sha256 != EXPECTED_SHA256:
        warnings.insert(
            0,
            "ADVERTENCIA: el SHA-256 del ZIP no coincide con el checksum registrado en el README; "
            "verifica que sea la misma versión de la fuente antes de comparar resultados.",
        )

    report = {
        "report_schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_type": "atributos y geometrías exportadas a GeoJSON; sin importación",
        "source": {
            "file": str(ZIP_PATH.relative_to(ROOT)),
            "zip_member": ZIP_MEMBER,
            "layer_name": LAYER_NAME,
            "sha256": source_sha256,
            "expected_sha256": EXPECTED_SHA256,
            "checksum_matches_expected": source_sha256 == EXPECTED_SHA256,
            "geojson_crs": dataset.get("crs"),
            "bbox": dataset.get("bbox"),
            "feature_count": len(summaries),
            "geometry_type_counts": dict(
                sorted(Counter(row.get("geometry_type") or "null" for row in summaries).items())
            ),
            "source_license_verified": False,
            "current_administrative_validity_verified": False,
        },
        "classification": {
            "field": "dm_bst",
            "counts": dict(sorted(status_counts.items())),
            "descriptions": CLASS_DESCRIPTIONS,
            "null_class_records": null_class_records,
            "special_class_records_dm_bst_3_or_4": special_class_records,
            "unexpected_class_records": unexpected_class_records,
        },
        "candidate_records_dm_bst_1": {
            "count": status_counts.get("1", 0),
            "unique_composite_source_codes": len(code_groups),
            "duplicate_code_group_count": len(duplicate_groups),
            "records_in_duplicate_groups": sum(
                group["record_count"] for group in duplicate_groups
            ),
            "duplicate_code_groups": duplicate_groups,
            "missing_composite_code_record_ids": missing_code_ids,
            "missing_name_record_ids": missing_name_ids,
        },
        "field_completeness": {
            field: {
                "null_or_blank_count": sum(
                    normalized_text(row.get(field)) is None for row in summaries
                ),
                "total": len(summaries),
            }
            for field in FIELDS_OF_INTEREST
        },
        "warnings": warnings,
        "limitations": [
            "No external official administrative source is consulted by this script.",
            "No polygon validity, topology, intersection, or area calculation is performed by this script.",
            "Geometry type counts describe GeoJSON geometry objects returned by GDAL; they do not establish administrative correctness.",
            "The output report is a derived artifact. The source ZIP is never written to.",
        ],
    }

    # Escribir el informe solo como resultado explícito de ejecutar este script.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Fuente: {ZIP_PATH.relative_to(ROOT)}")
    print(f"SHA-256: {source_sha256}")
    print(f"Checksum coincide: {'sí' if source_sha256 == EXPECTED_SHA256 else 'NO'}")
    print(f"Entidades: {len(summaries)}")
    print(f"Clasificación dm_bst: {dict(sorted(status_counts.items()))}")
    print(f"Códigos compuestos únicos entre dm_bst=1: {len(code_groups)}")
    print(f"Grupos de códigos repetidos: {len(duplicate_groups)}")
    print(f"Registros implicados en colisiones: {sum(g['record_count'] for g in duplicate_groups)}")
    print(f"Informe generado: {OUT.relative_to(ROOT)}")
    if source_sha256 != EXPECTED_SHA256:
        print("ATENCIÓN: revisa la versión de la fuente antes de usar o comparar el informe.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
