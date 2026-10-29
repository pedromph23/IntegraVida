# Revisión de códigos municipales duplicados

## Estado de la revisión

Diagnóstico preliminar de la capa atribuida al IGVSB y descrita
en los metadatos como publicada en 2016. No constituye una
certificación de límites oficiales vigentes.

No se modificaron ni eliminaron registros o geometrías.

## Resumen

- Entidades analizadas: 408.
- Registros con `dm_bst = 1`: 338.
- Códigos estado/municipio únicos con código: 334.
- Grupos de códigos duplicados: 4.
- Registros incluidos en esos grupos: 8.
- Registros sin código municipal: 0.
- Registros sin clasificación: 1.
- Registros con estados inesperados: 0.

## Casos detectados

### 1. Código 02-03

- `id_0=34`: Municipio Autónomo Atures.
- `id_0=349`: Municipio Fernando de Peñalver.
- Observación: mismo código y nombres diferentes.
- Geometría revisada previamente: polígonos disjuntos.

Acción pendiente: contrastar ambos registros con un catálogo
territorial documentado y determinar si existe un error de
atributos, de codificación o una particularidad de la fuente.

### 2. Código 11-14

- `id_0=368`: Municipio Urumaco.
- `id_0=390`: Municipio Miranda.
- Observación: mismo código y nombres diferentes.
- Geometría revisada previamente: comparten parte de su límite;
  la intersección observada fue lineal, sin área compartida.

Acción pendiente: verificar los códigos y nombres contra una
fuente territorial de referencia.

### 3. Código 17-10

- `id_0=398`: Municipio Tubores.
- `id_0=399`: Municipio Tubores.
- Observación: mismo código y nombre.
- Geometría revisada previamente: polígonos disjuntos.

Acción pendiente: determinar si son componentes territoriales
separados legítimos, registros duplicados o una particularidad
del producto cartográfico. No eliminar ninguno sin evidencia.

### 4. Código 23-20

- `id_0=381`: Municipio Sucre.
- `id_0=380`: Municipio Sucre.
- Observación en ambos registros: zona de sobreposición de límite
  entre los estados Mérida y Zulia.
- Geometría revisada previamente: se detectó contacto lineal
  aproximado de 26 km y un área de intersección calculada de
  aproximadamente 0,094 m² en la proyección utilizada.

Interpretación: el área calculada es muy pequeña y podría
corresponder a tolerancias numéricas o a la representación de
la frontera. La observación de la fuente indica que el caso
requiere tratamiento territorial especial.

Acción pendiente: consultar la documentación de origen y
establecer una política explícita de representación de límites.

## Limitaciones

- Los resultados geométricos anteriores son comprobaciones
  técnicas preliminares, no una validación oficial.
- Los estados `3` y `4` se agrupan provisionalmente como registros
  especiales; su significado debe confirmarse documentalmente.
- No se ha confirmado una URL pública de descarga ni una licencia
  que autorice la redistribución de la fuente.
- La fecha de los metadatos o del archivo no demuestra por sí sola
  que los límites sean actuales.
- Esta capa no debe utilizarse todavía como catálogo operativo
  certificado de estados y municipios de IntegraVida.

## Criterios para cerrar la revisión

1. Localizar la fuente oficial o documentación técnica verificable.
2. Confirmar el significado de los atributos y códigos.
3. Revisar los cuatro grupos con esa referencia.
4. Definir cómo representar límites compartidos y casos especiales.
5. Documentar licencia, procedencia, fecha y responsable de revisión.
6. Aprobar por separado cualquier importación a las tablas operativas.
