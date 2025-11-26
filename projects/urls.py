from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('project-list/', ProjectListAPIView.as_view(), name='project-list'),
    path('project/<int:pk>/', ProjectDetailAPIView.as_view(), name='project-detail'),
    path('search-projects/', ProjectSearchAPIView.as_view(), name='project-search'),
    path('payment-details/<int:plot_id>/', PlotPaymentBreakdownAPIView.as_view(), name='project-payment-details'),
    path("projects-brochure/", ProjectBrochureListAPIView.as_view(), name="project-list"),
    path("project-layout/",ProjectMapLayoutListAPIView.as_view(),name="project-layout")
    
    ]