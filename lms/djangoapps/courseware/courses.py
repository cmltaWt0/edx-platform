from fs.errors import ResourceNotFoundError
from functools import wraps
import logging
from path import path

from django.conf import settings
from django.http import Http404

from xmodule.course_module import CourseDescriptor
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from static_replace import replace_urls
from staticfiles.storage import staticfiles_storage

log = logging.getLogger(__name__)


def check_course(course_id, course_must_be_open=True, course_required=True):
    """
    Given a course_id, this returns the course object. By default,
    if the course is not found or the course is not open yet, this
    method will raise a 404.

    If course_must_be_open is False, the course will be returned
    without a 404 even if it is not open.

    If course_required is False, a course_id of None is acceptable. The
    course returned will be None. Even if the course is not required,
    if a course_id is given that does not exist a 404 will be raised.
    """
    course = None
    if course_required or course_id:
        try:
            course_loc = CourseDescriptor.id_to_location(course_id)
            course = modulestore().get_item(course_loc)
        except (KeyError, ItemNotFoundError):
            raise Http404("Course not found.")

        if course_must_be_open and not course.has_started():
            raise Http404("This course has not yet started.")

    return course


def course_image_url(course):
    return staticfiles_storage.url(course.metadata['data_dir'] + "/images/course_image.jpg")


def get_course_about_section(course, section_key):
    """
    This returns the snippet of html to be rendered on the course about page, given the key for the section.
    Valid keys:
    - overview
    - title
    - university
    - number
    - short_description
    - description
    - key_dates (includes start, end, exams, etc)
    - video
    - course_staff_short
    - course_staff_extended
    - requirements
    - syllabus
    - textbook
    - faq
    - more_info
    """

    # Many of these are stored as html files instead of some semantic markup. This can change without effecting
    # this interface when we find a good format for defining so many snippets of text/html.

# TODO: Remove number, instructors from this list
    if section_key in ['short_description', 'description', 'key_dates', 'video', 'course_staff_short', 'course_staff_extended',
                        'requirements', 'syllabus', 'textbook', 'faq', 'more_info', 'number', 'instructors', 'overview',
                        'effort', 'end_date', 'prerequisites']:
        try:
            with course.system.resources_fs.open(path("about") / section_key + ".html") as htmlFile:
                return replace_urls(htmlFile.read().decode('utf-8'), course.metadata['data_dir'])
        except ResourceNotFoundError:
            log.warning("Missing about section {key} in course {url}".format(key=section_key, url=course.location.url()))
            return None
    elif section_key == "title":
        return course.metadata.get('display_name', course.name)
    elif section_key == "university":
        return course.location.org
    elif section_key == "number":
        return course.number

    raise KeyError("Invalid about key " + str(section_key))

def get_course_info_section(course, section_key):
    """
    This returns the snippet of html to be rendered on the course info page, given the key for the section.
    Valid keys:
    - handouts
    - guest_handouts
    - updates
    - guest_updates
    """

    # Many of these are stored as html files instead of some semantic markup. This can change without effecting
    # this interface when we find a good format for defining so many snippets of text/html.

    if section_key in ['handouts', 'guest_handouts', 'updates', 'guest_updates']:
        try:
            with course.system.resources_fs.open(path("info") / section_key + ".html") as htmlFile:
                return replace_urls(htmlFile.read().decode('utf-8'), course.metadata['data_dir'])
        except ResourceNotFoundError:
            log.exception("Missing info section {key} in course {url}".format(key=section_key, url=course.location.url()))
            return "! Info section missing !"
        
    raise KeyError("Invalid about key " + str(section_key))

    
