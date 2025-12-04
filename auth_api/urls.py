from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', UserRegistrationAPIView.as_view(), name='user-register'),
    path('login_with_password/', LoginAPIView.as_view(), name='user-login'),
    path('user-profile/', UserDetailAPIView.as_view(), name='user-detail'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change_password"),

    path('send-otp/',SendOTPAPIView.as_view(),name='send-otp'),
    path('verify-otp/',VerifyOTPLoginAPIView.as_view(),name='verify-otp'),

    path('send-email-otp/',SendEmailOTPAPIView.as_view(),name='send-email-otp'),
    path('verify-email-otp/',VerifyEmailOTPAPIView.as_view(),name='verify-email-otp'),

    path("device-token/", RegisterDeviceTokenAPIView.as_view(), name="register_device_token"),
    ]