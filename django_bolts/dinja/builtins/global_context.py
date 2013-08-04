# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse as django_reverse
from jinja2 import Markup
from django.forms.widgets import Widget
#from django_bolts.dinja.base import render_to_string
import re
import json
import itertools

def url(name, *args, **kwargs):
    """
    Shortcut filter for reverse url on templates. Is a alternative to
    django {% url %} tag, but more simple.

    Usage example:
        {{ url('web:timeline', userid=2) }}

    This is a equivalent to django: 
        {% url 'web:timeline' userid=2 %}

    """
    return django_reverse(name, args=args, kwargs=kwargs)

def field_class(field):    
    return re.sub('field','',field.__class__.__name__.lower())    

def widget_class(field):
    field = field if isinstance(field,Widget) else field.field.widget
    return re.sub('input|widget|field','',field.__class__.__name__.lower())

def widget_render(field,**kwargs):
    wid = field.field.widget
    wid.attrs.update(kwargs)
    return Markup(unicode(field))
     
def form_slice(form,start=None,end=None):    
    keys = form.fields.keys()
    start = start if not isinstance(start,str) else keys.index(start)   
    end = end if not isinstance(end,str) else keys.index(end)     
    return ( form[ f ] for f in  keys[start:end] )


