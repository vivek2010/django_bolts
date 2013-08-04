import re
from datetime import date
from calendar import monthrange, IllegalMonthError
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


CREDIT_CARD_RE = r'^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\\d{3})\d{11})$'
MONTH_FORMAT = getattr(settings, 'MONTH_FORMAT', '%b')
VERIFICATION_VALUE_RE = r'^([0-9]{3,4})$'

__all__ = ['PaymentForm']

class CreditCardField(forms.CharField):
    """
    Form field that validates credit card numbers.
    """

    default_error_messages = {
        'required': _(u'Please enter a credit card number.'),
        'invalid': _(u'The credit card number you entered is invalid.'),
    }
    
    def get_cc_type(self, number):
        """
        Gets credit card type given number. Based on values from Wikipedia page
        "Credit card number".
        <a href="http://en.wikipedia.org/w/index.php?title=Credit_card_number<br />
    " title="http://en.wikipedia.org/w/index.php?title=Credit_card_number<br />
    ">http://en.wikipedia.org/w/index.php?title=Credit_card_number<br />
    </a>    """
        number = str(number)
        #group checking by ascending length of number
        if len(number) == 13:
            if number[0] == "4":
                return "Visa"
        elif len(number) == 14:
            if number[:2] == "36":
                return "MasterCard"
        elif len(number) == 15:
            if number[:2] in ("34", "37"):
                return "American Express"
        elif len(number) == 16:
            if number[:4] == "6011":
                return "Discover"
            if number[:2] in ("51", "52", "53", "54", "55"):
                return "MasterCard"
            if number[0] == "4":
                return "Visa"
        return "Unknown"    

    def clean(self, value):
        value = value.replace(' ', '').replace('-', '')
        if self.required and not value:
            raise forms.util.ValidationError(self.error_messages['required'])
        if value and not re.match(CREDIT_CARD_RE, value):
            raise forms.util.ValidationError(self.error_messages['invalid'])
        if value and (len(value) < 13 or len(value) > 16):
            raise forms.ValidationError("Please enter in a valid credit card number.")
        elif self.get_cc_type(value) not in ("Visa", "MasterCard","American Express", "Discover"):    
            raise forms.ValidationError("Please enter in a Visa, "+\
              "Master Card, Discover, or American Express credit card number.")        
        return super(CreditCardField, self).clean(value)    


class ExpiryDateWidget(forms.MultiWidget):
    """
    Widget containing two select boxes for selecting the month and year.
    """

    def decompress(self, value):
        return [value.month, value.year] if value else [None, None]

    def format_output(self, rendered_widgets):
        return u'<div class="expirydatefield">%s</div>' % ' '.join(rendered_widgets)


class ExpiryDateField(forms.MultiValueField):
    """
    Form field that validates credit card expiry dates.
    """

    default_error_messages = {
        'invalid_month': _(u'Please enter a valid month.'),
        'invalid_year': _(u'Please enter a valid year.'),
        'date_passed': _(u'This expiry date has passed.'),
    }

    def __init__(self, *args, **kwargs):
        today = date.today()
        error_messages = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            error_messages.update(kwargs['error_messages'])
        if 'initial' not in kwargs:
            # Set default expiry date based on current month and year
            kwargs['initial'] = today
#        months = [(x, '%02d (%s)' % (x, date(2000, x, 1).strftime(MONTH_FORMAT))) for x in xrange(1, 13)]
        months = [ (x, '%02d' % (x,)) for x in xrange(1, 13) ]
        years = [(x, x) for x in xrange(today.year, today.year + 15)]
        fields = (
            forms.ChoiceField(choices=months, error_messages={'invalid': error_messages['invalid_month']}),
            forms.ChoiceField(choices=years, error_messages={'invalid': error_messages['invalid_year']}),
        )
        super(ExpiryDateField, self).__init__(fields, *args, **kwargs)
        self.widget = ExpiryDateWidget(widgets=[fields[0].widget, fields[1].widget])

    def clean(self, value):
        expiry_date = super(ExpiryDateField, self).clean(value)
        if date.today() > expiry_date:
            raise forms.ValidationError(self.error_messages['date_passed'])
        return expiry_date

    def compress(self, data_list):
        if data_list:
            try:
                month = int(data_list[0])
            except (ValueError, TypeError):
                raise forms.ValidationError(self.error_messages['invalid_month'])
            try:
                year = int(data_list[1])
            except (ValueError, TypeError):
                raise forms.ValidationError(self.error_messages['invalid_year'])
            try:
                day = monthrange(year, month)[1] # last day of the month
            except IllegalMonthError:
                raise forms.ValidationError(self.error_messages['invalid_month'])
            except ValueError:
                raise forms.ValidationError(self.error_messages['invalid_year'])
            return date(year, month, day)
        return None


class VerificationValueField(forms.CharField):
    """
    Form field that validates credit card verification values (e.g. CVV2).
    See http://en.wikipedia.org/wiki/Card_Security_Code
    """

    widget = forms.TextInput(attrs={'maxlength': 4})
    default_error_messages = {
        'required': _(u'Please enter the three- or four-digit verification code for your credit card.'),
        'invalid': _(u'The verification value you entered is invalid.'),
    }

    def clean(self, value):
        value = value.replace(' ', '')
        if not value and self.required:
            raise forms.util.ValidationError(self.error_messages['required'])
        if value and not re.match(VERIFICATION_VALUE_RE, value):
            raise forms.util.ValidationError(self.error_messages['invalid'])
        return value

class SplitNameWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [forms.TextInput, forms.TextInput]
        super(SplitNameWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split(" ",1)
        return [None, None]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)
        
    

class PaymentForm(forms.Form):
        
    CARD_TYPES = (
        (1,'Visa'),
        (2,'Mastercard'),
        (3,'Discover'),
        (4,'American Express'),
    )    
    
    TOS = """By completing this transaction you certify that you are 18 years or older and agree to the <a href='/tos/'>Terms and Conditions</a> of this purchase <a href='/privacy_policy/'>Privacy Policy</a>    """

    name = forms.CharField(label="First/Last name",max_length=32,widget=SplitNameWidget(attrs={'size':'14'}),required=True)
    address = forms.CharField(label="Zip/postal code",max_length=64,widget=forms.TextInput(attrs={'style':'width:6em;'}))
    value = CreditCardField(label="Card Number",widget=forms.TextInput(attrs={'style':'width:16em;'}))
    kind = forms.ChoiceField(choices=CARD_TYPES,label="Select Card Type")
    cvv = VerificationValueField(label="CVV2",widget=forms.TextInput(attrs={'style':'width:3em'}))    
    expiry_date = ExpiryDateField(label="Expiry")
    tos = forms.BooleanField(label = TOS,initial=False,required=False)
    
    def clean_tos(self):
        value = self.cleaned_data['tos']
        if not value:
            raise forms.ValidationError("You must agree to our terms of services")
        return value 
    
