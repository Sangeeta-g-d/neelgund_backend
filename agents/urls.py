from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('projects-name-for-dropdown/', ProjectDropdownAPIView.as_view(), name='project-dropdown'),
    path('add-leads/', LeadCreateAPIView.as_view(), name='add-lead'),
    path('leads-list/', LeadListAPIView.as_view(), name='leads-list'),
    path("update-lead-status/<int:lead_id>/", LeadStatusUpdateAPIView.as_view()),
    path('customer/', CustomerListAPIView.as_view(), name='customer-list'),
    path('search-customer/', CustomerSearchAPIView.as_view(), name='customer-search'),
    path('customer-details/', CustomerListAPIView.as_view(), name='customer-details'),
    path('lead-plots/<int:project_id>/', LeadPlotAssignmentAPIView.as_view(), name='lead_plot_assignments'),    
    path('assign-projects/<int:pk>/', AssignProjectsToLeadAPIView.as_view(), name='assign-projects-to-lead'),

    path('banner-images/', TopProjectsAPIView.as_view(), name='top-projects'),
    path('upcoming-projects/', OngoingReadyProjectsAPIView.as_view(), name='ongoing-ready-projects'),

    # assign plot to lead
    path('available-plots/<int:project_id>/', AvailablePlotsAPIView.as_view(), name='available-plots'),
    path('assign-plot/<int:pk>/', AssignPlotsToLeadProjectAPIView.as_view(), name='assign-plot'),

    path('update-plot-status/<int:pk>/',UpdatePlotAssignmentStatusAPIView.as_view(),name="update-plot-status"),

    # commission
    path('lead-commissions/', AgentCommissionListAPIView.as_view(), name='agent-commissions'),
    path('booking-record/',AgentBookingRecordAPIView.as_view(),name="booking-record"),
    path('booking-details/<int:pk>/',AgentBookingDetailAPIView.as_view(),name="booking-details"),

    # agent earning
    path('agent-earning/', AgentEarningsSummaryAPIView.as_view(), name='agent-commission-summary'),
    path('withdraw-request/', AddWithdrawalRequestAPIView.as_view(), name='add-withdraw-request'),
    path('withdrawals/', AgentWithdrawalListAPIView.as_view(), name='agent-withdrawal-list'),

    # top 5 agents
    path('top-five/',TopAgentsCommissionAPIView.as_view(),name="top-five")
]

