#
# This file is part of my.gpodder.org.
#
# my.gpodder.org is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# my.gpodder.org is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with my.gpodder.org. If not, see <http://www.gnu.org/licenses/>.
#

import os.path
import StringIO
from datetime import datetime
from glob import glob
import errno

import Image
import ImageDraw

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import last_modified


LOGO_DIR = os.path.join(settings.BASE_DIR, '..', 'htdocs', 'media', 'logo')


def _last_modified(request, size, prefix, filename):

    target = os.path.join(LOGO_DIR, size, prefix, filename)

    try:
        return datetime.fromtimestamp(os.path.getmtime(target))

    except OSError:
        return None


class CoverArt(View):

    @method_decorator(last_modified(_last_modified))
    def get(self, request, size, prefix, filename):

        size = int(size)

        target = self.get_thumbnail(size, prefix, filename)
        original = self.get_original(prefix, filename)

        if os.path.exists(target):
            return self.send_file(target)

        if not os.path.exists(original):
            raise Http404('Cover Art not available' + original)

        target_dir = self.get_dir(target)

        try:
            im = Image.open(original)
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGB')
        except IOError:
            raise Http404('Cannot open cover file')

        try:
            im.thumbnail((size, size), Image.ANTIALIAS)
            resized = im
        except IOError as ex:
            print ex
            # raised when trying to read an interlaced PNG;
            # we use the original instead
            return self.send_file(original)

        # If it's a RGBA image, composite it onto a white background for JPEG
        if resized.mode == 'RGBA':
            background = Image.new('RGB', resized.size)
            draw = ImageDraw.Draw(background)
            draw.rectangle((-1, -1, resized.size[0]+1, resized.size[1]+1),
                           fill=(255, 255, 255))
            del draw
            resized = Image.composite(resized, background, resized)

        io = StringIO.StringIO()

        try:
            resized.save(io, 'JPEG', optimize=True, progression=True,
                         quality=80)
        except IOError as ex:
            return self.send_file(original)

        s = io.getvalue()

        fp = open(target, 'wb')
        fp.write(s)
        fp.close()

        return self.send_file(target)

    # the length of the prefix is defined here and in web/urls.py
    @staticmethod
    def get_prefix(filename):
        return filename[:3]

    @staticmethod
    def get_thumbnail(size, prefix, filename):
        return os.path.join(LOGO_DIR, str(size), prefix, filename)

    @staticmethod
    def get_existing_thumbnails(prefix, filename):
        files = glob(os.path.join(LOGO_DIR, '*', prefix, filename))
        return filter(lambda f: 'original' not in f, files)

    @staticmethod
    def get_original(prefix, filename):
        return os.path.join(LOGO_DIR, 'original', prefix, filename)

    @staticmethod
    def get_dir(filename):
        path = os.path.dirname(filename)
        try:
            os.makedirs(path)

        except OSError as ose:
            if ose.errno != errno.EEXIST:
                raise

        return path

    def send_file(self, filename):
        resp = HttpResponse(content_type='image/jpeg')
        resp.status_code = 200
        f = open(filename)
        resp.write(f.read())
        return resp
