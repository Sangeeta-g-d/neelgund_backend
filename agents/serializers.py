# serializers.py
from rest_framework import serializers
from admin_part.models import RealEstateProject
from .models import *
import pytz
from neelgund_backend.timezone_utils import format_datetime_ist

class ProjectDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealEstateProject
        fields = ['id', 'project_name']  # id (pk) + name only


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'id', 'full_name', 'contact_number', 'email', 'dob',
            'preferred_location', 'budget', 'city',
            'status', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'status']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['agent'] = request.user
        return super().create(validated_data)
    
class LeadListSerializer(serializers.ModelSerializer):
    project_names = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id',
            'full_name',
            'contact_number',
            'email',
            'dob',
            'preferred_location',
            'budget',
            'city',
            'status',
            'notes',
            'project_names',
            'created_at',
            'updated_at'
        ]

    def get_project_names(self, obj):
        """Return a list of project names linked with the lead via LeadProject."""
        lead_projects = obj.lead_projects.select_related("project")
        return [lp.project.project_name for lp in lead_projects]

    def get_created_at(self, obj):
        if obj.created_at:
            ist = pytz.timezone('Asia/Kolkata')
            return obj.created_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p')
        return None

    def get_updated_at(self, obj):
        if obj.updated_at:
            ist = pytz.timezone('Asia/Kolkata')
            return obj.updated_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p')
        return None


class CustomerListSerializer(serializers.ModelSerializer):
    project_names = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id',
            'full_name',
            'contact_number',
            'email',
            'dob',
            'preferred_location',
            'budget',
            'city',
            'status',
            'notes',
            'project_names',
            'created_at',
            'updated_at'
        ]

    def get_project_names(self, obj):
        """Get project names linked with this customer through LeadProject."""
        lead_projects = obj.customer_projects.select_related("project")
        return [lp.project.project_name for lp in lead_projects]

    def get_created_at(self, obj):
        if obj.created_at:
            ist = pytz.timezone('Asia/Kolkata')
            return obj.created_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p')
        return None

    def get_updated_at(self, obj):
        if obj.updated_at:
            ist = pytz.timezone('Asia/Kolkata')
            return obj.updated_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p')
        return None



class LeadStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=STATUS_CHOICES)

class CustomerListSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id',
            'full_name',
            'contact_number',
            'email',
            'dob',
            'preferred_location',
            'budget',
            'city',
            'status',
            'notes',
            'projects',
            'created_at',
            'updated_at'
        ]

    def get_projects(self, obj):
        # Customer has their LeadProject records via: customer_projects
        lead_projects = obj.customer_projects.select_related('project').prefetch_related('assigned_plots__plot')
        request = self.context.get('request')
        ist = pytz.timezone("Asia/Kolkata")

        return [
            {
                "assigned_id": lp.id,
                "id": lp.project.id,
                "project_id": lp.project.project_id,
                "project_name": lp.project.project_name,
                "location": lp.project.location,
                "status": lp.status,
                "project_image": (
                    request.build_absolute_uri(lp.project.banner_image.url)
                    if lp.project.banner_image else None
                ),
                "plot_assigned": lp.assigned_plots.exists(),
                "assigned_plots": [
                    {
                        "plot_id": ap.plot.id,
                        "plot_no": ap.plot.plot_no,
                        "size": ap.plot.size,
                        "area_sq": float(ap.plot.area_sq),
                        "price": ap.plot.price,
                        "status": ap.status,
                        "remarks": ap.remarks,
                        "assigned_at": ap.assigned_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p'),
                    }
                    for ap in lp.assigned_plots.all()
                ],
            }
            for lp in lead_projects
        ]

    def get_created_at(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        return obj.created_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p')

    def get_updated_at(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        return obj.updated_at.astimezone(ist).strftime('%d-%m-%Y %I:%M %p')



# serializers.py
class LeadPlotAssignmentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='lead_project.project.project_name', read_only=True)
    plot_no = serializers.CharField(source='plot.plot_no', read_only=True)

    plot_id = serializers.PrimaryKeyRelatedField(
        source='plot',
        queryset=PlotInventory.objects.all(),
        write_only=True,
        required=False
    )

    assigned_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = LeadPlotAssignment
        fields = [
            'id',
            'project_name',
            'plot_no',
            'plot_id',     # ✅ for updating plot
            'status',
            'remarks',
            'assigned_at',
            'updated_at',
        ]

    def get_assigned_at(self, obj):
        return format_datetime_ist(obj.assigned_at)

    def get_updated_at(self, obj):
        return format_datetime_ist(obj.updated_at)
    

class ProjectSummarySerializer(serializers.ModelSerializer):
    banner_image = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display')

    class Meta:
        model = RealEstateProject
        fields = ['id', 'project_name', 'location', 'status_display', 'banner_image']

    def get_banner_image(self, obj):
        request = self.context.get('request')
        if obj.banner_image:
            return request.build_absolute_uri(obj.banner_image.url)
        return None
    

class ProjectWithPriceSerializer(serializers.ModelSerializer):
    banner_image = serializers.SerializerMethodField()
    status = serializers.CharField(source='get_status_display')  # renamed field
    starting_price = serializers.SerializerMethodField()

    class Meta:
        model = RealEstateProject
        fields = ['id', 'project_name', 'location', 'status', 'banner_image', 'starting_price']

    def get_banner_image(self, obj):
        """Return absolute URL for banner image if available."""
        request = self.context.get('request')
        if obj.banner_image:
            return request.build_absolute_uri(obj.banner_image.url)
        return None

    def get_starting_price(self, obj):
        """Return the lowest price among all plots for this project."""
        plots = obj.plots.all()
        if not plots.exists():
            return None

        numeric_prices = []
        for p in plots:
            price_str = str(p.price).lower().replace(' ', '')
            try:
                if 'l' in price_str:  # 30L → 30,00,000
                    val = float(price_str.replace('l', '')) * 100000
                elif 'cr' in price_str:  # 1.2Cr → 1,20,00,000
                    val = float(price_str.replace('cr', '')) * 10000000
                else:
                    val = float(price_str)
                numeric_prices.append(val)
            except Exception:
                continue

        if not numeric_prices:
            return None

        min_val = min(numeric_prices)
        if min_val >= 10000000:
            return f"{min_val / 10000000:.2f} Cr"
        elif min_val >= 100000:
            return f"{min_val / 100000:.2f} L"
        else:
            return f"₹{int(min_val)}"



class PlotInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlotInventory
        fields = ['id', 'plot_no', 'size', 'area_sq', 'price', 'is_available']


# commission API according to the plots
class AgentCommissionSerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="project.project_name", read_only=True)
    plot_no = serializers.CharField(source="lead_plot.plot.plot_no", read_only=True)
    plot_price = serializers.CharField(source="lead_plot.plot.price", read_only=True)
    commission_percentage = serializers.DecimalField(
        source="project.commission_percentage",
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    available_for_withdrawal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = AgentCommission
        fields = [
            "id",
            "lead_name",
            "project_name",
            "plot_no",
            "plot_price",
            "commission_percentage",
            "total_commission",
            "withdrawable_amount",
            "withdrawn_amount",
            "available_for_withdrawal",
            "created_at"
        ]

    def get_lead_name(self, obj):
        return obj.lead_plot.lead_project.lead.full_name
    

class TopAgentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="agent.full_name")
    profile_image = serializers.ImageField(source="agent.profile_image", allow_null=True)
    rank = serializers.IntegerField()

    class Meta:
        model = AgentCommission
        fields = ["rank", "full_name", "profile_image", "total_commission"]