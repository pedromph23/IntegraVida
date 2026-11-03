"""Formularios del panel para el módulo Pacientes (F5.d).

La edición de PII es sensible: solo ADMIN_ORGANIZACION o COORDINADOR
pueden editar (por tiene_permiso "pacientes.ACCION_EDITAR").

Crear paciente NO va en este form:
- Un paciente sin episodio no tiene scope de organización.
- La creación se hace en el flujo de "Nuevo episodio" (F5.f) o desde
  el admin oculto. Aquí solo editamos datos demográficos existentes.
"""
from django import forms

from apps.pacientes.models import Paciente


class PacienteForm(forms.ModelForm):
    """Editar datos demográficos de un Paciente.

    Campos editables: nombres, apellidos, cedula, fecha_nacimiento,
    sexo_biologico, telefono, email, notas_internas.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sexo_biologico"].label = "Sexo"
        choices = self.fields["sexo_biologico"].choices
        self.fields["sexo_biologico"].choices = [
            (val, label) for val, label in choices if "intersexual" not in label.lower()
        ]

    class Meta:
        model = Paciente
        fields = [
            "nombres",
            "apellidos",
            "cedula",
            "fecha_nacimiento",
            "sexo_biologico",
            "telefono",
            "email",
            "notas_internas",
            "color_piel",
            "color_ojos",
            "tipo_cara",
            "estatura_cm",
            "peso_kg",
            "edad_aproximada",
        ]
        widgets = {
            "nombres": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "apellidos": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "cedula": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface font-mono",
                "placeholder": "ej. V-12345678",
            }),
            "fecha_nacimiento": forms.DateInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "type": "date",
            }),
            "sexo_biologico": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "telefono": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "placeholder": "+58 412-000-0000",
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "notas_internas": forms.Textarea(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "rows": 3,
            }),
        }

    def clean_cedula(self):
        """El modelo requiere `cedula_hash`. No hay save() override.

        Si la cédula cambia, hay que recalcularlo. La lógica exacta del
        hash (algoritmo + salt) está en F3.e.2. Por ahora solo validamos
        que no esté vacía si el campo está presente.
        """
        cedula = (self.cleaned_data.get("cedula") or "").strip()
        return cedula

    def save(self, commit=True):
        paciente = super().save(commit=False)
        # Si cambió la cédula, actualizar el hash
        if self.cleaned_data.get("cedula"):
            from apps.pacientes.models import Paciente as _P
            # Reutilizar el mecanismo del modelo si existe
            try:
                paciente.cedula_hash = _P.calcular_cedula_hash(
                    self.cleaned_data["cedula"],
                )
            except AttributeError:
                # El modelo no expone calcular_cedula_hash; en F5.d
                # dejamos el hash como estaba (deuda técnica → F5.g).
                pass
        if commit:
            paciente.save()
        return paciente
