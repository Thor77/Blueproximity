from threading import Thread

from blueproximity.log import logger


class GUIWorker(Thread):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def run(self):
        while True:
            # get next task from queue
            next_task = self.queue.get()
            logger.debug('Working on "%s"', next_task)
            # process task
            if next_task.action == 'quit':
                break
            self.queue.task_done()
