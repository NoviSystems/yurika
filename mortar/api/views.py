from rest_framework import mixins, viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from . import serializers
from .. import models


class PutOnlyUpdateModelMixin(object):
    update = mixins.UpdateModelMixin.update

    def perform_update(self, serializer):
        serializer.save()


class QueryViewSet(PutOnlyUpdateModelMixin,
                   mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = models.Query.objects.all()
    serializer_class = serializers.QuerySerializer

    def get_analysis(self):
        return models.Analysis.objects.get_or_create(id=0)[0]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs.get(lookup_url_kwarg, None)

        if lookup == 'current':
            # return get_object_or_404(models.Profile, owner__user=self.request.user)
            return models.Query.objects.get_or_create(
                analyses=self.get_analysis(),
                name='default')[0]
        return super(QueryViewSet, self).get_object()

    @list_route()
    def choices(self, request):
        """
        Returns all choices necessary for rendering the query part form.
        """
        dictionaries = list(models.Dictionary.objects.values_list('pk', 'name'))
        nodes = list(models.Node.objects.values_list('pk', 'name'))
        types = []

        if dictionaries:
            types.append(('dictionary part', 'Dictionary'))
        if nodes:
            types.append(('node part', 'MindMap term'))
        types += [
            ('part of speech part', 'Part of speech'),
        ]

        return Response({
            'occurance': list(models.QueryPart.OCCURANCE),
            'dictionary': dictionaries,
            'node': nodes,
            'part_of_speech': list(models.PartOfSpeechPart.PARTS_OF_SPEECH),
            'type': types
        })
