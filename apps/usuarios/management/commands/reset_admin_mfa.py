"""Borra el secret MFA de un usuario (emergencia: pérdida de dispositivo).

Uso:
    python3 manage.py reset_admin_mfa --username=pedro

Tras ejecutarlo, el usuario debe re-enrolarse vía
`python manage.py crear_admin_inicial --username=pedro` o al visitar
/<INTEGRAVIDA_ADMIN_SLUG>/mfa/ (que redirige a /setup/).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.usuarios.services import reset_admin_mfa


User = get_user_model()


class Command(BaseCommand):
    help = "Borra el secret MFA de un usuario (requiere acceso al host)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **opts):
        try:
            user = User.objects.get(username=opts["username"])
        except User.DoesNotExist:
            raise CommandError(f"Usuario '{opts['username']}' no existe.")

        if not user.admin_mfa_secret:
            self.stdout.write(self.style.WARNING(
                f"'{user.username}' no tiene secret MFA configurado."
            ))
            return

        reset_admin_mfa(user)
        self.stdout.write(self.style.SUCCESS(
            f"MFA reseteado para '{user.username}'. Re-enrolar en /<slug>/mfa/."
        ))
