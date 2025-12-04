from rest_framework import serializers
from .models import CustomUser,DeviceToken
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=True, allow_blank=False)
    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "email", "phone_number", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive")

        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'approved': user.approved,
            }
        }
    

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # include any fields you want the user to see / update
        fields = [
            'id',
            'email',
            'full_name',
            'phone_number',
            'approved',
            'adhar_card',
            'pan_card',
            'profile_image',
            'dob',
            'date_joined',
        ]
        read_only_fields = ['email', 'date_joined', 'approved']  # for example



class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["token", "device_type"]