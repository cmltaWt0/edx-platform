import logging
from xmodule.open_ended_grading_classes.grading_service_module import GradingService

from xmodule.x_module import ModuleSystem
from mitxmako.shortcuts import render_to_string

log = logging.getLogger(__name__)


class ControllerQueryService(GradingService):
    """
    Interface to staff grading backend.
    """
    def __init__(self, config):
        config['system'] = ModuleSystem(None, None, None, render_to_string, None)
        super(ControllerQueryService, self).__init__(config)
        self.url = config['url'] + config['grading_controller']
        self.login_url = self.url + '/login/'
        self.check_eta_url = self.url + '/get_submission_eta/'
        self.is_unique_url = self.url + '/is_name_unique/'
        self.combined_notifications_url = self.url + '/combined_notifications/'
        self.grading_status_list_url = self.url + '/get_grading_status_list/'
        self.flagged_problem_list_url = self.url + '/get_flagged_problem_list/'
        self.take_action_on_flags_url = self.url + '/take_action_on_flags/'

    def check_if_name_is_unique(self, location, problem_id, course_id):
        params = {
            'course_id': course_id,
            'location': location,
            'problem_id': problem_id
        }
        response = self.get(self.is_unique_url, params)
        return response

    def check_for_eta(self, location):
        params = {
            'location': location,
        }
        response = self.get(self.check_eta_url, params)
        return response

    def check_combined_notifications(self, course_id, student_id, user_is_staff, last_time_viewed):
        params = {
            'student_id': student_id,
            'course_id': course_id,
            'user_is_staff': user_is_staff,
            'last_time_viewed': last_time_viewed,
        }
        log.debug(self.combined_notifications_url)
        response = self.get(self.combined_notifications_url, params)
        return response

    def get_grading_status_list(self, course_id, student_id):
        params = {
            'student_id': student_id,
            'course_id': course_id,
        }

        response = self.get(self.grading_status_list_url, params)
        return response

    def get_flagged_problem_list(self, course_id):
        params = {
            'course_id': course_id,
            }

        response = self.get(self.flagged_problem_list_url, params)
        return response

    def take_action_on_flags(self, course_id, student_id, submission_id, action_type):
        params = {
            'course_id': course_id,
            'student_id': student_id,
            'submission_id': submission_id,
            'action_type': action_type
            }

        response = self.post(self.take_action_on_flags_url, params)
        return response
