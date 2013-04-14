import re
from htmlentitydefs import entitydefs

from django import template
from django.utils.safestring import mark_safe


register = template.Library()

@register.filter
def remove_html_tags(html):
    # If we would want more speed, we could make these global
    re_strip_tags = re.compile('<[^>]*>')
    re_unicode_entities = re.compile('&#(\d{2,4});')
    re_html_entities = re.compile('&(.{2,8});')
    re_newline_tags = re.compile('(<br[^>]*>|<[/]?ul[^>]*>|</li>)', re.I)
    re_listing_tags = re.compile('<li[^>]*>', re.I)

    result = html

    # Convert common HTML elements to their text equivalent
    result = re_newline_tags.sub('\n', result)
    result = re_listing_tags.sub('\n * ', result)
    result = re.sub('<[Pp]>', '\n\n', result)

    # Remove all HTML/XML tags from the string
    result = re_strip_tags.sub('', result)

    # Convert numeric XML entities to their unicode character
    result = re_unicode_entities.sub(lambda x: unichr(int(x.group(1))), result)

    # Convert named HTML entities to their unicode character
    result = re_html_entities.sub(lambda x: unicode(entitydefs.get(x.group(1),''), 'iso-8859-1'), result)

    # Convert more than two newlines to two newlines
    result = re.sub('([\r\n]{2})([\r\n])+', '\\1', result)

    return mark_safe(result.strip())
