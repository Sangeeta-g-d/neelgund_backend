from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserRegistrationSerializer, UserLoginSerializer, CustomUserSerializer
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .models import CustomUser, OTPVerification,EmailOTPVerification
from .utils import send_otp_via_smsalert
import random
import requests
from decouple import config
from django.utils import timezone
from django.core.mail import send_mail

class UserRegistrationAPIView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "status": status.HTTP_201_CREATED,
                    "message": "User registered successfully",
                    "user": {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email,
                        "phone_number": user.phone_number,
                        "approved": user.approved,
                    },
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": status.HTTP_400_BAD_REQUEST,
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            return Response({
                "status": status.HTTP_200_OK,
                "message": "Login successful",
                "user": data['user'],
                "access": data['access'],
                "refresh": data['refresh'],
            }, status=status.HTTP_200_OK)
        return Response({
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "Invalid credentials",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    

class UserDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = CustomUserSerializer(user)
        return Response({
            "status": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request):
        # for full update (or you can use patch for partial)
        user = request.user
        serializer = CustomUserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "status": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        serializer = CustomUserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "status": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)

        except TokenError:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        

class ChangePasswordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        # Validate all fields
        if not old_password or not new_password or not confirm_password:
            return Response(
                {"status": "error", "message": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check old password
        if not user.check_password(old_password):
            return Response(
                {"status": "error", "message": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check new and confirm password match
        if new_password != confirm_password:
            return Response(
                {"status": "error", "message": "New passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update password securely
        user.set_password(new_password)
        user.save()

        return Response(
            {"status": "success", "message": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )
    
class SendOTPAPIView(APIView):
    def post(self, request):
        phone = request.data.get("phone")
        if not phone:
            return Response(
                {"status": "error", "message": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp = random.randint(100000, 999999)
        print(f"📞 Received request to send OTP to: {phone}")
        print(f"✅ Generated OTP: {otp}")

        # 🧹 Clear old OTPs
        OTPVerification.objects.filter(phone_number=phone).delete()

        # 💾 Save new OTP
        OTPVerification.objects.create(
            phone_number=phone,
            otp=otp,
            created_at=timezone.now(),
            is_verified=False,
        )

        # ✅ Create the message with OTP
        message = (
                "Dear Customer, your OTP for verification is {otp}. Please use this OTP to complete your transaction. Do not share this with anyone. Thank you. NeelgundDevelopers[specialchar]Builders."
            )
        # ✅ SMS Alert payload - Using correct parameter names from documentation
        payload = {
            "apikey": config("SMS_ALERT_API_KEY"),
            "sender": config("SMS_ALERT_SENDER"),
            "mobileno": phone,
            "text": message
        }

        print(f"🌐 Sending POST request to SMS Alert with payload: {payload}")

        try:
            response = requests.post(
                "https://www.smsalert.co.in/api/push.json",
                data=payload,
                timeout=10
            )

            print(f"📡 SMS Alert HTTP Status: {response.status_code}")
            print(f"📨 SMS Alert Raw Response: {response.text}")

            # Check if response is valid JSON
            try:
                res_data = response.json()
            except ValueError:
                print("⚠️ Invalid JSON response from SMS Alert")
                return Response(
                    {"status": "error", "message": "Invalid response from SMS service."},
                    status=500
                )

            if res_data.get("status") == "success":
                print("✅ SMS sent successfully via SMS Alert.")
                return Response({"status": "success", "message": "OTP sent successfully."})
            else:
                error_desc = res_data.get("description", "SMS sending failed.")
                error_msg = res_data.get("message", error_desc)
                print(f"⚠️ SMS Alert Error: {error_msg}")
                
                return Response(
                    {"status": "error", "message": "Failed to send OTP. Please try again."},
                    status=500
                )

        except requests.exceptions.Timeout:
            print("⚠️ SMS Alert request timed out")
            return Response({"status": "error", "message": "SMS service timeout. Please try again."}, status=500)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ SMS Alert request failed: {e}")
            return Response({"status": "error", "message": "Failed to send OTP. Please try again."}, status=500)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
            return Response({"status": "error", "message": "Failed to send OTP. Please try again."}, status=500)
        
        
class VerifyOTPLoginAPIView(APIView):
    def post(self, request):
        phone_number = request.data.get("phone_number")
        otp = request.data.get("otp")

        if not phone_number or not otp:
            return Response({"status": "error", "message": "Phone number and OTP are required."}, status=400)

        otp_entry = OTPVerification.objects.filter(phone_number=phone_number, otp=otp, is_verified=False).last()

        if not otp_entry:
            return Response({"status": "error", "message": "Invalid OTP."}, status=400)

        if otp_entry.is_expired():
            return Response({"status": "error", "message": "OTP has expired."}, status=400)

        # Mark as verified
        otp_entry.is_verified = True
        otp_entry.save()

        user = CustomUser.objects.filter(phone_number=phone_number).first()
        if not user:
            return Response({"status": "error", "message": "User not found."}, status=404)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "status": "success",
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone_number": user.phone_number
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=200)
    
def generate_otp():
    return str(random.randint(100000, 999999))


class SendEmailOTPAPIView(APIView):
    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"status": 400, "message": "Email is required"}, status=400)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"status": 404, "message": "User not found"}, status=404)

        # generate OTP
        otp = str(random.randint(100000, 999999))

        # Save OTP
        EmailOTPVerification.objects.create(email=email, otp=otp)

        # Send email
        subject = "Your Login OTP"
        message = f"Your OTP for login is: {otp}. It is valid for 5 minutes."
        send_mail(subject, message, None, [email])

        return Response({
            "status": 200,
            "message": "OTP sent successfully"
        }, status=200)
    

# verify OTP
class VerifyEmailOTPAPIView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({
                "status": 400,
                "message": "Email and OTP are required"
            }, status=400)

        try:
            record = EmailOTPVerification.objects.filter(email=email, otp=otp).latest("created_at")
        except EmailOTPVerification.DoesNotExist:
            return Response({"status": 400, "message": "Invalid OTP"}, status=400)

        if record.is_verified:
            return Response({"status": 400, "message": "OTP already used"}, status=400)

        if record.is_expired():
            return Response({"status": 400, "message": "OTP expired"}, status=400)

        # Mark OTP verified
        record.is_verified = True
        record.save()

        # Get user
        user = CustomUser.objects.get(email=email)

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        user_data = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "approved": user.approved,
        }

        return Response({
            "status": 200,
            "message": "OTP verified, login successful",
            "user": user_data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=200)
