from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Lead, LeadProject, LeadPlotAssignment


# 1️⃣ When any plot status changes, update its parent project
@receiver([post_save, post_delete], sender=LeadPlotAssignment)
def update_project_status_on_plot_change(sender, instance, **kwargs):
    lead_project = instance.lead_project
    plots = lead_project.assigned_plots.all()

    if not plots.exists():
        # No plots assigned → revert project to interested
        lead_project.status = 'interested'

    else:
        active_plots = plots.exclude(status='cancelled')
        closed_count = active_plots.filter(status='closed').count()

        # Case: All active plots closed
        if active_plots.exists() and closed_count == active_plots.count():
            lead_project.status = 'closed'

        # Case: All plots cancelled (and none left active)
        elif not active_plots.exists():
            lead_project.status = 'cancelled'

        else:
            # Default to in_progress if there are mixed states
            lead_project.status = 'in_progress'

    lead_project.save(update_fields=['status'])


# 2️⃣ When any project status changes, update its parent lead
@receiver([post_save, post_delete], sender=LeadProject)
def update_lead_status_on_project_change(sender, instance, **kwargs):
    lead = instance.lead
    projects = lead.lead_projects.all()

    if not projects.exists():
        lead.status = 'new'

    else:
        # If any project is in_progress or visited → lead = in_progress
        if projects.filter(status__in=['in_progress', 'visited']).exists():
            lead.status = 'in_progress'

        # If all projects closed → lead = closed
        elif projects.exclude(status='closed').count() == 0:
            lead.status = 'closed'

        # If all cancelled → lead = cancelled
        elif projects.exclude(status='cancelled').count() == 0:
            lead.status = 'cancelled'

        # Otherwise remain in_progress
        else:
            lead.status = 'in_progress'

    lead.save(update_fields=['status'])




from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Lead, Customer
from django.db import transaction
@receiver(post_save, sender=Lead)
def convert_lead_to_customer(sender, instance, created, **kwargs):
    if instance.status != "booked":
        return

    def convert_after_commit():
        # create customer if not exists
        customer, _ = Customer.objects.get_or_create(
            lead=instance,
            defaults={
                "full_name": instance.full_name,
                "contact_number": instance.contact_number,
                "email": instance.email,
                "dob": instance.dob,
                "preferred_location": instance.preferred_location,
                "budget": instance.budget,
                "city": instance.city,
                "notes": instance.notes,
                "agent": instance.agent
            }
        )

        # attach customer to lead-project mapping
        LeadProject.objects.filter(lead=instance).update(
            customer=customer
        )

    transaction.on_commit(convert_after_commit)
