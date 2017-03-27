import django.views.generic

class Home(django.views.generic.TemplateView):
    template_name = "portrait/home.html"
home = Home.as_view()

