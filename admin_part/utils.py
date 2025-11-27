from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache


def login_required_nocache(view_func):
    return login_required(never_cache(view_func), login_url='/')
