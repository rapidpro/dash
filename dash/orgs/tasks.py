import inspect
import json
import logging
import threading
from functools import wraps

from celery import shared_task, signature
from django_valkey import get_valkey_connection
from valkey.exceptions import LockError

from django.apps import apps
from django.utils import timezone

from .models import Invitation, TaskState

DEFAULT_LOCK_TIMEOUT = 60 * 60 * 2  # 2 hours

logger = logging.getLogger(__name__)

# the lock held by the org task currently running in this worker process, so that task code
# at any depth can renew it via renew_org_task_lock()
_current_org_task = threading.local()


def renew_org_task_lock():
    """
    Renews the lease of the lock held by the org task currently running in this worker.

    Tasks that checkpoint their progress can call this after each unit of work and pass a
    lock_timeout that only needs to outlive one unit rather than a worst-case full run - a
    hard-killed worker then frees the org after one short lease instead of hours.

    :return: whether the lock is still owned - False means the lease already expired and the
             same task may have been started concurrently, so the caller should stop cleanly
    """
    lock = getattr(_current_org_task, "lock", None)
    if not lock:
        return True

    try:
        lock.extend(lock.timeout, replace_ttl=True)
        return True
    except LockError:
        return False


@shared_task(track_started=True, name="send_invitation_email_task")
def send_invitation_email_task(invitation_id):
    invitation = Invitation.objects.filter(pk=invitation_id).first()
    if invitation:
        invitation.send_email()
    else:
        logger.warning("invitation %s no longer exists", invitation_id)


@shared_task
def trigger_org_task(task_name, queue="celery"):
    """
    Triggers the given org task to be run for all active orgs
    :param task_name: the full task name, e.g. 'myproj.myapp.tasks.do_stuff'
    :param queue: the name of the queue to send org sub-tasks to
    """
    active_orgs = apps.get_model("orgs", "Org").objects.filter(is_active=True)
    for org in active_orgs:
        sig = signature(task_name, args=[org.pk])
        sig.apply_async(queue=queue)

    logger.info("Requested task '%s' for %d active orgs" % (task_name, len(active_orgs)))


def org_task(task_key, lock_timeout=DEFAULT_LOCK_TIMEOUT):
    """
    Decorator to create an org task.

    The task holds a lock while it runs so that it can't run concurrently for the same org. The lock expires after
    lock_timeout seconds (2 hours by default) so that a dead worker can't hold it forever - which means a task that
    runs longer than its lock timeout may be started concurrently. Set lock_timeout to comfortably exceed the task's
    worst-case runtime, or have the task call renew_org_task_lock() after each unit of work so that lock_timeout
    only needs to exceed one unit.

    :param task_key: the task key used for state storage and locking, e.g. 'do-stuff'
    :param lock_timeout: the lock timeout in seconds
    """

    def _org_task(task_func):
        def _decorator(org_id):
            org = apps.get_model("orgs", "Org").objects.get(pk=org_id)
            maybe_run_for_org(org, task_func, task_key, lock_timeout)

        return shared_task(wraps(task_func)(_decorator))

    return _org_task


def maybe_run_for_org(org, task_func, task_key, lock_timeout=DEFAULT_LOCK_TIMEOUT):
    """
    Runs the given task function for the specified org provided it's not already running
    :param org: the org
    :param task_func: the task function
    :param task_key: the task key
    :param lock_timeout: the lock timeout in seconds (defaults to 1 hour so dead workers can't hold the lock forever)
    """
    r = get_valkey_connection()

    key = TaskState.get_lock_key(org, task_key)

    lock = r.lock(key, timeout=lock_timeout)

    if not lock.acquire(blocking=False):
        logger.warning("Skipping task %s for org #%d as it is still running" % (task_key, org.id))
        return

    _current_org_task.lock = lock

    try:
        state = org.get_task_state(task_key)
        if state.is_disabled:
            logger.info("Skipping task %s for org #%d as is marked disabled" % (task_key, org.id))
            return

        logger.info("Started task %s for org #%d..." % (task_key, org.id))

        prev_results = json.loads(state.last_results) if state.last_results else None
        prev_started_on = state.last_successfully_started_on
        this_started_on = timezone.now()

        state.started_on = this_started_on
        state.ended_on = None
        state.save(update_fields=("started_on", "ended_on"))

        num_task_args = len(inspect.getfullargspec(task_func).args)

        assert num_task_args >= 1, "task signature must be foo(org) or foo(org, since, until)"

        task_args = [org]

        try:
            if num_task_args >= 3:
                task_args += [prev_started_on, this_started_on]
            if num_task_args >= 4:
                task_args.append(prev_results)

            results = task_func(*task_args)

            state.ended_on = timezone.now()
            state.last_successfully_started_on = this_started_on
            state.last_results = json.dumps(results)
            state.is_failing = False
            state.save(update_fields=("ended_on", "last_successfully_started_on", "last_results", "is_failing"))

            logger.info("Finished task %s for org #%d with result: %s" % (task_key, org.id, json.dumps(results)))

        except Exception as e:
            # note we don't clear last_results here so that incremental tasks can resume from their last
            # successful results after a transient failure
            state.ended_on = timezone.now()
            state.is_failing = True
            state.save(update_fields=("ended_on", "is_failing"))

            logger.exception("Task %s for org #%d failed" % (task_key, org.id))
            raise e  # re-raise with original stack trace
    finally:
        _current_org_task.lock = None

        try:
            lock.release()
        except LockError:
            # the lock expired before we finished (i.e. the task ran longer than its lock timeout) - don't let that
            # fail an otherwise successful run or mask an in-flight exception
            logger.warning(
                "Unable to release lock for task %s for org #%d as it is no longer owned" % (task_key, org.id)
            )
