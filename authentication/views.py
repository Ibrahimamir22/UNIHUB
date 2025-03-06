from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from authentication.serializers import RegisterSerializer, LoginSerializer
from accounts.serializers import UserProfileSerializer
from accounts.models import User
from django.contrib.auth.models import User
from .models import OTPVerification
from django.conf import settings  # Import settings
from django.contrib.auth import get_user_model  # Get custom user model
import json

User = get_user_model()

# Helper function to create JWT token
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# Signup API (Register)
class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False  # Require email verification
            user.save()
            
            # Send Verification Email
            token = default_token_generator.make_token(user)
            verification_link = f"http://{get_current_site(request).domain}{reverse('email-verify', args=[token])}"
            send_mail(
                'Email Verification',
                f'Click the link to verify your email: {verification_link}',
                'no-reply@unihub.com',
                [user.email],
                fail_silently=False,
            )
            
            return Response({'message': 'User registered successfully. Check your email to verify your account.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Email Verification API
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.filter(is_active=False).first()
            if user and default_token_generator.check_token(user, token):
                user.is_active = True
                user.save()
                return Response({'message': 'Email verified successfully!'}, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

# Login API
class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(username=serializer.validated_data['email'], password=serializer.validated_data['password'])
            if user:
                tokens = get_tokens_for_user(user)
                return Response({'tokens': tokens}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# User Profile API
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Signup Page (HTML)
def signup_page(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        username = request.POST.get("username")
        password = request.POST.get("password")
        date_of_birth = request.POST.get("date_of_birth")
        academic_year = request.POST.get("academic_year")

        try:
            # Create and save the user
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password,
                date_of_birth=date_of_birth,
                academic_year=academic_year,
            )

            # Generate JWT tokens for automatic login
            refresh = RefreshToken.for_user(user)

            # Store the token in the session (for frontend authentication)
            request.session["access_token"] = str(refresh.access_token)
            request.session["refresh_token"] = str(refresh)

            login(request, user)  # Log in the user
            return redirect("dashboard")  # Redirect to a dashboard instead of an API page

        except Exception as e:
            # Handle any registration errors (like duplicate username or email)
            error_message = f"Error: {str(e)}"
            return render(request, "authentication/signup.html", {"error_message": error_message})

    return render(request, "authentication/signup.html")


# Login Page (HTML)
def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(username=username, password=password)
        
        if user:
            login(request, user)
            return redirect("dashboard")  # Redirect to dashboard after login
        else:
            # If authentication fails, show an error message
            messages.error(request, "Invalid credentials. Please try again.")
    
    return render(request, "authentication/login.html")

def send_otp(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            otp_instance, created = OTPVerification.objects.get_or_create(user=user)
            otp_code = otp_instance.generate_otp()

            # Send OTP Email
            send_mail(
                "Your UniHub OTP Code",
                f"Your OTP Code is: {otp_code}. This code is valid for 5 minutes.",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            request.session["email"] = email  # Store email for verification
            return redirect("verify-otp")
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")

    return render(request, "authentication/send_otp.html")

def verify_otp(request):
    if request.method == "POST":
        email = request.session.get("email")
        otp_entered = request.POST.get("otp")

        try:
            user = User.objects.get(email=email)
            otp_instance = OTPVerification.objects.get(user=user)

            if otp_instance.otp == otp_entered and otp_instance.is_valid():
                otp_instance.delete()  # OTP is used and removed
                
                # Log in the user
                login(request, user)

                # Redirect to the dashboard
                messages.success(request, "OTP verified successfully. Redirecting to the dashboard.")
                return redirect("dashboard")  

            else:
                messages.error(request, "Invalid or expired OTP.")

        except (User.DoesNotExist, OTPVerification.DoesNotExist):
            messages.error(request, "Something went wrong. Try again.")

    return render(request, "authentication/verify_otp.html")