from mygpo.api.basic_auth import require_valid_user
from django.http import HttpResponse

@require_valid_user()
def device_subscription(request, username, device, format):
    return HttpResponse()

