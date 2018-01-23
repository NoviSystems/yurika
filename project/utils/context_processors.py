
from django.conf import settings
from django.core.urlresolvers import reverse

from mortar.models import Analysis

def google_analytics(request):
    """
    Add Google Analytics tracking context
    """
    return {'GA': settings.GOOGLE_ANALYTICS_KEY}

def analysis_status(request):
    if request.user.is_authenticated():
        try:
            analysis,created = Analysis.objects.get_or_create(id=0)
            return {'CONFIGURED': analysis.all_configured, 'RUNNING': analysis.any_running, 'FINISHED': analysis.all_finished}
        except:
            return {'CONFIGURED': False, 'RUNNING': False, 'FINISHED': False}
    return {'CONFIGURED': False, 'RUNNING': False, 'FINISHED': False}

def nav_current_page(request):
    nav = {
        '/configure': 'configure',
        '/execute': 'execute',
        '/explorer': 'explorer',
    }
    url = request.get_full_path()
    for nav_url, name in nav.items():
        if url.startswith(nav_url):
            return {'nav_active': name}
    return {}
