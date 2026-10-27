"""Políticas centrales de acceso a organizaciones."""

from collections.abc import Iterable

from django.contrib.auth.models import AnonymousUser

from apps.organizaciones.models import Membresia, Organizacion


def puede_administrar_plataforma(usuario) -> bool:
    """
    Solo una cuenta autenticada, activa y superusuario administra
    globalmente la plataforma.
    """
    return bool(
        usuario
        and not isinstance(usuario, AnonymousUser)
        and getattr(usuario, "is_authenticated", False)
        and getattr(usuario, "is_active", False)
        and getattr(usuario, "is_superuser", False)
    )


def tiene_acceso_a_organizacion(
    usuario,
    organizacion,
    roles_permitidos: Iterable[str] | None = None,
) -> bool:
    """
    Comprueba el acceso operativo de un usuario a una organización.

    Requisitos:
    - Usuario autenticado y activo.
    - Organización activa.
    - Membresía activa.
    - Si se especifican roles, la membresía debe tener uno de ellos.

    Esta función no concede privilegios globales a los superusuarios:
    la administración de plataforma se comprueba por separado.
    """
    if not usuario or isinstance(usuario, AnonymousUser):
        return False

    if not getattr(usuario, "is_authenticated", False):
        return False

    if not getattr(usuario, "is_active", False):
        return False

    if not isinstance(organizacion, Organizacion):
        return False

    if organizacion.estado != Organizacion.Estado.ACTIVA:
        return False

    consulta = Membresia.objects.filter(
        usuario_id=usuario.pk,
        organizacion_id=organizacion.pk,
        estado=Membresia.Estado.ACTIVA,
    )

    if roles_permitidos is not None:
        roles = tuple(roles_permitidos)

        if not roles:
            return False

        consulta = consulta.filter(rol__in=roles)

    return consulta.exists()
