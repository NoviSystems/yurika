from multiprocessing import Process

import dramatiq

from mortar import crawler


@dramatiq.actor(max_retries=0)
def crawl(task_id):
    proc = Process(target=crawler.crawl, args=(task_id, ))
    proc.start()
    proc.join()
