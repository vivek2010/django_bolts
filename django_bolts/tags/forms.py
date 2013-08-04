
from django_bolts.dinja.base import render_to_string
from django_bolts.dinja.decorators import dinja_tag 
from jinja2 import Markup
from django_bolts.utils import get_form_name
import re
import json
from django_bolts.utils.stringutils import camel_to_hyphen

def make_css_class(*classes):
    result = []
    history = set()
    for c in classes:
        parts = re.split(r'\s+',c)
        for part in parts:
            if part and part not in history:
                result.append(part)
                history.add(part)
    return ' '.join(result)

def make_attrs(attrs):
    result = []
    css = []
    for k,v in attrs.iteritems():
        if k == 'css':
            css.append(v)
            continue
        if isinstance(v,basestring):
            v = v.encode('string-escape')
        else:
            v = json.dumps(v)
        result.append("%s='%s'"% (k,v))
    css = make_css_class(*css)
    if css:
        result.append("class=%s"% css)    
    return " ".join(result)
            
@dinja_tag()            
def bolts_form_attrs(form,**kwargs):
    attrs = kwargs.copy()
    attrs['method'] = kwargs.pop('method','post')
    attrs['enctype']='multipart/form-data' if form.is_multipart() else 'application/x-www-form-urlencoded'
    return make_attrs(attrs)

@dinja_tag()
def bolts_form_submit(form,value="Submit",name=None, **kwargs):
    return Markup(create_submit_tag(form, value, name, **kwargs))

def create_submit_tag(form,value="Submit",name=None, **kwargs):
    name = name or get_form_name(form)
    attrs = kwargs.copy()
    attrs.update({'type': 'submit', 'value': value, 'name': name})    
    attrs = make_attrs(attrs)
    return "<input %s />"% (attrs, )

def create_form_tag(form,**kwargs):
    return "<form %s />"% bolts_form_attrs(**kwargs) 

def create_csrf_tag(request):
    from django.middleware.csrf import get_token        
    csrf_token = get_token(request)
    return u"<div style='display:none'><input type='hidden' name='csrfmiddlewaretoken' value='%s' /></div>" % (csrf_token,)        

@dinja_tag(takes_context=True)
def bolts_form(context,form,**kwargs):
    layout = kwargs.pop('layout',None) 
    template = kwargs.pop("using",None)
    request = context['request']
    csrf = create_csrf_tag(request)
    submit = create_submit_tag(form,**kwargs)
    fields = map(lambda f: render_field(f, template, {}, layout),(form[key] for key in form.fields) )
    fields.append(submit)
    fields.insert(0,csrf)
    return Markup( "".join( fields ) )


@dinja_tag()
def bolts_fields_slice(first=None,last=None,form=None,**kwargs):
    form = getattr(first,'form',getattr(last,'form',form)) 
    keys = form.fields.keys()
    first = keys.index( first.name ) if first else None
    last = keys.index( last.name ) + 1  if last else None
    return bolts_fields( *list(form[field] for field in  keys[first:last]), **kwargs)

        
@dinja_tag()        
def bolts_fields(*fields,**kwargs):
    template = kwargs.pop("using",None)
    layout = kwargs.pop('layout',None)         
    content = map(lambda f : render_field(f, template, kwargs, layout), fields)    
    return Markup( "".join( content ) )

            
@dinja_tag()            
def bolts_field(field,using=None,**kwargs):
    template = kwargs.pop("using",None)   
    layout = kwargs.pop('layout',None)      
    return Markup( render_field(field, template, kwargs, layout) )


def render_field(field,template,kwargs, layout):     
    inject_validation_tags(field)  
    process = lambda a: camel_to_hyphen( re.sub( r'widget|field', '',a.__class__.__name__) ).lower() 
    attrs =  make_attrs(kwargs)
    field_class_name = process(field.field)        
    widget = field.field.widget
    widget_class_name = process(widget)    
    context = {
               'layout':layout,
               'field':field,
               'field_name': field.name,
               'field_class':field_class_name,
               'widget':widget,
               'widget_class':widget_class_name,
               'attributes':attrs
    }    
    if callable(template):
        html = template(field, context)
    else:
        template = template or "bolts/field.jinja"
        html = render_to_string(template, context)
    return html    


def inject_validation_tags(field):
    field = field.field
    widget = field.widget
    attrs = {
             'max_length':'maxlength',
             'min_length':'minlength',
#             'regex':'pattern',
#             'required':'required'
    }
    
    convert = {
               '*': lambda a : json.dumps(a), 
#               'regex': lambda a: str(a.pattern).encode('string-escape') 
    }
        
    for k,v in attrs.iteritems():
        val = getattr(field, k, None)
        if val is not None:                      
            widget.attrs[v] = convert.get(k, convert['*'])(val)
    

@dinja_tag()
def bolts_widget(field,**kwargs):
    wid = field.field.widget
    wid.attrs.update(kwargs)
    return Markup(unicode(field))
