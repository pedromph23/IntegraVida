from django.apps import AppConfig


class FrontendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "frontend"
    verbose_name = "Frontend"

    def ready(self):
        from frontend.forms.auto_validate import install_auto_validators
        install_auto_validators()
