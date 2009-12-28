from django import forms
from django.utils.translation import ugettext as _
from mygpo.api.models import Device, DEVICE_TYPES, SyncGroup
import re

class UserAccountForm(forms.Form):
    email = forms.EmailField(label=_('Your Email Address'))
    public = forms.BooleanField(required=False, label=_('May we use your subscriptions for the toplist and suggestions?'))

class DeviceForm(forms.Form):
    name = forms.CharField(max_length=100, label=_('Name of this device'))
    type = forms.ChoiceField(choices=DEVICE_TYPES, label=_('What kind of device is this?'))
    uid = forms.CharField(max_length=50, label=_('What UID is configured on the pysical device?'))


class SyncForm(forms.Form):
    targets = forms.CharField()

    def set_targets(self, sync_targets, label=''):
        targets = self.sync_target_choices(sync_targets)
        self.fields['targets'] = forms.ChoiceField(choices=targets, label=label)

    def sync_target_choices(self, targets):
        """
        returns a list of tuples that can be used as choices for a ChoiceField.
        the first item in each tuple is a letter identifying the type of the 
        sync-target - either d for a Device, or g for a SyncGroup. This letter
        is followed by the id of the target.
        The second item in each tuple is the string-representation of the #
        target.
        """
        return [('%s%s' % ('d' if isinstance(t, Device) else 'g', t.id), t) for t in targets]


    def get_target(self):
        if not self.is_valid():
            raise ValueError()

        target = self.cleaned_data['targets']
        m = re.match('^([dg])(\d+)$', target)
        if m == None:
            raise ValueError()

        if m.group(1) == 'd':
            return Device.objects.get(pk=m.group(2))
        else:
            return SyncGroup.objects.get(pk=m.group(2))
