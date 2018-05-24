from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from yurika.accounts import models as accounts
from yurika.mortar import models as mortar

from . import fields


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    username = serializers.ReadOnlyField()

    class Meta:
        model = accounts.Account
        fields = ['url', 'username']
        extra_kwargs = {
            'url': {
                'lookup_field': 'username',
            }
        }


class NestedCrawlerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = mortar.CrawlerTask
        fields = ['message_id', 'status', 'started_at', 'finished_at', 'revoked']


class CrawlerSerializer(serializers.HyperlinkedModelSerializer):
    start_urls = fields.TextListField(child=serializers.URLField(), help_text=_("URLs to start the crawl from."))
    allowed_domains = fields.TextListField(child=fields.DomainField(), required=False, help_text=_("Domain whitelist."))
    blocked_domains = fields.TextListField(child=fields.DomainField(), required=False, help_text=_("Domain blacklist."))
    config = serializers.JSONField(required=False, help_text=_("Scrapy crawler configuration options."))

    task = NestedCrawlerTaskSerializer(read_only=True)

    class Meta:
        model = mortar.Crawler
        fields = ['url', 'start_urls', 'allowed_domains', 'blocked_domains', 'config', 'task']
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }
