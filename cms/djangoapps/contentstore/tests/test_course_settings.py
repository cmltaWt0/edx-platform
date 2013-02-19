import datetime
import time
import json
import calendar
import copy
from util import converters
from util.converters import jsdate_to_time

from django.contrib.auth.models import User
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.utils.timezone import UTC

import xmodule
from xmodule.modulestore import Location
from cms.djangoapps.models.settings.course_details import (CourseDetails,
                                                    CourseSettingsEncoder)
from cms.djangoapps.models.settings.course_grading import CourseGradingModel
from cms.djangoapps.contentstore.utils import get_modulestore

from django.test import TestCase
from utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


# YYYY-MM-DDThh:mm:ss.s+/-HH:MM
class ConvertersTestCase(TestCase):
    @staticmethod
    def struct_to_datetime(struct_time):
        return datetime.datetime(struct_time.tm_year, struct_time.tm_mon, struct_time.tm_mday, struct_time.tm_hour,
                                 struct_time.tm_min, struct_time.tm_sec, tzinfo=UTC())

    def compare_dates(self, date1, date2, expected_delta):
        dt1 = ConvertersTestCase.struct_to_datetime(date1)
        dt2 = ConvertersTestCase.struct_to_datetime(date2)
        self.assertEqual(dt1 - dt2, expected_delta, str(date1) + "-" + str(date2) + "!=" + str(expected_delta))

    def test_iso_to_struct(self):
        self.compare_dates(converters.jsdate_to_time("2013-01-01"), converters.jsdate_to_time("2012-12-31"), datetime.timedelta(days=1))
        self.compare_dates(converters.jsdate_to_time("2013-01-01T00"), converters.jsdate_to_time("2012-12-31T23"), datetime.timedelta(hours=1))
        self.compare_dates(converters.jsdate_to_time("2013-01-01T00:00"), converters.jsdate_to_time("2012-12-31T23:59"), datetime.timedelta(minutes=1))
        self.compare_dates(converters.jsdate_to_time("2013-01-01T00:00:00"), converters.jsdate_to_time("2012-12-31T23:59:59"), datetime.timedelta(seconds=1))


class CourseTestCase(ModuleStoreTestCase):
    def setUp(self):
        """
        These tests need a user in the DB so that the django Test Client
        can log them in.
        They inherit from the ModuleStoreTestCase class so that the mongodb collection
        will be cleared out before each test case execution and deleted
        afterwards.
        """
        uname = 'testuser'
        email = 'test+courses@edx.org'
        password = 'foo'

        # Create the use so we can log them in.
        self.user = User.objects.create_user(uname, email, password)

        # Note that we do not actually need to do anything
        # for registration if we directly mark them active.
        self.user.is_active = True
        # Staff has access to view all courses
        self.user.is_staff = True
        self.user.save()

        self.client = Client()
        self.client.login(username=uname, password=password)

        t = 'i4x://edx/templates/course/Empty'
        o = 'MITx'
        n = '999'
        dn = 'Robot Super Course'
        self.course_location = Location('i4x', o, n, 'course', 'Robot_Super_Course')
        CourseFactory.create(template=t, org=o, number=n, display_name=dn)


class CourseDetailsTestCase(CourseTestCase):
    def test_virgin_fetch(self):
        details = CourseDetails.fetch(self.course_location)
        self.assertEqual(details.course_location, self.course_location, "Location not copied into")
        self.assertIsNone(details.end_date, "end date somehow initialized " + str(details.end_date))
        self.assertIsNone(details.enrollment_start, "enrollment_start date somehow initialized " + str(details.enrollment_start))
        self.assertIsNone(details.enrollment_end, "enrollment_end date somehow initialized " + str(details.enrollment_end))
        self.assertIsNone(details.syllabus, "syllabus somehow initialized" + str(details.syllabus))
        self.assertEqual(details.overview, "", "overview somehow initialized" + details.overview)
        self.assertIsNone(details.intro_video, "intro_video somehow initialized" + str(details.intro_video))
        self.assertIsNone(details.effort, "effort somehow initialized" + str(details.effort))

    def test_encoder(self):
        details = CourseDetails.fetch(self.course_location)
        jsondetails = json.dumps(details, cls=CourseSettingsEncoder)
        jsondetails = json.loads(jsondetails)
        self.assertTupleEqual(Location(jsondetails['course_location']), self.course_location, "Location !=")
        # Note, start_date is being initialized someplace. I'm not sure why b/c the default will make no sense.
        self.assertIsNone(jsondetails['end_date'], "end date somehow initialized ")
        self.assertIsNone(jsondetails['enrollment_start'], "enrollment_start date somehow initialized ")
        self.assertIsNone(jsondetails['enrollment_end'], "enrollment_end date somehow initialized ")
        self.assertIsNone(jsondetails['syllabus'], "syllabus somehow initialized")
        self.assertEqual(jsondetails['overview'], "", "overview somehow initialized")
        self.assertIsNone(jsondetails['intro_video'], "intro_video somehow initialized")
        self.assertIsNone(jsondetails['effort'], "effort somehow initialized")

    def test_update_and_fetch(self):
        ## NOTE: I couldn't figure out how to validly test time setting w/ all the conversions
        jsondetails = CourseDetails.fetch(self.course_location)
        jsondetails.syllabus = "<a href='foo'>bar</a>"
        # encode - decode to convert date fields and other data which changes form
        self.assertEqual(CourseDetails.update_from_json(jsondetails.__dict__).syllabus,
                             jsondetails.syllabus, "After set syllabus")
        jsondetails.overview = "Overview"
        self.assertEqual(CourseDetails.update_from_json(jsondetails.__dict__).overview,
                             jsondetails.overview, "After set overview")
        jsondetails.intro_video = "intro_video"
        self.assertEqual(CourseDetails.update_from_json(jsondetails.__dict__).intro_video,
                             jsondetails.intro_video, "After set intro_video")
        jsondetails.effort = "effort"
        self.assertEqual(CourseDetails.update_from_json(jsondetails.__dict__).effort,
                             jsondetails.effort, "After set effort")


class CourseDetailsViewTest(CourseTestCase):
    def alter_field(self, url, details, field, val):
        setattr(details, field, val)
        # Need to partially serialize payload b/c the mock doesn't handle it correctly
        payload = copy.copy(details.__dict__)
        payload['course_location'] = details.course_location.url()
        payload['start_date'] = CourseDetailsViewTest.convert_datetime_to_iso(details.start_date)
        payload['end_date'] = CourseDetailsViewTest.convert_datetime_to_iso(details.end_date)
        payload['enrollment_start'] = CourseDetailsViewTest.convert_datetime_to_iso(details.enrollment_start)
        payload['enrollment_end'] = CourseDetailsViewTest.convert_datetime_to_iso(details.enrollment_end)
        resp = self.client.post(url, json.dumps(payload), "application/json")
        self.compare_details_with_encoding(json.loads(resp.content), details.__dict__, field + str(val))

    @staticmethod
    def convert_datetime_to_iso(datetime):
        if datetime is not None:
            return datetime.isoformat("T")
        else:
            return None

    def test_update_and_fetch(self):
        details = CourseDetails.fetch(self.course_location)

        # resp s/b json from here on
        url = reverse('course_settings', kwargs={'org': self.course_location.org, 'course': self.course_location.course,
                                                 'name': self.course_location.name, 'section': 'details'})
        resp = self.client.get(url)
        self.compare_details_with_encoding(json.loads(resp.content), details.__dict__, "virgin get")

        utc = UTC()
        self.alter_field(url, details, 'start_date', datetime.datetime(2012, 11, 12, 1, 30, tzinfo=utc))
        self.alter_field(url, details, 'start_date', datetime.datetime(2012, 11, 1, 13, 30, tzinfo=utc))
        self.alter_field(url, details, 'end_date', datetime.datetime(2013, 2, 12, 1, 30, tzinfo=utc))
        self.alter_field(url, details, 'enrollment_start', datetime.datetime(2012, 10, 12, 1, 30, tzinfo=utc))

        self.alter_field(url, details, 'enrollment_end', datetime.datetime(2012, 11, 15, 1, 30, tzinfo=utc))
        self.alter_field(url, details, 'overview', "Overview")
        self.alter_field(url, details, 'intro_video', "intro_video")
        self.alter_field(url, details, 'effort', "effort")

    def compare_details_with_encoding(self, encoded, details, context):
        self.compare_date_fields(details, encoded, context, 'start_date')
        self.compare_date_fields(details, encoded, context, 'end_date')
        self.compare_date_fields(details, encoded, context, 'enrollment_start')
        self.compare_date_fields(details, encoded, context, 'enrollment_end')
        self.assertEqual(details['overview'], encoded['overview'], context + " overviews not ==")
        self.assertEqual(details['intro_video'], encoded.get('intro_video', None), context + " intro_video not ==")
        self.assertEqual(details['effort'], encoded['effort'], context + " efforts not ==")

    def compare_date_fields(self, details, encoded, context, field):
        if details[field] is not None:
            if field in encoded and encoded[field] is not None:
                encoded_encoded = jsdate_to_time(encoded[field])
                dt1 = ConvertersTestCase.struct_to_datetime(encoded_encoded)

                if isinstance(details[field], datetime.datetime):
                    dt2 = details[field]
                else:
                    details_encoded = jsdate_to_time(details[field])
                    dt2 = ConvertersTestCase.struct_to_datetime(details_encoded)

                expected_delta =  datetime.timedelta(0)
                self.assertEqual(dt1 - dt2, expected_delta, str(dt1) + "!=" + str(dt2) + " at " + context)
            else:
                self.fail(field + " missing from encoded but in details at " + context)
        elif field in encoded and encoded[field] is not None:
            self.fail(field + " included in encoding but missing from details at " + context)


class CourseGradingTest(CourseTestCase):
    def test_initial_grader(self):
        descriptor = get_modulestore(self.course_location).get_item(self.course_location)
        test_grader = CourseGradingModel(descriptor)
        # ??? How much should this test bake in expectations about defaults and thus fail if defaults change?
        self.assertEqual(self.course_location, test_grader.course_location, "Course locations")
        self.assertIsNotNone(test_grader.graders, "No graders")
        self.assertIsNotNone(test_grader.grade_cutoffs, "No cutoffs")

    def test_fetch_grader(self):
        test_grader = CourseGradingModel.fetch(self.course_location.url())
        self.assertEqual(self.course_location, test_grader.course_location, "Course locations")
        self.assertIsNotNone(test_grader.graders, "No graders")
        self.assertIsNotNone(test_grader.grade_cutoffs, "No cutoffs")

        test_grader = CourseGradingModel.fetch(self.course_location)
        self.assertEqual(self.course_location, test_grader.course_location, "Course locations")
        self.assertIsNotNone(test_grader.graders, "No graders")
        self.assertIsNotNone(test_grader.grade_cutoffs, "No cutoffs")

        for i, grader in enumerate(test_grader.graders):
            subgrader = CourseGradingModel.fetch_grader(self.course_location, i)
            self.assertDictEqual(grader, subgrader, str(i) + "th graders not equal")

        subgrader = CourseGradingModel.fetch_grader(self.course_location.list(), 0)
        self.assertDictEqual(test_grader.graders[0], subgrader, "failed with location as list")

    def test_fetch_cutoffs(self):
        test_grader = CourseGradingModel.fetch_cutoffs(self.course_location)
        # ??? should this check that it's at least a dict? (expected is { "pass" : 0.5 } I think)
        self.assertIsNotNone(test_grader, "No cutoffs via fetch")

        test_grader = CourseGradingModel.fetch_cutoffs(self.course_location.url())
        self.assertIsNotNone(test_grader, "No cutoffs via fetch with url")

    def test_fetch_grace(self):
        test_grader = CourseGradingModel.fetch_grace_period(self.course_location)
        # almost a worthless test
        self.assertIn('grace_period', test_grader, "No grace via fetch")

        test_grader = CourseGradingModel.fetch_grace_period(self.course_location.url())
        self.assertIn('grace_period', test_grader, "No cutoffs via fetch with url")

    def test_update_from_json(self):
        test_grader = CourseGradingModel.fetch(self.course_location)
        altered_grader = CourseGradingModel.update_from_json(test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "Noop update")

        test_grader.graders[0]['weight'] = test_grader.graders[0].get('weight') * 2
        altered_grader = CourseGradingModel.update_from_json(test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "Weight[0] * 2")

        test_grader.grade_cutoffs['D'] = 0.3
        altered_grader = CourseGradingModel.update_from_json(test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "cutoff add D")

        test_grader.grace_period = {'hours' :  4, 'minutes' : 5, 'seconds': 0}
        altered_grader = CourseGradingModel.update_from_json(test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "4 hour grace period")

    def test_update_grader_from_json(self):
        test_grader = CourseGradingModel.fetch(self.course_location)
        altered_grader = CourseGradingModel.update_grader_from_json(test_grader.course_location, test_grader.graders[1])
        self.assertDictEqual(test_grader.graders[1], altered_grader, "Noop update")

        test_grader.graders[1]['min_count'] = test_grader.graders[1].get('min_count') + 2
        altered_grader = CourseGradingModel.update_grader_from_json(test_grader.course_location, test_grader.graders[1])
        self.assertDictEqual(test_grader.graders[1], altered_grader, "min_count[1] + 2")

        test_grader.graders[1]['drop_count'] = test_grader.graders[1].get('drop_count') + 1
        altered_grader = CourseGradingModel.update_grader_from_json(test_grader.course_location, test_grader.graders[1])
        self.assertDictEqual(test_grader.graders[1], altered_grader, "drop_count[1] + 2")
