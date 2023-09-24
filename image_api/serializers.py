from rest_framework import serializers
from .models import UserProfile,  Image, CustomTier


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class CustomTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomTier
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'
