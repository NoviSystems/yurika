import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import models
from factory.django import DjangoModelFactory
from faker import Factory as FakerFactory


faker = FakerFactory.create()
User = get_user_model()

PASSWORD = 'multipass'
HASHED = make_password(PASSWORD)


def _unique_attr(model, attr_name, callback, max_attempts=3):
    def wrapper(value=None):
        query = model
        if isinstance(model, type) and issubclass(model, models.Model):
            query = model.objects.all()

        for i in range(max_attempts):
            attempt = callback(value)

            if not query.filter(**{attr_name: attempt}).exists():
                return attempt

    return wrapper


class UserFactory(DjangoModelFactory):
    username = factory.LazyAttribute(_unique_attr(User, 'username', lambda p: faker.username()))
    email = factory.LazyAttribute(_unique_attr(User, 'email', lambda p: faker.email()))
    first_name = factory.LazyAttribute(lambda p: faker.first_name())
    last_name = factory.LazyAttribute(lambda p: faker.last_name())

    class Meta:
        model = User

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if extracted is None:
            self.password = HASHED
        else:
            self.password = make_password(extracted)
