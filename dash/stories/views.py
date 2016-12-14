from __future__ import unicode_literals

from dash.categories.fields import CategoryChoiceField
from dash.orgs.views import OrgPermsMixin, OrgObjPermsMixin
from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartCRUDL, SmartCreateView, SmartListView, SmartUpdateView
from .models import Category, Story, StoryImage


class StoryForm(forms.ModelForm):
    category = CategoryChoiceField(Category.objects.none())

    def __init__(self, *args, **kwargs):
        self.org = kwargs['org']
        del kwargs['org']
        super(StoryForm, self).__init__(*args, **kwargs)

        # We show all categories even inactive one in the dropdown
        qs = Category.objects.filter(org=self.org).order_by('name')
        self.fields['category'].queryset = qs

    class Meta:
        model = Story
        fields = ('is_active', 'title', 'featured', 'summary', 'content', 'written_by', 'audio_link',
                  'video_id', 'tags', 'category')


class StoryCRUDL(SmartCRUDL):
    model = Story
    actions = ('create', 'update', 'list', 'images')

    class Update(OrgObjPermsMixin, SmartUpdateView):
        form_class = StoryForm
        fields = (
            'is_active', 'title', 'featured', 'summary', 'content', 'written_by', 'audio_link',
            'video_id', 'tags', 'category')

        def pre_save(self, obj):
            obj = super(StoryCRUDL.Update, self).pre_save(obj)
            obj.audio_link = Story.format_audio_link(obj.audio_link)
            obj.tags = Story.space_tags(obj.tags)
            return obj

        def get_form_kwargs(self):
            kwargs = super(StoryCRUDL.Update, self).get_form_kwargs()
            kwargs['org'] = self.request.org
            return kwargs

    class List(OrgPermsMixin, SmartListView):
        fields = ('title', 'images', 'featured', 'created_on')
        search_fields = ('title__icontains',)
        link_fields = ('title', 'images',)
        default_order = ('-created_on',)

        def get_featured(self, obj):
            if obj.featured:
                return _("Yes")
            return _("No")

        def lookup_field_link(self, context, field, obj):
            if field == 'images':
                return reverse('stories.story_images', args=[obj.pk])
            else:
                return super(StoryCRUDL.List, self).lookup_field_link(context, field, obj)

        def get_images(self, obj):
            return obj.images.count()

        def get_queryset(self, **kwargs):
            queryset = super(StoryCRUDL.List, self).get_queryset(**kwargs)
            queryset = queryset.filter(org=self.derive_org())

            return queryset

    class Images(OrgObjPermsMixin, SmartUpdateView):
        success_url = '@stories.story_list'
        title = _("Story Images")

        def get_form(self):
            form = super(StoryCRUDL.Images, self).get_form()
            form.fields.clear()

            idx = 1

            # add existing images
            for image in self.object.images.all().order_by('pk'):
                image_field_name = 'image_%d' % idx
                image_field = forms.ImageField(
                    required=False, initial=image.image, label=_("Image %d") % idx,
                    help_text=_("Image to display on story page and in previews. (optional)"))

                self.form.fields[image_field_name] = image_field
                idx += 1

            while idx <= 3:
                self.form.fields['image_%d' % idx] = forms.ImageField(
                    required=False, label=_("Image %d") % idx,
                    help_text=_("Image to display on story page and in previews (optional)"))
                idx += 1

            return form

        def post_save(self, obj):
            obj = super(StoryCRUDL.Images, self).post_save(obj)

            # remove our existing images
            self.object.images.all().delete()

            # overwrite our new ones
            # TODO: this could probably be done more elegantly
            for idx in range(1, 4):
                image = self.form.cleaned_data.get('image_%d' % idx, None)

                if image:
                    StoryImage.objects.create(
                        story=self.object, image=image,
                        created_by=self.request.user, modified_by=self.request.user)

            return obj

    class Create(OrgPermsMixin, SmartCreateView):
        form_class = StoryForm
        success_url = 'id@stories.story_images'
        fields = (
            'title', 'featured', 'summary', 'content', 'written_by', 'audio_link', 'video_id', 'tags',
            'category')

        def pre_save(self, obj):
            obj = super(StoryCRUDL.Create, self).pre_save(obj)

            obj.org = self.request.org
            obj.audio_link = Story.format_audio_link(obj.audio_link)
            obj.tags = Story.space_tags(obj.tags)
            return obj

        def get_form_kwargs(self):
            kwargs = super(StoryCRUDL.Create, self).get_form_kwargs()
            kwargs['org'] = self.request.org
            return kwargs
