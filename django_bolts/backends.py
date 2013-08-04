from django.contrib.auth.models import User, check_password
from django.contrib.auth.backends import ModelBackend
 
class CaseInsensitiveBackend(ModelBackend):
  """
  By default ModelBackend does case _sensitive_ username authentication, which isn't what is
  generally expected.  This backend supports case insensitive username authentication.
  """
  def authenticate(self, username=None, password=None):
    try:
      user = User.objects.get(username__iexact=username)
      if user.check_password(password):
        return user
      else:
        return None
    except User.DoesNotExist:
      return None

class EmailAuthBackend(object):
    """
    Email Authentication Backend
    
    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
    """
    
    def authenticate(self, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        try:
            user = User.objects.get(email__iexact=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None 

    def get_user(self, user_id):
        """ Get a User object from the user_id. """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None