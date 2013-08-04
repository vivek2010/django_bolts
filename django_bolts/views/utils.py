
from django.shortcuts import render

__all__ = ['inform','confirm']


def inform(request,message,title=None,next_url=None,template='bolts/inform.html'):    
    next_url = next_url or request.get_full_path()    
    ctx = {'message':message,'title':title,'next_url':next_url}    
    return render(request,template,ctx)

def confirm(request,message,title=None,next_url=None,template='bolts/confirm.html',**kwargs):    
    """
    Renders an info box enclosed in a form with only hidden fields that contain items from
    kwargs. These are intended to provide context to the form handling view that called
    this function.
    Typical use is when a post-only action is accessed as GET e.g. deletion of a model.
    """
    next_url = next_url or request.get_full_path()    
    ctx = {'message':message,'title':title,'next_url':next_url}    
    ctx['context'] = kwargs
    return render(request,template,ctx)

