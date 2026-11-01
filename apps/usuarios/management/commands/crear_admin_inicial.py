"""Crea o re-enrola el MFA de un superuser del admin.

Uso:
    python3 manage.py crear_admin_inicial --username=pedro
    python3 manage.py crear_admin_inicial --username=pedro --reset

Imprime la URI otpauth:// y el secret Base32. Requiere acceso al host
(shell / SSH); no es un endpoint público.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.usuarios.services import enroll_admin_mfa, reset_admin_mfa


User = get_user_model()


class Command(BaseCommand):
    help = "Enrola (o re-enrola) MFA TOTP de un superuser del admin oculto."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username del superuser")
        parser.add_argument(
            "--reset", action="store_true",
            help="Regenera el secret aunque ya exista",
        )

    def handle(self, *args, **opts):
        username = opts["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuario '{username}' no existe.")

        if not (user.is_superuser or user.is_staff):
            raise CommandError(
                f"'{username}' no es superuser ni staff. No puede entrar al admin."
            )

        if user.admin_mfa_secret and not opts["reset"]:
            raise CommandError(
                "El usuario ya tiene MFA configurado. Usa --reset para regenerar."
            )

        if opts["reset"] and user.admin_mfa_secret:
            reset_admin_mfa(user)
            self.stdout.write(self.style.WARNING("Secret anterior borrado."))

        secret, uri = enroll_admin_mfa(user)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"MFA enrolado para '{username}'."
        ))
        self.stdout.write("")
        self.stdout.write("URI otpauth:// (introdúcela en tu app autenticadora):")
        self.stdout.write(self.style.MIGRATE_HEADING(uri))
        self.stdout.write("")
        self.stdout.write("Secret en Base32 (alternativa manual):")
        self.stdout.write(self.style.MIGRATE_HEADING(secret))
        self.stdout.write("")
        self.stdout.write(
            "Verifica el código de 6 dígitos en la próxima visita a "
            "/<INTEGRAVIDA_ADMIN_SLUG>/mfa/"
        )
