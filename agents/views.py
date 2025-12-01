# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from admin_part.models import RealEstateProject
from .serializers import *
from .models import *
from django.db.models import Sum
from rest_framework import status, permissions
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from django.db import transaction
import uuid
from .models import parse_price 
from neelgund_backend.timezone_utils import format_datetime_ist

class ProjectDropdownAPIView(APIView):
    def get(self, request):
        projects = RealEstateProject.objects.order_by('project_name')
        serializer = ProjectDropdownSerializer(projects, many=True)
        return Response({
            "status_code": 200,
            "status": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class LeadCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data.copy()

        # Prevent adding projects at creation
        data.pop('projects', None)
        data.pop('project_ids', None)

        # Auto-assign current agent
        data['agent'] = request.user.id

        email = data.get("email")
        contact_number = data.get("contact_number")

        # 🔍 Check for duplicates
        duplicate_leads = Lead.objects.filter(
            Q(email=email) | Q(contact_number=contact_number)
        )

        duplicate_message = None
        if duplicate_leads.exists():
            duplicate_message = "A lead with this phone number or email already exists."

        serializer = LeadSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            lead = serializer.save()

            response_data = {
                "status_code": 201,
                "status": "success",
                "message": "Lead created successfully",
                "data": LeadListSerializer(lead).data
            }

            # Include duplicate message if applicable
            if duplicate_message:
                response_data["duplicate_warning"] = duplicate_message

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response({
            "status_code": 400,
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# update lead status
class LeadStatusUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, lead_id):
        lead = get_object_or_404(Lead, id=lead_id)

        serializer = LeadStatusUpdateSerializer(data=request.data)

        if serializer.is_valid():
            new_status = serializer.validated_data['status']

            # 1️⃣ If trying to change to booked → check assigned projects
            if new_status == "booked":
                has_project = LeadProject.objects.filter(lead=lead).exists()

                if not has_project:
                    return Response({
                        "status_code": 400,
                        "status": "error",
                        "message": "Please add a project to this lead before marking status as 'Booked'."
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 2️⃣ If validated and project exists → update status
            lead.status = new_status
            lead.save(update_fields=['status', 'updated_at'])

            return Response({
                "status_code": 200,
                "status": "success",
                "message": "Lead status updated successfully",
                "data": LeadListSerializer(lead).data
            }, status=status.HTTP_200_OK)

        return Response({
            "status_code": 400,
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CustomerListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agent = request.user  

        # Fetch customers created by this agent
        customers = Customer.objects.filter(agent=agent).order_by('-created_at')

        serializer = CustomerListSerializer(customers, many=True)

        return Response({
            "status_code": 200,
            "status": "success",
            "count": customers.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    

# search API
class CustomerSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agent = request.user
        query = request.query_params.get('q', '').strip()
        status_filter = request.query_params.get('status')
        type_filter = request.query_params.get('type')

        leads = Customer.objects.filter(agent=agent)

        # --- Search logic ---
        if query:
            leads = leads.filter(
                Q(full_name__icontains=query) |
                Q(contact_number__icontains=query) |
                Q(email__icontains=query) |
                Q(projects__project_name__icontains=query)   # ✅ FIXED here
            ).distinct()

        # --- Optional filters ---
        if status_filter:
            leads = leads.filter(status__iexact=status_filter)
        if type_filter:
            leads = leads.filter(type__iexact=type_filter)

        leads = leads.order_by('-created_at')

        serializer = CustomerListSerializer(leads, many=True, context={'request': request})
        return Response({
            "status_code": 200,
            "status": "success",
            "count": leads.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    

class CustomerListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agent = request.user
        customers = Customer.objects.filter(agent=agent).select_related('lead')

        serializer = CustomerListSerializer(customers, many=True, context={'request': request})
        return Response({
            "status_code": 200,
            "status": "success",
            "data": serializer.data
        })


class LeadListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agent = request.user  

        # Fetch only leads for this agent
        leads = Lead.objects.filter(agent=agent).order_by('-created_at')

        serializer = LeadListSerializer(leads, many=True)

        return Response({
            "status_code": 200,
            "status": "success",
            "count": leads.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    

class LeadPlotAssignmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        lead_projects = LeadProject.objects.filter(
            project__id=project_id,
            lead__agent=request.user
        )

        if not lead_projects.exists():
            raise NotFound("No lead projects found for this agent and project.")

        assignments = LeadPlotAssignment.objects.filter(
            lead_project__in=lead_projects
        ).select_related('plot')
        
        serializer = LeadPlotAssignmentSerializer(assignments, many=True)
        return Response({
            "status_code": 200,
            "status": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, project_id):
        assignment_id = request.data.get("assignment_id")
        if not assignment_id:
            return Response({"error": "assignment_id is required."}, status=400)

        assignment = LeadPlotAssignment.objects.filter(
            id=assignment_id,
            lead_project__project__id=project_id,
            lead_project__lead__agent=request.user
        ).first()

        if not assignment:
            raise NotFound("No LeadPlotAssignment found for this project and agent.")

        # ✅ Pass the data to serializer for update
        serializer = LeadPlotAssignmentSerializer(
            assignment,
            data=request.data,
            partial=True  # allow updating only some fields
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status_code": 200,
                "status": "updated",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, project_id):
        assignment_id = request.data.get("assignment_id")
        if not assignment_id:
            return Response({"error": "assignment_id is required."}, status=400)

        assignment = LeadPlotAssignment.objects.filter(
            id=assignment_id,
            lead_project__project__id=project_id,
            lead_project__lead__agent=request.user
        ).first()

        if not assignment:
            raise NotFound("No LeadPlotAssignment found for this project and agent.")

        assignment.delete()
        return Response({
            "status_code": 200,
            "status": "deleted",
            "message": "Plot assignment deleted successfully."
        }, status=status.HTTP_200_OK)


class AssignProjectsToLeadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        agent = request.user
        lead = get_object_or_404(Lead, id=pk, agent=agent)

        project_ids = request.data.get("project_ids")
        if not project_ids or not isinstance(project_ids, list):
            return Response(
                {"error": "Please provide a valid list of project IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_projects = RealEstateProject.objects.filter(id__in=project_ids)
        if not valid_projects.exists():
            return Response(
                {"error": "No valid projects found for given IDs."},
                status=status.HTTP_404_NOT_FOUND
            )

        assigned_count = 0

        with transaction.atomic():
            for project in valid_projects:
                # Create LeadProject only if not already assigned
                obj, created = LeadProject.objects.get_or_create(
                    lead=lead,
                    project=project,
                    defaults={"status": "in_progress"}  # default status
                )
                if created:
                    assigned_count += 1

        # ✅ Keep your original response format
        return Response(
            {
                "status": status.HTTP_200_OK,
                "message": f"{assigned_count} project(s) assigned successfully.",
            },
            status=status.HTTP_200_OK,
        )
    

class TopProjectsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # or IsAuthenticated if needed

    def get(self, request):
        # Fetch the 5 most recently created published projects
        projects = RealEstateProject.objects.order_by('-created_at')[:5]
        serializer = ProjectSummarySerializer(projects, many=True, context={'request': request})
        
        return Response({
            "status_code": 200,
            "status": "success",
            "count": len(serializer.data),
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    

class OngoingReadyProjectsAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # Adjust if needed

    def get(self, request):
        # Fetch only Ready to Move & Under Construction projects
        projects = RealEstateProject.objects.filter(
            status__in=['under_construction', 'ready_to_move']
        ).order_by('-created_at')

        serializer = ProjectWithPriceSerializer(projects, many=True, context={'request': request})

        return Response({
            "status_code": 200,
            "status": "success",
            "count": len(serializer.data),
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    

class AvailablePlotsAPIView(APIView):
    def get(self, request, project_id):
        try:
            project = RealEstateProject.objects.get(id=project_id)
        except RealEstateProject.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        plots = project.plots.filter(is_available=True)
        serializer = PlotInventorySerializer(plots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class AssignPlotsToLeadProjectAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        """
        Assign one or more plots to a specific lead project.
        Creates corresponding AgentCommission record with withdrawable = 0.
        Ensures all selected plots belong to the same project.
        """
        agent = request.user
        lead_project = get_object_or_404(LeadProject, id=pk, lead__agent=agent)

        plot_ids = request.data.get("plot_ids")
        remarks = request.data.get("remarks", "")
        order_id = request.data.get("order_id")

        # Auto-generate an order_id if not provided
        if not order_id:
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # ✅ Validate plot_ids
        if not plot_ids or not isinstance(plot_ids, list):
            return Response(
                {
                    "status_code": 400,
                    "status": "error",
                    "message": "Please provide a valid list of plot IDs."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        project = lead_project.project

        # ✅ Filter plots belonging only to this project
        valid_plots = PlotInventory.objects.filter(
            id__in=plot_ids,
            project=project,
            is_available=True
        )

        if not valid_plots.exists():
            return Response(
                {
                    "status_code": 404,
                    "status": "error",
                    "message": "No valid available plots found for this project."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ Check if any requested plot does NOT belong to this project
        invalid_plot_ids = set(plot_ids) - set(valid_plots.values_list("id", flat=True))
        if invalid_plot_ids:
            return Response(
                {
                    "status_code": 400,
                    "status": "error",
                    "message": f"Some plots ({list(invalid_plot_ids)}) do not belong to project '{project.project_name}'. "
                               "Please select only plots available under this project."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        assigned_count = 0

        with transaction.atomic():
            for plot in valid_plots:
                obj, created = LeadPlotAssignment.objects.get_or_create(
                    lead_project=lead_project,
                    plot=plot,
                    defaults={
                        "status": "booked",
                        "assigned_by": agent,
                        "remarks": remarks,
                        "order_id": order_id,
                    },
                )
                if created:
                    assigned_count += 1

                    # ✅ Mark plot as unavailable
                    plot.is_available = False
                    plot.save(update_fields=["is_available"])

                    # ✅ Create AgentCommission with withdrawable = 0
                    commission_obj, created_comm = AgentCommission.objects.get_or_create(
                        lead_plot=obj,
                        agent=agent,
                        project=project,
                        defaults={
                            "withdrawable_amount": Decimal('0'),
                            "withdrawn_amount": Decimal('0'),
                        },
                    )
                    # ✅ Calculate total commission
                    commission_obj.calculate_total_commission()

        # ✅ Return all assigned plots for that lead project
        assigned_plots = [
            {
                "id": ap.plot.id,
                "plot_no": ap.plot.plot_no,
                "status": ap.status,
                "order_id": ap.order_id,
                "is_available": ap.plot.is_available,
            }
            for ap in lead_project.assigned_plots.select_related("plot")
        ]

        return Response(
            {
                "status_code": 200,
                "status": "success",
                "message": f"{assigned_count} plot(s) successfully assigned to lead project '{project.project_name}'.",
                "assigned_plots": assigned_plots
            },
            status=status.HTTP_200_OK,
        )

# change plot status
class UpdatePlotAssignmentStatusAPIView(APIView):
    # No authentication enforced here based on your earlier note
    permission_classes = []

    def post(self, request, pk):
        """
        Update the status of one or more assigned plots.

        Example payload:
        {
            "plot_ids": [1, 2],
            "status": "closed",
            "remarks": "Full payment done"
        }
        """
        lead_project = get_object_or_404(LeadProject, id=pk)

        plot_ids = request.data.get("plot_ids")
        new_status = request.data.get("status")
        remarks = request.data.get("remarks", "")

        # Validate input
        if not plot_ids or not isinstance(plot_ids, list):
            return Response(
                {"status_code": 400, "status": "error", "message": "Please provide a valid list of plot IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status not in dict(LeadPlotAssignment.PLOT_STATUS_CHOICES):
            return Response(
                {
                    "status_code": 400,
                    "status": "error",
                    "message": f"Invalid status '{new_status}'. Valid choices are: {list(dict(LeadPlotAssignment.PLOT_STATUS_CHOICES).keys())}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        assignments = LeadPlotAssignment.objects.filter(
            lead_project=lead_project, plot_id__in=plot_ids
        )

        if not assignments.exists():
            return Response(
                {
                    "status_code": 404,
                    "status": "error",
                    "message": "No valid plot assignments found for given IDs."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        updated_count = 0
        with transaction.atomic():
            for assignment in assignments:
                assignment.status = new_status
                assignment.remarks = remarks or assignment.remarks
                assignment.save(update_fields=["status", "remarks", "updated_at"])
                updated_count += 1

                # ✅ Toggle plot availability
                if new_status == "cancelled":
                    # Plot becomes available again
                    assignment.plot.is_available = True
                elif new_status in ["booked", "closed"]:
                    # Booked or closed plots should remain unavailable
                    assignment.plot.is_available = False
                assignment.plot.save(update_fields=["is_available"])

            # ✅ Update project & lead automatically
            self._update_project_status(lead_project)
            self._update_lead_status(lead_project.lead)

        updated_plots = [
            {
                "id": ap.plot.id,
                "plot_no": ap.plot.plot_no,
                "status": ap.status,
                "order_id": ap.order_id,
                "is_available": ap.plot.is_available,
            }
            for ap in lead_project.assigned_plots.select_related("plot")
        ]

        return Response(
            {
                "status_code": 200,
                "status": "success",
                "message": f"Status updated for {updated_count} plot(s) in project '{lead_project.project.project_name}'.",
                "updated_plots": updated_plots
            },
            status=status.HTTP_200_OK
        )

    # ✅ Step 1: Update project status
    def _update_project_status(self, lead_project):
        plots = lead_project.assigned_plots.all()
        if not plots.exists():
            return

        active_plots = plots.exclude(status="cancelled")

        if not active_plots.exists():
            lead_project.status = "cancelled"
        elif all(p.status == "closed" for p in active_plots):
            lead_project.status = "closed"
        else:
            lead_project.status = "in_progress"

        lead_project.save(update_fields=["status", "updated_at"])

    # ✅ Step 2: Update lead status based on all its projects
    def _update_lead_status(self, lead):
        projects = lead.lead_projects.exclude(status="cancelled")  # ignore cancelled ones

        if not projects.exists():
            lead.status = "cancelled"
            lead.save(update_fields=["status", "updated_at"])
            return

        project_statuses = [p.status for p in projects]

        if any(status == "in_progress" for status in project_statuses):
            lead.status = "in_progress"
        elif any(status == "closed" for status in project_statuses):
            lead.status = "closed"
        else:
            lead.status = "in_progress"

        lead.save(update_fields=["status", "updated_at"])


# agent commission
class AgentCommissionListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Returns all commissions of the logged-in agent.
        """
        user = request.user
        commissions = AgentCommission.objects.filter(agent=user).select_related(
            "lead_plot__lead_project__lead", "lead_plot__plot", "project"
        )
        serializer = AgentCommissionSerializer(commissions, many=True)
        return Response({
            "status": "success",
            "count": commissions.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# booking details 
class AgentBookingRecordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agent = request.user
        search_query = request.query_params.get("search", "").strip()
        project_filter = request.query_params.get("project", "").strip()

        # ✅ Base Query
        assignments = (
            LeadPlotAssignment.objects
            .select_related(
                "lead_project__project",
                "lead_project__lead",
                "plot",
            )
            .filter(assigned_by=agent)
        )

        if search_query:
            assignments = assignments.filter(
                Q(lead_project__lead__full_name__icontains=search_query)
                | Q(plot__plot_no__icontains=search_query)
            )

        if project_filter:
            assignments = assignments.filter(
                lead_project__project__project_name__icontains=project_filter
            )

        assignments = assignments.order_by("-assigned_at")

        booking_data = []

        for assignment in assignments:
            project = assignment.lead_project.project
            lead = assignment.lead_project.lead
            plot = assignment.plot

            total_price = parse_price(plot.price)
            total_sqft = getattr(plot, "area_sq", Decimal("0.00"))

            paid_amount = assignment.payments.filter(paid=True).aggregate(
                total=Sum("amount_paid")
            )["total"] or Decimal("0.00")

            balance_amount = total_price - paid_amount

            commission_obj = getattr(assignment, "commission", None)
            total_commission = commission_obj.total_commission if commission_obj else Decimal("0.00")

            # ✅ Project Phases
            project_phases = project.payment_phases.order_by("order")
            total_phases = project_phases.count()

            paid_phase_ids = assignment.payments.filter(paid=True).values_list("phase_id", flat=True)
            paid_phases_count = len(paid_phase_ids)

            # ✅ Identify Current Project Phase
            current_phase = project.current_phase
            current_phase_order = current_phase.order if current_phase else None

            # ✅ Find unpaid phases till current phase
            unpaid_phases = project_phases.exclude(id__in=paid_phase_ids)
            unpaid_till_current = unpaid_phases
            if current_phase_order:
                unpaid_till_current = unpaid_phases.filter(order__lte=current_phase_order)

            # ✅ Next payment phase (next immediate unpaid one)
            next_phase = unpaid_phases.order_by("order").first()

            # ✅ Calculate next payment
            next_payment_details = None
            if unpaid_till_current.exists():
                total_pending_percent = unpaid_till_current.aggregate(
                    total=Sum("payment_percentage")
                )["total"] or Decimal("0.00")

                next_payment_amount = (total_price * total_pending_percent) / Decimal("100")
                first_unpaid = unpaid_till_current.first()

                next_payment_details = {
                    "activity": first_unpaid.activity,
                    "payment_percentage": f"{total_pending_percent:.2f}",
                    "due": first_unpaid.get_due_display(),
                    "next_payment_amount": f"{next_payment_amount:.2f}",
                }

            # ✅ Current Phase Details
            current_phase_data = None
            if current_phase:
                current_phase_data = {
                    "activity": current_phase.activity,
                    "payment_percentage": f"{current_phase.payment_percentage:.2f}",
                    "due": current_phase.get_due_display(),
                }

            booking_data.append({
                "project_name": project.project_name,
                "booking_id": assignment.id,
                "plot_number": plot.plot_no,
                "plot_id": plot.id,
                "lead_name": lead.full_name,
                "date": format_datetime_ist(assignment.assigned_at),
                "total_price": f"{total_price:.2f}",
                "total_sqft": str(total_sqft),
                "paid_amount": f"{paid_amount:.2f}",
                "balance_amount": f"{balance_amount:.2f}",
                "total_commission": f"{total_commission:.2f}",
                "total_phases": total_phases,
                "paid_phases": paid_phases_count,
                "current_phase": current_phase_data,
                "next_payment_phase": next_payment_details,
            })

        # ✅ Wrap everything inside "data"
        return Response(
            {
                "status_code": 200,
                "status": "success",
                "data": {
                    "filters": {
                        "search": search_query,
                        "project": project_filter,
                    },
                    "total_results": len(booking_data),
                    "bookings": booking_data
                }
            },
            status=status.HTTP_200_OK
        )



# booking full details
class AgentBookingDetailAPIView(APIView):
    """
    Fetch detailed info for a specific booking, including project, plot, lead, payment, and commission details.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        agent = request.user

        # ✅ Get assignment for this agent
        assignment = get_object_or_404(
            LeadPlotAssignment.objects.select_related(
                "lead_project__lead",
                "lead_project__project",
                "plot"
            ),
            id=pk,
            assigned_by=agent
        )

        project = assignment.lead_project.project
        lead = assignment.lead_project.lead
        plot = assignment.plot

        # ✅ Calculate prices
        total_price = parse_price(plot.price)
        total_sqft = getattr(plot, "area_sq", Decimal("0.00"))

        paid_amount = assignment.payments.filter(paid=True).aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0.00")

        balance_amount = total_price - paid_amount

        # ✅ Commission details
        commission = getattr(assignment, "commission", None)
        total_commission = commission.total_commission if commission else Decimal("0.00")
        withdrawable_amount = commission.withdrawable_amount if commission else Decimal("0.00")
        withdrawn_amount = commission.withdrawn_amount if commission else Decimal("0.00")

        # ✅ Project phases
        phases = project.payment_phases.order_by("order")
        total_phases = phases.count()

        paid_phase_ids = assignment.payments.filter(paid=True).values_list("phase_id", flat=True)
        paid_phases_count = len(paid_phase_ids)

        # ✅ Current project phase
        current_phase = project.current_phase
        current_phase_order = current_phase.order if current_phase else None

        # ✅ Identify unpaid phases
        unpaid_phases = phases.exclude(id__in=paid_phase_ids)

        # ✅ Case: If lead has missed earlier payments and current phase has advanced
        # → Add all unpaid phases till current project phase
        if current_phase_order:
            pending_till_current = unpaid_phases.filter(order__lte=current_phase_order)
        else:
            pending_till_current = unpaid_phases

        # ✅ Calculate next payment info (sum of pending till current)
        next_payment_details = None
        if pending_till_current.exists():
            total_pending_percent = pending_till_current.aggregate(
                total=Sum("payment_percentage")
            )["total"] or Decimal("0.00")

            next_payment_amount = (total_price * total_pending_percent) / Decimal("100")
            first_unpaid = pending_till_current.first()

            next_payment_details = {
                "activity": first_unpaid.activity,
                "payment_percentage": f"{total_pending_percent:.2f}",
                "due": first_unpaid.get_due_display(),
                "next_payment_amount": f"{next_payment_amount:.2f}",
            }

        # ✅ Build response data
        data = {
            "project": {
                "id": project.id,
                "name": project.project_name,
                "location": project.location,
            },
            "booking": {
                "booking_id": assignment.id,
                "plot": {
                    "id": plot.id,
                    "plot_no": plot.plot_no,
                    "size": plot.size,
                    "area_sq": float(total_sqft),
                    "price": str(total_price),
                },
                "lead": {
                    "id": lead.id,
                    "full_name": lead.full_name,
                    "contact_number": lead.contact_number,
                    "email": lead.email,
                },
                "date": format_datetime_ist(assignment.assigned_at),
            },
            "payments": {
                "total_amount": f"{total_price:.2f}",
                "total_paid": f"{paid_amount:.2f}",
                "balance_amount": f"{balance_amount:.2f}",
                "next_phase": next_payment_details,
            },
            "commission": {
                "total_commission": f"{total_commission:.2f}",
                "withdrawable_amount": f"{withdrawable_amount:.2f}",
                "withdrawn_amount": f"{withdrawn_amount:.2f}",
                "available_for_withdrawal": f"{max(Decimal('0.00'), withdrawable_amount - withdrawn_amount):.2f}",
            },
            "phases": [
                {
                    "id": phase.id,
                    "activity": phase.activity,
                    "payment_percentage": f"{phase.payment_percentage:.2f}",
                    "due": phase.get_due_display(),
                    "status": "Paid" if phase.id in paid_phase_ids else "Pending",
                }
                for phase in phases
            ],
            "summary": {
                "total_phases": total_phases,
                "paid_phases": paid_phases_count,
                "unpaid_phases": total_phases - paid_phases_count,
            },
        }

        return Response(
            {
                "status_code": 200,
                "status": "success",
                "data": data
            },
            status=status.HTTP_200_OK
        )


# agent earning
class AgentEarningsSummaryAPIView(APIView):
    """
    API to fetch total commission summary for the logged-in agent.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # ✅ Fetch only this agent’s commissions
        commissions = AgentCommission.objects.filter(agent=user)

        if not commissions.exists():
            return Response({
                "status": "success",
                "data": {
                    "total_earned": "0.00",
                    "total_withdrawable": "0.00",
                    "total_withdrawn": "0.00"
                }
            })

        # ✅ Compute totals
        totals = commissions.aggregate(
            total_earned=Sum('total_commission'),
            total_withdrawn=Sum('withdrawn_amount'),
            withdrawable_raw=Sum('withdrawable_amount')
        )

        # ✅ Calculate available withdrawable = withdrawable - withdrawn
        available_for_withdrawal = (
            (totals['withdrawable_raw'] or Decimal('0')) -
            (totals['total_withdrawn'] or Decimal('0'))
        )

        return Response({
            "status": "success",
            "data": {
                "total_earned": str(totals['total_earned'] or Decimal('0')),
                "total_withdrawn": str(totals['total_withdrawn'] or Decimal('0')),
                "available_for_withdrawal": str(max(Decimal('0'), available_for_withdrawal))
            }
        })
    

# withdraw request
class AddWithdrawalRequestAPIView(APIView):
    """
    API for agents to request a commission withdrawal.
    - Ensures requested amount ≤ total available withdrawable balance.
    - Prevents multiple pending withdrawal requests.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        amount = request.data.get("amount")

        # ✅ Step 1: Check for existing pending withdrawal
        pending_request = CommissionWithdrawal.objects.filter(
            commission__agent=user, approved=False
        ).first()

        if pending_request:
            return Response({
                "status": "error",
                "message": (
                    f"You already have a pending withdrawal request of ₹{pending_request.amount}. "
                    "Please wait until it is processed before submitting another."
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Step 2: Validate amount
        if not amount:
            return Response({
                "status": "error",
                "message": "Amount is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({
                "status": "error",
                "message": "Invalid amount format."
            }, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({
                "status": "error",
                "message": "Withdrawal amount must be greater than zero."
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Step 3: Calculate total available withdrawable amount for this agent
        commissions = AgentCommission.objects.filter(agent=user)
        total_withdrawable = sum((c.available_for_withdrawal for c in commissions), Decimal('0'))

        if amount > total_withdrawable:
            return Response({
                "status": "error",
                "message": f"Requested amount exceeds withdrawable balance. Available: ₹{total_withdrawable}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Step 4: Create withdrawal request (pending approval)
        withdrawal = CommissionWithdrawal.objects.create(
            commission=commissions.first(),  # Any commission association for now
            amount=amount,
            approved=False
        )

        return Response({
            "status": "success",
            "message": "Withdrawal request submitted successfully.",
            "data": {
                "request_id": withdrawal.id,
                "amount": str(amount),
                "approved": withdrawal.approved,
                "requested_at": withdrawal.requested_at
            }
        }, status=status.HTTP_201_CREATED)
    
# withdraw request list 
class AgentWithdrawalListAPIView(APIView):
    """
    API to fetch all withdrawal requests of the logged-in agent.
    Includes pending and approved requests.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # ✅ Fetch all withdrawal requests for this agent (through commission relation)
        withdrawals = CommissionWithdrawal.objects.filter(
            commission__agent=user
        ).select_related('commission', 'commission__project').order_by('-requested_at')

        if not withdrawals.exists():
            return Response({
                "status": "success",
                "message": "No withdrawal requests found.",
                "data": []
            }, status=status.HTTP_200_OK)

        # ✅ Format response data
        data = []
        for w in withdrawals:
            data.append({
                "id": w.id,
                "amount": str(w.amount),
                "approved": w.approved,
                "project": getattr(w.commission.project, "project_name", None),
                "requested_at": w.requested_at.strftime("%Y-%m-%d %H:%M:%S"),
                "approved_at": (
                    w.approved_at.strftime("%Y-%m-%d %H:%M:%S")
                    if w.approved_at else None
                ),
                "status": "Approved" if w.approved else "Pending"
            })

        return Response({
            "status": "success",
            "count": len(data),
            "data": data
        }, status=status.HTTP_200_OK)
    


# top 5 agents
class TopAgentsCommissionAPIView(APIView):

    def get(self, request):
        agent_totals = (
            AgentCommission.objects
            .values("agent",
                    "agent__full_name",
                    "agent__profile_image")
            .annotate(total=Sum("total_commission"))
            .order_by("-total")[:5]
        )

        results = []

        for idx, agent in enumerate(agent_totals, start=1):

            profile_image = agent["agent__profile_image"]

            # add media prefix manually
            if profile_image:
                profile_image_url = f"/media/{profile_image}"
            else:
                profile_image_url = ""

            results.append({
                "rank": idx,
                "full_name": agent["agent__full_name"],
                "profile_image": profile_image_url,
                "total_commission": agent["total"],
            })

        return Response({
            "status": "success",
            "data": results
        }, status=status.HTTP_200_OK)
