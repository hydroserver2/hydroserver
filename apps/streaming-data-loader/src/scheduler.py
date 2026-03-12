import traceback
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import utc
from datetime import datetime
from PySide6.QtCore import QObject


logger = logging.getLogger("scheduler")


class DataLoaderScheduler(QObject):

    def __init__(self, hs_api, data_loader=None):
        super().__init__()

        self.data_loader = data_loader

        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.add_job(
            lambda: self.check_tasks(),
            id="sdl-scheduler",
            trigger="interval",
            seconds=60,
            next_run_time=datetime.utcnow()
        )

        logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

        self.hs_api = hs_api
        self.timeout = 60

        self.scheduler.start()
        self.job = None

    def terminate(self):
        self.scheduler.shutdown(wait=True)

    def pause(self):
        if self.scheduler.running:
            self.scheduler.pause()

    def resume(self):
        self.scheduler.resume()

    def check_tasks(self):
        """
        The check_tasks function is used to check the status of all tasks associated with a given SDL
        instance. It will iterate through each task and call the update_task function for each one.

        :param self
        :return: The tasks
        """

        try:
            success, message = self.check_data_loader()
            if success is False:
                logging.error(message)
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(e)

        try:
            tasks = self.hs_api.tasks.list(orchestration_system=self.data_loader, fetch_all=True)
            for task in tasks.items:
                self.update_task(task)
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(e)

    def check_data_loader(self):
        """
        The check_data_loader function checks to see if the data loader name provided by the user exists. If it does
        not, it creates a new data loader with that name. If it does exist, then it sets self.data_loader to that
        existing data loader.

        :param self
        :return: A tuple containing a boolean and a string
        """

        try:
            data_loader = self.hs_api.orchestrationsystems.get(uid=self.data_loader.uid)
        except (Exception,) as e:
            return False, str(e)

        self.data_loader = data_loader

        return True, ''

    def update_task(self, task):
        """
        The update_task function is called when a user updates the schedule of an existing task. It checks to see
        if the task has a scheduled job, and if it does not, it adds one. If there is already
        a scheduled job for that task, then update_task calls update_schedule to change the schedule.

        :param self
        :param task: Identify the task that is being updated
        :return: bool
        """

        scheduled_jobs = {
            scheduled_job.id: scheduled_job
            for scheduled_job in self.scheduler.get_jobs()
            if scheduled_job.id != 'hydroloader-scheduler'
        }

        if str(task.uid) not in scheduled_jobs.keys():
            self.add_schedule(task)
        else:
            self.update_schedule(task, scheduled_jobs[str(task.uid)])

        return True

    def add_schedule(self, task):
        """
        The add_schedule function is used to add a schedule for the task. The function takes in a
        TaskGetResponse object as an argument, which contains all the information needed to create and run
        scheduled data loading tasks.

        :param self
        :param task: TaskGetResponse: Pass the task object to the function
        :return: None
        """

        schedule_range = {}
        if task.start_time:
            schedule_range['start_time'] = task.start_time

        if task.interval and task.interval_period:
            self.scheduler.add_job(
                lambda: self.load_data(task=task),
                IntervalTrigger(
                    start_date=task.start_time,
                    **{task.interval_period: task.interval}
                ),
                id=str(task.uid),
                **schedule_range
            )
        elif task.crontab:
            self.scheduler.add_job(
                lambda: self.load_data(task=task),
                CronTrigger.from_crontab(task.crontab, timezone='UTC'),
                id=str(task.uid),
                **schedule_range
            )

    def update_schedule(self, task, scheduled_job):
        """
        The update_schedule function is called when a task is updated.
        It checks if the crontab or interval has changed, and if so, removes the old job from the scheduler and adds a
        new one. If neither have changed, it does nothing.

        :param self
        :param task: TaskGetResponse: Get the task information
        :param scheduled_job: Get the job id and trigger
        :return: None
        """

        if (
            (isinstance(scheduled_job.trigger, CronTrigger) and not task.crontab) or
            (isinstance(scheduled_job.trigger, IntervalTrigger) and not task.interval)
        ):
            self.scheduler.remove_job(scheduled_job.id)

        if isinstance(scheduled_job.trigger, CronTrigger):
            task_trigger = CronTrigger.from_crontab(task.crontab, timezone='UTC')
            task_trigger_value = str(task_trigger)
            scheduled_job_trigger_value = str(scheduled_job.trigger)
        elif isinstance(scheduled_job.trigger, IntervalTrigger):
            task_trigger = IntervalTrigger(
                start_date=task.start_time,
                **{task.interval_period: task.interval}
            )
            task_trigger_value = task_trigger.interval_length
            scheduled_job_trigger_value = scheduled_job.trigger.interval_length
        else:
            task_trigger_value = None
            scheduled_job_trigger_value = None

        if task_trigger_value != scheduled_job_trigger_value:
            self.scheduler.remove_job(scheduled_job.id)

        if not self.scheduler.get_job(scheduled_job.id) and \
                (task.crontab or task.interval):
            self.add_schedule(task)

    @staticmethod
    def load_data(task):
        """
        The load_data function is used to load data as defined in a task into
        HydroServer. The function takes in a single argument, which is an object
        representing the task that you want to load. This function will then
        call on the service's 'load_data' method, passing in the ID of the task as
        an argument.

        :param task: Identify the task that you want to load
        :return: None
        """

        task.refresh()

        if task.paused is True:
            logging.info(f'Task {task.name} is paused: Skipping')
            return

        logging.info(f'Loading data for task {task.name}')

        try:
            task.run_local()
            logging.info(f'Finished loading data for task {task.name}')

        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(e)
