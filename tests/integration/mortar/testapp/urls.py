import time

from django.conf.urls import include, url
from django.http import HttpResponse
from django.urls import reverse


def view_a(response):
    url_b = reverse('b')
    url_c = reverse('c')

    return HttpResponse(f"""
        <html>
        <body>
            <a href="{url_b}">Link to b</a>
            <a href="{url_c}">Link to c</a>
        </body>
        </html>
    """)


def view_b(response):
    url_c = reverse('c')

    return HttpResponse(f"""
        <html>
        <body>
            <a href="{url_c}">Link to c</a>
        </body>
        </html>
    """)


def view_c(response):
    url_a = reverse('a')

    return HttpResponse(f"""
        <html>
        <body>
            <a href="{url_a}">Link to a</a>
        </body>
        </html>
    """)


def view_slow(response):
    url_a = reverse('a')

    time.sleep(.5)

    return HttpResponse(f"""
        <html>
        <body>
            <a href="{url_a}">Link to a</a>
        </body>
        </html>
    """)


def view_ref_slow(response):
    url_slow = reverse('slow')

    return HttpResponse(f"""
        <html>
        <body>
            <a href="{url_slow}">Link to slow</a>
        </body>
        </html>
    """)


urlpatterns = [
    url(r'^a$', view_a, name='a'),
    url(r'^b$', view_b, name='b'),
    url(r'^c$', view_c, name='c'),
    url(r'^slow$', view_slow, name='slow'),
    url(r'^ref_slow$', view_ref_slow, name='ref-slow'),
    url(r'^$', view_c, name='home'),
    url(r'^', include('yurika.accounts.auth.urls')),
]
