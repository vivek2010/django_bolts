
from django_bolts.dinja.base import render_to_response, render_to_string, render_string

def template_to_string(*args,**kwargs):
    return render_to_string(*args,**kwargs)

def template_to_response(*args,**kwargs):
    return render_to_response(*args,**kwargs)

def format_string(source,context):
    return render_string(source, context)