from app.models import Animal, Habitat, Inhabitant, CustomUser
from rest_framework import serializers
from collections import OrderedDict
class HabitatSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display')
    origin = serializers.CharField(source='get_origin_display')

    class Meta:
        # Модель, которую мы сериализуем
        model = Habitat
        # Поля, которые мы сериализуем
        fields = ["status", "id", "name", "desc", "origin", "image"]

class AnimalSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display',
                                   default=Animal.Status.ENTERED,  required=False)
    conservation_status = serializers.CharField(source='get_conservation_status_display',
                                                default=Animal.ConservationStatus.NE, required=False)
    id = serializers.IntegerField(required=False)
    creator = serializers.EmailField(source='creator.email', required=False)
    moderator = serializers.EmailField(source='moderator.email', required=False)

    class Meta:
        # Модель, которую мы сериализуем
        model = Animal
        # Поля, которые мы сериализуем
        fields = ["status", "id", "conservation_status", "genus_lat", "genus_rus", "species_lat", "species_rus",
                   "start_date", "form_date", "fin_date", "creator", "moderator", "image"]
        
          



class InhabitantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        # Модель, которую мы сериализуем
        model = Inhabitant
        # Поля, которые мы сериализуем
        fields = ["id", "habitat", "species"]



class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']