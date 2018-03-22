"""URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

from project import views


___password_reset_confirm = r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    # Auth urls
    url(r'^login/$',                    views.LoginView.as_view(),                  name='login'),
    url(r'^logout/$',                   views.LogoutView.as_view(),                 name='logout'),

    url(r'^password_change/$',          views.PasswordChangeView.as_view(),         name='password_change'),
    url(r'^password_change/done/$',     views.PasswordChangeDoneView.as_view(),     name='password_change_done'),

    url(r'^password_reset/$',           views.PasswordResetView.as_view(),          name='password_reset'),
    url(r'^password_reset/done/$',      views.PasswordResetDoneView.as_view(),      name='password_reset_done'),
    url(___password_reset_confirm,      views.PasswordResetConfirmView.as_view(),   name='password_reset_confirm'),
    url(r'^reset/done/$',               views.PasswordResetCompleteView.as_view(),  name='password_reset_complete'),

    url(r'^', include('appname.urls')),
]
