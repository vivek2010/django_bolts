import functools
from django_bolts.dinja.base import env
import jinja2

__all__ = ['dinja_tag','dinja_filter','dinja_test','dinja_constants']

def dual_wrapper(call):
    def func(*args,**kw):
        fn  = args[0] if len(args) > 0 else None
        if callable(fn):
            f1 = call(*args,**kw)
            if f1 != fn:
                f1 = functools.update_wrapper(call, f1)
            return f1
        else:
            def f1(f2):
                return func(f2,*args,**kw)
            return f1
    return func


def dinja_tag(template=None,name=None,takes_context=False):
    def wrapper(fn):      
        fn_ = fn
        name_ = name or getattr(fn,'_decorated_function',fn).__name__ 
        if template:
            def func(ctx,*args,**kwargs):                
                t = env.get_template(template)                                                          
                if takes_context:                
                    values = fn_(ctx,*args,**kwargs)
                else:
                    values = fn_(*args,**kwargs)
                for k in ('request','user','STATIC_URL',
                    'csrf_token','MEDIA_URL','site','TIME_ZONE','messages'): 
                    if k in ctx: values[k] = ctx[k]                             
                return t.render( values )
            fn = jinja2.contextfunction(functools.update_wrapper(func,fn_))
        else :           
            if takes_context:                
                fn = jinja2.contextfunction(fn)
        env.globals[name_] = fn
        return fn_
    return wrapper
    
def dinja_filter(fn):
    name = getattr(fn,'_decorated_function',fn).__name__
    env.filters[name] = fn
    
def dinja_test(fn):
    name = getattr(fn,'_decorated_function',fn).__name__
    env.tests[name] = fn   
    
def dinja_constants(*args,**kwargs):
    ctx = {}
    for a in args: ctx.update(a)
    ctx.update(kwargs)        
    env.globals.update(ctx)    

    
                    