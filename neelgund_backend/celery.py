from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neelgund_backend.settings')

app = Celery('neelgund_backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto discover tasks inside installed apps
app.autodiscover_tasks()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        24 * 3600,  # every 24 hours
        'agents.tasks.check_maturity_task',  # reference by string
        name='Daily maturity check'
    )
