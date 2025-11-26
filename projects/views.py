
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from admin_part.models import RealEstateProject,ProjectPaymentPhase
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from decimal import Decimal
import re
from rest_framework.pagination import PageNumberPagination


class ProjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access
    def get(self, request):
        projects = RealEstateProject.objects.all().order_by('-created_at')
        serializer = RealEstateProjectSerializer(projects, many=True, context={'request': request})
        return Response({
            'status_code': status.HTTP_200_OK,
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    

class ProjectDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        project = get_object_or_404(RealEstateProject, pk=pk)
        serializer = ProjectDetailSerializer(project, context={'request': request})
        return Response({
            'status_code': status.HTTP_200_OK,
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class ProjectSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        status_filter = request.query_params.get('status', '').strip()
        min_price = request.query_params.get('min_price', '').strip()

        projects = RealEstateProject.objects.all().order_by('-created_at')

        # 🔍 Text-based filters
        if query:
            projects = projects.filter(
                Q(project_name__icontains=query) |
                Q(location__icontains=query) |
                Q(description__icontains=query)
            )

        if status_filter:
            projects = projects.filter(status__iexact=status_filter)

        # 💰 Robust converter supporting Cr, L, K, ₹, and numeric values
        def convert_price_to_lakhs(price_str):
            """
            Converts price strings to lakhs:
              - '1Cr'  → 100
              - '80L'  → 80
              - '10K'  → 0.1
              - '500000' → 5
            """
            if not price_str:
                return None

            price_str = str(price_str).upper().replace('₹', '').replace(' ', '').strip()
            try:
                numeric_part = Decimal(re.sub(r'[^0-9.]', '', price_str))

                if 'CR' in price_str:
                    return numeric_part * 100  # 1 Cr = 100 Lakhs
                elif 'L' in price_str:
                    return numeric_part         # Already in Lakhs
                elif 'K' in price_str:
                    return numeric_part / 100   # 1 Lakh = 100K
                else:
                    # Assume value is in rupees → convert to Lakhs
                    return numeric_part / 100000
            except Exception:
                return None

        min_price_val = convert_price_to_lakhs(min_price)

        # 🎯 Filter projects that have ANY plot >= given price
        if min_price_val is not None:
            valid_projects = []
            for project in projects:
                has_valid_plot = False
                for price_str in project.plots.values_list('price', flat=True):
                    price_val = convert_price_to_lakhs(price_str)
                    if price_val is not None and price_val >= min_price_val:
                        has_valid_plot = True
                        break  # ✅ One valid plot is enough

                if has_valid_plot:
                    valid_projects.append(project)

            projects = valid_projects

        # 🧾 Serialize results
        serializer = RealEstateProjectSerializer(projects, many=True, context={'request': request})
        return Response({
            'status_code': status.HTTP_200_OK,
            'status': 'success',
            'results_count': len(projects),
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    
class PlotPaymentBreakdownAPIView(APIView):
    """
    Returns payment breakdown for a plot based on its project's payment phases.
    """
    def get(self, request, plot_id):
    # 1️⃣ Fetch the plot
        plot = get_object_or_404(PlotInventory, id=plot_id)
        project = plot.project

        # 2️⃣ Convert price (e.g. "80L", "1.5Cr") → Decimal value (in Lakhs)
        price_str = plot.price.strip().upper()
        total_price_lakhs = Decimal(0)

        try:
            if 'CR' in price_str:
                total_price_lakhs = Decimal(price_str.replace('CR', '').strip()) * 100
            elif 'L' in price_str:
                total_price_lakhs = Decimal(price_str.replace('L', '').strip())
            else:
                total_price_lakhs = Decimal(price_str)
        except Exception:
            return Response({
                "status_code": status.HTTP_400_BAD_REQUEST,
                "status": "error",
                "message": f"Invalid price format for plot {plot.plot_no}."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3️⃣ Fetch payment phases ordered by 'order'
        phases = ProjectPaymentPhase.objects.filter(project=project).order_by('order')

        # 4️⃣ Build breakdown
        breakdown = []
        for phase in phases:
            value_lakhs = (total_price_lakhs * Decimal(phase.payment_percentage)) / 100

            # ✅ Format due (e.g. "60_days" → "60 days", "immediate" stays same)
            formatted_due = phase.due.replace('_', ' ')
            if formatted_due != 'immediate':
                formatted_due = formatted_due.capitalize()

            breakdown.append({
                "activity": phase.activity,
                "due": formatted_due,
                "payment_percentage": phase.payment_percentage,
                "calculated_value": f"{value_lakhs:.2f}L"
            })

        # 5️⃣ Return response
        return Response({
            "status_code": status.HTTP_200_OK,
            "status": "success",
            "data": {
                "plot_no": plot.plot_no,
                "project_name": project.project_name,
                "total_price": f"{total_price_lakhs:.2f}L",
                "payment_breakdown": breakdown
            }
        }, status=status.HTTP_200_OK)
    

class ProjectPagination(PageNumberPagination):
    page_size = 10  # default number of items per page
    page_size_query_param = "page_size"  # allow client to override, e.g. ?page_size=20
    max_page_size = 100  # prevent abuse


class ProjectBrochureListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Fetch paginated list of all projects with project ID, name, image, and brochure.
        Supports:
          - ?page=<num>
          - ?page_size=<num>
        """
        projects = RealEstateProject.objects.all().order_by("project_name")

        paginator = ProjectPagination()
        paginated_projects = paginator.paginate_queryset(projects, request)

        serializer = ProjectListSerializer(paginated_projects, many=True, context={"request": request})

        return paginator.get_paginated_response({
            "status_code": 200,
            "status": "success",
            "total_projects": projects.count(),
            "projects": serializer.data,
        })
    
class ProjectMapLayoutListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Fetch paginated list of all projects with project ID, name, image, and brochure.
        Supports:
          - ?page=<num>
          - ?page_size=<num>
        """
        projects = RealEstateProject.objects.all().order_by("project_name")

        paginator = ProjectPagination()
        paginated_projects = paginator.paginate_queryset(projects, request)

        serializer = ProjectMapLayoutSerializer(paginated_projects, many=True, context={"request": request})

        return paginator.get_paginated_response({
            "status_code": 200,
            "status": "success",
            "total_projects": projects.count(),
            "projects": serializer.data,
        })