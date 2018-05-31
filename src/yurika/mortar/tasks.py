from multiprocessing import Process

import dramatiq
from dramatiq.middleware import Shutdown, TimeLimitExceeded

from . import crawler, models


@dramatiq.actor(max_retries=0, notify_shutdown=True)
def crawl(task_id):
    # NOTE: wrapping the crawler in a task enables pipelining,
    #       otherwise this would be unnecessary indirection.
    task = models.CrawlerTask.objects.get(pk=task_id)

    proc = Process(target=crawler.crawl, args=(task, ))
    proc.start()

    try:
        while proc.exitcode is None:
            task.refresh_from_db()

            if task.revoked:
                proc.terminate()
                proc.join()
                raise task.Abort

            proc.join(.5)

    except (Shutdown, TimeLimitExceeded):
        proc.terminate()
        proc.join()

        raise
