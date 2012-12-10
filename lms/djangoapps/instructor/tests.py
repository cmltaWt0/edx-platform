"""
Unit tests for instructor dashboard

Based on (and depends on) unit tests for courseware.

Notes for running by hand:

django-admin.py test --settings=lms.envs.test --pythonpath=. lms/djangoapps/instructor
"""

import courseware.tests.tests as ct

import json

from nose import SkipTest
from mock import patch, Mock

from override_settings import override_settings

# Need access to internal func to put users in the right group
from django.contrib.auth.models import Group

from django.core.urlresolvers import reverse
from django_comment_client.models import Role, FORUM_ROLE_ADMINISTRATOR, \
    FORUM_ROLE_MODERATOR, FORUM_ROLE_COMMUNITY_TA, FORUM_ROLE_STUDENT
from django_comment_client.utils import has_forum_access

from instructor import staff_grading_service
from courseware.access import _course_staff_group_name
import courseware.tests.tests as ct
from xmodule.modulestore.django import modulestore
import xmodule.modulestore.django


@override_settings(MODULESTORE=ct.TEST_DATA_XML_MODULESTORE)
class TestInstructorDashboardGradeDownloadCSV(ct.PageLoader):
    '''
    Check for download of csv
    '''

    def setUp(self):
        xmodule.modulestore.django._MODULESTORES = {}

        self.full = modulestore().get_course("edX/full/6.002_Spring_2012")
        self.toy = modulestore().get_course("edX/toy/2012_Fall")

        # Create two accounts
        self.student = 'view@test.com'
        self.instructor = 'view2@test.com'
        self.password = 'foo'
        self.create_account('u1', self.student, self.password)
        self.create_account('u2', self.instructor, self.password)
        self.activate_user(self.student)
        self.activate_user(self.instructor)

        def make_instructor(course):
            group_name = _course_staff_group_name(course.location)
            g = Group.objects.create(name=group_name)
            g.user_set.add(ct.user(self.instructor))

        make_instructor(self.toy)

        self.logout()
        self.login(self.instructor, self.password)
        self.enroll(self.toy)


    def test_download_grades_csv(self):
        course = self.toy
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        msg = "url = {0}\n".format(url)
        response = self.client.post(url, {'action': 'Download CSV of all student grades for this course'})
        msg += "instructor dashboard download csv grades: response = '{0}'\n".format(response)

        self.assertEqual(response['Content-Type'],'text/csv',msg)

        cdisp = response['Content-Disposition']
        msg += "Content-Disposition = '%s'\n" % cdisp
        self.assertEqual(cdisp, 'attachment; filename=grades_{0}.csv'.format(course.id), msg)

        body = response.content.replace('\r','')
        msg += "body = '{0}'\n".format(body)

        # All the not-actually-in-the-course hw and labs come from the
        # default grading policy string in graders.py
        expected_body = '''"ID","Username","Full Name","edX email","External email","HW 01","HW 02","HW 03","HW 04","HW 05","HW 06","HW 07","HW 08","HW 09","HW 10","HW 11","HW 12","HW Avg","Lab 01","Lab 02","Lab 03","Lab 04","Lab 05","Lab 06","Lab 07","Lab 08","Lab 09","Lab 10","Lab 11","Lab 12","Lab Avg","Midterm","Final"
"2","u2","Fred Weasley","view2@test.com","","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0.0","0.0"
'''
        self.assertEqual(body, expected_body, msg)


FORUM_ROLES = [ FORUM_ROLE_ADMINISTRATOR, FORUM_ROLE_MODERATOR, FORUM_ROLE_COMMUNITY_TA ]
FORUM_ADMIN_ACTION_SUFFIX = { FORUM_ROLE_ADMINISTRATOR : 'admin', FORUM_ROLE_MODERATOR : 'moderator', FORUM_ROLE_COMMUNITY_TA : 'community TA'}
FORUM_ADMIN_USER = { FORUM_ROLE_ADMINISTRATOR : 'forumadmin', FORUM_ROLE_MODERATOR : 'forummoderator', FORUM_ROLE_COMMUNITY_TA : 'forummoderator'}

def action_name(operation, rolename):
    if operation == 'List':
        return '{0} course forum {1}s'.format(operation, FORUM_ADMIN_ACTION_SUFFIX[rolename])
    else:
        return '{0} forum {1}'.format(operation, FORUM_ADMIN_ACTION_SUFFIX[rolename])


_mock_service = staff_grading_service.MockStaffGradingService()

@override_settings(MODULESTORE=ct.TEST_DATA_XML_MODULESTORE)
class TestInstructorDashboardForumAdmin(ct.PageLoader):
    '''
    Check for change in forum admin role memberships
    '''

    def setUp(self):
        xmodule.modulestore.django._MODULESTORES = {}
        courses = modulestore().get_courses()


        self.course_id = "edX/toy/2012_Fall"
        self.toy = modulestore().get_course(self.course_id)

        # Create two accounts
        self.student = 'view@test.com'
        self.instructor = 'view2@test.com'
        self.password = 'foo'
        self.create_account('u1', self.student, self.password)
        self.create_account('u2', self.instructor, self.password)
        self.activate_user(self.student)
        self.activate_user(self.instructor)

        group_name = _course_staff_group_name(self.toy.location)
        g = Group.objects.create(name=group_name)
        g.user_set.add(ct.user(self.instructor))

        self.logout()
        self.login(self.instructor, self.password)
        self.enroll(self.toy)



    def initialize_roles(self, course_id):
        self.admin_role = Role.objects.get_or_create(name=FORUM_ROLE_ADMINISTRATOR, course_id=course_id)[0]
        self.moderator_role = Role.objects.get_or_create(name=FORUM_ROLE_MODERATOR, course_id=course_id)[0]
        self.community_ta_role = Role.objects.get_or_create(name=FORUM_ROLE_COMMUNITY_TA, course_id=course_id)[0]

    def test_add_forum_admin_users_for_unknown_user(self):
        course = self.toy
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'unknown'
        for action in ['Add', 'Remove']:
            for rolename in FORUM_ROLES:
                response = self.client.post(url, {'action': action_name(action, rolename), FORUM_ADMIN_USER[rolename]: username})
                self.assertTrue(response.content.find('Error: unknown username "{0}"'.format(username))>=0)

    def test_add_forum_admin_users_for_missing_roles(self):
        course = self.toy
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'u1'
        for action in ['Add', 'Remove']:
            for rolename in FORUM_ROLES:
                response = self.client.post(url, {'action': action_name(action, rolename), FORUM_ADMIN_USER[rolename]: username})
                self.assertTrue(response.content.find('Error: unknown rolename "{0}"'.format(rolename))>=0)

    def test_remove_forum_admin_users_for_missing_users(self):
        course = self.toy
        self.initialize_roles(course.id)
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'u1'
        action = 'Remove'
        for rolename in FORUM_ROLES:
            response = self.client.post(url, {'action': action_name(action, rolename), FORUM_ADMIN_USER[rolename]: username})
            self.assertTrue(response.content.find('Error: user "{0}" does not have rolename "{1}"'.format(username, rolename))>=0)

    def test_add_and_remove_forum_admin_users(self):
        course = self.toy
        self.initialize_roles(course.id)
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'u2'
        for rolename in FORUM_ROLES:
            response = self.client.post(url, {'action': action_name('Add', rolename), FORUM_ADMIN_USER[rolename]: username})
            self.assertTrue(response.content.find('Added "{0}" to "{1}" forum role = "{2}"'.format(username, course.id, rolename))>=0)
            self.assertTrue(has_forum_access(username, course.id, rolename))
            response = self.client.post(url, {'action': action_name('Remove', rolename), FORUM_ADMIN_USER[rolename]: username})
            self.assertTrue(response.content.find('Removed "{0}" from "{1}" forum role = "{2}"'.format(username, course.id, rolename))>=0)
            self.assertFalse(has_forum_access(username, course.id, rolename))

    def test_add_and_readd_forum_admin_users(self):
        course = self.toy
        self.initialize_roles(course.id)
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'u2'
        for rolename in FORUM_ROLES:
            # perform an add, and follow with a second identical add:
            self.client.post(url, {'action': action_name('Add', rolename), FORUM_ADMIN_USER[rolename]: username})
            response = self.client.post(url, {'action': action_name('Add', rolename), FORUM_ADMIN_USER[rolename]: username})
            self.assertTrue(response.content.find('Error: user "{0}" already has rolename "{1}", cannot add'.format(username, rolename))>=0)
            self.assertTrue(has_forum_access(username, course.id, rolename))

    def test_add_nonstaff_forum_admin_users(self):
        course = self.toy
        self.initialize_roles(course.id)
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'u1'
        rolename = FORUM_ROLE_ADMINISTRATOR
        response = self.client.post(url, {'action': action_name('Add', rolename), FORUM_ADMIN_USER[rolename]: username})
        self.assertTrue(response.content.find('Error: user "{0}" should first be added as staff'.format(username))>=0)

    def test_list_forum_admin_users(self):
        course = self.toy
        self.initialize_roles(course.id)
        url = reverse('instructor_dashboard', kwargs={'course_id': course.id})
        username = 'u2'
        added_roles = [FORUM_ROLE_STUDENT]  # u2 is already added as a student to the discussion forums
        self.assertTrue(has_forum_access(username, course.id, 'Student'))
        for rolename in FORUM_ROLES:
            response = self.client.post(url, {'action': action_name('Add', rolename), FORUM_ADMIN_USER[rolename]: username})
            self.assertTrue(has_forum_access(username, course.id, rolename))
            response = self.client.post(url, {'action': action_name('List', rolename), FORUM_ADMIN_USER[rolename]: username})
            for header in ['Username', 'Full name', 'Roles']:
                self.assertTrue(response.content.find('<th>{0}</th>'.format(header))>0)
            self.assertTrue(response.content.find('<td>{0}</td>'.format(username))>=0)
            # concatenate all roles for user, in sorted order:
            added_roles.append(rolename)
            added_roles.sort()
            roles = ', '.join(added_roles)
            self.assertTrue(response.content.find('<td>{0}</td>'.format(roles))>=0, 'not finding roles "{0}"'.format(roles))


@override_settings(MODULESTORE=ct.TEST_DATA_XML_MODULESTORE)
class TestStaffGradingService(ct.PageLoader):
    '''
    Check that staff grading service proxy works.  Basically just checking the
    access control and error handling logic -- all the actual work is on the
    backend.
    '''
    def setUp(self):
        xmodule.modulestore.django._MODULESTORES = {}

        self.student = 'view@test.com'
        self.instructor = 'view2@test.com'
        self.password = 'foo'
        self.location = 'TestLocation'
        self.create_account('u1', self.student, self.password)
        self.create_account('u2', self.instructor, self.password)
        self.activate_user(self.student)
        self.activate_user(self.instructor)
        
        self.course_id = "edX/toy/2012_Fall"
        self.toy = modulestore().get_course(self.course_id)
        def make_instructor(course):
            group_name = _course_staff_group_name(course.location)
            g = Group.objects.create(name=group_name)
            g.user_set.add(ct.user(self.instructor))

        make_instructor(self.toy)

        self.mock_service = staff_grading_service.grading_service()

        self.logout()

    def test_access(self):
        """
        Make sure only staff have access.
        """
        self.login(self.student, self.password)

        # both get and post should return 404
        for view_name in ('staff_grading_get_next', 'staff_grading_save_grade'):
            url = reverse(view_name, kwargs={'course_id': self.course_id})
            self.check_for_get_code(404, url)
            self.check_for_post_code(404, url)


    def test_get_next(self):
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_get_next', kwargs={'course_id': self.course_id})
        data = {'location': self.location}

        r = self.check_for_post_code(200, url, data)
        d = json.loads(r.content)
        self.assertTrue(d['success'])
        self.assertEquals(d['submission_id'], self.mock_service.cnt)
        self.assertIsNotNone(d['submission'])
        self.assertIsNotNone(d['num_graded'])
        self.assertIsNotNone(d['min_for_ml'])
        self.assertIsNotNone(d['num_pending'])
        self.assertIsNotNone(d['prompt'])
        self.assertIsNotNone(d['ml_error_info'])
        self.assertIsNotNone(d['max_score'])
        self.assertIsNotNone(d['rubric'])


    def test_save_grade(self):
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_save_grade', kwargs={'course_id': self.course_id})

        data = {'score': '12',
                'feedback': 'great!',
                'submission_id': '123',
                'location': self.location}
        r = self.check_for_post_code(200, url, data)
        d = json.loads(r.content)
        self.assertTrue(d['success'], str(d))
        self.assertEquals(d['submission_id'], self.mock_service.cnt)

    def test_get_problem_list(self):
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_get_problem_list', kwargs={'course_id': self.course_id})
        data = {}

        r = self.check_for_post_code(200, url, data)
        d = json.loads(r.content)
        self.assertTrue(d['success'], str(d))
        self.assertIsNotNone(d['problem_list'])


