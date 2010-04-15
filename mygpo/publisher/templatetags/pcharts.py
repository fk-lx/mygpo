from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
import hashlib
import math

register = template.Library()

@register.filter
def bar_chart(parts):

    maxv = max([ int(x['y']) for x in parts ])
    bar_width = 15
    bar_space = 15
    group_space = 20

    parts = [
        'cht=bvg',     # Vertical bar chart with grouped bars.
        'chs=%dx100' % ((bar_width + bar_space + group_space / 2) * len(parts)),
        'chl=%s' % '|'.join([x['x'] for x in parts]),
        'chd=t:%s' % ','.join([ repr(int(x['y'])) for x in parts ]),
        'chxt=x,y', # visible axes
        'chbh=%d,%d,%d' % (bar_width, bar_space, group_space),
        'chds=0,%d' % maxv, # avis scaling from 0 to max
        'chxr=1,0,%d' % maxv, # labeling for axis 1 (y) from 0 to max
        ]

    s = '<img src="http://chart.apis.google.com/chart?%s"' % '&'.join(parts)

    return mark_safe(s)
