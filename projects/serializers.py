# serializers.py
from rest_framework import serializers
from admin_part.models import RealEstateProject
from django.db.models import Sum
from admin_part.models import ProjectHighlight, PlotInventory,Amenity
from decimal import Decimal
import re


class RealEstateProjectSerializer(serializers.ModelSerializer):
    banner_image = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()

    class Meta:
        model = RealEstateProject
        fields = ['id', 'project_name', 'location', 'status', 'banner_image', 'starting_price']

    def get_banner_image(self, obj):
        request = self.context.get('request')
        if obj.banner_image and hasattr(obj.banner_image, 'url'):
            return request.build_absolute_uri(obj.banner_image.url)
        return None

    def get_starting_price(self, obj):
        """
        Fetch the lowest price among the plots of this project.
        Handles '30L', '1.2Cr', '25K', '3000000', etc.
        Converts everything to Lakhs internally for comparison,
        but preserves correct display format.
        """
        def convert_price(price_str):
            """Convert price string to (lakhs_value, display_unit, display_value)."""
            if not price_str:
                return None, None, None

            price_str = str(price_str).upper().replace('₹', '').replace(' ', '').strip()
            try:
                numeric_value = Decimal(re.sub(r'[^0-9.]', '', price_str))

                if 'CR' in price_str:
                    # 1 Cr = 100 Lakhs
                    return numeric_value * 100, 'Cr', numeric_value
                elif 'L' in price_str:
                    return numeric_value, 'L', numeric_value
                elif 'K' in price_str:
                    # 1 Lakh = 100K
                    return numeric_value / 100, 'K', numeric_value
                else:
                    # Assume value in rupees → convert to Lakhs
                    return numeric_value / 100000, 'L', numeric_value / 100000
            except Exception:
                return None, None, None

        plots = obj.plots.all().values_list('price', flat=True)
        converted_prices = []

        for p in plots:
            lakhs_value, unit, display_value = convert_price(p)
            if lakhs_value is not None:
                converted_prices.append({
                    'lakhs': lakhs_value,
                    'unit': unit,
                    'display': display_value
                })

        if not converted_prices:
            return None

        # Find the minimum price in Lakhs
        min_price = min(converted_prices, key=lambda x: x['lakhs'])
        unit = min_price['unit']
        display_value = min_price['display']

        # Properly format according to the detected unit
        if unit == 'Cr':
            return f"₹{round(display_value, 2)} Cr"
        elif unit == 'L':
            return f"₹{round(display_value, 2)} L"
        elif unit == 'K':
            return f"₹{int(display_value)} K"
        else:
            return f"₹{round(display_value, 2)} L"

class ProjectHighlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectHighlight
        fields = ['title', 'subtitle']


class PlotInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlotInventory
        fields = ['id','plot_no', 'size', 'area_sq', 'price', 'is_available']


class AmenitySerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon']

    def get_icon(self, obj):
        request = self.context.get('request')
        if obj.icon and hasattr(obj.icon, 'url'):
            return request.build_absolute_uri(obj.icon.url)
        return None

class ProjectDetailSerializer(serializers.ModelSerializer):
    banner_image = serializers.SerializerMethodField()
    brochure_url = serializers.SerializerMethodField()
    map_layout_url = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()
    total_area_sq_ft = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()
    available_plots = serializers.SerializerMethodField()
    booked_plots = serializers.SerializerMethodField()
    unique_plot_sizes = serializers.SerializerMethodField()
    highlights = ProjectHighlightSerializer(many=True, read_only=True)
    plots = PlotInventorySerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)

    class Meta:
        model = RealEstateProject
        fields = [
            'id',
            'project_name',
            'description',
            'banner_image',
            'brochure_url',
            'map_layout_url',
            'total_units',
            'total_area_sq_ft',
            'starting_price',
            'available_plots',
            'booked_plots',
            'unique_plot_sizes',
            'highlights',
            'plots',
            'amenities'
        ]

    def get_banner_image(self, obj):
        request = self.context.get('request')
        if obj.banner_image and hasattr(obj.banner_image, 'url'):
            return request.build_absolute_uri(obj.banner_image.url)
        return None

    def get_brochure_url(self, obj):
        request = self.context.get('request')
        if obj.brochure and hasattr(obj.brochure, 'url'):
            return request.build_absolute_uri(obj.brochure.url)
        return None

    def get_map_layout_url(self, obj):
        request = self.context.get('request')
        if obj.map_layout and hasattr(obj.map_layout, 'url'):
            return request.build_absolute_uri(obj.map_layout.url)
        return None

    def get_total_units(self, obj):
        return obj.plots.count()

    def get_total_area_sq_ft(self, obj):
        from django.db.models import Sum
        return obj.plots.aggregate(total_area=Sum('area_sq'))['total_area'] or 0

    def get_starting_price(self, obj):
        """Returns the minimum price with proper L/Cr suffix."""
        def parse_price(price_str):
            return price_str.strip().upper()

        prices = []
        for plot in obj.plots.all():
            price_with_suffix = parse_price(plot.price)
            if price_with_suffix:
                try:
                    if 'CR' in price_with_suffix:
                        numeric_value = float(price_with_suffix.replace('CR', '')) * 100
                    elif 'L' in price_with_suffix:
                        numeric_value = float(price_with_suffix.replace('L', ''))
                    else:
                        numeric_value = float(price_with_suffix)
                    prices.append((numeric_value, price_with_suffix))
                except:
                    continue

        if prices:
            prices.sort(key=lambda x: x[0])
            return prices[0][1]
        return None

    def get_available_plots(self, obj):
        return obj.plots.filter(is_available=True).count()

    def get_booked_plots(self, obj):
        return obj.plots.filter(is_available=False).count()

    def get_unique_plot_sizes(self, obj):
        return list(obj.plots.values_list('size', flat=True).distinct())


class ProjectListSerializer(serializers.ModelSerializer):
    banner_image = serializers.SerializerMethodField()
    brochure = serializers.SerializerMethodField()

    class Meta:
        model = RealEstateProject
        fields = ["id", "project_name", "banner_image", "brochure"]

    def get_banner_image(self, obj):
        request = self.context.get("request")
        if obj.banner_image:
            return request.build_absolute_uri(obj.banner_image.url)
        return None

    def get_brochure(self, obj):
        request = self.context.get("request")
        if obj.brochure:
            return request.build_absolute_uri(obj.brochure.url)
        return None


class ProjectMapLayoutSerializer(serializers.ModelSerializer):
    map_layout = serializers.SerializerMethodField()

    class Meta:
        model = RealEstateProject
        fields = ['id', 'project_name', 'map_layout']

    def get_map_layout(self, obj):
        request = self.context.get('request')
        if obj.map_layout:
            return request.build_absolute_uri(obj.map_layout.url)
        return None