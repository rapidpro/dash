from django import forms


class CategoryChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        label = "%s - %s" % (obj.org, obj.name)
        if not obj.is_active:
            label += " (Inactive)"

        return label

