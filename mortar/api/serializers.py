import json
from collections import OrderedDict

from rest_framework import serializers

from mortar import models
from project.utils import serializers as utils


class DictionaryPartSerializer(serializers.ModelSerializer):
    type = utils.CheckedTypeField()

    class Meta:
        model = models.DictionaryPart
        fields = ['type', 'occurance', 'dictionary']


class NodePartSerializer(serializers.ModelSerializer):
    type = utils.CheckedTypeField()

    class Meta:
        model = models.NodePart
        fields = ['type', 'occurance', 'node']


class PartOfSpeechPartSerializer(serializers.ModelSerializer):
    type = utils.CheckedTypeField()

    class Meta:
        model = models.PartOfSpeechPart
        fields = ['type', 'occurance', 'part_of_speech']


class RegexPartSerializer(serializers.ModelSerializer):
    type = utils.CheckedTypeField()

    class Meta:
        model = models.RegexPart
        fields = ['type', 'occurance', 'regex']


class QueryPartSerializer(utils.PolymorphicModelSerializer):

    class Meta:
        model = models.QueryPart
        types = OrderedDict([
            (models.DictionaryPart, DictionaryPartSerializer),
            (models.NodePart, NodePartSerializer),
            (models.PartOfSpeechPart, PartOfSpeechPartSerializer),
            (models.RegexPart, RegexPartSerializer),
        ])
        fields = ['type']
        list_serializer_class = utils.PolymorphicListSerializer


class QuerySerializer(serializers.ModelSerializer):
    parts = QueryPartSerializer(many=True)

    class Meta:
        model = models.Query
        fields = ['id', 'category', 'parts']

    def create(self, validated_data):
        parts = validated_data.pop('parts')

        # Set query relationship
        query = super().create(validated_data)
        for data in parts:
            data['query'] = query

        # Create related query parts
        QueryPartSerializer(
            data=self.get_initial()['parts'],
            many=True
        ).create(parts)

        return query

    def update(self, instance, validated_data):
        parts = validated_data.pop('parts')

        # Set query relationship
        query = super().update(instance, validated_data)
        for data in parts:
            data['query'] = query

        # Delete existing query parts
        query.parts.all().delete()

        # Create related query parts
        QueryPartSerializer(
            data=self.get_initial()['parts'],
            many=True
        ).create(parts)

        return query

    def save(self, **kwargs):
        result = super().save(**kwargs)
        result.elastic_json = json.dumps(result.json())
        result.save()
        return result
