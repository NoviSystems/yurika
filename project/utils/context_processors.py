from mortar.models import Analysis


def analysis_status(request):
    if request.user.is_authenticated():
        try:
            analysis, created = Analysis.objects.get_or_create(id=0)
            return {
                'CONFIGURED': analysis.all_configured,
                'RUNNING': analysis.any_running,
                'FINISHED': analysis.all_finished,
            }
        except Exception:
            return {'CONFIGURED': False, 'RUNNING': False, 'FINISHED': False}
    return {'CONFIGURED': False, 'RUNNING': False, 'FINISHED': False}
