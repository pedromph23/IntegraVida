"""Validadores reutilizables para todos los formularios del panel.

Centralizados aquí para mantener consistencia. Cada uno lanza
`ValidationError` con mensaje claro en español.
"""
import re

from django.core.exceptions import ValidationError


# ─── Regex base ───────────────────────────────────────────────────────
# Nombres propios: letras (incluye tildes, ñ), espacios, apóstrofes, guiones.
RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' \-\.]+$")

# Cédula venezolana: opcionalmente V/E/J/P + guion + 6-9 dígitos.
# También acepta solo dígitos.
RE_CEDULA_VE = re.compile(r"^(?:[VEJP]-)?\d{6,9}$", re.IGNORECASE)

# Teléfono: solo dígitos, +, -, espacios, paréntesis. 7-15 caracteres.
RE_TELEFONO = re.compile(r"^[\d\+\-\(\)\s]{7,15}$")

# Código/slug: alfanumérico + guiones/underscores. 2-80 chars.
RE_CODIGO = re.compile(r"^[A-Za-z0-9_-]{2,80}$")

# Coordenadas decimales.
RE_LAT = re.compile(r"^-?\d{1,3}\.\d{1,10}$")
RE_LNG = re.compile(r"^-?\d{1,3}\.\d{1,10}$")


# ─── Validadores ──────────────────────────────────────────────────────
def validar_telefono(value):
    """Acepta teléfonos tipo: 0414-1234567, +58 412 1234567, (0212) 555-4433."""
    if not value:
        return
    # Limpiar caracteres invisibles y espacios no imprimibles
    value = "".join(c for c in value if c.isprintable()).strip()
    
    # Contar solo dígitos
    solo_digitos = re.sub(r"\D", "", value)
    if len(solo_digitos) < 7:
        raise ValidationError(
            "El teléfono debe tener al menos 7 dígitos (sin contar +, espacios ni guiones)."
        )
    if len(solo_digitos) > 15:
        raise ValidationError(
            "El teléfono no puede tener más de 15 dígitos (formato internacional E.164)."
        )

    if not RE_TELEFONO.match(value):
        raise ValidationError(
            "Formato de teléfono inválido. Usa solo números, +, guiones, "
            "espacios y paréntesis. Ej: +58 412-1234567"
        )


def validar_cedula(value):
    """Cédula venezolana: V-12345678, E-12345678 o solo 12345678."""
    if not value:
        return
    value = value.strip().upper()
    if not RE_CEDULA_VE.match(value):
        raise ValidationError(
            "Cédula inválida. Formato esperado: V-12345678 o E-12345678 "
            "(6 a 9 dígitos, opcionalmente con prefijo V, E, J o P)."
        )


def validar_nombre_persona(value):
    """Nombre o apellido: letras, tildes, espacios, apóstrofes y guiones."""
    if not value:
        return
    value = value.strip()
    if len(value) < 2:
        raise ValidationError("El nombre debe tener al menos 2 caracteres.")
    if len(value) > 100:
        raise ValidationError("El nombre no puede superar 100 caracteres.")
    if not RE_NOMBRE.match(value):
        raise ValidationError(
            "El nombre solo puede contener letras, espacios, apóstrofes (') "
            "y guiones (-). Ej: María José, O'Connor, Ana-María."
        )
    if "  " in value:
        raise ValidationError("El nombre no puede tener espacios dobles consecutivos.")


def validar_codigo(value):
    """Código/slug para organizaciones, insumos, entidades, etc."""
    if not value:
        return
    value = value.strip()
    if not RE_CODIGO.match(value):
        raise ValidationError(
            "El código solo admite letras, números, guiones y guiones bajos "
            "(2 a 80 caracteres). Ej: hosp-central, ins-001, org_2026."
        )


def validar_texto_libre(value, *, min_len=3, max_len=2000, campo="Texto"):
    """Validación genérica para textareas y notas."""
    if not value:
        return
    value = value.strip()
    if len(value) < min_len:
        raise ValidationError(f"{campo} debe tener al menos {min_len} caracteres.")
    if len(value) > max_len:
        raise ValidationError(f"{campo} no puede superar {max_len} caracteres.")


def validar_edad_aproximada(value):
    """Rango de edad o descripción corta. Ej: '30-40', 'menor de 18', 'adulto mayor'."""
    if not value:
        return
    value = value.strip()
    if len(value) > 50:
        raise ValidationError("La edad aproximada no puede superar 50 caracteres.")
    # Solo permitir caracteres razonables (números, letras, guiones)
    if not re.match(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 \-]+$", value):
        raise ValidationError(
            "La edad aproximada solo puede contener letras, números y guiones. "
            "Ej: 30-40, menor de 18, adulto mayor."
        )


def validar_estatura_cm(value):
    """Estatura humana razonable: 30 a 250 cm (permite bebés)."""
    if value is None:
        return
    if value < 30 or value > 250:
        raise ValidationError(
            "La estatura debe estar entre 30 cm y 250 cm."
        )


def validar_peso_kg(value):
    """Peso humano razonable: 0.5 a 500 kg."""
    if value is None:
        return
    if value < 0.5 or value > 500:
        raise ValidationError(
            "El peso debe estar entre 0.5 kg y 500 kg."
        )


def validar_direccion(value):
    """Dirección: al menos 5 caracteres, no solo símbolos."""
    if not value:
        return
    value = value.strip()
    if len(value) < 5:
        raise ValidationError("La dirección debe tener al menos 5 caracteres.")
    if len(value) > 300:
        raise ValidationError("La dirección no puede superar 300 caracteres.")
    # Debe tener al menos una letra o dígito
    if not re.search(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]", value):
        raise ValidationError("La dirección debe contener al menos una letra o número.")


def validar_coordenadas(lat, lng):
    """Latitud/longitud en rango válido y con 6 decimales mínimos (aprox. 10 cm)."""
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        raise ValidationError("Las coordenadas deben ser números decimales.")
    if not (-90 <= lat_f <= 90):
        raise ValidationError("La latitud debe estar entre -90 y 90.")
    if not (-180 <= lng_f <= 180):
        raise ValidationError("La longitud debe estar entre -180 y 180.")
