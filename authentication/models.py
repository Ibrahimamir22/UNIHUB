import random
from django.conf import settings
from django.db import models
from django.utils.timezone import now

class OTPVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # ✅ Correct reference
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (now() - self.created_at).seconds < 300  # OTP expires in 5 minutes

    def generate_otp(self):
        self.otp = f"{random.randint(100000, 999999)}"
        self.created_at = now()
        self.save()
        return self.otp