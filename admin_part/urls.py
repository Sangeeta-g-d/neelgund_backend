from django.urls import path
from .views import *
from . import views


urlpatterns = [
    path('',views.admin_login,name="ad_login"),
    path('admin_dashboard/',views.admin_dashboard,name="admin_dashboard"),
    path('add_amenity/', AddAmenityView.as_view(), name='add_amenity'),
    path('add_project/',views.add_project,name="add_project"),
    path('projects/',views.projects,name="projects"),
    path('project-details/<int:project_id>/', views.project_details, name='project_details'),
    path('agents_list/', views.agents_list, name='agents_list'),
    path('approve-agent/<int:user_id>/', views.approve_agent, name='approve_agent'),
    path('deactivate-agent/<int:user_id>/', views.deactivate_agent, name='deactivate_agent'),
    path('leads/', views.leads, name='leads'),
    path('edit-project/<int:project_id>/', views.edit_project, name='edit_project'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete_project'),

    path('lead_list/', views.lead_list, name='lead_list'),

    path('agents/<int:agent_id>/', views.agent_detail, name='agent_detail'),
    path('lead_details/<int:lead_id>/',views.lead_details,name="lead_details"),
    path('lead-plot-details/<int:assignment_id>/', views.lead_plot_detail, name='lead_plot_detail'),


    # withdraw requests
    path('withdrawal_requests/',views.withdrawal_requests,name="withdrawal_requests"),
    path('approve_withdrawal/<int:pk>/', views.approve_withdrawal, name="approve_withdrawal"),

    path('add_agent/',views.add_agent,name="add_agent"),
    path('marketing_tools/',views.marketing_tools,name="marketing_tools"),
    path('projects/<int:project_id>/delete-brochure/', views.delete_project_brochure, name='delete_project_brochure'),
    path('projects/<int:project_id>/delete-map-layout/', views.delete_project_map_layout, name='delete_project_map_layout'),
    path('logout/', views.logout_view, name='logout'),

]