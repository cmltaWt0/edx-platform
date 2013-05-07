import datetime
import json
import logging
import pprint
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.core.context_processors import csrf
from django.core.mail import send_mail
from django.core.validators import ValidationError, validate_email
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseServerError
from django.shortcuts import redirect
from django_future.csrf import ensure_csrf_cookie
from mitxmako.shortcuts import render_to_response, render_to_string
from urllib import urlencode
import zendesk

import capa.calc
import track.views


log = logging.getLogger(__name__)


def calculate(request):
    ''' Calculator in footer of every page. '''
    equation = request.GET['equation']
    try:
        result = capa.calc.evaluator({}, {}, equation)
    except:
        event = {'error': map(str, sys.exc_info()),
                 'equation': equation}
        track.views.server_track(request, 'error:calc', event, page='calc')
        return HttpResponse(json.dumps({'result': 'Invalid syntax'}))
    return HttpResponse(json.dumps({'result': str(result)}))


class _ZendeskApi(object):
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
            api_version=2
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


def submit_feedback_via_zendesk(request):
    """
    Create a new user-requested Zendesk ticket.

    If Zendesk submission is not enabled, any request will raise `Http404`.
    If any configuration parameter (`ZENDESK_URL`, `ZENDESK_USER`, or
    `ZENDESK_API_KEY`) is missing, any request will raise an `Exception`.
    The request must be a POST request specifying `subject` and `details`.
    If the user is not authenticated, the request must also specify `name` and
    `email`. If the user is authenticated, the `name` and `email` will be
    populated from the user's information. If any required parameter is
    missing, a 400 error will be returned indicating which field is missing and
    providing an error message. If Zendesk returns any error on ticket
    creation, a 500 error will be returned with no body. Once created, the
    ticket will be updated with a private comment containing additional
    information from the browser and server, such as HTTP headers and user
    state. Whether or not the update succeeds, if the user's ticket is
    successfully created, an empty successful response (200) will be returned.
    """
    if not settings.MITX_FEATURES.get('ENABLE_FEEDBACK_SUBMISSION', False):
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
    tags = []
    if "tag" in request.POST:
        tags = [request.POST["tag"]]

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

    for header in ["HTTP_REFERER", "HTTP_USER_AGENT"]:
        additional_info[header] = request.META.get(header)

    zendesk_api = _ZendeskApi()

    additional_info_string = (
        "Additional information:\n\n" +
        "\n".join("%s: %s" % (key, value) for (key, value) in additional_info.items() if value is not None)
    )

    new_ticket = {
        "ticket": {
            "requester": {"name": realname, "email": email},
            "subject": subject,
            "comment": {"body": details},
            "tags": tags
        }
    }
    try:
        ticket_id = zendesk_api.create_ticket(new_ticket)
    except zendesk.ZendeskError as err:
        log.error("%s", str(err))
        return HttpResponse(status=500)

    # Additional information is provided as a private update so the information
    # is not visible to the user.
    ticket_update = {"ticket": {"comment": {"public": False, "body": additional_info_string}}}
    try:
        zendesk_api.update_ticket(ticket_id, ticket_update)
    except zendesk.ZendeskError as err:
        log.error("%s", str(err))
        # The update is not strictly necessary, so do not indicate failure to the user
        pass

    return HttpResponse()


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


def debug_request(request):
    """Return a pretty printed version of the request"""

    return HttpResponse("""<html>
<h1>request:</h1>
<pre>{0}</pre>

<h1>request.GET</h1>:

<pre>{1}</pre>

<h1>request.POST</h1>:
<pre>{2}</pre>

<h1>request.REQUEST</h1>:
<pre>{3}</pre>



</html>
""".format(
    pprint.pformat(request),
    pprint.pformat(dict(request.GET)),
    pprint.pformat(dict(request.POST)),
    pprint.pformat(dict(request.REQUEST)),
    ))
