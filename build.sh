#!/usr/bin/env bash
# build.sh
set -o errexit

# Instalar dependencias (Render lo hace automáticamente, pero lo forzamos)
pip install -r requirements.txt

# Compilar estáticos con WhiteNoise
python manage.py collectstatic --no-input

# Aplicar migraciones a Supabase
python manage.py migrate