import hashlib

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.emergencias.models import Emergencia, ReporteEmergencia


VENTANA_SEGUNDOS = 60
MAX_REPORTES_POR_IP = 5


def _obtener_ip(request):
    """No confiar en cabeceras de proxy no verificadas."""
    return request.META.get("REMOTE_ADDR") or None


def _supera_limite(ip):
    """
    Limita los reportes por IP durante una ventana de 60 segundos.
    Usa la caché y no consulta la tabla de auditoría.
    """
    if not ip:
        return False

    huella = hashlib.sha256(ip.encode("utf-8")).hexdigest()
    clave = f"integravida:emergencias:reportes:{huella}"

    # El primer envío crea el contador con valor 1.
    if cache.add(clave, 1, timeout=VENTANA_SEGUNDOS):
        return False

    try:
        cantidad = cache.incr(clave)
    except ValueError:
        # El contador pudo expirar entre la lectura y el incremento.
        if cache.add(clave, 1, timeout=VENTANA_SEGUNDOS):
            return False
        cantidad = cache.incr(clave)

    return cantidad > MAX_REPORTES_POR_IP


def _validar_texto(valor, campo, maximo):
    if not isinstance(valor, str):
        raise ValidationError({campo: "Este campo debe ser texto."})

    valor = valor.strip()

    if not valor:
        raise ValidationError({campo: "Este campo es obligatorio."})

    if len(valor) > maximo:
        raise ValidationError(
            {campo: f"No puede superar los {maximo} caracteres."}
        )

    return valor


@transaction.atomic
def recibir_reporte_publico(*, datos, request):
    """Registra un reporte ciudadano pendiente, sin confirmar emergencias."""
    if not isinstance(datos, dict):
        raise ValidationError("El cuerpo debe ser un objeto JSON.")

    campos_permitidos = {
        "descripcion",
        "ubicacion_texto",
        "referencia_lugar",
        "categoria",
    }
    campos_desconocidos = set(datos) - campos_permitidos

    if campos_desconocidos:
        raise ValidationError({
            "campos": "La solicitud contiene campos no permitidos."
        })

    descripcion = _validar_texto(
        datos.get("descripcion"), "descripcion", 5000
    )
    ubicacion = _validar_texto(
        datos.get("ubicacion_texto"), "ubicacion_texto", 300
    )

    referencia = datos.get("referencia_lugar", "")
    if not isinstance(referencia, str):
        raise ValidationError({
            "referencia_lugar": "Este campo debe ser texto."
        })

    referencia = referencia.strip()
    if len(referencia) > 250:
        raise ValidationError({
            "referencia_lugar": "No puede superar los 250 caracteres."
        })

    categoria = datos.get("categoria")
    categorias_validas = {
        valor for valor, _ in Emergencia.Categoria.choices
    }

    if categoria not in categorias_validas:
        raise ValidationError({
            "categoria": "Selecciona una categoría válida."
        })

    ip = _obtener_ip(request)

    if _supera_limite(ip):
        return None, True

    reporte = ReporteEmergencia.objects.create(
        categoria=categoria,
        descripcion=descripcion,
        ubicacion_texto=ubicacion,
        referencia_lugar=referencia,
        canal=ReporteEmergencia.Canal.WEB,
        estado_revision=ReporteEmergencia.EstadoRevision.PENDIENTE,
    )

    registrar_evento(
        accion="emergencia.reporte_publico",
        tipo_objeto="ReporteEmergencia",
        objeto_id=reporte.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion="Recepción de reporte ciudadano.",
        ip=ip,
        agente_usuario=request.META.get("HTTP_USER_AGENT", "")[:500],
        metadatos={
            "origen": "portal_publico",
            "estado": "PENDIENTE",
        },
    )

    return reporte, False
