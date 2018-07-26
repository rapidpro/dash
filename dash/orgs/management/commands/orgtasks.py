from __future__ import absolute_import, unicode_literals

import pytz

from django.core.management.base import BaseCommand, CommandError

from dash.orgs.models import Org, TaskState


class Command(BaseCommand):
    help = "Manages org specific tasks"

    RUNNING = "running"
    FAILING = "failing"
    ENABLE = "enable"
    DISABLE = "disable"
    ACTION_CHOICES = (RUNNING, FAILING, ENABLE, DISABLE)

    def add_arguments(self, parser):
        parser.add_argument("action", choices=self.ACTION_CHOICES, help="The action to perform")
        parser.add_argument("task", nargs="?", default=None, help="Key of a task")
        parser.add_argument("org_ids", metavar="ORG", type=int, nargs="*", help="The ids of the orgs")

    def handle(self, *args, **options):
        org_ids = options["org_ids"]
        action = options["action"]
        task_key = options["task"]

        orgs = Org.objects.order_by("pk")
        if org_ids:
            orgs = orgs.filter(pk__in=org_ids)
        else:
            orgs = orgs.filter(is_active=True)

        if action in (self.ENABLE, self.DISABLE) and not task_key:
            raise CommandError("Must provide a task key")

        if action == self.RUNNING:
            self.do_running(orgs, task_key)
        elif action == self.FAILING:
            self.do_failing(orgs, task_key)
        elif action == self.ENABLE:
            self.do_enable(orgs, task_key)
        elif action == self.DISABLE:
            self.do_disable(orgs, task_key)

    def do_running(self, orgs, task_key):
        tasks = TaskState.objects.filter(org__in=orgs, ended_on=None).exclude(started_on=None)
        tasks = tasks.select_related("org").order_by("org_id", "task_key")
        if task_key:
            tasks = tasks.filter(task_key=task_key)

        self.render_task_table(tasks)

    def do_failing(self, orgs, task_key):
        tasks = TaskState.objects.filter(org__in=orgs, is_failing=True)
        tasks = tasks.select_related("org").order_by("org_id", "task_key")
        if task_key:
            tasks = tasks.filter(task_key=task_key)

        self.render_task_table(tasks)

    def do_enable(self, orgs, task_key):
        num_updated = 0
        for org in orgs:
            task = TaskState.objects.filter(org=org, task_key=task_key).first()
            if task:
                task.is_disabled = False
                task.save(update_fields=("is_disabled",))
                num_updated += 1
            else:
                self.stdout.write("No such task for org #%d" % org.pk)

        self.stdout.write("Task %s enabled for %d orgs" % (task_key, num_updated))

    def do_disable(self, orgs, task_key):
        num_updated = 0
        for org in orgs:
            task = TaskState.objects.filter(org=org, task_key=task_key).first()
            if task:
                task.is_disabled = True
                task.save(update_fields=("is_disabled",))
                num_updated += 1
            else:
                self.stdout.write("No such task for org #%d" % org.pk)

        self.stdout.write("Task %s disabled for %d orgs" % (task_key, num_updated))

    def render_task_table(self, tasks):
        header = [cell("Org ID", 8), cell("Org Name", 20), cell("Key", 20), cell("Started On", 20)]

        self.stdout.write("".join(header))
        self.stdout.write("==================================================================")

        for task in tasks:
            row = [
                cell(task.org.pk, 8),
                cell(task.org.name, 20),
                cell(task.task_key, 20),
                cell(format_date(task.started_on), 20),
            ]
            self.stdout.write("".join(row))


def cell(val, width):
    return str(val).ljust(width)


def format_date(dt):
    return dt.astimezone(pytz.UTC).strftime("%b %d, %Y %H:%M") if dt else ""
