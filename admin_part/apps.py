from django.apps import AppConfig


class AdminPartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_part'

    def ready(self):
        # Import and initialize Firebase
        from neelgund_backend.firebase import initialize_firebase
        try:
            initialize_firebase()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Firebase initialization failed: {e}")
