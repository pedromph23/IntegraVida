"""Verifica la integridad criptográfica de EventoAuditoria (§7.3)."""
from django.core.management.base import BaseCommand

from apps.auditoria.models import (
    HASH_GENESIS, EventoAuditoria, calcular_hash,
)


class Command(BaseCommand):
    help = "Verifica la cadena de hashes de EventoAuditoria."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Muestra cada evento verificado.",
        )

    def handle(self, *args, **options):
        verbose = options["verbose"]
        eventos = EventoAuditoria.objects.order_by("ocurrido_en", "id")

        total = eventos.count()
        self.stdout.write(f"Eventos a verificar: {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "OK: cadena vacía (no hay eventos)"
            ))
            return

        hash_anterior_esperado = HASH_GENESIS
        errores = []
        previo_id = None

        for idx, evento in enumerate(eventos, start=1):
            # 1) hash_anterior debe coincidir con hash_actual del anterior
            if evento.hash_anterior != hash_anterior_esperado:
                errores.append(
                    f"[{idx}] {evento.id}: hash_anterior no coincide con "
                    f"el hash_actual del evento previo.\n"
                    f"     esperado: {hash_anterior_esperado}\n"
                    f"     actual:   {evento.hash_anterior}\n"
                    f"     previo:   {previo_id}"
                )

            # 2) hash_actual debe coincidir con el recalculado
            hash_recalculado = calcular_hash(evento)
            if hash_recalculado != evento.hash_actual:
                errores.append(
                    f"[{idx}] {evento.id}: hash_actual no coincide con el "
                    f"recalculado.\n"
                    f"     almacenado:   {evento.hash_actual}\n"
                    f"     recalculado:  {hash_recalculado}"
                )

            if verbose and not errores:
                self.stdout.write(
                    f"  [{idx}] {evento.id} — OK"
                )

            hash_anterior_esperado = evento.hash_actual
            previo_id = evento.id

        if errores:
            self.stdout.write(self.style.ERROR(
                f"FALLO: {len(errores)} problema(s) detectado(s)"
            ))
            for err in errores:
                self.stdout.write(self.style.ERROR(f"  {err}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(
            f"OK: cadena íntegra — {total} eventos verificados"
        ))
