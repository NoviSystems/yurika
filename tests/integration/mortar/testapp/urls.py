from django.conf.urls import include, url
from django.http import HttpResponse
from django.urls import reverse

from project.urls import authpatterns


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


urlpatterns = [
    url(r'^a$', view_a, name='a'),
    url(r'^b$', view_b, name='b'),
    url(r'^c$', view_c, name='c'),
    url(r'^$', view_c, name='home'),
    url(r'^', include(authpatterns)),
]
