from django import forms
from django.contrib.auth.models import User
from django.forms.extras.widgets import SelectDateWidget
from datetime import date
from django.core import validators

import re

from django.utils.encoding import force_unicode
from itertools import chain

__all__ = [
           'UniqueEmailField','UsernameField','NameField','RadioSelectNotNull',
           'DOBField','PasswordField','PasswordConfirmField',
           ]

class UsernameField(forms.RegexField):
    
    help_text = "Should be less than 30 characters and can contain only letters, numbers and underscores."
    
    def __init__(self,label='Username',help_text=help_text,unique=True,**kwargs):        
        super(UsernameField,self).__init__(regex=r'^[a-zA-Z][\w+]+$',
            help_text=help_text,
            max_length=40,
            widget=forms.TextInput(attrs={'size':'24'}),
            label=label,
            error_messages={'invalid': "Username must contain only letters, numbers and underscores."},
            **kwargs
        )                
        self.unique = unique
        if unique:
            self.widget.attrs['class'] = 'unique-username'
        else:
            self.widget.attrs['class'] = 'simple-username'
        
    def clean(self,value):        
        value = super(UsernameField,self).clean(value)
        if not self.unique: return value         
        try:            
            user = User.objects.get(username__iexact=value)
        except User.DoesNotExist:
            return value
        raise forms.ValidationError('"%s" is not available'%value)
                
        
class UniqueEmailField(forms.EmailField):
    
    def __init__(self,*args,**kwargs):
        kwargs.setdefault('widget',forms.TextInput(attrs={'size':'24'}))
        super(UniqueEmailField,self).__init__(*args,**kwargs)
        self.widget.attrs['class'] = 'unique-email email'
    
    def clean(self,*args,**kwargs):            
        value = super(UniqueEmailField,self).clean(*args,**kwargs)            
        try:            
            user = User.objects.get(email__iexact=value.lower())
        except User.DoesNotExist:
            return value
        raise forms.ValidationError("This email (%s) is already registered."%value)        
    
    
class PasswordField(forms.CharField):
    
    min_length = 8
    help_text = 'Should be atleast %s chars in length and must contain a digit'
     
    def __init__(self,*args,**kwargs):
        defaults = dict(label="Password",widget=forms.PasswordInput(attrs={'size':'16'}),max_length=128,help_text='')
        defaults.update(kwargs)
        self.min_length = kwargs.pop("min_length",self.min_length)
        super(PasswordField,self).__init__(*args,**defaults)

    def clean(self,*args,**kwargs):
        value = super(PasswordField,self).clean(*args,**kwargs)
        if len(value) < self.min_length : 
            raise forms.ValidationError('Passwords need to be atleast %s characters long'%self.min_length)
        return value
    
    
class PasswordConfirmField(forms.CharField):
    def __init__(self,*args,**kwargs):
        defaults = dict(label="Password (confirm)",widget=forms.PasswordInput(attrs={'size':'16'}),max_length=128)
        defaults.update(kwargs)
        super(PasswordConfirmField,self).__init__(*args,**defaults)
    
    @staticmethod
    def confirm():
        def clean(self):
            value2 = self.cleaned_data['password2']
            if 'password1' not in self.cleaned_data: return value2
            value = self.cleaned_data['password1']        
            if value != value2: raise forms.ValidationError("Passwords donot match")
            return value2
        return clean


class DOBField(forms.DateField):
    
    min_age = 0
    
    def __init__(self,*args,**kwargs):
        today = date.today()
        defaults = dict(label="Date of Birth",
            initial=today,
            widget=SelectDateWidget(years=range(1900,today.year+1))
        )
        defaults.update(kwargs)
        self.min_age = kwargs.pop('min_age',self.min_age)
        super(DOBField,self).__init__(*args,**defaults)
            
    def clean(self,*args,**kwargs):
        value = super(DOBField,self).clean(*args,**kwargs)
        age = self.calculate_age(value)
        if self.min_age and age < self.min_age:
            raise forms.ValidationError("You need to be atleast %s years to register"%self.min_age)
        return value           
        
    def calculate_age(self,born):
        today = date.today()
        try: # raised when birth date is February 29 and the current year is not a leap year
            birthday = born.replace(year=today.year)
        except ValueError:
            birthday = born.replace(year=today.year, day=born.day-1)
        if birthday > today:
            return today.year - born.year - 1
        else:
            return today.year - born.year


class NameField(forms.RegexField):
        
    def __init__(self,*args,**kwargs):
        defaults = dict(
            max_length=32,
            regex=r'[A-Za-z]+',
            error_messages = { 'invalid': 'Digits or special characters not allowed'  }
        )
        defaults.update(kwargs)
        super(NameField,self).__init__(*args,**defaults)                    


class RadioSelectNotNull(forms.RadioSelect):
    def get_renderer(self, name, value, attrs=None, choices=()):
        """Returns an instance of the renderer."""
        if value is None: value = ''
        str_value = force_unicode(value) # Normalize to string.
        final_attrs = self.build_attrs(attrs)
        choices = list(chain(self.choices, choices))
        if choices[0][0] == '':
            choices.pop(0)
        return self.renderer(name, str_value, final_attrs, choices)

    
                  