from django_bolts.views.resource import Resource
from django_bolts.views.decorators import view
from django_bolts.forms import get_all_forms
from django.shortcuts import redirect
from django.http import Http404


class DevResource(Resource):
    
    url_prefix = 'lab'
    template_prefix = 'lab'
    abstract = False
    
    def get_template_name(self, view, prefix=None):
        template = Resource.get_template_name(self, view, prefix=prefix)
        return template.replace(".html",".jinja")    
        
    @view("(\w+)")
    def forms(self,request,name):
        formlist = get_all_forms()
        if name not in formlist:
            raise Http404("%s not registered: %s"%(name,formlist.keys()))
        form_class = formlist[name]        
        if request.method == 'POST':
            form = form_class(request.POST,request.FILES)
            if form.is_valid():
                return redirect(self.get_view_name('form_done'))
        else:
            form = form_class()            
        return ('lab/form.jinja',{'form':form})
    
    @view("(\w+)")
    def widgets(self,request,name):
        pass
    
    @view()
    def form_done(self): return
    
    def form_edit(self):
        pass
    
    def form_new(self): return
    
    def form_template(self): return
    
    
    def tag_template(self): return
    
    