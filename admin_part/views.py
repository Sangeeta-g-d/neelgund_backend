from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Count, Q, Sum
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_protect
from .models import *
import pandas as pd
from auth_api.models import CustomUser
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from decimal import Decimal
from agents.models import Lead
import os
from django.utils import timezone
from pytz import timezone as pytz_timezone
from agents.models import LeadPlotPayment,LeadPlotAssignment,CommissionWithdrawal
from decimal import Decimal, ROUND_HALF_UP
from agents.models import AgentCommission

def admin_login(request):
    toast_message = None
    toast_type = "error"  # default type
    redirect_url = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_staff:
                login(request, user)

                # ✅ Remember Me logic
                if remember_me:
                    request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
                else:
                    request.session.set_expiry(0)  # expires on browser close

                toast_message = "Login successful! Redirecting..."
                toast_type = "success"
                redirect_url = "/admin_dashboard/"  # ✅ Correct key
            else:
                toast_message = "You are not authorized to access the admin panel."
        else:
            toast_message = "Invalid username or password."

    return render(request, "admin_login.html", {
        "toast_message": toast_message,
        "toast_type": toast_type,
        "redirect_url": redirect_url
    })

def admin_dashboard(request):
    # Summary counts
    projects_count = RealEstateProject.objects.count()
    agents_qs = CustomUser.objects.filter(is_staff=False)
    agents_count = agents_qs.count()
    leads_count = Lead.objects.count()
    plots_count = PlotInventory.objects.count()

    # Recent items
    recent_leads = Lead.objects.select_related('agent').order_by('-created_at')[:5]
    recent_agents = agents_qs.order_by('-date_joined')[:5]
    recent_projects = RealEstateProject.objects.order_by('-created_at')[:5]

    # Top performing agents by total commission (sum of AgentCommission.total_commission)
    top_agents = (
        CustomUser.objects.filter(is_staff=False)
        .annotate(total_commission_sum=Sum('commissions__total_commission'))
        .order_by('-total_commission_sum')[:5]
    )

    context = {
        'projects_count': projects_count,
        'agents_count': agents_count,
        'leads_count': leads_count,
        'plots_count': plots_count,
        'recent_leads': recent_leads,
        'recent_agents': recent_agents,
        'recent_projects': recent_projects,
        'top_agents': top_agents,
    }

    return render(request, 'admin_dashboard.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class AddAmenityView(View):
    def post(self, request):
        name = request.POST.get('name')
        icon = request.FILES.get('icon')

        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)

        if Amenity.objects.filter(name__iexact=name).exists():
            return JsonResponse({'error': 'Amenity already exists'}, status=400)

        try:
            amenity = Amenity.objects.create(name=name, icon=icon)
            return JsonResponse({
                'message': 'Amenity added successfully', 
                'id': amenity.id,
                'name': amenity.name
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
def add_project(request):
    amenities = Amenity.objects.all()
    toast_message = None

    if request.method == "POST":
        data = request.POST
        files = request.FILES
        excel_data = None
        excel_file = files.get("inventory_excel")

        # ✅ Step 1: Read Excel/CSV
        if excel_file:
            try:
                file_ext = os.path.splitext(excel_file.name)[1].lower()
                if file_ext in [".xlsx", ".xls", ".csv"]:
                    if file_ext == ".xlsx":
                        df = pd.read_excel(excel_file, engine="openpyxl")
                    elif file_ext == ".xls":
                        df = pd.read_excel(excel_file, engine="xlrd")
                    else:
                        df = pd.read_csv(excel_file)
                    excel_data = df.to_dict(orient="records")
                else:
                    raise ValueError("Unsupported file format.")
            except Exception as e:
                return render(request, 'add_project.html', {
                    'amenities': amenities,
                    'toast_message': f"❌ Invalid inventory file: {e}"
                })

        try:
            with transaction.atomic():
                # ✅ Step 2: Create Project
                project = RealEstateProject.objects.create(
                    project_id=data.get("project_id"),
                    project_name=data.get("project_name"),
                    location=data.get("location"),
                    project_type=data.get("project_type"),
                    description=data.get("description"),
                    banner_image=files.get("banner_image"),
                    brochure=files.get("brochure"),
                    map_layout=files.get("map_layout"),
                    total_plots=data.get("total_plots") or 0,
                    status=data.get("status"),
                    inventory_excel=files.get("inventory_excel"),
                    commission_percentage=data.get("commission_percentage") or 0,
                )

                # ✅ Step 3: Amenities
                project.amenities.set(data.getlist("amenities"))

                # ✅ Step 4: Highlights
                highlight_titles = data.getlist("highlight_title[]")
                highlight_subtitles = data.getlist("highlight_subtitle[]")
                for title, subtitle in zip(highlight_titles, highlight_subtitles):
                    if title.strip():
                        ProjectHighlight.objects.create(
                            project=project,
                            title=title.strip(),
                            subtitle=subtitle.strip() if subtitle else None
                        )

                # ✅ Step 5: Payment Phases
                phase_activities = data.getlist("phase_activity[]")
                phase_percentages = data.getlist("phase_percentage[]")
                phase_dues = data.getlist("phase_due[]")
                created_phases = []

                for idx, (activity, percentage, due) in enumerate(zip(phase_activities, phase_percentages, phase_dues), start=1):
                    if activity.strip():
                        phase = ProjectPaymentPhase.objects.create(
                            project=project,
                            activity=activity.strip(),
                            payment_percentage=percentage or 0,
                            due=due or 'immediate',
                            order=idx,
                        )
                        created_phases.append(phase)

                # ✅ Step 6: Set Current Phase (Manual OR Auto)
                current_phase_name = data.get("current_phase_name")
                current_phase = None
                if current_phase_name:
                    current_phase = next((p for p in created_phases if p.activity == current_phase_name), None)
                elif created_phases:
                    # Auto: default to first one if none selected
                    current_phase = created_phases[0]

                if current_phase:
                    project.current_phase = current_phase
                    project.save()

                # ✅ Step 7: Add Plots (Excel + Manual)
                if excel_data:
                    for row in excel_data:
                        plot_no = str(row.get("plot_no") or "").strip()
                        if plot_no:
                            PlotInventory.objects.create(
                                project=project,
                                plot_no=plot_no,
                                size=str(row.get("size") or "").strip(),
                                area_sq=row.get("area_sq") or 0,
                                price=str(row.get("price") or "").strip(),
                                is_available=True,
                            )

                for plot_no, size, area, price in zip(
                    data.getlist("plot_no[]"),
                    data.getlist("size[]"),
                    data.getlist("area_sq[]"),
                    data.getlist("price[]")
                ):
                    if plot_no:
                        PlotInventory.objects.create(
                            project=project,
                            plot_no=plot_no,
                            size=size,
                            area_sq=area or 0,
                            price=price or "",
                            is_available=True,
                        )

                toast_message = "✅ Project added successfully!"

        except Exception as e:
            print("Error adding project:", e)
            toast_message = f"❌ Failed to add project: {e}"

        return render(request, 'add_project.html', {
            'amenities': amenities,
            'toast_message': toast_message
        })

    return render(request, 'add_project.html', {'amenities': amenities})


def projects(request):
    projects = RealEstateProject.objects.all().order_by('-created_at')
    return render(request, 'projects.html', {'projects': projects})

def project_details(request, project_id):
    project = RealEstateProject.objects.get(id=project_id)
    plots = project.plots.all()
    highlights = project.highlights.all()
    payment_phases = project.payment_phases.all()
    current_phase = project.current_phase  # 👈 Add this line

    return render(request, 'project_details.html', {
        'project': project,
        'plots': plots,
        'highlights': highlights,
        'payment_phases': payment_phases,
        'current_phase': current_phase,  # 👈 Pass it to template
    })

def agents_list(request):
    users = CustomUser.objects.exclude(is_staff=True)\
                              .annotate(lead_count=Count('leads'))\
                              .order_by('-date_joined')
    
    # Fix: Count after annotation to ensure consistency
    approved_count = users.filter(approved=True).count()
    pending_count = users.filter(approved=False).count()
    
    # Calculate total leads across all agents
    total_leads = sum(user.lead_count for user in users)
    
    context = {
        'users': users,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'total_leads': total_leads,  # Add total leads to context
    }
    return render(request, 'agents_list.html', context)


def agent_detail(request, agent_id):
    agent = get_object_or_404(CustomUser, id=agent_id, is_staff=False)
    leads = Lead.objects.filter(agent=agent).select_related('agent').prefetch_related('projects')

    # Lead counts by status
    total_leads = leads.count()
    closed_deals = leads.filter(status='closed').count()
    leads_new = leads.filter(status='new').count()
    leads_in_progress = leads.filter(status='in_progress').count()
    leads_cancelled = leads.filter(status='cancelled').count()
    
    # Commission calculations
    commissions = AgentCommission.objects.filter(agent=agent)
    total_commission = commissions.aggregate(
        total=models.Sum('total_commission')
    )['total'] or 0
    
    available_commission = commissions.aggregate(
        available=models.Sum('withdrawable_amount') - models.Sum('withdrawn_amount')
    )['available'] or 0
    
    withdrawn_amount = commissions.aggregate(
        withdrawn=models.Sum('withdrawn_amount')
    )['withdrawn'] or 0

    # Withdrawal requests
    withdrawal_requests = CommissionWithdrawal.objects.filter(
        commission__agent=agent
    ).select_related('commission').order_by('-requested_at')

    # Get recent leads (last 10)
    recent_leads = leads.order_by('-created_at')[:10]

    context = {
        'agent': agent,
        'total_leads': total_leads,
        'closed_deals': closed_deals,
        'leads_new': leads_new,
        'leads_in_progress': leads_in_progress,
        'leads_cancelled': leads_cancelled,
        'total_commission': total_commission,
        'available_commission': available_commission,
        'withdrawn_amount': withdrawn_amount,
        'withdrawal_requests': withdrawal_requests,
        'recent_leads': recent_leads,
    }
    return render(request, 'agent_detail.html', context)


def edit_project(request, project_id):
    project = get_object_or_404(RealEstateProject, pk=project_id)
    amenities = Amenity.objects.all()
    toast_message = None

    if request.method == "POST":
        data = request.POST
        files = request.FILES

        try:
            with transaction.atomic():
                # 1️⃣ Update main project details
                project.project_id = data.get("project_id")
                project.project_name = data.get("project_name")
                project.location = data.get("location")
                project.project_type = data.get("project_type")
                project.description = data.get("description")
                project.total_plots = data.get("total_plots") or 0
                project.status = data.get("status")
                project.commission_percentage = data.get("commission_percentage") or 0

                # 🖼 Update files if uploaded
                if files.get("banner_image"):
                    project.banner_image = files.get("banner_image")
                if files.get("brochure"):
                    project.brochure = files.get("brochure")
                if files.get("map_layout"):
                    project.map_layout = files.get("map_layout")

                project.save()

                # 2️⃣ Update amenities
                project.amenities.set(data.getlist("amenities"))

                # 3️⃣ Update highlights (same as before)
                highlight_ids = data.getlist("highlight_id[]")
                highlight_titles = data.getlist("highlight_title[]")
                highlight_subtitles = data.getlist("highlight_subtitle[]")

                existing_ids = []
                for h_id, title, subtitle in zip(highlight_ids, highlight_titles, highlight_subtitles):
                    if title.strip():
                        if h_id:
                            highlight = ProjectHighlight.objects.get(id=h_id)
                            highlight.title = title.strip()
                            highlight.subtitle = subtitle.strip() if subtitle else None
                            highlight.save()
                            existing_ids.append(highlight.id)
                        else:
                            new_h = ProjectHighlight.objects.create(
                                project=project,
                                title=title.strip(),
                                subtitle=subtitle.strip() if subtitle else None
                            )
                            existing_ids.append(new_h.id)
                project.highlights.exclude(id__in=existing_ids).delete()

                # 4️⃣ Update payment phases
                phase_ids = data.getlist("phase_id[]")
                phase_activities = data.getlist("phase_activity[]")
                phase_percentages = data.getlist("phase_percentage[]")
                phase_dues = data.getlist("phase_due[]")

                existing_phase_ids = []
                for idx, (p_id, activity, percentage, due) in enumerate(zip(phase_ids, phase_activities, phase_percentages, phase_dues), start=1):
                    if activity.strip():
                        if p_id:
                            phase = ProjectPaymentPhase.objects.get(id=p_id)
                            phase.activity = activity.strip()
                            phase.payment_percentage = percentage or 0
                            phase.due = due
                            phase.order = idx
                            phase.save()
                            existing_phase_ids.append(phase.id)
                        else:
                            new_phase = ProjectPaymentPhase.objects.create(
                                project=project,
                                activity=activity.strip(),
                                payment_percentage=percentage or 0,
                                due=due,
                                order=idx
                            )
                            existing_phase_ids.append(new_phase.id)

                project.payment_phases.exclude(id__in=existing_phase_ids).delete()

                # 5️⃣ Update current phase (new)
                current_phase_id = data.get("current_phase")
                if current_phase_id:
                    project.current_phase_id = current_phase_id
                else:
                    project.current_phase = None
                project.save()

                # 6️⃣ Update plots
                plot_ids = data.getlist("plot_id[]")
                plot_nos = data.getlist("plot_no[]")
                sizes = data.getlist("size[]")
                areas = data.getlist("area_sq[]")
                prices = data.getlist("price[]")

                existing_plot_ids = []
                for p_id, p_no, size, area, price in zip(plot_ids, plot_nos, sizes, areas, prices):
                    if p_no.strip():
                        if p_id:
                            plot = PlotInventory.objects.get(id=p_id)
                            plot.plot_no = p_no
                            plot.size = size
                            plot.area_sq = area or 0
                            plot.price = price
                            plot.save()
                            existing_plot_ids.append(plot.id)
                        else:
                            new_plot = PlotInventory.objects.create(
                                project=project,
                                plot_no=p_no,
                                size=size,
                                area_sq=area or 0,
                                price=price,
                                is_available=True
                            )
                            existing_plot_ids.append(new_plot.id)
                project.plots.exclude(id__in=existing_plot_ids).delete()

                toast_message = "✅ Project updated successfully!"

        except Exception as e:
            print("Error updating project:", e)
            toast_message = f"❌ Failed to update project: {e}"

        return render(request, "edit_project.html", {
            "project": project,
            "amenities": amenities,
            "toast_message": toast_message
        })

    return render(request, "edit_project.html", {
        "project": project,
        "amenities": amenities
    })


@transaction.atomic
def delete_project(request, project_id):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            project = get_object_or_404(RealEstateProject, id=project_id)
            project.delete()
            return JsonResponse({"success": True, "message": "✅ Project deleted successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"❌ Failed to delete project: {e}"})
    return JsonResponse({"success": False, "message": "❌ Invalid request"})

@csrf_protect
@require_POST
def approve_agent(request, user_id):
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        user.approved = True
        user.save()
        return JsonResponse({'success': True, 'message': f'{user.full_name} has been approved.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_protect
@require_POST
def deactivate_agent(request, user_id):
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        user.approved = False
        user.save()
        return JsonResponse({'success': True, 'message': f'{user.full_name} has been deactivated.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
def leads(request):
    leads = Lead.objects.all().order_by('-created_at')
    return render(request, 'leads.html', {'leads': leads})

def lead_list(request):
    leads = (
        Lead.objects.select_related('agent')
        .prefetch_related('projects')
        .order_by('-created_at')
    )

    context = {
        "leads": leads
    }
    return render(request, 'leads_list.html', context)

def lead_details(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    lead_projects = lead.lead_projects.select_related('project').prefetch_related('assigned_plots__plot')

    # Convert assigned_at for all assigned plots to IST
    ist = pytz_timezone('Asia/Kolkata')
    for lead_project in lead_projects:
        for assignment in lead_project.assigned_plots.all():
            assignment.assigned_at_ist = assignment.assigned_at.astimezone(ist)

    context = {
        'lead': lead,
        'lead_projects': lead_projects,
    }
    return render(request, 'lead_details.html', context)


def lead_plot_detail(request, assignment_id):
    assignment = get_object_or_404(LeadPlotAssignment, id=assignment_id)
    project = assignment.plot.project
    lead = assignment.lead_project.lead
    phases = ProjectPaymentPhase.objects.filter(project=project).order_by('order')

    # --- Helper: Parse price strings like "80L", "1Cr", "50K"
    def parse_price(price_str):
        price_str = str(price_str).lower().strip()
        try:
            if 'cr' in price_str:
                return Decimal(price_str.replace('cr', '').strip()) * 10000000
            elif 'l' in price_str:
                return Decimal(price_str.replace('l', '').strip()) * 100000
            elif 'k' in price_str:
                return Decimal(price_str.replace('k', '').strip()) * 1000
            return Decimal(price_str)
        except Exception:
            return Decimal(0)

    plot_price = parse_price(assignment.plot.price)

    # --- Handle POST (Form Submission)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for phase in phases:
                    amount_paid = (plot_price * phase.payment_percentage / Decimal(100)).quantize(Decimal('0.01'))
                    remarks = request.POST.get(f'remarks_{phase.id}')
                    paid_value = request.POST.get(f'paid_{phase.id}') == 'on'

                    payment, created = LeadPlotPayment.objects.get_or_create(
                        lead_plot=assignment,
                        phase=phase,
                        defaults={'amount_paid': amount_paid, 'remarks': remarks, 'paid': paid_value}
                    )
                    if not created:
                        payment.amount_paid = amount_paid
                        payment.remarks = remarks
                        payment.paid = paid_value
                        payment.save()

                messages.success(request, "Payment phases updated successfully!")
            return redirect('lead_plot_detail', assignment_id=assignment.id)
        except Exception as e:
            messages.error(request, f"Error updating payments: {str(e)}")

    # --- Existing payments
    existing_payments = {p.phase_id: p for p in assignment.payments.all()}

    # --- Totals
    total_paid = sum(p.amount_paid for p in existing_payments.values() if p.paid)
    total_balance = plot_price - total_paid

    # --- Current project phase (if any)
    current_phase = project.current_phase

    # --- Calculate next payment logic
    next_payment_balance = Decimal(0)
    next_unpaid_phases = []

    if current_phase:
        current_order = current_phase.order
        # Include all phases <= current_phase.order (because they are part of work done so far)
        # but only if they are unpaid
        for phase in phases:
            payment = existing_payments.get(phase.id)
            if phase.order <= current_order and (not payment or not payment.paid):
                phase_amount = (plot_price * phase.payment_percentage / Decimal(100)).quantize(Decimal('0.01'))
                next_payment_balance += phase_amount
                next_unpaid_phases.append(phase)
    else:
        # If no current phase, just take the first unpaid phase
        for phase in phases:
            payment = existing_payments.get(phase.id)
            if not payment or not payment.paid:
                phase_amount = (plot_price * phase.payment_percentage / Decimal(100)).quantize(Decimal('0.01'))
                next_payment_balance += phase_amount
                next_unpaid_phases.append(phase)
                break

    # --- Optional: Get first unpaid phase (for UI)
    next_phase = next_unpaid_phases[0] if next_unpaid_phases else None

    # --- Phase balance dictionary (for table)
    phase_balance_dict = {
        phase.id: (plot_price * phase.payment_percentage / Decimal(100)).quantize(Decimal('0.01'))
        for phase in phases
    }

    context = {
        'assignment': assignment,
        'lead': lead,
        'project': project,
        'phases': phases,
        'plot_price': plot_price,
        'existing_payments': existing_payments,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'next_phase': next_phase,
        'next_payment_balance': next_payment_balance,  # ✅ total of unpaid phases <= current phase
        'phase_balance_dict': phase_balance_dict,
        'current_phase': current_phase,
    }

    return render(request, 'lead_plot_detail.html', context)    


# withdraw request
from django.utils import timezone
import pytz

def withdrawal_requests(request):
    ist = pytz.timezone("Asia/Kolkata")

    withdrawals_qs = (
        CommissionWithdrawal.objects
        .select_related("commission", "commission__agent", "commission__project")
        .order_by("-requested_at")
    )

    total_requests = withdrawals_qs.count()
    pending_requests = withdrawals_qs.filter(approved=False).count()
    approved_requests = withdrawals_qs.filter(approved=True).count()

    withdrawals = list(withdrawals_qs)

    for w in withdrawals:
        if w.requested_at:
            w.requested_at = timezone.localtime(w.requested_at, ist)

        if w.approved_at:
            w.approved_at = timezone.localtime(w.approved_at, ist)

    context = {
        'withdrawals': withdrawals,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
    }

    return render(request, 'withdrawal_requests.html', context)


@require_POST
def approve_withdrawal(request, pk):
    withdrawal = get_object_or_404(CommissionWithdrawal, id=pk)

    if withdrawal.approved:
        messages.info(request, "This withdrawal has already been approved.")
        return redirect('withdrawal_requests')

    with transaction.atomic():
        withdrawal.approved = True
        withdrawal.approved_at = timezone.now()
        withdrawal.save()

        commission = withdrawal.commission
        amount = withdrawal.amount
        commission.withdrawable_amount = max(Decimal('0'), commission.withdrawable_amount - amount)
        commission.withdrawn_amount += amount
        commission.save()

    messages.success(request, f"Withdrawal of ₹{withdrawal.amount} for {commission.agent.full_name} approved successfully.")
    return redirect('withdrawal_requests')

def marketing_tools(request):
    projects = RealEstateProject.objects.filter(
        Q(brochure__isnull=False) | Q(map_layout__isnull=False)
    ).order_by('-created_at')
    
    # Separate projects with brochures and maps for better organization
    projects_with_brochures = [p for p in projects if p.brochure]
    projects_with_maps = [p for p in projects if p.map_layout]
    
    context = {
        'projects': projects,
        'projects_with_brochures': projects_with_brochures,
        'projects_with_maps': projects_with_maps,
    }
    return render(request, 'marketing_tools.html', context)


@require_POST
@csrf_protect
def delete_project_brochure(request, project_id):
    project = get_object_or_404(RealEstateProject, id=project_id)
    if project.brochure:
        # Delete file from storage, then clear field
        project.brochure.delete(save=False)
        project.brochure = None
        project.save(update_fields=['brochure'])
    return JsonResponse({'success': True, 'message': 'Brochure deleted successfully.'})


@require_POST
@csrf_protect
def delete_project_map_layout(request, project_id):
    project = get_object_or_404(RealEstateProject, id=project_id)
    if project.map_layout:
        project.map_layout.delete(save=False)
        project.map_layout = None
        project.save(update_fields=['map_layout'])
    return JsonResponse({'success': True, 'message': 'Map layout deleted successfully.'})

def add_agent(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        dob = request.POST.get("dob", None)

        adhar_card = request.FILES.get("adhar_card")
        pan_card = request.FILES.get("pan_card")
        profile_image = request.FILES.get("profile_image")

        # Validate required fields
        if not full_name or not email or not phone_number:
            messages.error(request, "Full name, email, and phone number are required.")
            return redirect("add_agent")

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("add_agent")

        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            full_name=full_name,
            phone_number=phone_number,
            dob=dob or None,
            approved = True
        )

        # Use phone number as password
        user.set_password(phone_number)

        # Optional documents
        if adhar_card:
            user.adhar_card = adhar_card
        if pan_card:
            user.pan_card = pan_card
        if profile_image:
            user.profile_image = profile_image

        user.save()
        messages.success(request, "Agent added successfully!")
        return redirect("add_agent")

    return render(request, "add_agent.html")


