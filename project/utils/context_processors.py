from mortar.models import Analysis


def analysis_status(request):
    if request.user.is_authenticated():
        try:
            pk = request.session.get('analysis')
            analysis = Analysis.objects.get(pk=pk)
            return {
                'CONFIGURED': analysis.all_configured,
                'RUNNING': analysis.any_running,
                'FINISHED': analysis.all_finished,
            }
        except Analysis.DoesNotExist:
            return {'CONFIGURED': False, 'RUNNING': False, 'FINISHED': False}
    return {'CONFIGURED': False, 'RUNNING': False, 'FINISHED': False}
