from django_bolts.sites import site,BoltsSite

def autodiscover():
    import os    
    import copy
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule
    from django_bolts.views.resource import Resource
    from django_bolts.utils.inspectutils import get_subclasses
    import django_bolts.tags 
    import django_bolts.views.dev
    
    for app in settings.INSTALLED_APPS:
        mod = import_module(app)        
        # Attempt to import the app's admin module.        
        try:
            import_module('%s.tags' % app)
        except:
            pass
        try:
            import_module("%s.views"% app)
        except:
            pass
    resources = get_subclasses(Resource)    
    for rsrc in resources:
        if not rsrc.abstract:
            site.register( rsrc() )        