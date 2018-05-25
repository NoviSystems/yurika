from rest_framework import viewsets

from yurika.accounts import models as accounts
from yurika.mortar import models as mortar

from . import serializers


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = accounts.Account.objects.all()
    serializer_class = serializers.AccountSerializer
    lookup_field = 'username'


class CrawlerViewSet(viewsets.ModelViewSet):
    queryset = mortar.Crawler.objects.all()
    serializer_class = serializers.CrawlerSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        return super().get_queryset() \
            .filter(crawleraccount__account=self.request.user.account)

    def perform_create(self, serializer):
        crawler = serializer.save()
        account = self.request.user.account

        # Account ownership relationship
        mortar.CrawlerAccount.objects.create(
            crawler=crawler,
            account=account,
        )
