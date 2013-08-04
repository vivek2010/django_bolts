from django_bolts.utils import init_constructor, modify_request_query
from django_bolts.exceptions import LoginRequired, InvalidRequest
from django.http import HttpResponse
from django.shortcuts import render, redirect
import functools
import traceback
from django_bolts.views.utils import confirm,inform
from django_bolts.utils import is_form_submitted, get_form_name
from django.contrib import messages

import json
from django.views.decorators.csrf import csrf_exempt


__all__ = ['view', 'hijax_view', 'form_view', 'json_view', 'jsonrpc_wrap', 'json_wrap']

RPC_PARSE_ERROR = -32700
RPC_INVALID_REQUEST = -32600
RPC_METHOD_NOT_FOUND = -32601
RPC_INVALID_PARAMS = -32602
RPC_INTERNAL_ERROR = 32603

RPC_MESSAGES = {
    RPC_PARSE_ERROR: 'Parse Error',
    RPC_INVALID_REQUEST: 'Invalid Request',
    RPC_METHOD_NOT_FOUND: 'Method Not Found',
    RPC_INVALID_PARAMS: 'Invalid Params',
    RPC_INTERNAL_ERROR: 'Internal Error'
}

VERSION = '2.0'


class view(object):
    login = False
    prefix = None
    csrf = None
    name = None
    _position = 0
    template = None

    def __init__(self, url=None, **kwargs):
        self.url = url
        init_constructor(self, kwargs)
        view._position += 1
        self._position = view._position
        self.func_orig = None

    def is_permitted(self, request):
        if self.login and not request.user.is_authenticated():
            raise LoginRequired

    def wrap(self, func):
        return func

    def render(self, rsrc, request, fname, ctx):
        template = self.template
        if isinstance(ctx, (list, tuple)):
            template, ctx = ctx
        elif isinstance(ctx, HttpResponse):
            return ctx
        if not template:
            template = rsrc.get_template_name(fname, prefix=self.prefix)
        return render(request, template, ctx)

    def __call__(self, func):

        orig = func
        while hasattr(orig, "func_orig"):
            orig = orig.func_orig
        func = orig

        inner_wrapper = self.wrap(func)

        def wrapper(rsrc, request, *args, **kwargs):            
            self.is_permitted(request)
            fname = func.__name__
            result = inner_wrapper(rsrc, request, *args, **kwargs)            
            return self.render(rsrc, request, fname, result)

        functools.update_wrapper(wrapper, func)

        wrapper.func_orig = func
        wrapper.rx = self.url
        wrapper.name = self.name if self.name is not None else func.__name__
        wrapper.__view__ = True
        wrapper._position = self._position

        return wrapper


class form_view(view):

    valid = True

    def __init__(self,url,form_class,**kwargs):
        super(form_view,self).__init__(url,**kwargs)
        self.is_multi = isinstance(form_class,(list,tuple))
        self.form_classes = form_class if self.is_multi else [form_class]

    def wrap(self,func):
        def wrapper(rsrc,request,*args,**kwargs):
            is_post = request.method == 'POST'
            forms = []
            ctx = {}
            is_valid = False
            for fclass in self.form_classes:
                name = get_form_name(fclass)
                if is_post and is_form_submitted(fclass, request):
                    form = fclass(request.POST,request.FILES)
                    if self.valid:
                        if form.is_valid():
                            is_valid = True
                    else:
                        is_valid = True
                else:
                    form = fclass()
                ctx[name] = form
                forms.append(form)
            if is_valid:
                first_form = forms[0]
                if not self.is_multi: forms = first_form
                return func(rsrc,request,forms,*args,**kwargs)
            ctx['form'] = first_form
            return ctx
        return wrapper


class json_view(view):

    kind  = 'json'
    limit = 1024

    def wrap(self,func):
        limit = self.limit
        def wrapper(rsrc,request,*args,**kwargs):
            try:
                data = json.loads( request.read(limit) )
            except ValueError,e:
                return json_error(RPC_PARSE_ERROR)
            if data.get('jsonrpc',None) != VERSION: return json_error(RPC_INVALID_REQUEST)
            mid = data.get('id',None)
            method = data.get('method',None)
            if not method or method[0] == '_': return json_error(RPC_METHOD_NOT_FOUND,id=mid)
            params = data.get('params',())
            try:
                if isinstance(params,(tuple,list,dict)):
                    result = func(rsrc,method,params,*args,**kwargs)
                else:
                    return json_error(RPC_INVALID_PARAMS,id=mid)
                return json_done(result,id=mid)
            except Exception,e:
                return json_error(RPC_INTERNAL_ERROR,id=mid,message=str(e))

        return wrapper


class hijax_view(view):

    login = True
    message = "Please confirm your action"

    def wrap(self,func):
        def wrapper(rsrc,request,*args,**kwargs):
            user = request.user
            if request.method == 'POST':
                result = func(self,user,*args,**kwargs)
                result['value'] = 10
                return inform(request,result)
            else:
                if request.is_ajax():
                    raise InvalidRequest
                else:
                    return confirm(request,self.message)
        return wrapper


def jsonrpc_wrap(limit=1024):    
    def wrapper_outer(func):
        @csrf_exempt
        def wrapper(request, *args, **kwargs):            
            try:                
                data = json.loads(request.read(limit))                
            except ValueError,e:                
                return json_error(RPC_PARSE_ERROR)
            if data.get('jsonrpc', None) != VERSION:
                return json_error(RPC_INVALID_REQUEST)
            mid = data.get('id', None)
            method = data.get('method', None)
            if not method or method[0] == '_':
                return json_error(RPC_METHOD_NOT_FOUND, mid=mid)
            params = data.get('params', ())
            try:
                if isinstance(params, (tuple, list, dict)):
                    result = func(request, method, params, *args, **kwargs)                    
                else:                    
                    return json_error(RPC_INVALID_PARAMS, mid=mid)
                return json_done(result, mid=mid)
            except NotImplementedError:                
                return json_error(RPC_METHOD_NOT_FOUND, mid=mid)
            except Exception, e:                
                return json_error(RPC_INTERNAL_ERROR, mid=mid, message=str(e))
            return functools.update_wrapper(wrapper, func)
        return wrapper
    return wrapper_outer


def json_wrap(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return json_done(result,1)
        except Exception,e:
            return json_error(RPC_INTERNAL_ERROR, message=str(e), mid=1)
    return functools.update_wrapper(wrapper, func)


def ajax_post(func):
    """
    func should return a string on success
    or raise an exception to inform about error
    if the exception has to_json method then it'll be called to get the error information
    """
    def wrapper(request,*args,**kwargs):                
        ajax = request.is_ajax() 
        if request.method != "POST":
            if ajax:
                return json_error(RPC_INVALID_REQUEST,1)
            else:
                return HttpResponse("Invalid Request",status=400)        
        next_url = request.GET.get('next', request.META["HTTP_REFERER"])
        try:
            success = False                     
            message = func(request,*args,**kwargs)            
            if isinstance(message,(list,tuple)):
                success, message = message                        
            if ajax:                
                return json_done(message,1) if success else json_error(
                                                            RPC_INTERNAL_ERROR,1,message)
            else:
                if message: 
                    messages.add_message(request, 
                        messages.SUCCESS if success else messages.ERROR, 
                        message)
                return redirect(next_url)   
        except Exception, e:                   
            message = e.message if not hasattr(e,'to_json') else e.to_json()
            if ajax:
                return json_error(RPC_INTERNAL_ERROR,message=message,mid=1)
            else:
                messages.add_message(request, messages.ERROR, message)
                return redirect(next_url)
            
    return functools.update_wrapper(wrapper,func)    
        
def json_pack(data):
    data = json.dumps(data)
    return HttpResponse(content=data,mimetype='application/json')


def json_error(error_id, mid=None, message=None, data=None):
    if not mid:
        return json_pack('error')
    msg = message or RPC_MESSAGES[RPC_INTERNAL_ERROR]
    errdata = {'code': error_id, 'message': msg, 'data': data}
    data = {'jsonrpc': VERSION, 'error': errdata}
    data['id'] = mid
    return json_pack(data)


def json_done(result, mid=None):
    if not mid:
        return json_pack('ok')
    data = {'id': mid, 'result': result, 'jsonrpc': VERSION}
    return json_pack(data)
