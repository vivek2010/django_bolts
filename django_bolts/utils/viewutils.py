
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django import forms

from django_bolts.utils import make_unique_name,modify_request_query, init_constructor
from collections import OrderedDict
from django.contrib.auth import login
from django.db.models.query import QuerySet

__all__ = ['ListHelper','SessionCookie','SortHelper','BooleanFilterHelper',
           'NullForm','is_pagination','SearchFormMixin']
   
class HelperField(object):
    
    __slots__ = ['value','used','asc','label','url']
        
    def __init__(self,value,used,request,field_name,label,asc=False):
        self.asc = asc                
        self.used = used
        self.label = label        
        self.value = value        
        kwargs = { field_name: value }
        self.url = modify_request_query(request,**kwargs)    
                      
                    
class BaseHelper(object):
    def __init__(self,actions):
        srs = OrderedDict()        
        namemap = OrderedDict()    
        store = set()
        default = None
        first = None
        for values in actions:
            if isinstance(values,basestring):
                values = (values, )
            label = values[0]
            func = values[-1] if len(values) > 1 else None
            name = values[1] if len(values) > 2 else make_unique_name(label, store)                  
            if label[0] == '*':
                default = name
                label = label[1:]          
            if first is None: first = name                      
            namemap[name] = label
            store.add(name)                              
            srs[label] = func                          
        self.default = default or first
        self.actions = srs        
        self.name_map = namemap
            
            
class SortHelper(BaseHelper):    
    
    def process(self,queryset,request,field_name):            
        sorter_list = OrderedDict()                
        alias = request.REQUEST.get(field_name,None)    
        desc = True
        name_map = self.name_map
        sorter_list.current = {'label':name_map.get(self.default)}
        if alias :
            if alias[0] != '-':
                desc = False
            else :
                alias = alias[1:]        
#        if alias not in name_map and self.default: 
#            alias = self.default
#            desc= True           
        for name,label in name_map.iteritems():             
            order = True            
            used = False                        
            if alias == name:  
                used = True  
                order = desc                   
                key = self.actions[ label ]             
                if callable(key): 
                    queryset = key(request,queryset,order)
                elif key:
                    if key[0] == '-':
                        key = key[1:]
                        way = not order
                    else:
                        way = order
                    queryset = queryset.order_by( "%s%s"%( "" if way else "-" ,key ) ) 
            value = name#"%s%s"%( "" if order else "-" , name)                                       
            sort_field = HelperField(value,used,request,field_name,label,asc=order)
            sorter_list[name] = sort_field
            if used:
                sorter_list.current = sort_field  
            else:
                sorter_list.current = {'label':''}                                                              
        return sorter_list, queryset              

        
class BooleanFilterHelper(BaseHelper):    

    def process(self,queryset,request,field_name):                
        alias = request.REQUEST.get(field_name,None)
        name_map = self.name_map                    
#        if not alias or alias not in name_map and self.default: alias = self.default        
        field_list = OrderedDict()          
        field_list.current = {'label':name_map.get(self.default)}    
        selected = False
        for name,label in name_map.iteritems():                    
            used = False
            value = name            
            if alias == name:
                used = True
                call = self.actions[ label ]                
                if call:
                    queryset = call(request,queryset)                
            field = HelperField(value,used,request,field_name,label)
            field_list[name]=field
            if used:
                selected = True
                field_list.current = field
        if not selected:
            fl = field_list.get(self.default)
            if fl:
                fl.used = True                                      
        return field_list,queryset
                    
             
class ListHelper(object):   
    
    sort_name = 'o'
    filter_name = 'f'
    page_name = 'p'
    prefix = ""
    page_size = 20

    def __init__(self,filters=None,sorters=None,**kwargs):        
        self.filters = BooleanFilterHelper(filters) if filters else None  
        self.sorters = SortHelper(sorters) if sorters else None 
        init_constructor(self,kwargs)

    def process(self,request,object_list,page_size=None,prefix=None):
        #prefix here is useful when this is part of queryset
        ctx = {}                
        
        prefix = prefix or self.prefix or ""
        page_size = page_size or self.page_size or 20
        
        filter_name = "%s%s"%(prefix,self.filter_name)
        sort_name = "%s%s"%(prefix,self.sort_name)
        page_name = "%s%s"%(prefix,self.page_name)        
                            
        ctx['total_objects'] = object_list        
        if self.filters:
            filter_fields, object_list = self.filters.process(object_list,request,filter_name)
            ctx['filters'] = filter_fields        
        
        if self.sorters:
            sort_fields, object_list = self.sorters.process(object_list,request,sort_name)
            ctx['sorters'] = sort_fields
                    
        page = request.GET.get(page_name,1)
                
        results = paginate_results(object_list, page, page_size, context=ctx)
        
        results['page_obj'].page_field_name = page_name 
        
        return results        


def paginate_results(object_list,page,size,context=None):
    ctx  = context or {}                                    
    paginator = Paginator(object_list,size)                                                                            
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)   
    ctx['object_list'] = page_obj.object_list
    ctx['page_obj'] = page_obj
    ctx['paginator'] = paginator
    ctx['is_paginated'] = True  
    ctx['is_empty'] = paginator.count == 0           
    return ctx  

def apply_sorters():
    pass

def apply_filters():
    pass
                            
class SessionCookie(object):
    
    def __init__(self,name,request):
        self.request = request
        self.name = name

    @property
    def state(self):
        return self.request.session.get(self.name,None)
    
    @state.setter
    def state(self,val):
        self.request.session[ self.name ] = val
        
    def __eq__(self,val):
        return val == self.state
    
    def clear(self):
        del self.request.session[ self.name ]
            

class SearchFormMixin(object):
    
    def process_fields(self,unknown):
        for name,field in self.fields.items():                     
            field.required = False            
            if isinstance( field.widget,(forms.CheckboxSelectMultiple,forms.SelectMultiple)) : continue                    
            if hasattr(field,'choices') and list(field.choices):                                
                fchoices = list(field.choices)
                initial = fchoices[0][0]       
                if initial == '':
                    choices = list(fchoices)
                    choices.pop(0)
                    field.choices = tuple( choices )      
                    initial = True            
                if initial:
                    choices = list(field.choices)                    
                    choices.insert( 0, ('', unknown) )
                    field.choices = tuple( choices )                                    
                field.initial = 0       
    
    @staticmethod        
    def has_field(queryset,field_name):
        model = queryset.model if isinstance(queryset,QuerySet) else queryset
        meta = model._meta
        field_names = set(meta.get_all_field_names())
        return field_name in field_names                          
                
    def apply_filters(self,queryset):        
        kwargs = {}
        model = queryset.model
        meta = model._meta
        field_names = set(meta.get_all_field_names())
        excludes = set( getattr(self,'exclude_filters',[]) )
        includes = set( getattr(self,'include_filters', self.fields.keys() ) )
        includes.difference_update(excludes)
        data = self.cleaned_data        
        for name in includes:                         
            value = data.get(name,None)            
            if not value: continue            
            call = getattr(self,'filter_%s'%name,None)
            if callable(call):
                result = call( queryset, value, data )
                if isinstance(result,QuerySet):
                    queryset = result                                     
            else:                
                if name not in field_names: continue     
                field = name if not call else call                                            
                if isinstance(value,(tuple,list,QuerySet)):
                    field = '%s__in'%field                
                kwargs[field] = value
        return queryset.filter(**kwargs)


class NullForm(forms.Form):
    cleaned_data = {}
    def is_valid(self,*args,**kwargs): return True    

    
def is_pagination(request):
    gt = request.GET
    return gt and ( 'order' in gt or 'filter' in gt or 'page' in gt )        

def auth_login(request,user):
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request,user)
    return user    