import datetime
import json
import logging
import random
import string
import sys
import uuid
import feedparser
import urllib
import itertools
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.core.mail import send_mail
from django.core.validators import validate_email, validate_slug, ValidationError
from django.db import IntegrityError
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from mitxmako.shortcuts import render_to_response, render_to_string
from django.core.urlresolvers import reverse
from BeautifulSoup import BeautifulSoup
from django.core.cache import cache

from django_future.csrf import ensure_csrf_cookie
from student.models import Registration, UserProfile, PendingNameChange, PendingEmailChange, CourseEnrollment
from util.cache import cache_if_anonymous 
from xmodule.course_module import CourseDescriptor
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError

from models import Registration, UserProfile, PendingNameChange, PendingEmailChange, CourseEnrollment
from datetime import date

log = logging.getLogger("mitx.student")


def csrf_token(context):
    ''' A csrf token that can be included in a form.
    '''
    csrf_token = context.get('csrf_token', '')
    if csrf_token == 'NOTPROVIDED':
        return ''
    return u'<div style="display:none"><input type="hidden" name="csrfmiddlewaretoken" value="%s" /></div>' % (csrf_token)


@ensure_csrf_cookie
@cache_if_anonymous
def index(request):

    ''' Redirects to main page -- info page if user authenticated, or marketing if not
    '''

    if settings.COURSEWARE_ENABLED and request.user.is_authenticated():
        return redirect(reverse('dashboard'))

    feed_data = cache.get("students_index_rss_feed_data")
    if feed_data == None:
        if hasattr(settings, 'RSS_URL'):
            feed_data = urllib.urlopen(settings.RSS_URL).read()
        else:
            feed_data = render_to_string("feed.rss", None)
        cache.set("students_index_rss_feed_data", feed_data, settings.RSS_TIMEOUT)

    feed = feedparser.parse(feed_data)
    entries = feed['entries'][0:3]
    for entry in entries:
        soup = BeautifulSoup(entry.description)
        entry.image = soup.img['src'] if soup.img else None

    courses = modulestore().get_courses()
    universities = defaultdict(list)
    for university, group in itertools.groupby(courses, lambda course: course.org):
        [universities[university].append(course) for course in group]

    return render_to_response('index.html', {'universities': universities, 'entries': entries})

def course_from_id(id):
    course_loc = CourseDescriptor.id_to_location(id)
    return modulestore().get_item(course_loc)

@login_required
@ensure_csrf_cookie
def dashboard(request):
    user = request.user
    enrollments = CourseEnrollment.objects.filter(user=user)

    # Build our courses list for the user, but ignore any courses that no longer
    # exist (because the course IDs have changed). Still, we don't delete those
    # enrollments, because it could have been a data push snafu.
    courses = []
    for enrollment in enrollments:
        try:
            courses.append(course_from_id(enrollment.course_id))
        except ItemNotFoundError:
            log.error("User {0} enrolled in non-existant course {1}"
                      .format(user.username, enrollment.course_id))
    
    
    message = ""
    if not user.is_active:
        message = render_to_string('registration/activate_account_notice.html', {'email': user.email})

    context = {'courses': courses, 'message' : message}
    return render_to_response('dashboard.html', context)


def try_change_enrollment(request):
    """
    This method calls change_enrollment if the necessary POST 
    parameters are present, but does not return anything. It
    simply logs the result or exception. This is usually
    called after a registration or login, as secondary action.
    It should not interrupt a successful registration or login.
    """
    if 'enrollment_action' in request.POST:
        try:
            enrollment_output = change_enrollment(request)
            # There isn't really a way to display the results to the user, so we just log it
            # We expect the enrollment to be a success, and will show up on the dashboard anyway
            log.info("Attempted to automatically enroll after login. Results: {0}".format(enrollment_output))
        except Exception, e:
            log.error("Exception automatically enrolling after login: {0}".format(str(e)))
    

@login_required
def change_enrollment_view(request):
    return HttpResponse(json.dumps(change_enrollment(request)))

def change_enrollment(request):
    if request.method != "POST":
        raise Http404
    
    action = request.POST.get("enrollment_action" , "")
    user = request.user
    course_id = request.POST.get("course_id", None)
    if course_id == None:
        return HttpResponse(json.dumps({'success': False, 'error': 'There was an error receiving the course id.'}))
        
    if action == "enroll":
        # Make sure the course exists
        # We don't do this check on unenroll, or a bad course id can't be unenrolled from
        try:
            course = course_from_id(course_id)
        except ItemNotFoundError:
            log.error("User {0} tried to enroll in non-existant course {1}"
                      .format(user.username, enrollment.course_id))
            return {'success': False, 'error': 'The course requested does not exist.'}
                
        enrollment, created = CourseEnrollment.objects.get_or_create(user=user, course_id=course.id)
        return {'success': True}
        
    elif action == "unenroll":
        try:
            enrollment =  CourseEnrollment.objects.get(user=user, course_id=course_id)
            enrollment.delete()
            return {'success': True}
        except CourseEnrollment.DoesNotExist:
            return {'success': False, 'error': 'You are not enrolled for this course.'}
    else:
        return {'success': False, 'error': 'Invalid enrollment_action.'}
    
    return {'success': False, 'error': 'We weren\'t able to unenroll you. Please try again.'}

# Need different levels of logging
@ensure_csrf_cookie
def login_user(request, error=""):
    ''' AJAX request to log in the user. '''
    if 'email' not in request.POST or 'password' not in request.POST:
        return HttpResponse(json.dumps({'success': False,
                                        'value': 'There was an error receiving your login information. Please email us.'}))  # TODO: User error message

    email = request.POST['email']
    password = request.POST['password']
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        log.warning("Login failed - Unknown user email: {0}".format(email))
        return HttpResponse(json.dumps({'success': False,
                                        'value': 'Email or password is incorrect.'}))  # TODO: User error message

    username = user.username
    user = authenticate(username=username, password=password)
    if user is None:
        log.warning("Login failed - password for {0} is invalid".format(email))
        return HttpResponse(json.dumps({'success': False,
                                        'value': 'Email or password is incorrect.'}))

    if user is not None and user.is_active:
        try:
            login(request, user)
            if request.POST.get('remember') == 'true':
                request.session.set_expiry(None) # or change to 604800 for 7 days
                log.debug("Setting user session to never expire")
            else:
                request.session.set_expiry(0)
        except Exception as e:
            log.critical("Login failed - Could not create session. Is memcached running?")
            log.exception(e)

        log.info("Login success - {0} ({1})".format(username, email))
        
        try_change_enrollment(request)
        
        return HttpResponse(json.dumps({'success':True}))

    log.warning("Login failed - Account not active for user {0}".format(username))
    return HttpResponse(json.dumps({'success':False,
                                    'value': 'This account has not been activated. Please check your e-mail for the activation instructions.'}))

@ensure_csrf_cookie
def logout_user(request):
    ''' HTTP request to log out the user. Redirects to marketing page'''
    logout(request)
    return redirect('/')

@login_required
@ensure_csrf_cookie
def change_setting(request):
    ''' JSON call to change a profile setting: Right now, location
    '''
    up = UserProfile.objects.get(user=request.user) #request.user.profile_cache
    if 'location' in request.POST:
        up.location=request.POST['location']
    up.save()

    return HttpResponse(json.dumps({'success':True,
                                    'location':up.location,}))

@ensure_csrf_cookie
def create_account(request, post_override=None):
    ''' JSON call to enroll in the course. '''
    js={'success':False}

    post_vars = post_override if post_override else request.POST

    # Confirm we have a properly formed request
    for a in ['username', 'email', 'password', 'name']:
        if a not in post_vars:
            js['value'] = "Error (401 {field}). E-mail us.".format(field=a)
            return HttpResponse(json.dumps(js))

    if post_vars.get('honor_code', 'false') != u'true':
        js['value']="To enroll, you must follow the honor code.".format(field=a)
        return HttpResponse(json.dumps(js))


    if post_vars.get('terms_of_service', 'false') != u'true':
        js['value']="You must accept the terms of service.".format(field=a)
        return HttpResponse(json.dumps(js))

    # Confirm appropriate fields are there.
    # TODO: Check e-mail format is correct.
    # TODO: Confirm e-mail is not from a generic domain (mailinator, etc.)? Not sure if
    # this is a good idea
    # TODO: Check password is sane
    for a in ['username', 'email', 'name', 'password', 'terms_of_service', 'honor_code']:
        if len(post_vars[a]) < 2:
            error_str = {'username' : 'Username of length 2 or greater',
                         'email' : 'Properly formatted e-mail',
                         'name' : 'Your legal name ',
                         'password': 'Valid password ',
                         'terms_of_service': 'Accepting Terms of Service',
                         'honor_code': 'Agreeing to the Honor Code'}
            js['value']="{field} is required.".format(field=error_str[a])
            return HttpResponse(json.dumps(js))

    try:
        validate_email(post_vars['email'])
    except ValidationError:
        js['value']="Valid e-mail is required.".format(field=a)
        return HttpResponse(json.dumps(js))

    try:
        validate_slug(post_vars['username'])
    except ValidationError:
        js['value']="Username should only consist of A-Z and 0-9.".format(field=a)
        return HttpResponse(json.dumps(js))

    u = User(username=post_vars['username'],
             email=post_vars['email'],
             is_active=False)
    u.set_password(post_vars['password'])
    r = Registration()
    # TODO: Rearrange so that if part of the process fails, the whole process fails.
    # Right now, we can have e.g. no registration e-mail sent out and a zombie account
    try:
        u.save()
    except IntegrityError:
        # Figure out the cause of the integrity error
        if len(User.objects.filter(username=post_vars['username'])) > 0:
            js['value'] = "An account with this username already exists."
            return HttpResponse(json.dumps(js))

        if len(User.objects.filter(email=post_vars['email'])) > 0:
            js['value'] = "An account with this e-mail already exists."
            return HttpResponse(json.dumps(js))

        raise

    r.register(u)

    up = UserProfile(user=u)
    up.name = post_vars['name']
    up.country = post_vars['country']
    up.gender = post_vars['gender']
    up.mailing_address = post_vars['mailing_address']

    date_fields = ['date_of_birth__year', 'date_of_birth__month', 'date_of_birth__day']
    if all(len(post_vars[field]) > 0 for field in date_fields):
        up.date_of_birth = date(int(post_vars['date_of_birth__year']),
                int(post_vars['date_of_birth__month']),
                int(post_vars['date_of_birth__day']))

    up.save()
    
    d = {'name': post_vars['name'],
         'key': r.activation_key,
         }

    subject = render_to_string('emails/activation_email_subject.txt', d)
        # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/activation_email.txt', d)

    try:
        if settings.MITX_FEATURES.get('REROUTE_ACTIVATION_EMAIL'):
            dest_addr = settings.MITX_FEATURES['REROUTE_ACTIVATION_EMAIL']
            message = "Activation for %s (%s): %s\n" % (u,u.email,up.name) + '-' * 80 + '\n\n' + message
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [dest_addr], fail_silently=False)
        elif not settings.GENERATE_RANDOM_USER_CREDENTIALS:
            res = u.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)
    except:
        log.exception(sys.exc_info())
        js['value'] = 'Could not send activation e-mail.'
        return HttpResponse(json.dumps(js))
     
    # Immediately after a user creates an account, we log them in. They are only
    # logged in until they close the browser. They can't log in again until they click
    # the activation link from the email.
    login_user = authenticate(username=post_vars['username'], password = post_vars['password'] )
    login(request, login_user)
    request.session.set_expiry(0)  
    
    try_change_enrollment(request)
    
    js={'success': True}
    return HttpResponse(json.dumps(js), mimetype="application/json")

def create_random_account(create_account_function):

    def id_generator(size=6, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    def inner_create_random_account(request):
        post_override= {'username' : "random_" + id_generator(),
                            'email' : id_generator(size=10, chars=string.ascii_lowercase) + "_dummy_test@mitx.mit.edu",
                            'password' : id_generator(),
                            'location' : id_generator(size=5, chars=string.ascii_uppercase),
                            'name' : id_generator(size=5, chars=string.ascii_lowercase) + " " + id_generator(size=7, chars=string.ascii_lowercase),
                            'honor_code' : u'true',
                            'terms_of_service' : u'true',}

        return create_account_function(request, post_override = post_override)

    return inner_create_random_account

if settings.GENERATE_RANDOM_USER_CREDENTIALS:
    create_account = create_random_account(create_account)

@ensure_csrf_cookie
def activate_account(request, key):
    ''' When link in activation e-mail is clicked
    '''
    r=Registration.objects.filter(activation_key=key)
    if len(r)==1:
        user_logged_in = request.user.is_authenticated()
        already_active = True
        if not r[0].user.is_active:
            r[0].activate()
            already_active = False
        resp = render_to_response("registration/activation_complete.html",{'user_logged_in':user_logged_in, 'already_active' : already_active})
        return resp
    if len(r)==0:
        return render_to_response("registration/activation_invalid.html",{'csrf':csrf(request)['csrf_token']})
    return HttpResponse("Unknown error. Please e-mail us to let us know how it happened.")

@ensure_csrf_cookie
def password_reset(request):
    ''' Attempts to send a password reset e-mail. '''
    if request.method != "POST":
        raise Http404
    form = PasswordResetForm(request.POST)
    if form.is_valid():
        form.save( use_https = request.is_secure(),
                   from_email = settings.DEFAULT_FROM_EMAIL,
                   request = request )
        return HttpResponse(json.dumps({'success':True,
                                        'value': render_to_string('registration/password_reset_done.html', {})}))
    else:
        return HttpResponse(json.dumps({'success':False,
                                        'error': 'Invalid e-mail'}))

@ensure_csrf_cookie
def reactivation_email(request):
    ''' Send an e-mail to reactivate a deactivated account, or to
    resend an activation e-mail. Untested. '''
    email = request.POST['email']
    try:
        user = User.objects.get(email = 'email')
    except User.DoesNotExist:
        return HttpResponse(json.dumps({'success':False,
                                        'error': 'No inactive user with this e-mail exists'}))

    if user.is_active:
        return HttpResponse(json.dumps({'success':False,
                                        'error': 'User is already active'}))

    reg = Registration.objects.get(user = user)
    reg.register(user)

    d={'name':UserProfile.get(user = user).name,
       'key':r.activation_key}

    subject = render_to_string('reactivation_email_subject.txt',d)
    subject = ''.join(subject.splitlines())
    message = render_to_string('reactivation_email.txt',d)

    res=u.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)

    return HttpResponse(json.dumps({'success':True}))


@ensure_csrf_cookie
def change_email_request(request):
    ''' AJAX call from the profile page. User wants a new e-mail.
    '''
    ## Make sure it checks for existing e-mail conflicts
    if not request.user.is_authenticated:
        raise Http404

    user = request.user

    if not user.check_password(request.POST['password']):
        return HttpResponse(json.dumps({'success':False,
                                        'error':'Invalid password'}))

    new_email = request.POST['new_email']
    try:
        validate_email(new_email)
    except ValidationError:
        return HttpResponse(json.dumps({'success':False,
                                        'error':'Valid e-mail address required.'}))

    if len(User.objects.filter(email = new_email)) != 0:
        ## CRITICAL TODO: Handle case sensitivity for e-mails
        return HttpResponse(json.dumps({'success':False,
                                        'error':'An account with this e-mail already exists.'}))

    pec_list = PendingEmailChange.objects.filter(user = request.user)
    if len(pec_list) == 0:
        pec = PendingEmailChange()
        pec.user = user
    else :
        pec = pec_list[0]

    pec.new_email = request.POST['new_email']
    pec.activation_key = uuid.uuid4().hex
    pec.save()

    if pec.new_email == user.email:
        pec.delete()
        return HttpResponse(json.dumps({'success':False,
                                        'error':'Old email is the same as the new email.'}))

    d = {'key':pec.activation_key,
         'old_email' : user.email,
         'new_email' : pec.new_email}

    subject = render_to_string('emails/email_change_subject.txt',d)
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/email_change.txt',d)

    res=send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [pec.new_email])

    return HttpResponse(json.dumps({'success':True}))

@ensure_csrf_cookie
def confirm_email_change(request, key):
    ''' User requested a new e-mail. This is called when the activation
    link is clicked. We confirm with the old e-mail, and update
    '''
    try:
        pec=PendingEmailChange.objects.get(activation_key=key)
    except PendingEmailChange.DoesNotExist:
        return render_to_response("invalid_email_key.html", {})

    user = pec.user
    d = {'old_email' : user.email,
         'new_email' : pec.new_email}

    if len(User.objects.filter(email = pec.new_email)) != 0:
        return render_to_response("email_exists.html", d)


    subject = render_to_string('emails/email_change_subject.txt',d)
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/confirm_email_change.txt',d)
    up = UserProfile.objects.get( user = user )
    meta = up.get_meta()
    if 'old_emails' not in meta:
        meta['old_emails'] = []
    meta['old_emails'].append([user.email, datetime.datetime.now().isoformat()])
    up.set_meta(meta)
    up.save()
    user.email = pec.new_email
    user.save()
    pec.delete()
    user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)

    return render_to_response("email_change_successful.html", d)

@ensure_csrf_cookie
def change_name_request(request):
    ''' Log a request for a new name. '''
    if not request.user.is_authenticated:
        raise Http404

    try:
        pnc = PendingNameChange.objects.get(user = request.user)
    except PendingNameChange.DoesNotExist:
        pnc = PendingNameChange()
    pnc.user = request.user
    pnc.new_name = request.POST['new_name']
    pnc.rationale = request.POST['rationale']
    if len(pnc.new_name)<2:
        return HttpResponse(json.dumps({'success':False,'error':'Name required'}))
    if len(pnc.rationale)<2:
        return HttpResponse(json.dumps({'success':False,'error':'Rationale required'}))
    pnc.save()
    return HttpResponse(json.dumps({'success':True}))


@ensure_csrf_cookie
def pending_name_changes(request):
    ''' Web page which allows staff to approve or reject name changes. '''
    if not request.user.is_staff:
        raise Http404

    changes = list(PendingNameChange.objects.all())
    js = {'students': [{'new_name': c.new_name,
                        'rationale':c.rationale,
                        'old_name':UserProfile.objects.get(user=c.user).name,
                        'email':c.user.email,
                        'uid':c.user.id,
                        'cid':c.id} for c in changes]}
    return render_to_response('name_changes.html', js)


@ensure_csrf_cookie
def reject_name_change(request):
    ''' JSON: Name change process. Course staff clicks 'reject' on a given name change '''
    if not request.user.is_staff:
        raise Http404

    try:
        pnc = PendingNameChange.objects.get(id=int(request.POST['id']))
    except PendingNameChange.DoesNotExist:
        return HttpResponse(json.dumps({'success': False, 'error': 'Invalid ID'}))

    pnc.delete()
    return HttpResponse(json.dumps({'success': True}))


@ensure_csrf_cookie
def accept_name_change(request):
    ''' JSON: Name change process. Course staff clicks 'accept' on a given name change '''
    if not request.user.is_staff:
        raise Http404

    try:
        pnc = PendingNameChange.objects.get(id=int(request.POST['id']))
    except PendingNameChange.DoesNotExist:
        return HttpResponse(json.dumps({'success': False, 'error': 'Invalid ID'}))

    u = pnc.user
    up = UserProfile.objects.get(user=u)

    # Save old name
    meta = up.get_meta()
    if 'old_names' not in meta:
        meta['old_names'] = []
    meta['old_names'].append([up.name, pnc.rationale, datetime.datetime.now().isoformat()])
    up.set_meta(meta)

    up.name = pnc.new_name
    up.save()
    pnc.delete()

    return HttpResponse(json.dumps({'success': True}))

