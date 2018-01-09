
from django.conf import settings
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
            return {'ANALYSIS_STATUS': analysis.status}
        except:
            return {'ANALYSIS_STATUS': 0}
    return {'ANALYSIS_STATUS': 0}
