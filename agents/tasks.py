from celery import shared_task
from .models import AgentCommission

@shared_task
def check_maturity_task():
    for commission in AgentCommission.objects.all():
        commission.update_maturity()
