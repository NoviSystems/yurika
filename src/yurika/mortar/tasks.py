from multiprocessing import get_context

import dramatiq
from dramatiq.middleware import Shutdown, TimeLimitExceeded

from . import models
from .crawler import process


spawn = get_context('spawn')


@dramatiq.actor(max_retries=0, notify_shutdown=True)
def crawl(task_id):
    # NOTE: wrapping the crawler in a task enables pipelining and offloading to
    #       a remote worker. Otherwise this would be unnecessary indirection.
    task = models.CrawlerTask.objects.get(pk=task_id)

    proc = spawn.Process(target=process.crawl, args=(task_id, ))
    proc.start()

    try:
        while proc.exitcode is None:
            task.refresh_from_db()

            if task.revoked:
                proc.terminate()
                proc.join()
                raise task.Abort

            proc.join(.5)

    except (Shutdown, TimeLimitExceeded) as exc:
        # Shutdown/TimeLimitExceeded are interrupts, not errors.
        task.log_error('Dramatiq process terminated.')
        raise task.Abort from exc

    except Exception as exc:
        task.log_exception(exc)
        raise

    finally:
        proc.terminate()
        proc.join()

        if proc.exitcode != 0:
            task.log_error(f'Crawler returned a non-zero exit code: {proc.exitcode}')
