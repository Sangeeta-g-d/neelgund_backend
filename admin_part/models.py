from django.db import models
from django.utils import timezone
import uuid

from django.core.validators import MinValueValidator, MaxValueValidator
# Create your models here.


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.ImageField(upload_to='amenity_icons/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class RealEstateProject(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mixed', 'Mixed Use'),
    ]

    STATUS_CHOICES = [
        ('ready_to_move', 'Ready to Move'),
        ('under_construction', 'Under Construction'),
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
    ]
    current_phase = models.ForeignKey(
        'ProjectPaymentPhase',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='current_for_projects'
    )
    project_id = models.CharField(max_length=50, unique=True)
    project_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)

    banner_image = models.ImageField(upload_to='projects/banner_images/', blank=True, null=True)
    brochure = models.FileField(upload_to='projects/brochures/', blank=True, null=True)
    map_layout = models.ImageField(upload_to='projects/map_layouts/', blank=True, null=True)

    total_plots = models.PositiveIntegerField(default=0)

    # ✅ Status field with choices
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='upcoming'
    )

    inventory_excel = models.FileField(upload_to='projects/inventory_excels/', blank=True, null=True)
    amenities = models.ManyToManyField('Amenity', blank=True)

    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission percentage for this project"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.project_name or str(self.project_id)


class PlotInventory(models.Model):
    """Individual plot details (can be auto-imported from Excel or added manually)"""
    project = models.ForeignKey(RealEstateProject, on_delete=models.CASCADE, related_name='plots')
    plot_no = models.CharField(max_length=50)
    size = models.CharField(max_length=100, help_text="Example: 30x40 ft")
    area_sq = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total area in sq. ft")
    price = models.CharField(max_length=20, help_text="Example: 80L, 30L")

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.project.project_name} - Plot {self.plot_no}"
    
class ProjectPaymentPhase(models.Model):
    DUE_CHOICES = [
        ('immediate', 'Immediate'),
        ('30_days', 'Within 30 Days'),
        ('60_days', 'Within 60 Days'),
        ('90_days', 'Within 90 Days'),
        ('120_days', 'Within 120 Days'),
        ('custom', 'Custom Duration'),
    ]

    project = models.ForeignKey(
        'RealEstateProject',
        on_delete=models.CASCADE,
        related_name='payment_phases'
    )
    activity = models.CharField(max_length=255, help_text="Name of the payment phase/activity")
    payment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Payment percentage for this phase"
    )
    due = models.CharField(
        max_length=50,
        choices=DUE_CHOICES,
        default='immediate',
        help_text="When the payment is due"
    )
    order = models.PositiveIntegerField(default=0, help_text="Order of the payment phase")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ('project', 'activity')
        verbose_name = "Project Payment Phase"
        verbose_name_plural = "Project Payment Phases"

    def __str__(self):
        return f"{self.project.project_name} - {self.activity} ({self.payment_percentage}%)"

class ProjectHighlight(models.Model):
    """Key highlights for a real estate project."""
    project = models.ForeignKey(
        RealEstateProject,
        on_delete=models.CASCADE,
        related_name='highlights'
    )
    title = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Project Highlight"
        verbose_name_plural = "Project Highlights"

    def __str__(self):
        return f"{self.project.project_name} - {self.title}"
