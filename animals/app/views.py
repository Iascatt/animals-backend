from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from app.serializers import AnimalSerializer
from app.serializers import HabitatSerializer, UserSerializer
from app.models import Animal, Habitat, CustomUser, Inhabitant
from rest_framework import viewsets, status
from rest_framework.views import APIView
from datetime import date, datetime
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from .permissions import IsAdmin, IsManager
from rest_framework.response import Response
from rest_framework import status
import redis
import uuid
from django.shortcuts import render
from .minio import add_pic, del_pic
import logging
import json

logger = logging.getLogger(__name__)

session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


class UserViewSet(viewsets.ModelViewSet):
    """Класс, описывающий методы работы с пользователями
    Осуществляет связь с таблицей пользователей в базе данных
    """
    #permission_classes = [IsAuthenticatedOrReadOnly]

    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    model_class = CustomUser

    def create(self, request):
        """
        Функция регистрации новых пользователей
        Если пользователя c указанным в request email ещё нет, в БД будет добавлен новый пользователь.
        """
        logger.info('Received request data: %s', request.data)
        logger.info('Received request headers: %s', request.headers)

        if self.model_class.objects.filter(email=request.data['email']).exists():
            return Response({'status': 'Exist'}, status=400)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            print(serializer.data)
            self.model_class.objects.create_user(email=serializer.data['email'],
                                     password=serializer.data['password'],
                                     is_superuser=serializer.data['is_superuser'],
                                     is_staff=serializer.data['is_staff'])
            response = Response({'status': 'Success'})
            response.headers["Access-Control-Allow-Methods"] = "POST"
            response.headers["Access-Control-Allow-Headers"] = "Content-type"
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
            return response
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [AllowAny]
        elif self.action in ['list']:
            permission_classes = [IsAdmin | IsManager]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [AllowAny]

        return [permission() for permission in permission_classes]

def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes        
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator


# Auth
@permission_classes([AllowAny])
@csrf_exempt
@swagger_auto_schema(method='post', request_body=UserSerializer)
@api_view(['Post'])
def login_view(request):
    """
    Вход в аккаунт
    """
    email = request.data["email"] # допустим передали username и password
    password = request.data["password"]
    user = authenticate(request, email=email, password=password)
    if user is not None:
        random_key = uuid.uuid4()
        session_storage.set(random_key.hex, user.pk)

        response = JsonResponse({'pk': user.pk, 'is_moderator': user.is_staff, 'email': email,
                                  'session_id': random_key.hex})
        response.set_cookie("session_id", random_key.hex, samesite=settings.
                            SESSION_COOKIE_SAMESITE, secure=settings.SESSION_COOKIE_SECURE)
        # Allow `POST /greet`...
        response.headers["Access-Control-Allow-Methods"] = "POST"
        # ...with `Content-type` header in the request...
        response.headers["Access-Control-Allow-Headers"] = "Content-type"
        # ...from https://www.google.com origin.
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"

        return response
    else:
        return HttpResponse("{'status': 'error', 'error': 'login failed'}", status=400)

@permission_classes([IsAuthenticatedOrReadOnly])
@swagger_auto_schema(method='post', request_body=UserSerializer)
@api_view(['Post'])
def logout_view(request):
    """
    Выход из аккаунта
    """
    logout(request._request)
    response = Response({'status': 'Success'})
    ssid = ""
    if "session_id" in request.COOKIES.keys():
        ssid = request.COOKIES["session_id"]
    if not ssid:
        ssid = request.headers["Authorization"]
    if ssid:
        session_storage.delete(ssid)
        response.delete_cookie("session_id")
    return response

def get_user(request):
    cookies = request.COOKIES
    ssid = ""
    if "session_id" in cookies.keys():
        ssid = cookies["session_id"]

    if not ssid:
        ssid = request.headers["Authorization"]
 
    if ssid:
        logger.warning('session_id: '+ssid)
        user_pk = session_storage.get(ssid)
        if user_pk is not None:
            user = get_object_or_404(CustomUser, pk=user_pk)
            return user
                
def get_current_draft(request):
        user = get_user(request)
        drafts = Animal.objects.filter(creator=user).filter(status=
                    Animal.Status.ENTERED)
        logger.warning(drafts)
        if len(drafts) == 0:
            return 
        elif len(drafts) == 1:
            return drafts[0]
        else:
            raise Exception("Черновиков больше одного")

@api_view(['Get'])
@swagger_auto_schema()
def get_animals_habitats(request, pk, format=None):
    """
    Получить информацию о местах обитания животного
    """
    try:
        user = get_user(request)
        if not user:
            return HttpResponse('session_id is not assosiated with a user', status=401)
    except:
        return HttpResponse('Unauthorized', status=401)
    finally:
        animal = get_object_or_404(Animal, pk=pk)
        if (user.is_staff or user.is_superuser) or animal.creator == user:
            habitats = [i.habitat for i in Inhabitant.objects.filter(species=animal)]
            serializer = HabitatSerializer(habitats, many=True)
            return Response(serializer.data)
        else:
            return HttpResponse("Нет прав на получение информации о виде", status=403)

@api_view(['Get'])     
@swagger_auto_schema()
def get_draft_habitats(request, format=None):
    """
    Получить информацию о местах обитания в черновике
    """
    try:
        draft = get_current_draft(request)
        if not draft:
            return HttpResponse([], status=204)
        habitats = [i.habitat for i in Inhabitant.objects.filter(species=draft)]
        serializer = HabitatSerializer(habitats)
        return Response(serializer.data)

    except Exception as e:
        return HttpResponse(str(e), status=400)

@api_view(['Get'])     
@swagger_auto_schema()
def get_draft(request, format=None):
    """
    Получить информацию о полях в черновике
    """
    try:
        draft = get_current_draft(request)
        serializer = HabitatSerializer(draft)
        return Response(serializer.data)
    except Exception as e:
        return HttpResponse(str(e), status=403)
# Animals
class AnimalItem(APIView):
    @swagger_auto_schema()
    def get(self, request, pk, format=None):
        """
        Получить информацию о виде животного
        """
        try:
            user = get_user(request)
            if not user:
                return HttpResponse('session_id is not assosiated with a user', status=401)
        except:
            return HttpResponse('Unauthorized', status=401)
        finally:
            animal = get_object_or_404(Animal, pk=pk)
            if (user.is_staff or user.is_superuser) or animal.creator == user:
                serializer = AnimalSerializer(animal)
                return Response(serializer.data)
            else:
                return HttpResponse("Нет прав на получение информации о виде", status=403)

    
    @swagger_auto_schema(request_body=AnimalSerializer)
    def put(self, request, pk, format=None):
        """
        Обновить информацию о виде животного
        """
        try:
            user = get_user(request)
            if not user:
                return HttpResponse('session_id is not assosiated with a user', status=401)

            else:
                return HttpResponse('session_id is not assosiated with a user', status=401)
        except:
            return HttpResponse('Unauthorized', status=401)
        finally:
            animal = get_object_or_404(Animal, pk=pk)

            if (user.is_staff or user.is_superuser) or animal.creator == user: 
                serializer = AnimalSerializer(animal, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return HttpResponse("Нет прав на изменение информации о виде", status=403)


    @swagger_auto_schema()
    def delete(self, request, pk, format=None):    
        """
        Удалить информацию о виде животного
        """
        try:
            user = get_user(request)
            if not user:
                return HttpResponse('session_id is not assosiated with a user', status=401)
        except:
            return HttpResponse('Unauthorized', status=401)
        finally:
            animal = get_object_or_404(Animal, pk=pk)

            if animal.creator != user:
                return HttpResponse('Нельзя удалить не создателям заявки', status=403)
            animal.status = Animal.Status.DELETED
            animal.save()
            return Response("success")

@swagger_auto_schema(method='put')
@api_view(['Put'])
def form_animal_request(request, pk):
    """
    Сформировать заявку на регистрацию вида животного
    """
    try:
        user = get_user(request)
        if not user:
            return HttpResponse('session_id is not assosiated with a user', status=401)
    except:
        return HttpResponse('Unauthorized', status=401)
    finally:
        if animal.creator != user:
            return HttpResponse('Нельзя сформировать не создателям заявки', status=403)
        animal = get_object_or_404(Animal, pk=pk)
        animal.status = Animal.Status.ACTIVE
        animal.form_date = date.today()
        animal.save()
        return Response("success")

@swagger_auto_schema(method='put')
@api_view(['Put'])
def approve_animal_request(request, pk):
    """
    Одобрить заявку на регистрацию вида животного
    """
    try:
        user = get_user(request)
        if not user:
            return HttpResponse('session_id is not assosiated with a user', status=401)
    except:
        return HttpResponse('Unauthorized', status=401)
    finally:
        if not (user.is_staff or user.is_superuser):
            return HttpResponse('Нельзя одобрить не модератором', status=403)
        animal = get_object_or_404(Animal, pk=pk)
        animal.status = Animal.Status.FINISHED
        animal.fin_date = date.today()
        animal.save()
        return Response("success")

@swagger_auto_schema(method='put')
@api_view(['Put'])
def reject_animal_request(request, pk):
    """
    Отклонить заявку на регистрацию вида животного
    """
    try:
        user = get_user(request)
        if not user:
            return HttpResponse('session_id is not assosiated with a user', status=401)
    except:
        return HttpResponse('Unauthorized', status=401)
    finally:
        if not (user.is_staff or user.is_superuser):
            return HttpResponse('Нельзя отклонить не модератором', status=403)
        animal = get_object_or_404(Animal, pk=pk)

        animal.status = Animal.Status.CANCELLED
        animal.fin_date = date.today()

        animal.save()
        return Response("success", status=200)
    
class AnimalImage(APIView):
    @swagger_auto_schema()
    def post(self, request, pk, format=None):
        """
        Загрузить фото животного
        """
        try:
            user = get_user(request)
            if not user:
                return HttpResponse('session_id is not assosiated with a user', status=401)
            animal = get_object_or_404(Animal, pk=pk)
            if animal.creator == user.pk:
                return add_pic(animal, request.FILES['file'], "animals")
            return HttpResponse('Нельзя добавить фото не создателю', status=403)

        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=AnimalSerializer)
    def delete(self, request, pk, format=None):    
        """
        Удалить фото животного
        """
        try:
            user = get_user(request)
            if not user:
                return HttpResponse('session_id is not assosiated with a user', status=401)
            animal = get_object_or_404(Animal, pk=pk)
            if animal.creator == user.pk:
                return del_pic(animal, "animals")
            return HttpResponse('Нельзя удалить фото не создателю', status=403)

        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

class AnimalList(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'start-date',
                openapi.IN_QUERY,
                description="Дата создания заявки",
                type=openapi.FORMAT_DATE,
            ),
            openapi.Parameter(
                'fin-date',
                openapi.IN_QUERY,
                description="Дата окончания заявки",
                type=openapi.FORMAT_DATE,
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Статус заявки",
                type=openapi.TYPE_STRING,
            )
        ]
    )
    def get(self, request, format=None):
        """
        Вернуть список видов животных, созданных пользователем
        """
        animals = Animal.objects.exclude(status=
                    Animal.Status.DELETED)
        str_start = request.GET.get("start-date", '') 
        str_fin = request.GET.get("fin-date", '') 
        if str_start:
            start = datetime.strptime(str_start, "%Y-%m-%d").date()
            animals = animals.filter(form_date__gte=start)

        if str_fin:
            fin = datetime.strptime(str_fin, "%Y-%m-%d").date()
            animals = animals.filter(form_date__lte=fin)

        logger.warning("Dates are converted")
        search_status = request.GET.get("status", '')
        if search_status:
            animals = animals.filter(status=search_status)

        try:
            user = get_user(request)
            if not user:
                return HttpResponse('session_id is not assosiated with a user', status=401)

            if (user.is_staff or user.is_superuser): 
                animals = animals.exclude(status=Animal.Status.ENTERED)

            else:
                animals = animals.filter(creator__email=user)

            serializer = AnimalSerializer(animals, many=True)
            logger.error(serializer.data)
            return Response(serializer.data)
        except Exception as e:
            logger.error('Error: '+str(e))
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
           

# Habitats
class HabitatItem(APIView):
    @swagger_auto_schema()
    def get(self, request, pk, format=None):
        """
        Вернуть информацию о месте обитания
        """
        logger.warning('Request cookies:')
        cookies = request.COOKIES
        logger.warning(cookies)

        habitat = get_object_or_404(Habitat, pk=pk)
        serializer = HabitatSerializer(habitat)
        return Response(serializer.data)
        
    @swagger_auto_schema(request_body=HabitatSerializer)
    def post(self, request, format=None):    
        """
        Добавить новое место обитания
        """
        serializer = HabitatSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @swagger_auto_schema(request_body=HabitatSerializer)
    def put(self, request, pk, format=None):
        """
        Обновить информацию о месте обитания
        """
        animal = get_object_or_404(animal, pk=pk)
        serializer = AnimalSerializer(animal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=HabitatSerializer)
    def delete(self, request, pk, format=None):    
        """
        Удалить информацию о месте обитания
        """
        habitat = get_object_or_404(Habitat, pk=pk)
        habitat.status = Habitat.Status.DELETED
        habitat.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class HabitatList(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'name',
                openapi.IN_QUERY,
                description="Поиск по названию",
                type=openapi.TYPE_STRING,
            )
        ]
    )
    def get(self, request, format=None):
        """
        Вернуть отфильтрованные места обитания животных
        """
        logger.info('Received request cookies: %s', str(request.COOKIES))

        habitats = Habitat.objects.filter(status=
            Habitat.Status.ACTIVE).filter(name__startswith=request.GET.get('name', ''))
        serializer = HabitatSerializer(habitats, many=True)
        return Response(serializer.data)

class HabitatImage(APIView):
    @swagger_auto_schema()
    def post(self, request, pk, format=None):
        """
        Загрузить фото места обитания
        """
        try:
            habitat = get_object_or_404(Habitat, pk=pk)
            return add_pic(habitat, request.FILES['file'], "habitats")
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=AnimalSerializer)
    def delete(self, request, pk, format=None):    
        """
        Удалить фото места обитания
        """
        try:
            habitat = get_object_or_404(Habitat, pk=pk)
            return add_pic(habitat, "habitats")
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
#m-m
class AnimalToHabitat(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    @swagger_auto_schema()
    @csrf_exempt
    def put(self, request, pk, format=None):    
        """
        Добавить место обитания в заявку-черновик
        """
        user = get_user(request)
        draft = Animal.objects.get_or_create(creator=user, status=Animal.Status.ENTERED)[0]
        logger.warn(draft)
        try:
            link = Inhabitant.objects.get_or_create(habitat=get_object_or_404(Habitat, id=pk), species=draft)
            logger.warn(link)

            return Response("success")
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema()
    def delete(self, request, pk, format=None):    
        """
        Удалить место обитания из заявки-черновика
        """
        draft = get_current_draft(request)
        if draft:
            link = get_object_or_404(Inhabitant, habitat=pk, species=draft.id)
            link.delete()
            return Response("success")
        else:
            return Response("no draft", status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='put')
@api_view(['PUT'])
@permission_classes([AllowAny])
def set_conservation_status(request, pk, format=None):
    """
    Асинхронно установить охранный статус животного
    """
    try:
        # Преобразуем строку в объект Python JSON
        json_data = json.loads(request.body.decode('utf-8'))
        const_token = 'qwerty'

        if const_token != json_data['token']:
            return Response(data={'message': 'Ошибка, токен не соответствует'}, status=status.HTTP_403_FORBIDDEN)

       
        try:
            # Выводит конкретную заявку создателя
            animal = get_object_or_404(Animal, id=json_data['id'])
            animal.conservation_status = json_data['status']
          
            animal.save()
            return Response({'message': 'Status updated'})
        except ValueError:
            return Response({'message': 'Недопустимый формат преобразования'}, status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError as e:
        print(f'Error decoding JSON: {e}')
        return Response(data={'message': 'Ошибка декодирования JSON'}, status=status.HTTP_400_BAD_REQUEST)
    