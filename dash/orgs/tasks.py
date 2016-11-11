from __future__ import unicode_literals

import inspect
import json
import logging
import six
import sys
import time

from celery import shared_task, signature
from django_redis import get_redis_connection
from django.apps import apps
from django.utils import timezone
from functools import wraps
from .models import Invitation, Org


ORG_TASK_LOCK_KEY = 'org-task-lock:%s:%s'

logger = logging.getLogger(__name__)


@shared_task(track_started=True, name='send_invitation_email_task')
def send_invitation_email_task(invitation_id):
    invitation = Invitation.objects.get(pk=invitation_id)
    invitation.send_email()


@shared_task(name='orgs.build_boundaries')
def build_boundaries():
    start = time.time()
    r = get_redis_connection()

    key = 'build_boundaries'
    if not r.get(key):
        with r.lock(key, timeout=900):
            active_orgs = Org.objects.filter(is_active=True)
            for org in active_orgs:
                logger.debug("=" * 40)
                org.build_boundaries()
    logger.debug("Task: build_boundaries took %ss" % (time.time() - start))


@shared_task(track_started=True, name='rebuild_org_boundaries')
def rebuild_org_boundaries(org_id):
    try:
        # get our org
        from .models import Org
        org = Org.objects.get(pk=org_id)
        org.build_boundaries()
    except Exception as e:
        logger.exception("Error building org boundaries refresh: %s" % str(e))


@shared_task
def trigger_org_task(task_name, queue='celery'):
    """
    Triggers the given org task to be run for all active orgs
    :param task_name: the full task name, e.g. 'myproj.myapp.tasks.do_stuff'
    :param queue: the name of the queue to send org sub-tasks to
    """
    active_orgs = apps.get_model('orgs', 'Org').objects.filter(is_active=True)
    for org in active_orgs:
        sig = signature(task_name, args=[org.pk])
        sig.apply_async(queue=queue)

    logger.info("Requested task '%s' for %d active orgs" % (task_name, len(active_orgs)))


def org_task(task_key, lock_timeout=None):
    """
    Decorator to create an org task.
    :param task_key: the task key used for state storage and locking, e.g. 'do-stuff'
    :param lock_timeout: the lock timeout in seconds
    """
    def _org_task(task_func):
        def _decorator(org_id):
            org = apps.get_model('orgs', 'Org').objects.get(pk=org_id)
            maybe_run_for_org(org, task_func, task_key, lock_timeout)

        return shared_task(wraps(task_func)(_decorator))
    return _org_task


def maybe_run_for_org(org, task_func, task_key, lock_timeout):
    """
    Runs the given task function for the specified org provided it's not already running
    :param org: the org
    :param task_func: the task function
    :param task_key: the task key
    :param lock_timeout: the lock timeout in seconds
    """
    r = get_redis_connection()
    key = ORG_TASK_LOCK_KEY % (org.pk, task_key)
    if r.get(key):
        logger.warn("Skipping for org #%d as it is still running" % org.pk)
    else:
        with r.lock(key, timeout=lock_timeout):
            state = org.get_task_state(task_key)
            if state.is_disabled:
                logger.info("Skipping for org #%d as task is marked disabled" % org.pk)
                return

            logger.info("Started for org #%d..." % org.pk)

            prev_started_on = state.last_successfully_started_on
            this_started_on = timezone.now()

            state.started_on = this_started_on
            state.ended_on = None
            state.save(update_fields=('started_on', 'ended_on'))

            num_task_args = len(inspect.getargspec(task_func).args)

            try:
                if num_task_args == 3:
                    results = task_func(org, prev_started_on, this_started_on)
                elif num_task_args == 1:
                    results = task_func(org)
                else:
                    raise ValueError("Task signature must be foo(org) or foo(org, since, until)")  # pragma: no cover

                state.ended_on = timezone.now()
                state.last_successfully_started_on = this_started_on
                state.last_results = json.dumps(results)
                state.is_failing = False
                state.save(update_fields=('ended_on', 'last_successfully_started_on', 'last_results', 'is_failing'))

                logger.info("Succeeded for org #%d with result: %s" % (org.pk, json.dumps(results)))

            except Exception:
                state.ended_on = timezone.now()
                state.last_results = None
                state.is_failing = True
                state.save(update_fields=('ended_on', 'last_results', 'is_failing'))

                six.reraise(*sys.exc_info())  # re-raise with original stack trace
