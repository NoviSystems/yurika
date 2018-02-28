"""
Serializers for polymorphic types.
"""
from django.db import models
from rest_framework import serializers


def verbose_name(model):
    opts = model._meta

    # if model._deferred:
    #     return verbose_name(opts.proxy_for_model)
    return opts.verbose_name.lower()


class CheckedTypeField(serializers.Field):

    def __init__(self, **kwargs):
        # The `source` needs to be set to '*', since there is no corresponding
        # 'type' field on the model. The type is instead derived via the model's
        # meta class. This is relevant to serialization of model instances.
        kwargs['source'] = '*'
        super(CheckedTypeField, self).__init__(**kwargs)

    def run_validation(self, data):
        self.validate_type(data)
        return super(CheckedTypeField, self).run_validation(data)

    def validate_type(self, data):
        expected = verbose_name(self.parent.Meta.model)
        if data != expected:
            raise serializers.ValidationError(
                'Invalid type. Expected \'{}\', but got \'{}\'.'.format(
                    expected, data,
                )
            )

    def to_internal_value(self, data):
        return {}

    def to_representation(self, value):
        return verbose_name(value)


class CheckedPolymorphicTypeField(CheckedTypeField):

    def validate_type(self, data):
        expected = [verbose_name(model) for model in self.parent.Meta.types]
        if data not in expected:
            raise serializers.ValidationError(
                'Invalid type. Expected one of {}, but got \'{}\'.'.format(
                    expected, data,
                )
            )


class PolymorphicModelSerializer(serializers.ModelSerializer):
    """
    Uses either the incoming `data` or the outgoing `instance` to determine
    which concrete serializer class to use.

    Note that it is assumed that the incoming `data` type is found under the
    `type` key, and corresponds to the model's type, not a model field.

    Example:

        class MediaSerializer(PolymorphicModelSerializer):
            class Meta:
                model = models.Media
                types = OrderedDict([
                    (models.Article, ArticleSerializer),
                    (models.Book, BookSerializer),
                    (models.Photo, PhotoSerializer),
                ])
                fields = ['type']
                list_serializer_class = PolymorphicListSerializer

    """
    type = CheckedPolymorphicTypeField()

    def __new__(cls, instance=None, data=serializers.empty, **kwargs):
        assert hasattr(cls.Meta, 'types')

        # get the serializer subclass for provided data
        if isinstance(data, dict):
            model = {
                verbose_name(model): model for model in cls.Meta.types
            }.get(data.get('type'))

            if model is not None:
                cls = cls.Meta.types[model]
                return cls(instance=instance, data=data, **kwargs)

        # get the serializer subclass for an instance
        if hasattr(instance, '_meta'):
            model = instance._meta.model

            if model in cls.Meta.types:
                cls = cls.Meta.types[model]
                return cls(instance=instance, data=data, **kwargs)

        return super(PolymorphicModelSerializer, cls) \
            .__new__(cls, instance=instance, data=data, **kwargs)


class PolymorphicListSerializer(serializers.ListSerializer):
    """
    Enables polymorphic behavior for list serializers and nested to-many
    relationships.
    """

    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        self.child_class = type(kwargs['child'])
        self.child_kwargs = kwargs.copy()
        self.child_kwargs.pop('child')

        super().__init__(instance=instance, data=data, **kwargs)

    def get_child(self, instance=None, data=serializers.empty):
        return self.child_class(instance=instance, data=data,
                                **self.child_kwargs)

    # TODO:
    # The following methods should be able to removed (sans the subclasses
    # change in to_representation) if the corresponding PR is merged. See:
    # https://github.com/encode/django-rest-framework/pull/5847

    def get_initial(self):
        if hasattr(self, 'initial_data'):
            return [
                self.get_child(data=item).get_initial()
                for item in self.initial_data
            ]
        return []

    def to_internal_value(self, data):
        """
        List of dicts of native values <- List of dicts of primitive datatypes.
        """
        if not isinstance(data, list):
            message = self.error_messages['not_a_list'].format(
                input_type=type(data).__name__
            )
            raise serializers.ValidationError({
                serializers.api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='not_a_list')

        if not self.allow_empty and len(data) == 0:
            if self.parent and self.partial:
                raise serializers.SkipField()

            message = self.error_messages['empty']
            raise serializers.ValidationError({
                serializers.api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='empty')

        ret = []
        errors = []

        for item in data:
            try:
                validated = self.get_child(data=item).run_validation(item)
            except serializers.ValidationError as exc:
                errors.append(exc.detail)
            else:
                ret.append(validated)
                errors.append({})

        if any(errors):
            raise serializers.ValidationError(errors)

        return ret

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        # Dealing with nested relationships, data can be a Manager,
        # so, first get a queryset from the Manager if needed
        if isinstance(data, models.Manager):
            data = data.all()

        if isinstance(data, models.QuerySet):
            data = data.select_subclasses()

        return [
            self.get_child(instance=item).to_representation(item)
            for item in data
        ]

    def create(self, validated_data):
        return [
            self.get_child(data=data).create(attrs)
            for data, attrs in zip(self.get_initial(), validated_data)
        ]
