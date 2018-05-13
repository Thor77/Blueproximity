from threading import Thread

from blueproximity.log import logger


class GUIWorker(Thread):
    def __init__(self, input_queue, output_queue):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue

    def run(self):
        while True:
            # get next task from queue
            next_task = self.input_queue.get()
            logger.debug('Working on "%s"', next_task)
            # process task
            if next_task.action == 'quit':
                self.input_queue.task_done()
                break
            self.input_queue.task_done()
