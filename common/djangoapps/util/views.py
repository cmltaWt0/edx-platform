import json
import logging
import sys
import boto
import urllib2
import requests
import ssl
import string
import os
import sys
import re
import tempfile
from functools import wraps

from django.conf import settings
from django.core.cache import caches
from django.core.validators import ValidationError, validate_email
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import server_error
from django.http import (Http404, HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect,
                         HttpResponseServerError)
import dogstats_wrapper as dog_stats_api
from edxmako.shortcuts import render_to_response
import zendesk
from microsite_configuration import microsite

import calc
import track.views

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

log = logging.getLogger(__name__)


def ensure_valid_course_key(view_func):
    """
    This decorator should only be used with views which have argument course_key_string (studio) or course_id (lms).
    If course_key_string (studio) or course_id (lms) is not valid raise 404.
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        course_key = kwargs.get('course_key_string') or kwargs.get('course_id')
        if course_key is not None:
            try:
                CourseKey.from_string(course_key)
            except InvalidKeyError:
                raise Http404

        response = view_func(request, *args, **kwargs)
        return response

    return inner


@requires_csrf_token
def jsonable_server_error(request, template_name='500.html'):
    """
    500 error handler that serves JSON on an AJAX request, and proxies
    to the Django default `server_error` view otherwise.
    """
    if request.is_ajax():
        msg = {"error": "The edX servers encountered an error"}
        return HttpResponseServerError(json.dumps(msg))
    else:
        return server_error(request, template_name=template_name)


def handle_500(template_path, context=None, test_func=None):
    """
    Decorator for view specific 500 error handling.
    Custom handling will be skipped only if test_func is passed and it returns False

    Usage:

        @handle_500(
            template_path='certificates/server-error.html',
            context={'error-info': 'Internal Server Error'},
            test_func=lambda request: request.GET.get('preview', None)
        )
        def my_view(request):
            # Any unhandled exception in this view would be handled by the handle_500 decorator
            # ...

    """
    def decorator(func):
        """
        Decorator to render custom html template in case of uncaught exception in wrapped function
        """
        @wraps(func)
        def inner(request, *args, **kwargs):
            """
            Execute the function in try..except block and return custom server-error page in case of unhandled exception
            """
            try:
                return func(request, *args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                if settings.DEBUG:
                    # In debug mode let django process the 500 errors and display debug info for the developer
                    raise
                elif test_func is None or test_func(request):
                    # Display custom 500 page if either
                    #   1. test_func is None (meaning nothing to test)
                    #   2. or test_func(request) returns True
                    log.exception("Error in django view.")
                    return render_to_response(template_path, context)
                else:
                    # Do not show custom 500 error when test fails
                    raise
        return inner
    return decorator


def calculate(request):
    ''' Calculator in footer of every page. '''
    equation = request.GET['equation']
    try:
        result = calc.evaluator({}, {}, equation)
    except:
        event = {'error': map(str, sys.exc_info()),
                 'equation': equation}
        track.views.server_track(request, 'error:calc', event, page='calc')
        return HttpResponse(json.dumps({'result': 'Invalid syntax'}))
    return HttpResponse(json.dumps({'result': str(result)}))


class _ZendeskApi(object):

    CACHE_PREFIX = 'ZENDESK_API_CACHE'
    CACHE_TIMEOUT = 60 * 60

    def __init__(self):
        """
        Instantiate the Zendesk API.

        All of `ZENDESK_URL`, `ZENDESK_USER`, and `ZENDESK_API_KEY` must be set
        in `django.conf.settings`.
        """
        self._zendesk_instance = zendesk.Zendesk(
            settings.ZENDESK_URL,
            settings.ZENDESK_USER,
            settings.ZENDESK_API_KEY,
            use_api_token=True,
            api_version=2,
            # As of 2012-05-08, Zendesk is using a CA that is not
            # installed on our servers
            client_args={"disable_ssl_certificate_validation": True}
        )

    def create_ticket(self, ticket):
        """
        Create the given `ticket` in Zendesk.

        The ticket should have the format specified by the zendesk package.
        """
        ticket_url = self._zendesk_instance.create_ticket(data=ticket)
        return zendesk.get_id_from_url(ticket_url)

    def update_ticket(self, ticket_id, update):
        """
        Update the Zendesk ticket with id `ticket_id` using the given `update`.

        The update should have the format specified by the zendesk package.
        """
        self._zendesk_instance.update_ticket(ticket_id=ticket_id, data=update)

    def get_group(self, name):
        """
        Find the Zendesk group named `name`. Groups are cached for
        CACHE_TIMEOUT seconds.

        If a matching group exists, it is returned as a dictionary
        with the format specifed by the zendesk package.

        Otherwise, returns None.
        """
        cache = caches['default']
        cache_key = '{prefix}_group_{name}'.format(prefix=self.CACHE_PREFIX, name=name)
        cached = cache.get(cache_key)
        if cached:
            return cached
        groups = self._zendesk_instance.list_groups()['groups']
        for group in groups:
            if group['name'] == name:
                cache.set(cache_key, group, self.CACHE_TIMEOUT)
                return group
        return None


def _record_feedback_in_zendesk(
        realname,
        email,
        subject,
        details,
        tags,
        additional_info,
        group_name=None,
        require_update=False
):
    """
    Create a new user-requested Zendesk ticket.

    Once created, the ticket will be updated with a private comment containing
    additional information from the browser and server, such as HTTP headers
    and user state. Returns a boolean value indicating whether ticket creation
    was successful, regardless of whether the private comment update succeeded.

    If `group_name` is provided, attaches the ticket to the matching Zendesk group.

    If `require_update` is provided, returns False when the update does not
    succeed. This allows using the private comment to add necessary information
    which the user will not see in followup emails from support.
    """
    zendesk_api = _ZendeskApi()

    additional_info_string = (
        u"Additional information:\n\n" +
        u"\n".join(u"%s: %s" % (key, value) for (key, value) in additional_info.items() if value is not None)
    )

    # Tag all issues with LMS to distinguish channel in Zendesk; requested by student support team
    zendesk_tags = list(tags.values()) + ["LMS"]

    # Per edX support, we would like to be able to route white label feedback items
    # via tagging
    white_label_org = microsite.get_value('course_org_filter')
    if white_label_org:
        zendesk_tags = zendesk_tags + ["whitelabel_{org}".format(org=white_label_org)]

    new_ticket = {
        "ticket": {
            "requester": {"name": realname, "email": email},
            "subject": subject,
            "comment": {"body": details},
            "tags": zendesk_tags
        }
    }
    group = None
    if group_name is not None:
        group = zendesk_api.get_group(group_name)
        if group is not None:
            new_ticket['ticket']['group_id'] = group['id']
    try:
        ticket_id = zendesk_api.create_ticket(new_ticket)
        if group_name is not None and group is None:
            # Support uses Zendesk groups to track tickets. In case we
            # haven't been able to correctly group this ticket, log its ID
            # so it can be found later.
            log.warning('Unable to find group named %s for Zendesk ticket with ID %s.', group_name, ticket_id)
    except zendesk.ZendeskError:
        log.exception("Error creating Zendesk ticket")
        return False

    # Additional information is provided as a private update so the information
    # is not visible to the user.
    ticket_update = {"ticket": {"comment": {"public": False, "body": additional_info_string}}}
    try:
        zendesk_api.update_ticket(ticket_id, ticket_update)
    except zendesk.ZendeskError:
        log.exception("Error updating Zendesk ticket with ID %s.", ticket_id)
        # The update is not strictly necessary, so do not indicate
        # failure to the user unless it has been requested with
        # `require_update`.
        if require_update:
            return False
    return True


DATADOG_FEEDBACK_METRIC = "lms_feedback_submissions"


def _record_feedback_in_datadog(tags):
    datadog_tags = [u"{k}:{v}".format(k=k, v=v) for k, v in tags.items()]
    dog_stats_api.increment(DATADOG_FEEDBACK_METRIC, tags=datadog_tags)


def submit_feedback(request):
    """
    Create a new user-requested ticket, currently implemented with Zendesk.

    If feedback submission is not enabled, any request will raise `Http404`.
    If any configuration parameter (`ZENDESK_URL`, `ZENDESK_USER`, or
    `ZENDESK_API_KEY`) is missing, any request will raise an `Exception`.
    The request must be a POST request specifying `subject` and `details`.
    If the user is not authenticated, the request must also specify `name` and
    `email`. If the user is authenticated, the `name` and `email` will be
    populated from the user's information. If any required parameter is
    missing, a 400 error will be returned indicating which field is missing and
    providing an error message. If Zendesk ticket creation fails, 500 error
    will be returned with no body; if ticket creation succeeds, an empty
    successful response (200) will be returned.
    """
    if not settings.FEATURES.get('ENABLE_FEEDBACK_SUBMISSION', False):
        raise Http404()
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if (
        not settings.ZENDESK_URL or
        not settings.ZENDESK_USER or
        not settings.ZENDESK_API_KEY
    ):
        raise Exception("Zendesk enabled but not configured")

    def build_error_response(status_code, field, err_msg):
        return HttpResponse(json.dumps({"field": field, "error": err_msg}), status=status_code)

    additional_info = {}

    required_fields = ["subject", "details"]
    if not request.user.is_authenticated():
        required_fields += ["name", "email"]
    required_field_errs = {
        "subject": "Please provide a subject.",
        "details": "Please provide details.",
        "name": "Please provide your name.",
        "email": "Please provide a valid e-mail.",
    }

    for field in required_fields:
        if field not in request.POST or not request.POST[field]:
            return build_error_response(400, field, required_field_errs[field])

    subject = request.POST["subject"]
    details = request.POST["details"]
    tags = dict(
        [(tag, request.POST[tag]) for tag in ["issue_type", "course_id"] if tag in request.POST]
    )

    if request.user.is_authenticated():
        realname = request.user.profile.name
        email = request.user.email
        additional_info["username"] = request.user.username
    else:
        realname = request.POST["name"]
        email = request.POST["email"]
        try:
            validate_email(email)
        except ValidationError:
            return build_error_response(400, "email", required_field_errs["email"])

    for header, pretty in [
        ("HTTP_REFERER", "Page"),
        ("HTTP_USER_AGENT", "Browser"),
        ("REMOTE_ADDR", "Client IP"),
        ("SERVER_NAME", "Host")
    ]:
        additional_info[pretty] = request.META.get(header)

    success = _record_feedback_in_zendesk(realname, email, subject, details, tags, additional_info)
    _record_feedback_in_datadog(tags)

    return HttpResponse(status=(200 if success else 500))


def info(request):
    ''' Info page (link from main header) '''
    return render_to_response("info.html", {})


# From http://djangosnippets.org/snippets/1042/
def parse_accept_header(accept):
    """Parse the Accept header *accept*, returning a list with pairs of
    (media_type, q_value), ordered by q values.
    """
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0)
        media_params = []
        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, tuple(media_params), q))
    result.sort(lambda x, y: -cmp(x[2], y[2]))
    return result


def accepts(request, media_type):
    """Return whether this request has an Accept header that matches type"""
    accept = parse_accept_header(request.META.get("HTTP_ACCEPT", ""))
    return media_type in [t for (t, p, q) in accept]

def hello(request):
    return HttpResponse('hello')

def sign_cloudfront_url(request):
    import time
    from path import Path as path
    url = request.GET['url']
    url = url.replace(" ", "+");
    SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)
    CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', "/edx/app/edxapp/"))
    CONFIG_PREFIX = SERVICE_VARIANT + "." if SERVICE_VARIANT else ""
    with open(CONFIG_ROOT / CONFIG_PREFIX + "env.json") as env_file:
        ENV_TOKENS = json.load(env_file)
    aws_access_key_id = ENV_TOKENS.get("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = ENV_TOKENS.get("AWS_SECRET_ACCESS_KEY")
    s3 = boto.connect_s3(aws_access_key_id, aws_secret_access_key)
    cf = boto.connect_cloudfront(aws_access_key_id, aws_secret_access_key)
    key_pair_id = ENV_TOKENS.get("SIGNING_KEY_ID")
    priv_key_file = ENV_TOKENS.get("SIGNING_KEY_FILE")
    expires = int(time.time()) + 600
    http_resource = url
    dist = cf.get_all_distributions()[0].get_distribution()
    http_signed_url = dist.create_signed_url(http_resource, key_pair_id, expires, private_key_file=priv_key_file)
#    raise NotImplementedError(url + "\n" + http_signed_url)
    return HttpResponse(http_signed_url)

def get_keywords(request):
    keywords = open('/edx/app/edxapp/search/keywords', 'r')
    return HttpResponse(keywords)

def add_keyword(request):
    try:
        keyFileHandler = open('/edx/app/edxapp/search/keywords', 'r')
        keywords = json.loads(keyFileHandler.read())
        keyFileHandler.close()
        key = request.GET['key']
 	if(keywords["keys"].get(key)):
	    keywords["keys"][key] = keywords["keys"][key] + 1;
	else:
	    keywords["keys"][key] = 1
        keyFileHandler = open('/edx/app/edxapp/search/keywords', 'w')
        keyFileHandler.write(json.dumps(keywords))
        keyFileHandler.close()
    except Exception, e:
        return HttpResponse(e)
    return HttpResponse(json.dumps(keywords))


def get_auth_token(request):
    try:
	uid = request.GET['uid']
        keyFileHandler = open('/edx/app/edxapp/auths/' + uid,'r')
        token = keyFileHandler.read()
        keyFileHandler.close()
    except Exception, e:
        return HttpResponse(e)
    return HttpResponse(token)
    #return HttpResponse("<html><body><div style='font-family:Calibri; font-size:18px; color:#7777aa; text-align:center;'>Sample Response</div></body></html>")

def rem_keyword(request):
    try:
        keyFileHandler = open('/edx/app/edxapp/search/keywords', 'r')
        keywords = json.loads(keyFileHandler.read())
        keyFileHandler.close()
        key = request.GET['key']
        if(keywords["keys"].get(key)):
            keywords["keys"][key] = keywords["keys"][key] - 1;
        keyFileHandler = open('/edx/app/edxapp/search/keywords', 'w')
        keyFileHandler.write(json.dumps(keywords))
        keyFileHandler.close()
    except Exception, e:
        return HttpResponse(e)
    return HttpResponse(json.dumps(keywords))

def latest_app_version(request):
    try:
        from path import Path as path
        SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)
        CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', "/edx/app/edxapp/"))
        CONFIG_PREFIX = SERVICE_VARIANT + "." if SERVICE_VARIANT else ""
        with open(CONFIG_ROOT / CONFIG_PREFIX + "env.json") as env_file:
            ENV_TOKENS = json.load(env_file)
        version = ENV_TOKENS.get("MOBILE_APP_VERSION")
    except Exception, e:
        return HttpResponse(e)
    return HttpResponse('{"app_version":"' + str(version) + '"}')

def video_upload(request):
    if request.method == 'POST':
        #if form.is_valid():
	cloudFrontURL = "https://d2a8rd6kt4zb64.cloudfront.net/"
#	try:
	if True:
	    filename = request.FILES['file'].name
            with open('/tmp/' + filename, 'wb+') as destination:
                for chunk in request.FILES['file'].chunks():
                    destination.write(chunk)
    	    course_directory = request.POST['course_directory']
            metadata = get_video_metadata('/tmp/' + filename)
	    bitrate_in_kbps = to_kilo_bits_per_second(metadata['bitrate'])
	    ENV_TOKENS = get_all_env_tokens()
	    if bitrate_in_kbps > 2048:
		return HttpResponse('{"status":"error", "message":"Video can not be uploaded due to unacceptable bitrate. If you are not sure how to fix it, please contact operations at appliedx_ops@amat.com"}')
	    aws_access_key_id = ENV_TOKENS.get("AWS_ACCESS_KEY_ID")
	    aws_secret_access_key = ENV_TOKENS.get("AWS_SECRET_ACCESS_KEY")
	    s3 = boto.connect_s3(aws_access_key_id, aws_secret_access_key)
	    cf = boto.connect_cloudfront(aws_access_key_id, aws_secret_access_key)
	    bucket_name = ENV_TOKENS.get("AWS_BUCKET_NAME")
	    bucket = s3.get_bucket(bucket_name)
	    object_name = course_directory + "/" + string.replace(filename, " ", "_")
	    key = bucket.new_key(object_name)
	    key.set_contents_from_filename('/tmp/' + filename)
            cloudFrontURL += object_name
#    	except Exception, e:
   #         return HttpResponse(e)
    message = "Video has been uploaded succesfully."
    if bitrate_in_kbps > 1536:
	message += "Please note that bitrate is slightly higher than recommended."
    response = '{"status":"success", "message":"' + message + '", "cloudfront_url":"' + cloudFrontURL + '", "metadata":' + json.dumps(metadata) + '}'
    return HttpResponse(response)

def upload(request):
    ''' Info page (link from main header) '''
    return render_to_response("upload.html", {})

def s3_video_list(request):
    video_list = "[]"
    try:
        foldername = request.GET['course_folder']
        from path import Path as path
    	SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)
    	CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', "/edx/app/edxapp/"))
    	CONFIG_PREFIX = SERVICE_VARIANT + "." if SERVICE_VARIANT else ""
    	with open(CONFIG_ROOT / CONFIG_PREFIX + "env.json") as env_file:
            ENV_TOKENS = json.load(env_file)
    	aws_access_key_id = ENV_TOKENS.get("AWS_ACCESS_KEY_ID")
    	aws_secret_access_key = ENV_TOKENS.get("AWS_SECRET_ACCESS_KEY")
        aws_video_bucket_name = ENV_TOKENS.get("AWS_BUCKET_NAME")
    	s3 = boto.connect_s3(aws_access_key_id, aws_secret_access_key)
	bucket = s3.get_bucket(aws_video_bucket_name)
    	files = bucket.list(foldername)
	filenames = []
	for key in files:
	    filenames.append(key.name)
	video_list = json.dumps(filenames)
    except Exception, e:
        return HttpResponse(e)
    return HttpResponse(video_list)


def apple_app_site_association(request):
    ''' Info page (link from main header) '''
    return render_to_response("apple-app-site-association", {})

def get_video_metadata(filepath):
    tmpf = tempfile.NamedTemporaryFile()
    os.system("avconv -i \"%s\" 2> %s" % (filepath, tmpf.name))
    lines = tmpf.readlines()
    tmpf.close()
    metadata = {}
    for l in lines:
        l = l.strip()
        if l.startswith('Duration'):
            metadata['duration'] = re.search('Duration: (.*?),', l).group(0).split(':',1)[1].strip(' ,')
	    metadata['bitrate'] = re.search("bitrate: (\d+ kb/s)", l).group(0).split(':')[1].strip()
	if l.startswith('Stream #0.') and re.search('Video: (.*? \(.*?\)),? ',l) is not None:
		metadata['video'] = {}
		metadata['video']['codec'], metadata['video']['profile'] = \
		[e.strip(' ,()') for e in re.search('Video: (.*? \(.*?\)),? ', l).group(0).split(':')[1].split('(')]
		metadata['video']['resolution'] = re.search('([1-9]\d+x\d+)', l).group(1)
		metadata['video']['bitrate'] = re.search('(\d+ kb/s)', l).group(1)
		metadata['video']['fps'] = re.search('(\d+ fps)', l).group(1)
	if l.startswith('Stream #0.') and re.search('Video: (.*? \(.*?\)),? ',l) is None:
		metadata['audio'] = {}
		metadata['audio']['codec'] = re.search('Audio: (.*?) ', l).group(1)
		metadata['audio']['frequency'] = re.search(', (.*? Hz),', l).group(1)
		metadata['audio']['bitrate'] = re.search(', (\d+ kb/s)', l).group(1)
    return metadata

def get_all_env_tokens():
    try:
        from path import Path as path
        SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)
        CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', "/edx/app/edxapp/"))
        CONFIG_PREFIX = SERVICE_VARIANT + "." if SERVICE_VARIANT else ""
        with open(CONFIG_ROOT / CONFIG_PREFIX + "env.json") as env_file:
            ENV_TOKENS = json.load(env_file)
    except Exception, e:
        return HttpResponse(e)
    return ENV_TOKENS

def to_kilo_bits_per_second(raw):
    split = raw.split(" ")
    value = int(split[0])
    denomination = split[1].split("/s")[0]
    if denomination[0] == "k":
        value *= 1
    if denomination[0] == "m":
        value *= 1000
    if denomination[0] == "g":
        value *= 1000000
    if denomination[0] == "t":
        value *= 1000000000
    if denomination[1] == "B":
        value *= 8
    return value

