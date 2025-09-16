from django.db import models

class Upload(models.Model):
    file = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Upload(id={self.id}, file={self.file.name})'