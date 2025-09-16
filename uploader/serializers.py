# uploader/serializers.py
from rest_framework import serializers
from .models import Upload

class UploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = ['id', 'file', 'created_at']
        read_only_fields = ['id', 'created_at']
