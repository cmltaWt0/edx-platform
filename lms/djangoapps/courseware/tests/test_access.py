import unittest
import logging
import time
from mock import Mock, MagicMock, patch

from django.conf import settings
from django.test import TestCase

from xmodule.course_module import CourseDescriptor
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore import Location
from xmodule.timeparse import parse_time
from xmodule.x_module import XModule, XModuleDescriptor
import courseware.access as access
from .factories import CourseEnrollmentAllowedFactory


class AccessTestCase(TestCase):
    def test__has_global_staff_access(self):
        u = Mock(is_staff=False)
        self.assertFalse(access._has_global_staff_access(u))

        u = Mock(is_staff=True)
        self.assertTrue(access._has_global_staff_access(u))

    def test__has_access_to_location(self):
        location = Location('i4x://edX/toy/course/2012_Fall')

        self.assertFalse(access._has_access_to_location(None, location,
                                                        'staff', None))
        u = Mock()
        u.is_authenticated.return_value = False
        self.assertFalse(access._has_access_to_location(u, location,
                                                        'staff', None))
        u = Mock(is_staff=True)
        self.assertTrue(access._has_access_to_location(u, location,
                                                       'instructor', None))
        # A user has staff access if they are in the staff group
        u = Mock(is_staff=False)
        g = Mock()
        g.name = 'staff_edX/toy/2012_Fall'
        u.groups.all.return_value = [g]
        self.assertTrue(access._has_access_to_location(u, location,
                                                        'staff', None))
        # A user has staff access if they are in the instructor group
        g.name = 'instructor_edX/toy/2012_Fall'
        self.assertTrue(access._has_access_to_location(u, location,
                                                        'staff', None))

        # A user has instructor access if they are in the instructor group
        g.name = 'instructor_edX/toy/2012_Fall'
        self.assertTrue(access._has_access_to_location(u, location,
                                                        'instructor', None))

        # A user does not have staff access if they are
        # not in either the staff or the the instructor group
        g.name = 'student_only'
        self.assertFalse(access._has_access_to_location(u, location,
                                                        'staff', None))

        # A user does not have instructor access if they are
        # not in the instructor group
        g.name = 'student_only'
        self.assertFalse(access._has_access_to_location(u, location,
                                                        'instructor', None))

    def test__has_access_string(self):
        u = Mock(is_staff=True)
        self.assertFalse(access._has_access_string(u, 'not_global', 'staff', None))

        u._has_global_staff_access.return_value = True
        self.assertTrue(access._has_access_string(u, 'global', 'staff', None))

        self.assertRaises(ValueError, access._has_access_string, u, 'global', 'not_staff', None)

    def test__has_access_descriptor(self):
        # TODO: override DISABLE_START_DATES and test the start date branch of the method
        u = Mock()
        d = Mock()
        d.start = time.gmtime(time.time() - 86400)   # make sure the start time is in the past

        # Always returns true because DISABLE_START_DATES is set in test.py
        self.assertTrue(access._has_access_descriptor(u, d, 'load'))
        self.assertRaises(ValueError, access._has_access_descriptor, u, d, 'not_load_or_staff')

    def test__has_access_course_desc_can_enroll(self):
        u = Mock()
        yesterday = time.gmtime(time.time() - 86400)
        tomorrow = time.gmtime(time.time() + 86400)
        c = Mock(enrollment_start=yesterday, enrollment_end=tomorrow)

        # User can enroll if it is between the start and end dates
        self.assertTrue(access._has_access_course_desc(u, c, 'enroll'))

        # User can enroll if authenticated and specifically allowed for that course
        # even outside the open enrollment period
        u = Mock(email='test@edx.org', is_staff=False)
        u.is_authenticated.return_value = True

        c = Mock(enrollment_start=tomorrow, enrollment_end=tomorrow, id='edX/test/2012_Fall')

        allowed = CourseEnrollmentAllowedFactory(email=u.email, course_id=c.id)

        self.assertTrue(access._has_access_course_desc(u, c, 'enroll'))

        # Staff can always enroll even outside the open enrollment period
        u = Mock(email='test@edx.org', is_staff=True)
        u.is_authenticated.return_value = True

        c = Mock(enrollment_start=tomorrow, enrollment_end=tomorrow, id='edX/test/Whenever')
        self.assertTrue(access._has_access_course_desc(u, c, 'enroll'))

        # TODO:
        # Non-staff cannot enroll outside the open enrollment period if not specifically allowed
