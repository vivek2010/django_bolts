
from django.conf.urls import patterns, include, url
import django_bolts.utils as cutils
import inspect

from django_bolts.utils import init_constructor
from django_bolts.utils.stringutils import join_with_underscore
from django_bolts.utils.viewutils import ListHelper

__all__ = ['Resource','ChildResource']
   

class ResourceBase(object):
    
    page_size = 25
    template_prefix = None
    url_prefix = None      
    verbose_name = None
    verbose_name_plural = None
    abstract = False    
    
    model = None
    
    filters = None
    
    sorters = None
    
    def __init__(self,parent=None,url_prefix=None):
        self.parent = parent                     
        if url_prefix is not None: self.url_prefix = url_prefix
        classes= inspect.getmembers(self.__class__, lambda a : inspect.isclass(a) and issubclass(a,ChildResource) )        
        for name,cls in classes:            
            setattr(self,name,cls(parent=self,url_prefix=name))
        self.helper = ListHelper(sorters=self.sorters,filters=self.filters)
        
    def get_template_name(self,view,prefix=None):        
        return "%s/%s.html"%(prefix or self.template_prefix,view)
    
    def get_view_name(self,view):
        rootname = self.get_url_name()            
        fname = view.__name__ if inspect.ismethod(view) else view                
        fname = cutils.camel_to_underscore(fname).lower()                        
        name = join_with_underscore(rootname,fname)   
        return name
    
    def get_view_url(self,view):
        rootname = self.get_url_name()           
        func = view if inspect.ismethod(view) else getattr(self,view)
        rx = func.rx or '' 
        if rx.startswith("-"):
            path = rx[1:]
        else:   
            fname = func.name
            if fname.startswith('-'): parts = [fname[1:]]    
            else: parts = [ a for a in (rootname,func.name,rx) if a ]                             
            if parts:
                path = '/'.join(parts).replace('_', '/')
            else:
                path = ''
        if path:
            if path[-1] == '-': path = path[:-1]
            else: path += '/'             
        path = "^%s$"%path        
        return path
    
    def get_url_name(self):
        basename = self.parent.get_url_name() if self.parent else ''
        return join_with_underscore(self.url_prefix,basename)         
    
    def get_url_pattern(self):
        rsrc = self
        
        members = inspect.getmembers(rsrc)
        
        urlpatterns = []          
        
        result = patterns('')
        for fname,func in members:                                 
            if inspect.ismethod(func) and hasattr(func,'__view__'):                
                fname = cutils.camel_to_underscore(fname).lower()                
                name = self.get_view_name(func)
                path = self.get_view_url(func)
                                
                u = url( path, getattr(rsrc,fname) ,name=name)
                            
                urlpatterns.append(u)
                
            elif isinstance(func,ChildResource):                        
                result+= func.get_url_pattern(func)
                            
        return result + urlpatterns
    
    def paginate(self,request,object_list=None,ctx=None):
        object_list = object_list or self.model.objects.all()
        return self.helper.process(request, object_list, ctx or {})        
                

class Resource(ResourceBase):
    pass

class ChildResource(ResourceBase):    
    pass
        
            
  