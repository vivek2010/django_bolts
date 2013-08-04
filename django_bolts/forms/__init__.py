from .fields import *
from django_bolts.utils import get_form_name

_forms = {}

def get_all_forms():
    return _forms.copy()

def register(*args,**kwargs):        
    for a in args:
        if isinstance(a, dict):
            _forms.update(a)
        else:
            key = get_form_name(a)
            _forms[key] = a                
    _forms.update(kwargs)    
    