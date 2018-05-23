from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().select_related('account')


class AccountManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(username=models.F('user__username'))


# For more information, read:
# https://docs.djangoproject.com/en/2.0/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project
class User(AbstractUser):
    objects = UserManager()

    class Meta:
        base_manager_name = 'objects'


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    objects = AccountManager()

    class Meta:
        base_manager_name = 'objects'


@receiver(post_save, sender=User)
def user_account(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)
