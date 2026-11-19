from django.apps import AppConfig


class CentersConfig(AppConfig):
    name = 'centers'

    def ready(self):
        from .search import connect_signals
        connect_signals()
