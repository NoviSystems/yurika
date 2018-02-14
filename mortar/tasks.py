"""
BSD 3-Clause License

Copyright (c) 2018, North Carolina State University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. The names "North Carolina State University", "NCSU" and any trade‐name,
   personal name, trademark, trade device, service mark, symbol, image, icon,
   or any abbreviation, contraction or simulation thereof owned by North
   Carolina State University must not be used to endorse or promoteproducts
   derived from this software without prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


import logging

from celery import shared_task
from django.db.transaction import atomic
from scrapy.crawler import CrawlerProcess
from django.conf import settings
from django.utils import timezone

from twisted.python import log as twisted_log

import mortar.utils as utils
import mortar.models as models
import mortar.crawlers as crawler_classes

class CrawlerErrorLogHandler(logging.Handler):

    def emit(self, record):
        if record.levelno < logging.WARNING:
            return
        analysis = models.Analysis.objects.get(pk=0)
        analysis.crawler.log_error(self.format(record))

# Start Crawler
@shared_task(bind=True)
def run_crawler(self, crawler_pk):
    analysis = models.Analysis.objects.get(pk=0)
    crawler = models.Crawler.objects.get(pk=crawler_pk)

    crawler.clear_errors()

    if crawler.category != 'web':
        crawler.log_error('Only web crawlers are currently supported, not "{}"'.format(crawler.category))
        return

    name = crawler.name
    index = crawler.index.name
    seeds = [seed.urlseed.url for seed in crawler.seed_list.all()]

    crawler.process_id = self.request.id
    crawler.status = 0
    crawler.started_at = timezone.now()
    crawler.save()

    analysis.finished_at = None
    analysis.started_at = timezone.now()
    analysis.save()

    process = CrawlerProcess({
        'USER_AGENT': '',
        "SPIDER_MIDDLEWARES": {
            "mortar.crawlers.ErrorLogMiddleware": 1000,
            "mortar.crawlers.BlockUrlMiddleware": 900,
        },
        'ROBOTSTXT_OBEY': True,
    }, install_root_handler=False)

    # Scrapy messes with logging. Undo that.
    logging.config.dictConfig(settings.LOGGING)

    # Log errors in ExecuteError table
    handler = CrawlerErrorLogHandler()
    logging.root.addHandler(handler)

    # Log twisted errors in ExecuteError table
    def log_twisted_error(twisted_error_dict):
        if twisted_error_dict['isError']:
            analysis = models.Analysis.objects.get(pk=0)
            msg = '\n'.join(twisted_error_dict['message'])
            analysis.crawler.log_error(msg)
    twisted_log.addObserver(log_twisted_error)

    try:
        process.crawl(
            crawler_classes.WebCrawler,
            start_urls=seeds,
            name=name,
            index=index,
            index_mapping=crawler._meta.index_mapping
        )
        process.start()
    except Exception as e:
        crawler.log_error(e)
        raise

    crawler.finished_at = timezone.now()
    crawler.status = 1
    crawler.process_id = None
    crawler.save()

# Sync Dictionaries
@shared_task(bind=True)
def sync_dictionaries(self):
    utils.update_dictionaries()

# Reindex and Tokenize Documents
@shared_task(bind=True)
def preprocess(self, tree_pk):
    analysis = models.Analysis.objects.get(pk=0)
    analysis.finished_at = None
    analysis.started_at = timezone.now()
    tree = models.Tree.objects.get(pk=tree_pk)
    tree.clear_errors()
    tree.status = 0;
    tree.started_at = timezone.now()
    tree.process_id = self.request.id
    tree.save()

    try:
        utils.process(tree, {'names': [], 'regexs': []}, analysis.query)
    except Exception as e:
        tree.log_error(e)
        raise

    tree.status = 1;
    tree.finished_at = timezone.now()
    tree.process_id = None
    tree.save()

# Run Query
@shared_task(bind=True)
def run_query(self, query_pk):
    analysis = models.Analysis.objects.get(pk=0)
    query = models.Query.objects.get(pk=query_pk)
    query.clear_errors()

    query.started_at = timezone.now()
    query.process_id = self.request.id
    query.save()


    try:
        utils.annotate(analysis)
    except Exception as e:
        query.log_error(e)
        raise

    query.finished_at = timezone.now()
    query.process_id = None
    query.save()

    analysis.finished_at = timezone.now()
    analysis.save()
