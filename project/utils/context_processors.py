
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
            analysis = Analysis.objects.get_or_create(id=0)
            if analysis.status == 5:
                return {'ANALYZED': True}
        except:
            return {'ANALYZED': False}
    return {'ANALYZED': False}
