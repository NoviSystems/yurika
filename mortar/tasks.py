from multiprocessing import Process

import dramatiq
from dramatiq.middleware import Shutdown, TimeLimitExceeded

from mortar import crawler, models


DAY = 86_400_000


# We can't actually use an infinite time limit, as the redis broker will assume
# the lack of a (n)ack is due to a network error. Instead, cap at 7 days, which
# is shy of the 7.5 day requeue period.
@dramatiq.actor(max_retries=0, time_limit=(7 * DAY), notify_shutdown=True)
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
