from django.contrib.auth.models import AbstractUser
from django.db import models


# For more information, read:
# https://docs.djangoproject.com/en/2.0/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project
class User(AbstractUser):
    pass


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
