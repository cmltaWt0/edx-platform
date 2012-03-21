"""
WE'RE USING MIGRATIONS!

If you make changes to this model, be sure to create an appropriate migration
file and check it in at the same time as your model changes. To do that,

1. Go to the mitx dir
2. ./manage.py schemamigration user --auto description_of_your_change
3. Add the migration file created in mitx/courseware/migrations/
"""
import uuid

from django.db import models
from django.contrib.auth.models import User
import json

#from cache_toolbox import cache_model, cache_relation

class UserProfile(models.Model):
    class Meta:
        db_table = "auth_userprofile"

    ## CRITICAL TODO/SECURITY
    # Sanitize all fields. 
    # This is not visible to other users, but could introduce holes later
    user = models.OneToOneField(User, unique=True, db_index=True, related_name='profile')
    name = models.CharField(blank=True, max_length=255, db_index=True)
    language = models.CharField(blank=True, max_length=255, db_index=True)
    location = models.CharField(blank=True, max_length=255, db_index=True)
    meta = models.CharField(blank=True, max_length=255) # JSON dictionary for future expansion
    courseware = models.CharField(blank=True, max_length=255, default='course.xml')

    def get_meta(self):
        try: 
            js = json.reads(self.meta)
        except:
            js = dict()
        return js

    def set_meta(self,js):
        self.meta = json.dumps(js)

## TODO: Should be renamed to generic UserGroup, and possibly
# Given an optional field for type of group
class UserTestGroup(models.Model):
    users = models.ManyToManyField(User, db_index=True)
    name = models.CharField(blank=False, max_length=32, db_index=True)
    description = models.TextField(blank=True)

class Registration(models.Model):
    ''' Allows us to wait for e-mail before user is registered. A
        registration profile is created when the user creates an 
        account, but that account is inactive. Once the user clicks
        on the activation key, it becomes active. '''
    class Meta:
        db_table = "auth_registration"

    user = models.ForeignKey(User, unique=True)
    activation_key = models.CharField(('activation key'), max_length=32, unique=True, db_index=True)

    def register(self, user):
        # MINOR TODO: Switch to crypto-secure key
        self.activation_key=uuid.uuid4().hex
        self.user=user
        self.save()

    def activate(self):
        self.user.is_active = True
        self.user.save()
        #self.delete()

class PendingNameChange(models.Model):
    user = models.OneToOneField(User, unique=True, db_index=True)
    new_name = models.CharField(blank=True, max_length=255)
    rationale = models.CharField(blank=True, max_length=1024)

class PendingEmailChange(models.Model):
    user = models.OneToOneField(User, unique=True, db_index=True)
    new_email = models.CharField(blank=True, max_length=255, db_index=True)
    activation_key = models.CharField(('activation key'), max_length=32, unique=True, db_index=True)

#cache_relation(User.profile)

#### Helper methods for use from python manage.py shell. 

def get_user(email):
    u = User.objects.get(email = email)
    up = UserProfile.objects.get(user = u)
    return u,up

def user_info(email):
    u,up = get_user(email)
    print "User id", u.id
    print "Username", u.username
    print "E-mail", u.email
    print "Name", up.name
    print "Location", up.location
    print "Language", up.language
    return u,up

def change_email(old_email, new_email):
    u = User.objects.get(email = old_email)
    u.email = new_email
    u.save()

def change_name(email, new_name):
    u,up = get_user(email)
    up.name = new_name
    up.save()

def user_count():
    print "All users", User.objects.all().count()
    print "Active users", User.objects.filter(is_active = True).count()
    return User.objects.all().count()

def active_user_count():
    return User.objects.filter(is_active = True).count()

def create_group(name, description):
    utg = UserTestGroup()
    utg.name = name
    utg.description = description
    utg.save()

def add_user_to_group(group, user):
    utg = UserTestGroup.objects.get(name = group)
    utg.users.add(User.objects.get(username = user))
    utg.save()

def remove_user_from_group(group, user):
    utg = UserTestGroup.objects.get(name = group)
    utg.users.remove(User.objects.get(username = user))
    utg.save()

def add_user_to_default_group(group, description, user):
    utg = UserTestGroup.objects.get(name = group)
    utg.users.add(User.objects.get(username = user))
    utg.save()

