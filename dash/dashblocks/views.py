from smartmin.views import SmartCRUDL, SmartListView, SmartUpdateView, SmartCreateView

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from dash.orgs.views import OrgObjPermsMixin, OrgPermsMixin

from .models import DashBlockType, DashBlock, DashBlockImage


class DashBlockTypeCRUDL(SmartCRUDL):
    model = DashBlockType
    actions = ('create', 'update', 'list')

    class List(SmartListView):
        title = _("Content Types")
        fields = ('name', 'slug', 'description')
        link_fields = ('name',)


class DashBlockFormMixin(object):

    def get_type(self):
        if 'type' in self.request.REQUEST:
            return DashBlockType.objects.get(id=self.request.REQUEST.get('type'))
        return None

    def get_context_data(self, *args, **kwargs):
        context = super(DashBlockFormMixin, self).get_context_data(*args, **kwargs)
        context['type'] = self.get_type()
        return context

    def get_success_url(self):
        url = reverse('dashblocks.dashblock_list')
        return "%s?type=%d" % (url, self.object.dashblock_type.id)

    def derive_exclude(self):
        exclude = super(DashBlockFormMixin, self).derive_exclude()

        block_type = self.get_type()
        if block_type:
            if not self.request.user.has_perm(self.permission):
                exclude.append('dashblock_type')

            if not block_type.has_summary:
                exclude.append('summary')

            if not block_type.has_video:
                exclude.append('video_id')

            if not block_type.has_title:
                exclude.append('title')

            if not block_type.has_tags:
                exclude.append('tags')

            if not block_type.has_image:
                exclude.append('image')

            if not block_type.has_link:
                exclude.append('link')

            if not block_type.has_color:
                exclude.append('color')

        # if this user does not have global permissins, remove org as a field
        if not self.request.user.has_perm(self.permission):
            exclude.append('org')

        return exclude

    def pre_save(self, obj):
        obj = super(DashBlockFormMixin, self).pre_save(obj)

        block_type = self.get_type()
        if block_type:
            obj.dashblock_type = block_type

        # if the user doesn't have global permissions, set the org appropriately
        if not self.request.user.has_perm(self.permission):
            obj.org = self.request.org

        obj.space_tags()
        return obj


class DashBlockCRUDL(SmartCRUDL):
    model = DashBlock
    permissions = True
    actions = ('create', 'update', 'list')

    class List(OrgPermsMixin, SmartListView):
        fields = ('title', 'priority', 'dashblock_type', 'tags')
        link_fields = ('title',)
        default_order = '-modified_on'
        search_fields = (
            'title__icontains', 'content__icontains', 'summary__icontains')

        def derive_fields(self):
            fields = super(DashBlockCRUDL.List, self).derive_fields()
            block_type = self.get_type()
            if block_type:
                if not block_type.has_tags:
                    fields = type(fields)(x for x in fields if x != 'tags')
            return fields

        def get_title(self, obj):
            block_type = self.get_type()
            if block_type:
                if not block_type.has_title:
                    return unicode(obj)
            return obj.title

        def derive_title(self):
            type = self.get_type()
            if not type:
                return _("Content Blocks")
            else:
                return _("%s Blocks") % type.name

        def get_type(self):
            if 'type' in self.request.REQUEST and not self.request.REQUEST.get('type') == '0':
                return DashBlockType.objects.get(id=self.request.REQUEST.get('type'))
            elif 'slug' in self.request.REQUEST:
                return DashBlockType.objects.get(slug=self.request.REQUEST.get('slug'))
            return None

        def get_queryset(self, **kwargs):
            queryset = super(DashBlockCRUDL.List, self).get_queryset(**kwargs)

            dashblock_type = self.get_type()
            if dashblock_type:
                queryset = queryset.filter(dashblock_type=dashblock_type)

            queryset = queryset.filter(dashblock_type__is_active=True)
            queryset = queryset.filter(org=self.request.org)

            return queryset

        def get_context_data(self, *args, **kwargs):
            context = super(DashBlockCRUDL.List, self).get_context_data(*args, **kwargs)
            context['types'] = DashBlockType.objects.filter(is_active=True)
            context['filtered_type'] = self.get_type()
            return context

    class Update(OrgObjPermsMixin, DashBlockFormMixin, SmartUpdateView):
        fields = (
            'title', 'summary', 'content', 'image', 'color', 'link',
            'video_id', 'tags', 'dashblock_type', 'priority', 'is_active')

        def get_type(self):
            return self.object.dashblock_type

        def derive_title(self):
            return _("Edit %s") % self.get_type().name

    class Create(OrgPermsMixin, DashBlockFormMixin, SmartCreateView):
        grant_permissions = ('dashblocks.change_dashblock',)

        def derive_initial(self, *args, **kwargs):
            initial = super(DashBlockCRUDL.Create, self).derive_initial(*args, **kwargs)
            dashblock_type = self.get_type()
            other_blocks = DashBlock.objects.filter(
                is_active=True,
                org=self.derive_org(),
                dashblock_type=dashblock_type,
            )
            other_blocks = other_blocks.order_by('-priority')
            if not other_blocks:
                initial['priority'] = 0
            else:
                initial['priority'] = other_blocks[0].priority + 1

            return initial

        def derive_title(self):
            block_type = self.get_type()
            if block_type:
                return _("Create %s") % block_type.name
            else:
                return _("Create Content Block")


class DashBlockImageCRUDL(SmartCRUDL):
    model = DashBlockImage
    actions = ('create', 'update', 'list')

    class Update(SmartUpdateView):
        exclude = (
            'dashblock', 'modified_by', 'modified_on', 'created_on',
            'created_by', 'width', 'height')
        title = "Edit Image"
        success_message = "Image edited successfully."

        def get_success_url(self):
            return reverse('dashblocks.dashblock_update', args=[self.object.dashblock.id])

    class Create(SmartCreateView):
        exclude = (
            'dashblock', 'is_active', 'modified_by', 'modified_on',
            'created_on', 'created_by', 'width', 'height')
        title = "Add Image"
        success_message = "Image added successfully."

        def derive_initial(self, *args, **kwargs):
            initial = super(DashBlockImageCRUDL.Create, self).derive_initial(*args, **kwargs)
            dashblock = DashBlock.objects.get(pk=self.request.REQUEST.get('dashblock'))
            images = dashblock.sorted_images()
            if not images:
                initial['priority'] = 0
            else:
                initial['priority'] = images[0].priority + 1
            return initial

        def get_success_url(self):
            return reverse('dashblocks.dashblock_update', args=[self.object.dashblock.id])

        def pre_save(self, obj):
            obj = super(DashBlockImageCRUDL.Create, self).pre_save(obj)
            obj.dashblock = DashBlock.objects.get(pk=self.request.REQUEST.get('dashblock'))
            return obj
