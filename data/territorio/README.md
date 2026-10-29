# Datos territoriales — revisión de límites municipales IGVSB

**Estado: material de análisis; no certificado para uso operativo.** No importar esta capa directamente al catálogo territorial de IntegraVida hasta completar la validación administrativa, cartográfica y jurídica descrita en este documento.

## Fuente examinada

- Archivo original: `data/territorio/original/Limites_municipales_de_venezuela_IGVSB_WGS84.zip`
- Capa: `Limites_municipales_de_venezuela_IGVSB_WGS84/Limites_municipales_de_venezuela_IGVSB_WGS84.shp`
- SHA-256 verificado: `f5c9712ef77a7e4c2692a7c967f7436533b359a4a22cb280e2763b910671991f`
- Entidades: 408
- Geometría declarada: `Polygon`
- CRS declarado: EPSG:4326
- Extensión: longitud -73.366467 a -58.094341; latitud 0.645370 a 12.197286
- Campos observados: `id_0`, `dm_acc`, `ara`, `dm_bst`, `nam`, `ngov`, `nm3`, `nm4`, `sag`, `txt`, `dm_cent`, `dm_cmun`.
- Los metadatos examinados atribuyen la capa al Instituto Geográfico de Venezuela Simón Bolívar (IGVSB) y describen límites municipales, con metadatos fechados en 2016 y XML modificado en 2021. Estas fechas no certifican que la capa represente la división administrativa vigente.
- La URL pública original, la vigencia actual, las condiciones de licencia y los permisos de redistribución no se han verificado de manera independiente. Los metadatos contienen una ruta de red privada, que no sirve como referencia pública reproducible.

El ZIP original debe mantenerse intacto. No extraerlo encima de otros datos ni modificar sus archivos internos. Su hash debe verificarse de nuevo antes de un análisis futuro:

```bash
sha256sum data/territorio/original/Limites_municipales_de_venezuela_IGVSB_WGS84.zip
```

## Clasificación observada de `dm_bst`

El análisis de los 408 registros obtuvo:

| `dm_bst` | Cantidad | Interpretación prudente |
|---|---:|---|
| `1` | 338 | Candidatos que la capa clasifica con valor 1; no equivale por sí solo a certificación de municipio vigente. |
| `3` | 65 | Registros descritos en la inspección como zonas de sobreposición de límites entre municipios. |
| `4` | 4 | Registros descritos como zonas sin jurisdicción territorial entre municipios. |
| Nulo | 1 | Registro `id_0=408`, `nam=GUAYANA ESEQUIBA`; requiere tratamiento separado y revisión oficial, no incorporación automática. |
| **Total** | **408** | La suma coincide con el número de entidades de la capa. |

`id_0` es el identificador de registro de esta fuente; no debe tratarse como código administrativo oficial. Tampoco se ha demostrado que `dm_cent` y `dm_cmun` sean códigos oficiales únicos. Los nombres de campos por sí solos no certifican su semántica ni las unidades de `ara`.

## Colisiones detectadas en los candidatos `dm_bst=1`

Se identificaron cuatro combinaciones repetidas de `(dm_cent, dm_cmun)`: 338 registros, 334 combinaciones distintas y 8 registros implicados en colisiones. Se conservan los valores originales de código como texto para no perder ceros iniciales.

| Código de la fuente | `id_0` | Nombre | Área `ara` de origen | Área calculada de la geometría (aprox.) | Observación |
|---|---:|---|---:|---:|---|
| `02-03` | 34 | Municipio Autónomo Atures | 4.071.400.000 | 4.018.098.550 m² | Colisiona con un registro de nombre distinto. |
| `02-03` | 349 | Municipio Fernando de Peñalver | 754.046.000 | 742.809.081 m² | Colisiona con Atures; las geometrías examinadas no se intersectan. |
| `11-14` | 368 | Municipio Urumaco | 902.358.000 | 891.205.952 m² | Comparte segmentos lineales de frontera con el registro 390. |
| `11-14` | 390 | Municipio Miranda | 2.187.870.000 | 2.160.912.720 m² | Colisiona con Urumaco, pese a tener nombre distinto. |
| `17-10` | 398 | Municipio Tubores | 25.129.400 | 24.817.526 m² | Geometría `POLYGON`; no se intersecta con el registro 399 en la comprobación realizada. |
| `17-10` | 399 | Municipio Tubores | 148.879.000 | 147.034.111 m² | Geometría `MULTIPOLYGON` con siete componentes; no se intersecta con el registro 398 en la comprobación realizada. |
| `23-20` | 380 | Municipio Sucre | 183.049.000 | 180.720.178 m² | `txt`: “Zona de Sobreposición de Límite entre los Estados Mérida-Zulia”. |
| `23-20` | 381 | Municipio Sucre | 336.220.000 | 331.961.392 m² | Mismo nombre, códigos y anotación que el registro 380; geometría distinta. |

Las áreas calculadas se obtuvieron transformando la geometría a EPSG:6933 y calculando el área. Las unidades y el método de cálculo de `ara` no están suficientemente documentados. En los ocho registros examinados, las geometrías resultaron válidas según `ST_IsValid`, pero esto no certifica su exactitud cartográfica ni su correspondencia con la división administrativa oficial. Los valores de área de la tabla son diagnósticos, no superficies oficiales certificadas.

### Intersecciones revisadas

- **Atures / Fernando de Peñalver (34/349):** geometrías distintas; no se detectó intersección en la consulta realizada.
- **Urumaco / Miranda (368/390):** `MULTILINESTRING`, área calculada igual a cero. El resultado es compatible con segmentos de frontera compartidos, no con una superposición superficial detectable.
- **Tubores (398/399):** geometrías distintas; no se detectó intersección en la consulta realizada.
- **Sucre (380/381):** intersección `GEOMETRYCOLLECTION`, área aproximada de `0,0944 m²` en EPSG:6933. La colección contiene numerosos segmentos lineales y un polígono diminuto. Es una superficie insignificante a escala municipal, pero no se puede atribuir la causa con certeza sin una revisión cartográfica adicional.

`ST_Intersects` significa que las geometrías comparten al menos un punto; no implica necesariamente que compartan superficie positiva. La validez topológica de una geometría tampoco acredita la corrección administrativa del límite.

## Diferencia entre `ara` y el área geométrica

En los ocho registros de las cuatro colisiones, el valor `ara` es mayor que el área calculada a partir de la geometría. Las diferencias son aproximadamente del orden del 1–1,5 %. Se debe registrar como una discrepancia pendiente de explicación, sin sobrescribir ni “corregir” automáticamente el campo de origen. Para resolverla se necesita documentación de la definición, unidad, proyección y método de cálculo de `ara`.

## Análisis reproducible

El script `data/territorio/analisis/analizar_igvsb.py` lee la capa directamente desde el ZIP usando el sistema virtual `/vsizip/` de GDAL; no requiere extraer el Shapefile. Genera un informe JSON en:

`data/territorio/analisis/informes/calidad_igvsb_2016.json`

El informe se genera únicamente al ejecutar explícitamente el script. El script no escribe en PostgreSQL, no realiza importaciones y no modifica el ZIP original. El análisis automático documenta metadatos disponibles, clasificación, campos ausentes y colisiones de atributos. Las comprobaciones geométricas descritas en este README provienen de consultas de solo lectura ejecutadas por separado con `ogrinfo` y deben repetirse si cambia la fuente o la versión de GDAL.

Requisitos: GDAL con `ogr2ogr` disponible en el `PATH` y Python 3. El script no necesita Django ni conexión a la base de datos.

Desde la raíz del repositorio:

```bash
python data/territorio/analisis/analizar_igvsb.py
```

No ejecutar el script hasta revisar sus cambios y decidir que se desea generar o reemplazar el informe JSON de salida.

## Condiciones previas a cualquier importación operativa

1. Localizar una publicación oficial pública, verificable y vigente, y registrar URL, fecha de consulta y versión.
2. Confirmar licencia, atribución y permisos de uso y redistribución.
3. Contrastar nombres, códigos, límites estatales y municipales con una referencia administrativa oficial vigente.
4. Resolver las cuatro colisiones y cualquier registro especial mediante reglas documentadas y aprobadas; no elegir entidades por orden, tamaño o `id_0`.
5. Verificar significado, unidades y metodología de `ara`, `dm_cent`, `dm_cmun`, `dm_bst` y `dm_acc` con documentación de la fuente.
6. Revisar validez, geometrías vacías, tipos `Polygon`/`MultiPolygon`, intersecciones, huecos, solapamientos y sistema de referencia.
7. Definir y probar una transformación controlada a `MultiPolygonField` si ese es el modelo de destino.
8. Registrar fuente, versión, fecha de importación, checksum, responsable, reglas de transformación, advertencias y trazabilidad por entidad.
9. Aprobar la importación por separado. El análisis no constituye autorización para cargar los datos a PostgreSQL.

## Organización

- `original/`: archivos fuente inmutables.
- `analisis/`: scripts e informes derivados.
- `inspeccion/`: notas y resultados de inspección manual.

**Estado final de esta revisión:** útil para análisis técnico preliminar; no aprobado como catálogo territorial operativo de IntegraVida.
