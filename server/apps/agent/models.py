from django.db import models


# Create your models here.

class Configuration(models.Model):
    key = models.CharField(max_length=150)
    value = models.CharField(max_length=150)
