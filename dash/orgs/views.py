from __future__ import unicode_literals

import re

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from smartmin.views import (
    SmartCRUDL, SmartCreateView, SmartReadView, SmartUpdateView,
    SmartListView, SmartFormView, SmartTemplateView)
from .forms import CreateOrgLoginForm, OrgForm
from .models import Org, OrgBackground, Invitation, TaskState


class OrgPermsMixin(object):
    """
    Get the organisation and the user within the inheriting view so that it be
    come easy to decide whether this user has a certain permission for that
    particular organization to perform the view's actions
    """
    def get_user(self):
        return self.request.user

    def derive_org(self):
        return self.request.org

    def pre_process(self, request, *args, **kwargs):
        user = self.get_user()
        org = self.derive_org()

        if user.is_superuser:
            return None

        if not org:
            return HttpResponseRedirect(reverse('orgs.org_choose'))

        return None

    def has_org_perm(self, permission):
        (app_label, codename) = permission.split(".")

        if self.get_user().is_superuser:
            return True

        if self.get_user().is_anonymous():
            return False

        if self.org:
            org_group = self.get_user().get_org_group()
            if org_group:
                if org_group.permissions.filter(content_type__app_label=app_label,
                                                codename=codename).exists():
                    return True

        return False

    def has_permission(self, request, *args, **kwargs):
        """
        Figures out if the current user has permissions for this view.
        """
        self.kwargs = kwargs
        self.args = args
        self.request = request
        self.org = self.derive_org()

        if self.get_user().is_superuser:
            return True

        if self.get_user().has_perm(self.permission):
            return True

        return self.has_org_perm(self.permission)


class OrgObjPermsMixin(OrgPermsMixin):

    def get_object_org(self):
        return self.get_object().org

    def has_org_perm(self, codename):
        has_org_perm = super(OrgObjPermsMixin, self).has_org_perm(codename)

        if has_org_perm:
            user = self.get_user()

            if user.is_anonymous():
                return True
            return user.get_org() == self.get_object_org()

        return False

    def has_permission(self, request, *args, **kwargs):
        has_perm = super(OrgObjPermsMixin, self).has_permission(request, *args, **kwargs)

        if has_perm:
            user = self.get_user()

            # user has global permission
            if user.has_perm(self.permission):
                return True

            return user.get_org() == self.get_object_org()

        return False


class InferOrgMixin(object):
    @classmethod
    def derive_url_pattern(cls, path, action):
        return r'^%s/%s/$' % (path, action)

    def get_object(self, *args, **kwargs):
        return self.request.org


class OrgCRUDL(SmartCRUDL):
    actions = ('create', 'list', 'update', 'choose', 'home', 'edit',
               'manage_accounts', 'create_login', 'join', 'chooser')
    model = Org

    class Chooser(SmartTemplateView):
        permission = False
        template_name = getattr(settings, 'SITE_CHOOSER_TEMPLATE', 'orgs/org_chooser.html')

        def get_context_data(self, **kwargs):
            all_orgs = Org.objects.filter(is_active=True).order_by('name')

            # populate a 'host' attribute on each org so we can link off to them
            for org in all_orgs:
                org.host = org.build_host_link()

            return dict(orgs=all_orgs)

    class Create(SmartCreateView):
        form_class = OrgForm
        fields = ('name', 'language', 'timezone', 'subdomain',
                  'domain', 'api_token', 'logo', 'administrators')

    class Update(SmartUpdateView):
        form_class = OrgForm
        fields = ('is_active', 'name', 'language', 'timezone', 'subdomain',
                  'domain', 'api_token', 'logo', 'administrators')

    class List(SmartListView):
        fields = ('name', 'timezone', 'created_on', 'modified_on')

    class Choose(SmartFormView):
        class ChooseForm(forms.Form):
            def __init__(self, *args, **kwargs):
                self.user = kwargs['user']
                del kwargs['user']

                super(OrgCRUDL.Choose.ChooseForm, self).__init__(*args, **kwargs)
                self.fields['organization'].queryset = self.user.get_user_orgs()

            organization = forms.ModelChoiceField(queryset=Org.objects.filter(id__lte=-1),
                                                  empty_label=None)

        form_class = ChooseForm
        fields = ('organization',)
        title = _("Select your Organization")

        def pre_process(self, request, *args, **kwargs):
            if self.request.user.is_authenticated():
                user_orgs = self.request.user.get_user_orgs()

                if self.request.user.is_superuser:
                    return HttpResponseRedirect(reverse('orgs.org_list'))

                elif not user_orgs:
                    messages.info(
                        request, _("Your account is not associated to an "
                                   "organization. Please Contact the adminstrator."))
                    return HttpResponseRedirect(reverse('users.user_login'))

                elif user_orgs.count() == 1:
                    org = user_orgs[0]
                    if org and self.request.org:
                        if self.request.org == org:
                            self.request.session['org_id'] = org.pk
                            return HttpResponseRedirect(self.get_success_url())

            return None

        def get_context_data(self, **kwargs):
            context = super(OrgCRUDL.Choose, self).get_context_data(**kwargs)

            context['orgs'] = self.request.user.get_user_orgs()
            return context

        def has_permission(self, request, *args, **kwargs):
            return self.request.user.is_authenticated()

        def get_form_kwargs(self):
            kwargs = super(OrgCRUDL.Choose, self).get_form_kwargs()
            kwargs['user'] = self.request.user
            return kwargs

        def form_valid(self, form):
            org = form.cleaned_data['organization']

            if org in self.request.user.get_user_orgs():
                self.request.session['org_id'] = org.pk
                self.request.org = org

            return HttpResponseRedirect(org.build_host_link() + self.get_success_url())

        def get_success_url(self):
            return getattr(settings, 'SITE_USER_HOME', reverse('orgs.org_home'))

    class Home(InferOrgMixin, OrgPermsMixin, SmartReadView):
        title = _("Your Organization")
        fields = ('name', 'subdomain', 'api_token')

        def get_api_token(self, obj):
            if obj and obj.api_token:
                return "*" * 32 + obj.api_token[32:]
            else:
                return _("Not Set")

    class Edit(InferOrgMixin, OrgPermsMixin, SmartUpdateView):
        title = _("Your Organization")
        success_url = '@orgs.org_home'
        fields = ('name',)

        def derive_fields(self):
            fields = super(OrgCRUDL.Edit, self).derive_fields()
            is_super = self.request.user.is_superuser

            config_fields = getattr(settings, 'ORG_CONFIG_FIELDS', [])
            for config_field in config_fields:
                if is_super or not config_field.get('superuser_only', False):
                    fields.append(config_field['name'])

            return fields

        def get_form(self):
            form = super(OrgCRUDL.Edit, self).get_form()
            is_super = self.request.user.is_superuser

            # add all our configured org fields as well
            config_fields = getattr(settings, 'ORG_CONFIG_FIELDS', [])
            for config_field in config_fields:
                if is_super or not config_field.get('superuser_only', False):
                    field_name = config_field['name']
                    if field_name == 'featured_state':
                        choices = [(feature['properties']['id'], feature['properties']['name'])
                                   for feature in self.org.get_country_geojson()['features']]
                        form.fields[field_name] = forms.ChoiceField(choices=choices,
                                                                    **config_field['field'])
                    elif field_name.startswith('has_') or field_name.startswith('is_'):
                        form.fields[field_name] = forms.BooleanField(**config_field['field'])
                    else:
                        form.fields[field_name] = forms.CharField(**config_field['field'])

            return form

        def pre_save(self, obj):
            obj = super(OrgCRUDL.Edit, self).pre_save(obj)
            cleaned = self.form.cleaned_data
            is_super = self.request.user.is_superuser

            config_fields = getattr(settings, 'ORG_CONFIG_FIELDS', [])
            for config_field in config_fields:
                if is_super or not config_field.get('superuser_only', False):
                    name = config_field['name']
                    obj.set_config(name, cleaned.get(name, None))

            return obj

        def derive_initial(self):
            initial = super(OrgCRUDL.Edit, self).derive_initial()
            is_super = self.request.user.is_superuser

            config_fields = getattr(settings, 'ORG_CONFIG_FIELDS', [])
            for config_field in config_fields:
                if is_super or not config_field.get('superuser_only', False):
                    name = config_field['name']
                    initial[name] = self.object.get_config(name)

            return initial

        def get_object(self, *args, **kwargs):
            return self.request.org

    class ManageAccounts(InferOrgMixin, OrgPermsMixin, SmartUpdateView):

        class InviteForm(forms.ModelForm):
            emails = forms.CharField(label=_("Invite people to your organization"), required=False)
            user_group = forms.ChoiceField(choices=(('A', _("Administrators")),
                                                    ('E', _("Editors"))),
                                           required=True, initial='E', label=_("User group"))

            def clean_emails(self):
                emails = self.cleaned_data['emails'].lower().strip()
                if emails:
                    email_list = emails.split(',')
                    for email in email_list:
                        try:
                            validate_email(email)
                        except ValidationError:
                            raise forms.ValidationError(
                                _("One of the emails you entered is invalid."))
                return emails

            class Meta:
                model = Invitation
                fields = ('emails', 'user_group')

        form_class = InviteForm
        success_url = '@orgs.org_home'
        success_message = ""
        GROUP_LEVELS = ('administrators', 'editors')

        def derive_title(self):
            return _("Manage %(name)s Accounts") % {'name': self.get_object().name}

        def add_check_fields(self, form, objects, org_id, field_dict):
            for obj in objects:
                fields = []
                for grp_level in self.GROUP_LEVELS:
                    check_field = forms.BooleanField(required=False)
                    field_name = "%s_%d" % (grp_level, obj.id)

                    form.fields[field_name] = check_field
                    fields.append(field_name)

                field_dict[obj] = fields

        def derive_initial(self):
            self.org_users = self.get_object().get_org_users()

            initial = dict()
            for grp_level in self.GROUP_LEVELS:
                if grp_level == 'administrators':
                    assigned_users = self.get_object().get_org_admins()
                if grp_level == 'editors':
                    assigned_users = self.get_object().get_org_editors()

                for obj in assigned_users:
                    key = "%s_%d" % (grp_level, obj.id)
                    initial[key] = True

            return initial

        def get_form(self):
            form = super(OrgCRUDL.ManageAccounts, self).get_form()
            self.group_fields = dict()
            self.add_check_fields(form, self.org_users, self.get_object().pk, self.group_fields)

            return form

        def post_save(self, obj):
            obj = super(OrgCRUDL.ManageAccounts, self).post_save(obj)

            cleaned_data = self.form.cleaned_data
            user = self.request.user
            org = self.get_object()

            user_group = cleaned_data['user_group']

            emails = cleaned_data['emails'].lower().strip()
            email_list = emails.split(',')

            if emails:
                for email in email_list:

                    # if they already have an invite, update it
                    invites = Invitation.objects.filter(email=email, org=org).order_by('-pk')
                    invitation = invites.first()

                    if invitation:

                        # remove any old invites
                        invites.exclude(pk=invitation.pk).delete()

                        invitation.user_group = user_group
                        invitation.is_active = True
                        invitation.save()
                    else:
                        invitation = Invitation.objects.create(email=email,
                                                               org=org,
                                                               user_group=user_group,
                                                               created_by=user,
                                                               modified_by=user)

                    invitation.send_invitation()

            # remove all the org users
            for user in self.get_object().get_org_admins():
                if user != self.request.user:
                    self.get_object().administrators.remove(user)
                else:
                    self.get_object().administrators.add(user)
            for user in self.get_object().get_org_editors():
                self.get_object().editors.remove(user)

            # now update the org accounts
            for field in self.form.fields:
                if self.form.cleaned_data[field]:
                    matcher = re.match("(\w+)_(\d+)", field)
                    if matcher:
                        user_type = matcher.group(1)
                        user_id = matcher.group(2)
                        user = User.objects.get(pk=user_id)
                        if user_type == 'administrators':
                            self.get_object().administrators.add(user)
                        if user_type == 'editors':
                            self.get_object().editors.add(user)

            # update our org users after we've removed them
            self.org_users = self.get_object().get_org_users()

            return obj

        def get_context_data(self, **kwargs):
            context = super(OrgCRUDL.ManageAccounts, self).get_context_data(**kwargs)
            org = self.get_object()
            context['org'] = org
            context['org_users'] = self.org_users
            context['group_fields'] = self.group_fields
            context['invites'] = Invitation.objects.filter(org=org, is_active=True)

            return context

    class CreateLogin(SmartFormView):
        title = ""
        form_class = CreateOrgLoginForm
        success_message = ''
        submit_button_name = _("Create")
        permission = False

        def pre_process(self, request, *args, **kwargs):
            secret = self.kwargs.get('secret')
            org = self.get_object()
            if not org:
                messages.info(
                    request, _("Your invitation link is invalid. Please "
                               "contact your organization administrator."))
                return HttpResponseRedirect('/')

            elif request.org != org:
                redirect_path = reverse('orgs.org_create_login', args=[secret])
                redirect_path = org.build_host_link() + redirect_path
                return HttpResponseRedirect(redirect_path)

            return None

        def form_valid(self, form):
            user = Org.create_user(self.form.cleaned_data['email'],
                                   self.form.cleaned_data['password'])
            user.first_name = self.form.cleaned_data['first_name']
            user.last_name = self.form.cleaned_data['last_name']
            user.save()

            invitation = self.get_invitation()

            # log the user in
            user = authenticate(username=user.username,
                                password=self.form.cleaned_data['password'])
            login(self.request, user)

            obj = self.get_object()
            if invitation.user_group == 'A':
                obj.administrators.add(user)
            elif invitation.user_group == 'E':
                obj.editors.add(user)

            # make the invitation inactive
            invitation.is_active = False
            invitation.save()

            return super(OrgCRUDL.CreateLogin, self).form_valid(form)

        @classmethod
        def derive_url_pattern(cls, path, action):
            return r'^%s/%s/(?P<secret>\w+)/$' % (path, action)

        def get_invitation(self, **kwargs):
            invitation = None
            secret = self.kwargs.get('secret')
            invitations = Invitation.objects.filter(secret=secret, is_active=True)
            if invitations:
                invitation = invitations[0]
            return invitation

        def get_object(self, **kwargs):
            invitation = self.get_invitation()
            if invitation:
                return invitation.org

        def derive_title(self):
            org = self.get_object()
            return _("Join %(name)s") % {'name': org.name}

        def get_context_data(self, **kwargs):
            context = super(OrgCRUDL.CreateLogin, self).get_context_data(**kwargs)

            context['secret'] = self.kwargs.get('secret')
            context['org'] = self.get_object()

            return context

        def get_success_url(self):
            return getattr(settings, 'SITE_USER_HOME', reverse('orgs.org_home'))

    class Join(SmartUpdateView):
        class JoinForm(forms.ModelForm):

            class Meta:
                model = Org
                fields = ()

        success_message = ''
        form_class = JoinForm
        submit_button_name = _("Join")
        permission = False

        def pre_process(self, request, *args, **kwargs):
            secret = self.kwargs.get('secret')

            org = self.get_object()
            if not org:
                messages.info(
                    request, _("Your invitation link has expired. Please "
                               "contact your organization administrator."))
                return HttpResponseRedirect('/')
            elif request.org != org:

                redirect_path = org.build_host_link() + reverse('orgs.org_join', args=[secret])
                return HttpResponseRedirect(redirect_path)

            if not request.user.is_authenticated():
                return HttpResponseRedirect(reverse('orgs.org_create_login', args=[secret]))
            return None

        def derive_title(self):
            org = self.get_object()
            return _("Join %(name)s") % {'name': org.name}

        def save(self, org):
            org = self.get_object()
            invitation = self.get_invitation()
            if org:
                if invitation.user_group == 'A':
                    org.administrators.add(self.request.user)
                elif invitation.user_group == 'E':
                    org.editors.add(self.request.user)

                # make the invitation inactive
                invitation.is_active = False
                invitation.save()

                # set the active org on this user
                self.request.user.set_org(org)
                self.request.session['org_id'] = org.pk

        @classmethod
        def derive_url_pattern(cls, path, action):
            return r'^%s/%s/(?P<secret>\w+)/$' % (path, action)

        def get_invitation(self, **kwargs):
            invitation = None
            secret = self.kwargs.get('secret')
            invitations = Invitation.objects.filter(secret=secret, is_active=True)
            if invitations:
                invitation = invitations[0]
            return invitation

        def get_object(self, **kwargs):
            invitation = self.get_invitation()
            if invitation:
                return invitation.org

        def get_context_data(self, **kwargs):
            context = super(OrgCRUDL.Join, self).get_context_data(**kwargs)

            context['org'] = self.get_object()
            return context

        def get_success_url(self):
            return getattr(settings, 'SITE_USER_HOME', reverse('orgs.org_home'))


class OrgBackgroundCRUDL(SmartCRUDL):
    model = OrgBackground
    actions = ('create', 'update', 'list')

    class Update(OrgObjPermsMixin, SmartUpdateView):
        fields = ('is_active', 'name', 'background_type', 'image')

    class List(OrgPermsMixin, SmartListView):
        fields = ("name", "background_type")

        def derive_fields(self):
            if self.request.user.is_superuser:
                return ('org', 'name', 'background_type')
            return ('name', 'background_type')

        def get_background_type(self, obj):
            return obj.get_background_type_display()

        def get_queryset(self, **kwargs):
            queryset = super(OrgBackgroundCRUDL.List, self).get_queryset(**kwargs)

            if not self.get_user().is_superuser:
                queryset = queryset.filter(org=self.derive_org())

            return queryset

    class Create(OrgPermsMixin, SmartCreateView):

        def derive_fields(self):
            if self.request.user.is_superuser:
                return ('org', 'name', 'background_type', 'image')
            return ('name', 'background_type', 'image')

        def pre_save(self, obj):
            obj = super(OrgBackgroundCRUDL.Create, self).pre_save(obj)

            if not self.get_user().is_superuser:
                org = self.derive_org()
                if org:
                    obj.org = org

            return obj


class TaskCRUDL(SmartCRUDL):
    actions = ('list',)
    model = TaskState
    model_name = _("Task")
    path = 'task'

    class List(SmartListView):
        title = _("Tasks")
        link_fields = ('org',)
        default_order = ('org__name', 'task_key')

        def lookup_field_link(self, context, field, obj):
            if field == 'org':
                return reverse('orgs.org_update', args=[obj.org_id])
            else:
                return super(TaskCRUDL.List, self).lookup_field_link(context, field, obj)
