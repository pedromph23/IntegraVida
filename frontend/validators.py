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
    """Valida teléfonos venezolanos e internacionales.

    Válidos:
      - Venezuela nacional: 0414-1234567, 0212-555-4433, 04241234567
      - Venezuela internacional: +58 414 1234567, +584141234567
      - Otros países (con prefijo +): +1 555 1234567, +34 612345678

    Rechaza:
      - Números sin estructura (4532153253215)
      - Dígitos repetidos (1111111111, 0000000000)
      - Secuencias (1234567890, 0123456789)
      - Prefijos no venezolanos sin + (453..., 912...)
    """
    if not value:
        return

    # 1. Limpiar caracteres invisibles
    value = "".join(c for c in value if c.isprintable()).strip()

    # 2. Limpiar todo excepto dígitos, +, -, (, ), espacio
    limpio = re.sub(r"[^\d\+\-\(\)\s]", "", value)
    if not limpio:
        raise ValidationError("El teléfono no contiene caracteres válidos.")

    # 3. Solo dígitos, para validaciones estructurales
    solo_digitos = re.sub(r"\D", "", limpio)

    # 4. Anti-basura: todos iguales
    if len(set(solo_digitos)) == 1:
        raise ValidationError(
            "El teléfono no puede tener todos los dígitos iguales (ej: 1111111111)."
        )

    # 5. Anti-basura: secuencia ascendente o descendente
    if solo_digitos in ("0123456789", "9876543210", "1234567890", "0987654321"):
        raise ValidationError(
            "El teléfono no puede ser una secuencia (ej: 1234567890)."
        )
    # Anti-secuencia parcial: subcadena de 8 dígitos secuenciales
    for i in range(len(solo_digitos) - 7):
        sub = solo_digitos[i:i+8]
        asc = "".join(str((int(sub[0]) + j) % 10) for j in range(8))
        desc = "".join(str((int(sub[0]) - j) % 10) for j in range(8))
        if sub == asc or sub == desc:
            raise ValidationError(
                "El teléfono contiene una secuencia de dígitos no permitida."
            )

    # 6. Formato internacional (con prefijo +)
    if limpio.startswith("+"):
        # Debe tener entre 8 y 16 dígitos totales
        if not (8 <= len(solo_digitos) <= 16):
            raise ValidationError(
                "El teléfono internacional debe tener entre 8 y 16 dígitos."
            )
        # Prefijos de país comunes (2-3 dígitos)
        prefijos_validos = ["58", "1", "34", "52", "57", "51", "56", "55", "54",
                            "44", "33", "39", "49", "81", "86", "91", "7", "20",
                            "27", "30", "31", "32", "36", "40", "41", "43", "45",
                            "46", "47", "48", "60", "61", "62", "63", "64", "65",
                            "66", "82", "84", "90", "92", "95", "98"]
        if not any(solo_digitos.startswith(p) for p in prefijos_validos):
            raise ValidationError(
                "Prefijo de país no reconocido. Ej válidos: +58 (VE), +1 (US), +34 (ES)."
            )
        return  # Válido

    # 7. Formato venezolano nacional (empieza con 0)
    if solo_digitos.startswith("0"):
        # Debe tener exactamente 11 dígitos
        if len(solo_digitos) != 11:
            raise ValidationError(
                "Un teléfono venezolano debe tener exactamente 11 dígitos "
                "(ej: 0414-1234567 o 0212-5554433)."
            )
        # Celulares válidos: 0412, 0414, 0416, 0424, 0426
        # Fijos válidos: 0212, 0234, 0241, 0243, 0244, 0246, 0247, 0248, 0249,
        #                0251, 0252, 0253, 0254, 0255, 0256, 0257, 0258, 0259,
        #                0261-0269, 0271-0279, 0281-0289, 0291-0295
        prefijo4 = solo_digitos[:4]
        celulares = {"0412", "0414", "0416", "0424", "0426"}
        fijos_validos = {"0212", "0234", "0241", "0243", "0244", "0246", "0247",
                         "0248", "0249", "0251", "0252", "0253", "0254", "0255",
                         "0256", "0257", "0258", "0259", "0261", "0262", "0263",
                         "0264", "0265", "0266", "0267", "0268", "0269", "0271",
                         "0272", "0273", "0274", "0275", "0276", "0277", "0278",
                         "0279", "0281", "0282", "0283", "0284", "0285", "0286",
                         "0287", "0288", "0289", "0291", "0292", "0293", "0294",
                         "0295"}
        if prefijo4 not in (celulares | fijos_validos):
            raise ValidationError(
                f"El prefijo '{prefijo4}' no es un código de área venezolano válido. "
                "Celulares: 0412, 0414, 0416, 0424, 0426. "
                "Fijos: 0212, 0234, 0241, etc."
            )
        return  # Válido

    # 8. Cualquier otra cosa: rechazar
    raise ValidationError(
        "Teléfono inválido. Formatos aceptados: "
        "0414-1234567 (celular VE), 0212-5554433 (fijo VE), "
        "+58 414 1234567 (internacional VE), +1 5551234567 (otro país con +)."
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
    """Valida nombres reales. Rechaza basura como "jdsufuguhugHUHUIDHGH7...".

    Reglas:
    - Solo letras (con tildes), espacios, apóstrofes y guiones.
    - Cada palabra: 2-40 chars, al menos una vocal.
    - Máximo 6 palabras (nombre completo real).
    - Cada palabra empieza con mayúscula o minúscula (sin números).
    """
    if not value:
        return

    value = value.strip()

    if len(value) < 2:
        raise ValidationError("El nombre debe tener al menos 2 caracteres.")
    if len(value) > 100:
        raise ValidationError("El nombre no puede superar 100 caracteres.")
    if "  " in value:
        raise ValidationError("El nombre no puede tener espacios dobles consecutivos.")

    # Solo letras, espacios, apóstrofes y guiones
    if not re.match(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'\- ]+$", value):
        raise ValidationError(
            "El nombre solo puede contener letras, espacios, apóstrofes (') "
            "y guiones (-)."
        )

    # Análisis por palabra
    palabras = re.split(r"[\s\-]+", value)
    palabras = [p for p in palabras if p]  # ignorar vacías

    if len(palabras) > 6:
        raise ValidationError(
            "El nombre tiene demasiadas palabras (máximo 6: nombres + apellidos)."
        )

    VOCALES = "aeiouáéíóúüAEIOUÁÉÍÓÚÜ"

    for palabra in palabras:
        # Sin números (por si acaso)
        if any(c.isdigit() for c in palabra):
            raise ValidationError(
                "El nombre no puede contener números."
            )
        # Longitud razonable por palabra
        if len(palabra) < 2:
            raise ValidationError(
                "Cada palabra del nombre debe tener al menos 2 letras."
            )
        if len(palabra) > 40:
            raise ValidationError(
                "Cada palabra del nombre no puede superar 40 caracteres."
            )
        # Debe tener al menos una vocal (evita "jdsfghj" o "wwwwww")
        if not any(v in VOCALES for v in palabra):
            raise ValidationError(
                "Cada palabra del nombre debe tener al menos una vocal "
                "(el nombre parece no ser real)."
            )
        # No puede ser una sola letra repetida
        if len(set(palabra.lower())) == 1:
            raise ValidationError(
                "El nombre contiene letras repetidas sin sentido."
            )



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
