
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from datetime import date
from django.http import HttpResponseForbidden, HttpResponse
from django.template import RequestContext
import json
import string
import random
import inspect
import re
import time
import os
from django.shortcuts import render
from django.db.models import Model 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import functools
from django.core import urlresolvers
from django.contrib.contenttypes.models import ContentType
import hashlib
from django_bolts.utils.formutils import *
from django.utils.importlib import import_module
from django.conf import settings
import errno
import tempfile

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local


_thread_locals = local()

def get_daily_temp_dir(base_dir=None):
    base_dir = base_dir or settings.TEMP_MEDIA_ROOT
    today = date.today()    
    folder = os.path.join(base_dir,"%s/%s/%s"%(today.year,today.month,today.day))
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
    return folder

def get_unique_temp_filename(prefix,suffix):
    file_obj = tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, delete=False)
    name = file_obj.name
    file_obj.close()
    return name

def get_current_request():
    """ returns the request object for this thead """
    return getattr(_thread_locals, "request", None)


def get_current_user():
    """ returns the current user, if exist, otherwise returns None """
    request = get_current_request()
    if request:
        return getattr(request, "user", None)
    
def resolve_url(to, *args, **kwargs):
    # If it's a model, use get_absolute_url()
    if hasattr(to, 'get_absolute_url'):
        return to.get_absolute_url()

    # Next try a reverse URL resolution.
    try:
        return urlresolvers.reverse(to, args=args, kwargs=kwargs)
    except urlresolvers.NoReverseMatch:
        # If this is a callable, re-raise.
        if callable(to):
            raise
        # If this doesn't "feel" like a URL, re-raise.
        if '/' not in to and '.' not in to:
            raise

    # Finally, fall back and assume it's a URL
    return to    

def init_constructor(self,kwargs):
    for k in kwargs:
        if hasattr(self,k):
            setattr(self,k,kwargs[k])
        else:
            raise AttributeError(k)

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
def camel_to_underscore(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()

def camel_to_hyphen(name):
    s1 = first_cap_re.sub(r'\1-\2', name)
    return all_cap_re.sub(r'\1-\2', s1).lower()

def modify_request_query(request,*args,**kwargs):
    values = {}
    for a in args: values.update(a)
    values.update(kwargs)
    query = request.GET.copy()    
    for k,v in values.items():
        query[k] = v
    path = request.path_info
    return "%s?%s"%(path,query.urlencode())    
    
def calculate_age(born):    
    today = date.today()
    if not born: return 0
    try: # raised when birth date is February 29 and the current year is not a leap year
        birthday = born.replace(year=today.year)
    except ValueError:
        birthday = born.replace(year=today.year, day=born.day-1)
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year
    
def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))
    
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_client_latlng(request):    
    from django.contrib.gis.geoip import GeoIP
    g = GeoIP()
    ip = get_client_ip(request)
    if ip == '127.0.0.1': ip = 'erotq.com'
    return g.lat_lon(ip) or (43.6481, 79.4042)#toronto

def model_instance_from_dict(model,**qdict):
    meta = model._meta
    names = set( meta.get_all_field_names() )
    names.difference_update( {a.name for a in meta.many_to_many} )
    return model( **dict( (k,v) for k,v in qdict.items() if k in names ) )

def make_unique_name(label,store,total=3):    
    maxlen = total    
    label = label.lower()[:maxlen]
    label = re.sub(r'[^a-z]','',label)
    i = 1
    base_label = label  
    while label in store:
        label = "%s%s"%(base_label,i)
        i+=1
    store.add(label)
    return label

        
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

    
def create_uid(item):
    """
    returns a unique id for any object that has an id field.
    """
    ct = ContentType.objects.get_for_model(item)
    return "bt%05d%d"%(ct.id,item.id)


def resolve_uid(uid):    
    """
    resolves uid to object
    """
    prefix = 7
    cid,oid = uid[:prefix],uid[prefix:]
    ct = ContentType.objects.get_for_id(int(cid[2:]))
    return ct.get_object_for_this_type(id=int(oid))

def import_class(name):
    parts = name.split(".")
    cname = parts.pop()    
    mod = import_module(".".join(parts))
    return getattr(mod,cname)
     
if __name__ == '__main__':         
    print id_generator(4)
    print calculate_age(date.today().replace(year=1981))
    
    cands = ['asdas d as dasd','asdasdad',' d asd as d asd as da da']
    store = set()
    for c in cands:
        print make_unique_name(c, store)