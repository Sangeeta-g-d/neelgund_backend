from django.db import models
from django.utils import timezone
from auth_api.models import CustomUser
from admin_part.models import RealEstateProject, PlotInventory
from admin_part.models import ProjectPaymentPhase
from decimal import Decimal
import re
from django.db.models.signals import post_save
from django.dispatch import receiver


STATUS_CHOICES = [
    ('not_contacted', 'Not Contacted'),
    ('interest_or_lost', 'Interest / Lost'),
    ('ready_for_visit', 'Ready for Visit'),
    ('visit_completed', 'Visit Completed'),
    ('looking_other_location', 'Looking Other Location'),
    ('booked', 'Booked'),
]

class PersonBase(models.Model):
    full_name = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    preferred_location = models.CharField(max_length=255, blank=True, null=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    agent = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class Lead(PersonBase):
    projects = models.ManyToManyField(
        RealEstateProject,
        through='LeadProject',
        related_name='leads',blank=True, null=True
    )

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='not_contacted')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Customer(PersonBase):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    lead = models.OneToOneField(Lead, on_delete=models.SET_NULL, null=True, related_name="customer")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress'
    )

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

class LeadProject(models.Model):
    PROJECT_STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,   # CHANGE THIS
        null=True,
        blank=True,
        related_name="lead_projects"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_projects"
    )

    project = models.ForeignKey(
        RealEstateProject,
        on_delete=models.CASCADE,
        related_name="project_leads"
    )

    status = models.CharField(
        max_length=50,
        choices=PROJECT_STATUS_CHOICES,
        default='interested'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer', 'project')

    def __str__(self):
        return f"{self.customer.full_name} → {self.project.project_name} ({self.status})"


class LeadPlotAssignment(models.Model):
    PLOT_STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    lead_project = models.ForeignKey(
        LeadProject,
        on_delete=models.CASCADE,
        related_name='assigned_plots'
    )
    plot = models.ForeignKey(
        PlotInventory,
        on_delete=models.CASCADE,
        related_name='lead_assignments'
    )
    assigned_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_lead_plots'
    )
    order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Used to group multiple plots added together in a single order"
    )
    status = models.CharField(
        max_length=50,
        choices=PLOT_STATUS_CHOICES,
        default='booked'
    )
    remarks = models.TextField(blank=True, null=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lead_project', 'plot')
        verbose_name = "Lead Plot Assignment"
        verbose_name_plural = "Lead Plot Assignments"

    def __str__(self):
        return f"{self.lead_project.lead.full_name} → {self.plot.plot_no} ({self.status})"


class LeadPlotPayment(models.Model):
    lead_plot = models.ForeignKey(
        LeadPlotAssignment,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    phase = models.ForeignKey(
        ProjectPaymentPhase,
        on_delete=models.CASCADE,
        related_name='lead_plot_payments'
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('lead_plot', 'phase')

    def __str__(self):
        return f"{self.lead_plot.plot.plot_no} - {self.phase.activity} ({self.amount_paid})"

    def save(self, *args, **kwargs):
        """
        When a payment is marked as paid, automatically release corresponding
        percentage of agent's commission as withdrawable.
        """
        from decimal import Decimal
        from django.db import transaction

        is_new = self._state.adding
        previous_paid = False

        if not is_new:
            previous_paid = LeadPlotPayment.objects.filter(id=self.id).values_list("paid", flat=True).first()

        super().save(*args, **kwargs)

        # ✅ Only proceed if newly paid or changed from unpaid → paid
        if self.paid and (is_new or previous_paid is False):
            with transaction.atomic():
                commission = getattr(self.lead_plot, "commission", None)
                if commission:
                    total_commission = commission.total_commission
                    phase_percentage = Decimal(self.phase.payment_percentage)

                    # Calculate proportional commission for this phase
                    release_amount = (total_commission * phase_percentage) / Decimal("100")

                    # ✅ Update withdrawable amount
                    commission.withdrawable_amount += release_amount
                    commission.save(update_fields=["withdrawable_amount", "updated_at"])



# ✅ Utility function to safely parse shorthand prices like "1.5Cr", "80L", "45K", etc.
def parse_price(price_str):
    """
    Convert price string like '80L', '1.2Cr', '45K', '25,00,000' etc. to Decimal rupee value.
    """
    if not price_str:
        return Decimal('0')
    
    s = str(price_str).strip().lower().replace(',', '')
    match = re.match(r'^(\d+(\.\d+)?)([a-z]*)$', s)
    if not match:
        return Decimal('0')

    amount = Decimal(match.group(1))
    unit = match.group(3)

    if unit in ['k', 'k.']:        # Thousands
        return amount * Decimal('1000')
    elif unit in ['l', 'lac', 'lakh', 'lacs', 'lakhs']:
        return amount * Decimal('100000')
    elif unit in ['cr', 'crore', 'crores']:
        return amount * Decimal('10000000')
    else:
        return amount  # plain number or already in rupees


# ✅ Main Commission Model
class AgentCommission(models.Model):
    """
    Stores total and withdrawable commission for each agent for each plot assignment.
    """
    lead_plot = models.OneToOneField(
        LeadPlotAssignment,
        on_delete=models.CASCADE,
        related_name='commission'
    )
    agent = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='commissions'
    )
    project = models.ForeignKey(
        RealEstateProject,
        on_delete=models.CASCADE,
        related_name='commissions'
    )

    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    withdrawable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    withdrawn_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_total_commission(self):
        """
        Calculates total commission for the agent when plot is assigned.
        """
        if not self.project or not self.lead_plot:
            return
        
        total_price = parse_price(self.lead_plot.plot.price)
        self.total_commission = (total_price * Decimal(self.project.commission_percentage)) / Decimal('100')
        self.save()

    @property
    def available_for_withdrawal(self):
        return max(Decimal('0'), self.withdrawable_amount - self.withdrawn_amount)

    def __str__(self):
        return f"{self.agent.full_name} - {self.project.project_name} ({self.total_commission})"


# ✅ Optional: Track individual withdrawal requests
class CommissionWithdrawal(models.Model):
    commission = models.ForeignKey(
        AgentCommission,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.commission.agent.full_name} - ₹{self.amount} ({'Approved' if self.approved else 'Pending'})"

    class Meta:
        verbose_name = "Commission Withdrawal"
        verbose_name_plural = "Commission Withdrawals"  