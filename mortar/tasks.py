from multiprocessing import Process

import dramatiq

from mortar import crawler, models


@dramatiq.actor(max_retries=0)
def crawl(task_id):
    task = models.CrawlerTask.objects.get(pk=task_id)

    proc = Process(target=crawler.crawl, args=(task, ))
    proc.start()
    proc.join()
