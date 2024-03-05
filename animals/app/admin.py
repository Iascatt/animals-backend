from django.contrib import admin
from app import models

admin.site.register(models.Habitat)
admin.site.register(models.Animal)
admin.site.register(models.Inhabitant)