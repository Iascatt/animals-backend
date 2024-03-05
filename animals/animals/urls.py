"""
URL configuration for animals project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from app import views
from django.urls import include, path
from rest_framework import permissions, routers
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()
router.register(r'user', views.UserViewSet, basename='user')

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include(router.urls)),
    path(r'animals/', views.AnimalList.as_view(), name='animals-list'),
    path(r'animals/<int:pk>/', views.AnimalItem.as_view(), name='animal-item'),
    path(r'animals/<int:pk>/form/', views.form_animal_request, name='animal-form'),
    path(r'animals/<int:pk>/reject/', views.reject_animal_request, name='animal-reject'),
    path(r'animals/<int:pk>/approve/', views.approve_animal_request, name='animal-approve'),
    path(r'animals/<int:pk>/image/', views.AnimalImage.as_view(), name='animal-image'),
    path(r'animals/<int:pk>/set-status/', views.set_conservation_status, name='animal-image'),

    path(r'habitats/', views.HabitatList.as_view(), name='habitats-list'),
    path(r'habitats/<int:pk>/', views.HabitatItem.as_view(), name='habitat-item'),
    path(r'habitats/<int:pk>/image/', views.HabitatImage.as_view(), name='habitat-image'),

    path(r'inhabitant/<int:pk>/', views.AnimalToHabitat.as_view(), name='animal-habitat-links'),
    path(r'habitats/animals/<int:pk>/', views.get_animals_habitats, name='get-animals-habitats'),
    path(r'habitats/animals/draft/', views.get_draft_habitats, name='get-draft-habitats'),
    path(r'animals/draft/', views.get_draft, name='get-draft-habitats'),



    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('accounts/login/',  views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout') 
]