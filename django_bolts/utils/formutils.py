import hashlib
import inspect
import time
 
def get_form_name(form):
    if not inspect.isclass(form): form = form.__class__    
    meta = getattr(form,'Meta',None)
    if not meta:
        form.Meta = type('Meta',(object,),{})
        meta = form.Meta
    if not hasattr(meta,'name'):
        md5 = hashlib.md5()
        md5.update(form.__name__ + str(time.time()))
        meta.name = md5.hexdigest()
    return meta.name     
    
def get_form_submit_name(form):    
    return "submit-%s"%get_form_name(form)  

def get_form_method(form):
    if not inspect.isclass(form): form = form.__class__    
    meta = getattr(form,'Meta',None)
    return 'POST' if not meta else getattr(meta,'method','POST').upper()          

def is_form_submitted(form,request):
    name = get_form_submit_name(form)
    method = get_form_method(form)
    return name in request.GET if method == 'GET' else name in request.POST

    