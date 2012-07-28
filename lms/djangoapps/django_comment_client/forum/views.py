from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.utils import simplejson
from django.core.context_processors import csrf

from mitxmako.shortcuts import render_to_response, render_to_string
from courseware.courses import check_course

import comment_client
import dateutil
from dateutil.tz import tzlocal
from datehelper import time_ago_in_words

from django_comment_client.utils import get_categorized_discussion_info

import json

def render_accordion(request, course, discussion_info, discussion_id):
    context = {
        'course': course,
        'discussion_info': discussion_info,
        'active': discussion_id,
        'csrf': csrf(request)['csrf_token'],
    }

    return render_to_string('discussion/accordion.html', context)

def render_discussion(request, course_id, threads, discussion_id=None, search_text=''):
    context = {
        'threads': threads,
        'discussion_id': discussion_id,
        'search_bar': render_search_bar(request, course_id, discussion_id, text=search_text),
        'user_info': comment_client.get_user_info(request.user.id, raw=True),
        'tags': comment_client.get_threads_tags(raw=True),
        'course_id': course_id,
    }
    return render_to_string('discussion/inline.html', context)

def render_search_bar(request, course_id, discussion_id=None, text=''):
    if not discussion_id:
        return ''
    context = {
        'discussion_id': discussion_id,
        'text': text,
        'course_id': course_id,
    }
    return render_to_string('discussion/search_bar.html', context)

def forum_form_discussion(request, course_id, discussion_id):

    course = check_course(course_id)

    _, course_name, _ = course_id.split('/')

    url_course_id = course_id.replace('/', '_').replace('.', '_')

    discussion_info = get_categorized_discussion_info(request, course)#request.user, course, course_name, url_course_id)

    search_text = request.GET.get('text', '')

    if len(search_text) > 0:
        threads = comment_client.search(search_text, discussion_id)
    else:
        threads = comment_client.get_threads(discussion_id, recursive=False)

    context = {
        'csrf': csrf(request)['csrf_token'],
        'COURSE_TITLE': course.title,
        'course': course,
        'init': '',
        'content': render_discussion(request, course_id, threads, discussion_id, search_text),
        'accordion': render_accordion(request, course, discussion_info, discussion_id),
    }

    return render_to_response('discussion/index.html', context)

def render_single_thread(request, course_id, thread_id):
    context = {
        'thread': comment_client.get_thread(thread_id, recursive=True),
        'user_info': comment_client.get_user_info(request.user.id, raw=True),
        'tags': comment_client.get_threads_tags(raw=True),
        'course_id': course_id,
    }
    return render_to_string('discussion/single_thread.html', context)

def single_thread(request, course_id, thread_id):

    course = check_course(course_id)

    context = {
        'csrf': csrf(request)['csrf_token'],
        'init': '',
        'content': render_single_thread(request, course_id, thread_id),
        'accordion': '',
        'course': course,
    }

    return render_to_response('discussion/index.html', context)

def search(request, course_id):

    course = check_course(course_id)
    text = request.GET.get('text', None)
    threads = comment_client.search(text)
    context = {
        'csrf': csrf(request)['csrf_token'],
        'init': '',
        'content': render_discussion(request, course_id, threads, search_text=text),
        'accordion': '',
        'course': course,
    }

    return render_to_response('discussion/index.html', context)
