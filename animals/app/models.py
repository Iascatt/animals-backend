from django.db import models
from django.contrib.auth.models import User, UserManager, AbstractBaseUser, PermissionsMixin

class NewUserManager(UserManager):
    def create_user(self,email,password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')

        email = self.normalize_email(email) 
        user = self.model(email=email, **extra_fields) 
        user.set_password(password)
        user.save(using=self.db)

        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(("email адрес"), unique=True)
    password = models.CharField(verbose_name="Пароль")    
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь модератором?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")

    USERNAME_FIELD = 'email'

    objects =  NewUserManager()
 
class Animal(models.Model):
    # статус заявки
    class Status(models.TextChoices):
        ENTERED = "E", "черновик" # черновик
        ACTIVE = "A", "в работе" # передана модератору
        FINISHED = "F", "одобрена" # одобрена модератором
        CANCELLED = "C", "отклонена" # отклонена модератором
        DELETED = "D", "удалена" # удалена создателем
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.ENTERED, verbose_name="Статус заявки") # введён, в работе, завершён, отменён, удалён

    # Первичный ключ
    id = models.BigAutoField(auto_created = True, primary_key=True)
    
    # Охранный статус
    class ConservationStatus(models.IntegerChoices):
        EX = 0, "Исчезнувшие"
        EW = 1, "Исчезнувшие в дикой природе"
        CR = 2, "Находящиеся на грани исчезновения"
        EN = 3, "Исчезающие"
        VU = 4, "Уязвимые"
        NT = 5, "Находящиеся в состоянии, близком к угрожаемому"
        CD = 6, "Зависимые от усилий по сохранению"
        LC = 7, "Пониженная уязвимость"
        DD = 8, "Недостаток данных"
        NE = 9, "Неоценённые"
    conservation_status = models.IntegerField(choices=ConservationStatus.choices, default=ConservationStatus.NE, verbose_name="Охранный статус")

    # Род
    genus_lat = models.CharField(max_length=50, verbose_name="Род лат.", default="Homo") 
    genus_rus = models.CharField(max_length=50, verbose_name="Род рус. (опц.) ", null=True) 
    # Вид
    species_lat = models.CharField(max_length=50, verbose_name="Вид лат.", default="Sapiens") 
    species_rus = models.CharField(max_length=50, verbose_name="Вид рус. (опц.) ", null=True)
    
    # Даты начала и завершения заявки
    start_date = models.DateField(null=True, verbose_name="Дата создания")
    form_date = models.DateField(null=True, verbose_name="Дата формирования")
    fin_date = models.DateField(blank=True, null=True, verbose_name="Дата завершения")  

    creator = models.ForeignKey(CustomUser, models.CASCADE, related_name='creator', verbose_name="Создатель заявки", null=True)
    moderator = models.ForeignKey(CustomUser, models.CASCADE, blank=True, related_name='moderator', verbose_name="Модератор заявки", null=True)

    image = models.CharField(max_length=100, null=True) 

    def __str__(self):
        return f'{self.species_lat}'

class Habitat(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "A", "действует"
        DELETED = "D", "удален"
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.ACTIVE, verbose_name="Статус") # статус удален/действует

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="Название места обитания")
    desc = models.CharField(max_length=1000, verbose_name="Описание места обитания", blank=True, default='')

    # Происхождение: биогенное или антропогенное
    class Origin(models.TextChoices):
        BIO = "B", "биогенная"
        ART = "A", "антропогенная" #artifitial
    origin = models.CharField(max_length=1, choices=Origin.choices, default=Origin.BIO, verbose_name="Происхождение") 

    image = models.CharField(max_length=100, blank=True, null=True) 

    def __str__(self):
        return f'{self.name}'


class Inhabitant(models.Model):
    habitat = models.ForeignKey(Habitat, models.CASCADE)
    species = models.ForeignKey(Animal, models.CASCADE)

    class Meta:
        unique_together = ('habitat', 'species')


