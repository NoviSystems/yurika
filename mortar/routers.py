class AnalysisRouter(object):
    '''A router to control what the user can interact with through SQL Explorer'''
    def db_for_read(self, model, **hints):
        if model._meta.db_table == 'annotations':
            return 'explorer'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.db_table == 'anotations':
            return 'explorer'
        return None
 
    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.db_table == 'annotations' or obj2._meta.db_table == 'annotations':
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'explorer':
            return model_name == 'annotation'
        elif model_name == 'annotation':
            return False
        return None
