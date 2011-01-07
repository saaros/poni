import time
import logging
import threading
import Queue as queue


class Task(threading.Thread):
    def __init__(self, target=None):
        threading.Thread.__init__(self, target=target)
        self.log = logging.getLogger("task")
        self.daemon = True
        self.runner = None
        self.start_time = None
        self.stop_tie = None

    def can_start(self):
        return True

    def run(self):
        try:
            self.start_time = time.time()
            self.execute()
        finally:
            self.stop_time = time.time()
            self.runner.task_finished(self)


class Runner:
    def __init__(self):
        self.log = logging.getLogger("runner")
        self.not_started = set()
        self.started = set()
        self.stopped = set()
        self.finished_queue = queue.Queue()
        
    def add_task(self, task):
        task.runner = self
        self.not_started.add(task)

    def task_finished(self, task):
        self.finished_queue.put(task)

    def check(self):
        for task in list(self.not_started):
            if not task.can_start():
                continue

            self.started.add(task)
            self.not_started.remove(task)
            task.start()

    def wait_task_to_finish(self):
        task = self.finished_queue.get()
        self.log.debug("task %s finished, took %.2f seconds", task,
                       (task.stop_time - task.start_time))
        self.started.remove(task)
        self.stopped.add(task)

    def run_all(self):
        while self.not_started or self.started:
            self.check()
            self.wait_task_to_finish()
