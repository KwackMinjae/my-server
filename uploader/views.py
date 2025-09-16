from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})

from rest_framework import viewsets
from .models import Upload
from .serializers import UploadSerializer

class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all().order_by('-id')
    serializer_class = UploadSerializer