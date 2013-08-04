from django.shortcuts import render,redirect, get_object_or_404
import django_bolts.utils as cutils
from django.contrib.auth.models import User
from django.contrib.sites.models import get_current_site
from django.http import HttpResponseForbidden,HttpResponse
from django.template.loader import render_to_string
from django_bolts.views.resource import Resource
from django_bolts.views.decorators import view
from django_bolts.models import EmailConfirmation, RegistrationProfile
import json

def post_activation_email(self,request,user):
    from django.template import RequestContext
    from django.utils.safestring import mark_safe
    from django.utils.text import normalize_newlines
    
    ctx = RequestContext(self,request)
    subject = render_to_string("registration/post_activation_email_subject.txt",{'user':user},ctx)
    content = render_to_string("registration/post_activation_email.txt",{'user':user},ctx)
    
    normalized_text = normalize_newlines(subject)    
    subject =  mark_safe(normalized_text.replace('\n', ' '))
        
    user.email_user(subject,content)    


class AccountsResource(Resource):
    
    template_prefix = 'registration'
    verbose_name = 'accounts'
    url_prefix = 'accounts'
    create_form = None
    edit_form = None
    abstract = True
    
    def get_url_pattern(self):
        from django.conf.urls import patterns, include, url
        prefix = self.url_prefix
        urlpatterns = patterns( '',             
            url(r'^%s/'%prefix, include('django.contrib.auth.urls')),                                                   
        )           
        pattern =  urlpatterns + Resource.get_url_pattern(self)
        return pattern
    
    @view("(\w+)")
    def activate(self,request,activation_key):    
        account = RegistrationProfile.objects.activate_user(activation_key)    
        if account:
            post_activation_email(self,request,account)
            return redirect('accounts_activation_done')        
        return {}

    @view()
    def activation_done(self,request): return        
    
    @view()
    def activation_begin(self,request): return     
    
    @view()
    def registration_done(self,request): return
    
    def registration_forbidden(self,request):
        return HttpResponseForbidden(status=403,content='Forbidden')
    
    @view()
    def add_user(self,request):        
        ctx = {}
        if request.user.is_authenticated():
            return self.registration_forbidden(request)
        if request.method == 'POST':
            form = self.create_form(request.POST,request.FILES)
            if form.is_valid():
                user = self.create_user(request,form)
                user.save()
                if not user.is_active:
                    site = get_current_site(self.request)
                    registration_profile = RegistrationProfile.objects.create_profile(user)        
                    registration_profile.send_activation_email(site)        
                    return redirect('accounts_activation_begin')                                    
                else:
                    return redirect('accounts_registration_done')                
        else:            
            form = self.create_form()
        ctx['form'] = form            
        return ctx      
    
    def is_signup_allowed(self):
        pass    
    
    def create_user(self,form):
        pass        
            
    @view("(\w+)")
    def email_confirm(self,request,activation_key):    
        account = EmailConfirmation.objects.confirm(activation_key)    
        return render(self,request,'registration/email_confirmation.html',{'account':account})      
    
    @view("(\d+)")
    def avatar(self,request,uid):
        user = get_object_or_404(User,pk=uid)
        url = user.get_avatar_url()        
        return redirect(url)        
    
    @view("(\d+)")
    def profile(self,request,uid):
        user = get_object_or_404(User,pk=uid)
        url = user.get_profile().get_absolute_url()    
        return redirect(url)

    @view("(\w+)")
    def presence(self,request,username):    
        user = get_object_or_404(User,username=username)
        return HttpResponse(content=str( user.presence ), status = 200 )
        
    @view()
    def check_username(self,request):
        name = request.GET.get('username',False)
        if name:        
            result = User.objects.filter(username__iexact=name).exists()
        else:
            result = name
        return HttpResponse(content=json.dumps(not result),mimetype='plain/text',status=200)    
    
    @view()
    def check_email(self,request):
        email = request.GET.get('email',False)        
        if email:        
            result = User.objects.filter(email__iexact=email).exists()
        else:
            result = email
        return HttpResponse(content=json.dumps(not result),mimetype='plain/text',status=200)
  
            
#from django.contrib.auth.views import AuthenticationForm, login as orig_login
#
#def login(request):
##    if request.is_ajax():
##        return render(request,"registration/login_xhr.html", dict( form = AuthenticationForm() ) )
##    else:
#    return orig_login(request)     
