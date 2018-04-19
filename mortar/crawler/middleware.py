class ExceptionLoggingMiddleware(object):

    def process_spider_exception(self, response, exception, spider):
        spider.task.log_exception(exception)
