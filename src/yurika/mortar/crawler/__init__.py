from scrapy.crawler import CrawlerProcess
from scrapy.utils import log

from .spiders import WebCrawler

__all__ = ['crawl']


def crawl(task):
    # prevent scrapy from mucking with our logging configuration
    log.dictConfig = lambda _: _

    def twisted_exc(failure):
        # it's necessary to manually log the exception, as twisted loses the
        # real traceback object, but retains the frames to semi-rebuild it.
        task.errors.create(
            message=str(failure.value),
            traceback=failure.getTraceback(),
        )

    process = CrawlerProcess({**task.crawler.config, **{
        # enables state persistence, allowing crawler to be paused/unpaused
        'JOBDIR': task.crawler.state_dir,
    }}, install_root_handler=False)

    deferred = process.crawl(
        WebCrawler,
        start_urls=task.crawler.start_urls.splitlines(),
        task=task,

        # scrapy.spidermiddlewares.offsite.OffsiteMiddleware
        allowed_domains=task.crawler.allowed_domains.splitlines(),
        # mortar.middleware.BlockDomainMiddleware
        blocked_domains=task.crawler.blocked_domains.splitlines(),
        # mortar.middleware.LogExceptionMiddleware
        exception_logger=task.log_exception,
    )
    deferred.addErrback(twisted_exc)
    process.start()
