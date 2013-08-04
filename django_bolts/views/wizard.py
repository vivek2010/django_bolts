
from django.shortcuts import render, redirect, Http404
from django.core.urlresolvers import reverse
from collections import OrderedDict
from django_bolts.utils.storage import SessionStorage 
from django.contrib.formtools.wizard.views import StepsHelper
from django.views.generic import TemplateView
from django import forms    
import os 
from django_bolts.utils import camel_to_underscore, get_form_method , get_client_ip
from django_bolts.utils.inspectutils import get_subclasses
from django.forms.models import save_instance
from django.db.models.signals import post_init
from django.http import HttpResponse
import json
from hobbyist.commons.utils import ajax_redirect


class HelperBase(object):

    def __init__(self, wizard):
        self._wizard = wizard

    def __dir__(self):
        return self.all

    def __len__(self):
        return self.count

    @property
    def count(self):
        "Returns the total number of steps/forms in this the wizard."
        return len(self.all)

    @property
    def first(self):
        "Returns the name of the first step."
        return self.all[0]

    @property
    def last(self):
        "Returns the name of the last step."
        return self.all[-1]

    @property
    def index(self):
        "Returns the index for the current step."
        current = self.current
        return self.all.index(current)

    @property
    def previous(self):
        i = self.index
        if i <= 0: return None 
        return i-1        
    
    @property
    def next(self):
        total = self.count
        i = self.index
        if i >= total: return None 
        return i+1        

    @property
    def step0(self):
        return int(self.index)

    @property
    def step1(self):
        return int(self.index) + 1    

class StepsHelper(HelperBase):

    def __repr__(self):
        return '<StepsHelper for %s (steps: %s)>' % (self._wizard, self.all)

    @property
    def all(self):
        "Returns the names of all steps/forms."
        return list(self._wizard.get_form_list())

    @property
    def current(self):
        """
Returns the current step. If no current step is stored in the
storage backend, the first step will be returned.
"""
        return self._wizard.current_step or self.first
   
    @property
    def next(self):
        "Returns the next step."
        return self._wizard.get_next_step()

    @property
    def previous(self):
        "Returns the previous step."
        return self._wizard.get_prev_step()

    @property
    def index(self):
        "Returns the index for the current step."
        return self._wizard.get_step_index()
  
class StorageForm(object):
    
    def __init__(self,data, model=None,instance=None):        
        self.cleaned_data = data
        self.is_bound = True
        self.errors = []
        self.model = model
        self.instance = instance 
            
    def __getitem__(self,name):        
        return self.cleaned_data[name]
    
    def __iter__(self):
        return iter(self.cleaned_data)
    
    def items(self):
        return self.cleaned_data.iteritems()
    
    def get(self,*args):
        return self.cleaned_data.get(*args)
            
    def is_valid(self):
        return True
    
    def save(self,instance=None,commit=False):
        instance = instance or self.instance or (self.model() if self.model else None)
        if not instance: return None
        if self.model and not isinstance(instance,self.model): return None
        save_instance(self,instance,commit=commit)
        return instance
       

class CommonWizard(TemplateView):    
    
    step_list = None
    
    template_dir = None
    
    wizard_name = None
    
    done_step = 'done'
    
    url_name = None    
    
    def __init__(self,*args,**kwargs):
        super(CommonWizard,self).__init__(*args,**kwargs)
        self.request = None
        self.instance = None
        self.is_ajax = False
        self.args = ()
        self.kwargs = {}
        form_list = OrderedDict()    
        step_labels = OrderedDict()
        self.extra_context = {}
        last = None
        for step in self.step_list:  
            if not isinstance(step,(tuple,list)):
                step = [step]                  
            name = step[0]
            form = step[1] if len(step) > 1 else None
            label = step[2] if len(step)> 2 else None                            
            form_list[name] = form    
            if label:
                step_labels[name] = label
            last = name
        self.done_step = last                                                          
        form_list[self.done_step] = None        
        self.step_labels = step_labels
        self.form_list = form_list 
        self.has_step_label = False  
        
    def get_instance_from_storage(self,storage): 
        return self.load_instance()
    
    def get_instance_from_request(self,request,*args,**kwargs): pass
    
    def get_request_step(self,request,*args,**kwargs): 
        return kwargs.get('step',None) 
        
    def load_for_session_key(self,session_key):                
        self.storage = SessionStorage(self.get_prefix(),session_key)
        self.instance = self.get_instance_from_storage(self.storage)
        self.steps = StepsHelper(self)
        self.kwargs = self.storage.get("kwargs",{})
        self.args = self.storage.get("args",())
        
    def load_for_request(self,request):        
        self.storage = SessionStorage(self.get_prefix(),request.session)
        if self.current_step == self.done_step:
            self.instance = self.load_instance()
        else:
            self.instance = self.get_instance_from_request(self.request,*self.args,**self.kwargs)
        if self.instance: self.store_instance(self.instance)
        self.steps = StepsHelper(self)

    @property
    def name(self):
        return self.wizard_name or self.__class__.__name__.lower().replace('wizard','')
            
    @classmethod
    def clsid(cls):
        return hash("%s.%s"%(cls.__module__,cls.__name__))
    
    @classmethod
    def get_clsid_map(cls):
        result = {}        
        for c in get_subclasses(cls):
            clsid = c.clsid()
            c = "%s.%s"%(cls.__module__,c.__name__)
            result[ clsid ] = c
        return result    
    
    @classmethod
    def get_class_for_clsid(cls,cid):
        cid = int(cid)
        for c in get_subclasses(cls):
            if c.clsid() == cid:
                return c        
    
    @classmethod
    def get_instance_for_clsid(cls, clsid, session_key):
        klass = cls.get_class_for_clsid(clsid)
        if not klass: 
            raise ValueError("No wizard class found for the given id: %s"%clsid)
        ins = klass()
        ins.load_for_session_key(session_key)
        return ins        
        
    @classmethod
    def as_url(cls,prefix,pk=False):
        from django.conf.urls import url
        pattern = r'(?:/(?P<step>\w+))?/'
        prefix = prefix.strip("/")
        if not cls.url_name :
            raise Exception("URL name not specified for %s"% (cls.__name__))        
        pk = r'(?:/(?P<pk>\d+))?' if pk else ''
        pattern = "^%s%s%s"%(prefix,pk,pattern)
        return url(pattern, cls.as_view(), name=cls.url_name )
        
    def get_template_names(self):
        return [ os.path.join(self.template_dir,"%s.html"%self.current_step) ]        
    
    def is_marked(self):
        return self.storage.get("__mark",False) is True
    
    def mark(self):
        self.storage.set("__mark",True)
    
    def get_prefix(self):   
        return camel_to_underscore(self.__class__.__name__)                                  
        
    def dispatch(self, request,*args, **kwargs):        
        self.args = args
        self.kwargs = kwargs
        self.request = request
        self.is_ajax = request.is_ajax()        

        current_step = self.get_request_step(request,*args,**kwargs)
                            
        self.current_step = current_step   
               
        self.has_step_label = current_step in self.step_labels
        
        if current_step is not None and current_step not in self.get_form_list() :                    
            raise Http404           
        
        self.load_for_request(request)                                  
                
        if current_step == self.done_step:            
            return self.render_done()
                        
        self.storage.set("user",self.request.user)        
        self.storage.set('ip', get_client_ip(self.request))
        self.storage.set('args',args)
        self.storage.set('kwargs',kwargs)
        self.storage.set('subdomain',getattr(request,'subdomain',None))

        #if somebody arrives in the middle without having started from the beginning then
        #they should be sent back to the first url
        if current_step == None or not self.is_marked() :
            self.clear()   
            if self.is_forbidden(current_step):
                return self.render_forbidden()         
            self.mark()                    
            return self.redirect(self.get_step_url(self.steps.first))       
                          
        response = super(CommonWizard,self).dispatch(request,*args,**kwargs)

        return response 
    
    def get(self, request, *args, **kwargs):
        #if step is the last step then, it cannot be an action
        step = self.current_step
        form_class = self.form_list[ step ]                
        if request.GET and 'GET' == get_form_method(form_class):                                    
            return self.render_submit(step,request.GET,{})
        else:
            return self.render_step(step)
                        
    def post(self, request, *args, **kwargs):
        step = self.current_step
        return self.render_submit(step,request.POST,request.FILES)
            
    def is_enabled(self,step):
        return True
    
    def is_forbidden(self,step):
        return False
    
    def is_committed(self,step):
        next_step = self.steps.next            
        return not next_step or next_step == self.done_step
    
    def render_forbidden(self):   
        raise NotImplementedError
    
    def get_request_subdomain(self):
        if self.request:
            return self.request.subdomain
        else:
            return self.storage.get('subdomain')        

    def get_request_ip(self):
        return get_client_ip(self.request) if self.request else self.storage.get("ip")
    
    def get_request_user(self):
        return self.request.user if self.request else self.storage.get("user") 
            
    def get_form_list(self):
        result = OrderedDict()
        for key, form in self.form_list.iteritems() :
            if self.is_enabled(key):            
                result[key] = form
        return result        

    def form_valid(self,form):
        pass
    
    def form_invalid(self,form):
        pass    

    def get_form_kwargs(self,step):
        return {}
    
    def get_form_initial(self,step):
        return {}
    
    def get_next_step_url(self,step=None):
        if not step: 
            step = self.current_step
        next_step = self.get_next_step(step)
        if next_step:
            return self.get_step_url(next_step)
            
    def get_next_step(self, step=None):
        """
        Returns the next step after the given `step`. If no more steps are
        available, None will be returned. If the `step` argument is None, the
        current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()        
        key = form_list.keys().index(step) + 1        
        if len(form_list.keys()) > key:
            return form_list.keys()[key]
        return None

    def get_prev_step(self, step=None):
        """
        Returns the previous step before the given `step`. If there are no
        steps available, None will be returned. If the `step` argument is
        None, the current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        key = form_list.keys().index(step) - 1
        if key >= 0:
            return form_list.keys()[key]
        return None

    def get_step_index(self, step=None):
        """
        Returns the index for the given `step` name. If no step is given,
        the current step will be used to get the index.
        """
        if step is None:
            step = self.steps.current
        return self.get_form_list().keys().index(step)   
    
    def get_form_instance(self,step):
        return self.instance
        
    def get_step_url(self,step):
        data = self.kwargs.copy()    
        if step:    
            data['step'] = step
        return reverse(self.url_name,kwargs=data)   
            
    def get_done_url(self):
        return self.get_step_url(self.done_step)        
    
    def get_first_url(self):
        return self.get_step_url(None) 

    def get_stored_data_for_step(self,form_key):
        form_class = self.get_form_list().get(form_key,None)
        if not form_class: return None
        data = self.storage.get_step_cleaned_data(form_key)
        if not data: return None
        model = None
        meta = getattr(form_class,'Meta',None)
        if meta:  model = getattr(meta,'model',None) 
        return StorageForm(data,model=model)          

    def get_cleaned_data_for_step(self, step):
        if step in self.form_list:
            form_obj = self.get_form(step=step,
                data=self.storage.get_step_data(step),
                files=self.storage.get_step_files(step))
            if form_obj and form_obj.is_valid():
                return form_obj.cleaned_data
        return None 
            
    def get_step_data(self, step):
        func = self.get_cleaned_data_for_step if self.request else self.get_stored_data_for_step
        return func(step)       

    def get_form(self,step=None,data=None,files=None):
        if not step: step = self.current_step
        form_list = self.get_form_list()
        form_class = form_list[step]
        if not form_class: return None
        kwargs = self.get_form_kwargs(step)
        kwargs['initial'] = self.get_form_initial(step)
        if issubclass(form_class, forms.ModelForm):
            kwargs['instance'] = self.get_form_instance(step)
        kwargs['data'] = data
        kwargs['files'] = files        
        form = form_class(**kwargs)    
        return form
        
    def get_invalid_form_step(self):
        for form_key in self.get_form_list():                                 
            data = self.storage.get_step_data(form_key)
            files = self.storage.get_step_files(form_key)            
            form_obj = self.get_form(step=form_key,data=data,files=files)
            if form_obj is None: continue
            valid = form_obj.is_valid()
            if not valid and self.request :     
                return form_key                   
                
    def get_all_stored_data(self):
        result = {}
        for step in self.get_form_list():
            data = self.get_stored_data_for_step(step)
            if data is None: continue
            result[step] = data
        return result

    def redirect(self,url,**kwargs):        
        if not self.is_ajax:            
            return redirect(url) 
        external = url.startswith("https") or url == self.get_done_url()
        return ajax_redirect(url,not external,**kwargs)
    
    def render_step(self,step):
        """
        Render all non-form get requests
        """
        data = self.storage.get_step_data(step)
        files = self.storage.get_step_files(step)
        form = self.get_form(step,data,files)
        self.clean_for_commit()
        return self.render(form)       
                        
    def render_submit(self,step,data,files):        
        form = self.get_form(step,data,files)            
        if form.is_valid():  
            cleaned_data = form.cleaned_data
            self.storage.set_step_data(step,form.data)
            self.storage.set_step_files(step,form.files)
            self.storage.set_step_cleaned_data(step, cleaned_data)                        
            self.form_valid(form)      
            if self.is_committed(step or self.current_step):
                step = self.get_invalid_form_step()
                if step: 
                    return self.render_revalidation_failure(step)
                self.prepare_for_commit()
                return self.render_commit()                         
            return self.redirect(self.get_step_url(self.steps.next or self.done_step))
        else:            
            self.form_invalid(form)
            return self.render(form)

    def render_commit(self):                                        
        self.process_commit()
        return self.redirect( self.get_done_url() )           
                                
    def render(self,form):
        context = self.get_context_data() or {}
        context.update( self.extra_context )
        self.form = form
        context['wizard'] = self
        context['form'] = form                       
        return self.render_to_response(context)
    
    def render_revalidation_failure(self,failed_step):
        """
        When a step fails, we have to redirect the user to the first failing
        step.
        """    
        return self.redirect(self.get_step_url(failed_step))
        
    def render_done(self):            
        item = self.load_instance()
        if not item:    raise Http404
        return self.done(item) 
                
    def done(self,item):
        """
        I should return a valid response
        """        
        self.extra_context['object'] = item    
        return self.render(None)
    
    def clean_for_commit(self):
        """
        Run for all steps that are not commited i.e for all get requests
        """
        
    def prepare_for_commit(self):
        """
        Run just before committed step i.e. after submission of form in the second last step 
        """
    
    def process_commit(self,clean=True):
        self.request = None
        ins = self.commit(self.get_all_stored_data())                  
        self.store_instance(ins)                        
        if clean: self.clear()                           
        self.storage.save()            
        return ins

    def commit(self,form_list):
        """
        I have to return something. This is the only way to ensure that
        only legitimate users reach this page.
        """
        raise NotImplementedError            
        
    def clear(self):
        self.storage.clear()
            
    def store_instance(self,ins):                
        session = self.storage.session
        key = "%s-instance"%self.get_prefix()
        session[key] = ins
        session.modified = True

    def load_instance(self):        
        if self.instance: return self.instance        
        session = self.storage.session
        key = "%s-instance"%self.get_prefix()
        item = session.get(key,None)
        if item:            
            #this is interesting. stored instance has incorrect kind during the upgrade
            #and this gets persisted during login process.
            #this overwrites all changes to the user.
            item = item.__class__.objects.get(pk=item.pk)
#            post_init.send(sender=item.__class__,instance=item)
        return item    