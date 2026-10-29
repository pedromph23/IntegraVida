# IntegraVida

Plataforma en desarrollo para apoyar la gestión de emergencias,
la coordinación entre organizaciones y la consulta de información
territorial en Venezuela.

## Estado actual

El proyecto está en desarrollo. Incluye una base Django con PostgreSQL
y PostGIS, usuarios, organizaciones, auditoría, territorio y recepción
y revisión de reportes de emergencia.

Las funcionalidades descritas aquí corresponden al código existente;
no implica que todos los módulos operativos estén terminados ni que
la aplicación esté preparada para producción.

## Tecnologías

- Python y Django.
- PostgreSQL con la extensión PostGIS.
- GeoDjango para almacenar geometrías y puntos geográficos.
- Psycopg 3 como adaptador de PostgreSQL.
- python-dotenv para cargar variables desde `.env`.
- Pruebas automatizadas con el sistema de pruebas de Django.

Las versiones instaladas están registradas en `requirements.txt`.

## Módulos

### Usuarios — `apps.usuarios`

Define el modelo de usuario personalizado de Django. El proyecto utiliza
`AUTH_USER_MODEL = "usuarios.Usuario"`.

### Organizaciones — `apps.organizaciones`

Gestiona organizaciones y membresías con roles y estados. Los servicios
del módulo verifican la pertenencia activa y los permisos correspondientes.

API interna disponible:

- `GET /api/interno/organizaciones/`

### Auditoría — `apps.auditoria`

Registra eventos de auditoría con información del actor, la operación,
el objeto afectado, el resultado y los metadatos permitidos.

### Territorio — `apps.territorio`

Define entidades geográficas de Venezuela mediante modelos GeoDjango
y campos `MultiPolygonField`. La carga y actualización de los límites
territoriales debe documentarse como un proceso separado.

### Emergencias — `apps.emergencias`

Incluye los modelos de emergencias y reportes ciudadanos, recepción
pública de reportes, consulta pública de emergencias y revisión interna
con controles de acceso y auditoría.

Rutas principales:

- `GET /api/publico/emergencias/`
- `GET /api/publico/emergencias/<uuid>/`
- `POST /api/publico/emergencias/reportes/`
- `GET /api/interno/emergencias/reportes/`
- `POST /api/interno/emergencias/reportes/<uuid>/revision/`
- `POST /api/interno/emergencias/reportes/<uuid>/vincular/`

Los reportes ciudadanos no deben considerarse emergencias confirmadas
hasta que pasen el proceso de revisión establecido.

## Requisitos del sistema

- Linux o WSL2 con Debian/Ubuntu.
- Python compatible con la versión de Django fijada en `requirements.txt`.
- PostgreSQL.
- PostGIS compatible con la instalación de PostgreSQL.
- Bibliotecas del sistema requeridas por GeoDjango, incluyendo GDAL,
  GEOS y PROJ.

En Debian/Ubuntu, las dependencias del sistema se pueden instalar
con los paquetes disponibles para la versión de la distribución:

```bash
sudo apt update
sudo apt install postgresql postgis gdal-bin libgdal-dev \
    libgeos-dev libproj-dev
```

Verifica los nombres y las versiones de los paquetes disponibles en
tu distribución antes de instalarlos.

## Instalación local en WSL

### 1. Entrar al proyecto

```bash
cd "$HOME/proyectos/integravida"
```

### 2. Crear y activar el entorno virtual

Si el entorno `.venv` ya existe y funciona, puedes conservarlo.

Para crear uno nuevo:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
chmod 600 .env
```

Edita `.env` con los datos de tu instalación local. No publiques ese
archivo ni compartas sus secretos.

Variables principales:

- `DJANGO_SECRET_KEY`: clave secreta de Django.
- `DJANGO_DEBUG`: `True` para desarrollo local; `False` en producción.
- `DJANGO_ALLOWED_HOSTS`: hosts autorizados separados por comas.
- `DB_NAME`: nombre de la base de datos.
- `DB_USER`: usuario de PostgreSQL.
- `DB_PASSWORD`: contraseña de PostgreSQL.
- `DB_HOST`: host de PostgreSQL.
- `DB_PORT`: puerto de PostgreSQL.
- `EMAIL_BACKEND`: backend de correo de Django.

No utilices claves de ejemplo en un despliegue público.

### 5. Preparar PostgreSQL y PostGIS

Crea el usuario y la base de datos local si todavía no existen.
El usuario configurado debe tener los permisos necesarios para ejecutar
las migraciones y crear la base de datos de pruebas.

Conéctate a la base de datos de la aplicación y habilita PostGIS:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

No ejecutes comandos de creación o eliminación sobre una base existente
sin comprobar primero su propietario, contenido y configuración.

### 6. Aplicar migraciones

```bash
python manage.py showmigrations
python manage.py migrate
```

### 7. Crear un administrador local

```bash
python manage.py createsuperuser
```

### 8. Ejecutar verificaciones

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --keepdb
```

La opción `--keepdb` conserva la base de pruebas entre ejecuciones.
Úsala solamente cuando quieras reutilizar esa base y sepas que corresponde
al entorno de pruebas actual.

### 9. Iniciar el servidor local

```bash
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`.

## Configuración y seguridad

- `.env` contiene configuración local y debe permanecer fuera de Git.
- `.env.example` es la plantilla de variables sin secretos.
- No se deben publicar credenciales, datos personales ni registros de
  emergencias sin una evaluación de privacidad.
- Los permisos internos deben verificarse en los servicios y vistas.
- La limitación de reportes por IP debe validarse con el backend de caché
  adecuado para el entorno de despliegue.
- No debe utilizarse `DEBUG=True` en producción.
- Antes de desplegar, deben definirse HTTPS, hosts autorizados, manejo de
  errores, correo, caché, copias de seguridad y monitorización.

## Datos territoriales

Los datos de análisis territorial de `data/` no forman parte del proceso
de instalación documentado todavía. Antes de versionarlos o distribuirlos
deben verificarse su procedencia, licencia, metadatos y necesidad operativa.

## Desarrollo y contribuciones

Antes de cada commit:

1. Ejecutar las pruebas pertinentes.
2. Ejecutar `python manage.py check`.
3. Ejecutar `python manage.py makemigrations --check --dry-run`.
4. Revisar `git diff --check` y `git status --short`.
5. Confirmar que no se incluyan secretos, bases de datos locales ni
   archivos territoriales no aprobados.

IntegraVida continúa en desarrollo y no debe considerarse listo para
coordinar emergencias reales hasta completar las pruebas operativas,
la revisión de seguridad y la preparación del despliegue.
