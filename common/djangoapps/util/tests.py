"""Tests for the util package"""

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from student.tests.factories import UserFactory
from util import views
from zendesk import ZendeskError
import json
import mock


@mock.patch.dict("django.conf.settings.MITX_FEATURES", {"ENABLE_FEEDBACK_SUBMISSION": True})
@override_settings(ZENDESK_URL="dummy", ZENDESK_USER="dummy", ZENDESK_API_KEY="dummy")
@mock.patch("util.views._ZendeskApi", autospec=True)
class SubmitFeedbackViaZendeskTest(TestCase):
    def setUp(self):
        """Set up data for the test case"""
        self._request_factory = RequestFactory()
        self._anon_user = AnonymousUser()
        self._auth_user = UserFactory.create(
            email="test@edx.org",
            username="test",
            profile__name="Test User"
        )
        # This contains a tag to ensure that tags are submitted correctly
        self._anon_fields = {
            "email": "test@edx.org",
            "name": "Test User",
            "subject": "a subject",
            "details": "some details",
            "tag": "a tag"
        }
        # This does not contain a tag to ensure that tag is optional
        self._auth_fields = {"subject": "a subject", "details": "some details"}

    def _test_request(self, user, fields):
        """
        Generate a request and invoke the view, returning the response.

        The request will be a POST request from the given `user`, with the given
        `fields` in the POST body.
        """
        req = self._request_factory.post(
            "/submit_feedback",
            data=fields,
            HTTP_REFERER="test_referer",
            HTTP_USER_AGENT="test_user_agent"
        )
        req.user = user
        return views.submit_feedback_via_zendesk(req)

    def _assert_bad_request(self, response, field, zendesk_mock_class):
        """
        Assert that the given `response` contains correct failure data.

        It should have a 400 status code, and its content should be a JSON
        object containing the specified `field` and an `error`.
        """
        self.assertEqual(response.status_code, 400)
        resp_json = json.loads(response.content)
        self.assertTrue("field" in resp_json)
        self.assertEqual(resp_json["field"], field)
        self.assertTrue("error" in resp_json)
        # There should be absolutely no interaction with Zendesk
        self.assertFalse(zendesk_mock_class.return_value.mock_calls)

    def _test_bad_request_omit_field(self, user, fields, omit_field, zendesk_mock_class):
        """
        Invoke the view with a request missing a field and assert correctness.

        The request will be a POST request from the given `user`, with POST
        fields taken from `fields` minus the entry specified by `omit_field`.
        The response should have a 400 (bad request) status code and specify
        the invalid field and an error message, and the Zendesk API should not
        have been invoked.
        """
        filtered_fields = {k: v for (k, v) in fields.items() if k != omit_field}
        resp = self._test_request(user, filtered_fields)
        self._assert_bad_request(resp, omit_field, zendesk_mock_class)

    def _test_bad_request_empty_field(self, user, fields, empty_field, zendesk_mock_class):
        """
        Invoke the view with an empty field and assert correctness.

        The request will be a POST request from the given `user`, with POST
        fields taken from `fields`, replacing the entry specified by
        `empty_field` with the empty string. The response should have a 400
        (bad request) status code and specify the invalid field and an error
        message, and the Zendesk API should not have been invoked.
        """
        altered_fields = fields.copy()
        altered_fields[empty_field] = ""
        resp = self._test_request(user, altered_fields)
        self._assert_bad_request(resp, empty_field, zendesk_mock_class)

    def _test_success(self, user, fields):
        """
        Generate a request, invoke the view, and assert success.

        The request will be a POST request from the given `user`, with the given
        `fields` in the POST body. The response should have a 200 (success)
        status code.
        """
        resp = self._test_request(user, fields)
        self.assertEqual(resp.status_code, 200)

    def test_bad_request_anon_user_no_name(self, zendesk_mock_class):
        """Test a request from an anonymous user not specifying `name`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "name", zendesk_mock_class)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "name", zendesk_mock_class)

    def test_bad_request_anon_user_no_email(self, zendesk_mock_class):
        """Test a request from an anonymous user not specifying `email`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "email", zendesk_mock_class)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "email", zendesk_mock_class)

    def test_bad_request_anon_user_no_subject(self, zendesk_mock_class):
        """Test a request from an anonymous user not specifying `subject`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "subject", zendesk_mock_class)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "subject", zendesk_mock_class)

    def test_bad_request_anon_user_no_details(self, zendesk_mock_class):
        """Test a request from an anonymous user not specifying `details`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "details", zendesk_mock_class)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "details", zendesk_mock_class)

    def test_valid_request_anon_user(self, zendesk_mock_class):
        """
        Test a valid request from an anonymous user.

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the Zendesk API.
        """
        zendesk_mock_instance = zendesk_mock_class.return_value
        zendesk_mock_instance.create_ticket.return_value = 42
        self._test_success(self._anon_user, self._anon_fields)
        expected_calls = [
            mock.call.create_ticket(
                {
                    "ticket": {
                        "requester": {"name": "Test User", "email": "test@edx.org"},
                        "subject": "a subject",
                        "comment": {"body": "some details"},
                        "tags": ["a tag"]
                    }
                }
            ),
            mock.call.update_ticket(
                42,
                {
                    "ticket": {
                        "comment": {
                            "public": False,
                            "body":
                            "Additional information:\n\n"
                            "HTTP_USER_AGENT: test_user_agent\n"
                            "HTTP_REFERER: test_referer"
                        }
                    }
                }
            )
        ]
        self.assertEqual(zendesk_mock_instance.mock_calls, expected_calls)

    def test_bad_request_auth_user_no_subject(self, zendesk_mock_class):
        """Test a request from an authenticated user not specifying `subject`."""
        self._test_bad_request_omit_field(self._auth_user, self._auth_fields, "subject", zendesk_mock_class)
        self._test_bad_request_empty_field(self._auth_user, self._auth_fields, "subject", zendesk_mock_class)

    def test_bad_request_auth_user_no_details(self, zendesk_mock_class):
        """Test a request from an authenticated user not specifying `details`."""
        self._test_bad_request_omit_field(self._auth_user, self._auth_fields, "details", zendesk_mock_class)
        self._test_bad_request_empty_field(self._auth_user, self._auth_fields, "details", zendesk_mock_class)

    def test_valid_request_auth_user(self, zendesk_mock_class):
        """
        Test a valid request from an authenticated user.

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the Zendesk API.
        """
        zendesk_mock_instance = zendesk_mock_class.return_value
        zendesk_mock_instance.create_ticket.return_value = 42
        self._test_success(self._auth_user, self._auth_fields)
        expected_calls = [
            mock.call.create_ticket(
                {
                    "ticket": {
                        "requester": {"name": "Test User", "email": "test@edx.org"},
                        "subject": "a subject",
                        "comment": {"body": "some details"},
                        "tags": []
                    }
                }
            ),
            mock.call.update_ticket(
                42,
                {
                    "ticket": {
                        "comment": {
                            "public": False,
                            "body":
                            "Additional information:\n\n"
                            "username: test\n"
                            "HTTP_USER_AGENT: test_user_agent\n"
                            "HTTP_REFERER: test_referer"
                        }
                    }
                }
            )
        ]
        self.assertEqual(zendesk_mock_instance.mock_calls, expected_calls)

    def test_get_request(self, zendesk_mock_class):
        """Test that a GET results in a 405 even with all required fields"""
        req = self._request_factory.get("/submit_feedback", data=self._anon_fields)
        req.user = self._anon_user
        resp = views.submit_feedback_via_zendesk(req)
        self.assertEqual(resp.status_code, 405)
        self.assertIn("Allow", resp)
        self.assertEqual(resp["Allow"], "POST")
        # There should be absolutely no interaction with Zendesk
        self.assertFalse(zendesk_mock_class.mock_calls)

    def test_zendesk_error_on_create(self, zendesk_mock_class):
        """
        Test Zendesk returning an error on ticket creation.

        We should return a 500 error with no body
        """
        err = ZendeskError(msg="", error_code=404)
        zendesk_mock_instance = zendesk_mock_class.return_value
        zendesk_mock_instance.create_ticket.side_effect = err
        resp = self._test_request(self._anon_user, self._anon_fields)
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.content)

    def test_zendesk_error_on_update(self, zendesk_mock_class):
        """
        Test for Zendesk returning an error on ticket update.

        If Zendesk returns any error on ticket update, we return a 200 to the
        browser because the update contains additional information that is not
        necessary for the user to have submitted their feedback.
        """
        err = ZendeskError(msg="", error_code=500)
        zendesk_mock_instance = zendesk_mock_class.return_value
        zendesk_mock_instance.update_ticket.side_effect = err
        resp = self._test_request(self._anon_user, self._anon_fields)
        self.assertEqual(resp.status_code, 200)

    @mock.patch.dict("django.conf.settings.MITX_FEATURES", {"ENABLE_FEEDBACK_SUBMISSION": False})
    def test_not_enabled(self, zendesk_mock_class):
        """
        Test for Zendesk submission not enabled in `settings`.

        We should raise Http404.
        """
        with self.assertRaises(Http404):
            self._test_request(self._anon_user, self._anon_fields)

    def test_zendesk_not_configured(self, zendesk_mock_class):
        """
        Test for Zendesk not fully configured in `settings`.

        For each required configuration parameter, test that setting it to
        `None` causes an otherwise valid request to return a 500 error.
        """
        def test_case(missing_config):
            with mock.patch(missing_config, None):
                with self.assertRaises(Exception):
                    self._test_request(self._anon_user, self._anon_fields)

        test_case("django.conf.settings.ZENDESK_URL")
        test_case("django.conf.settings.ZENDESK_USER")
        test_case("django.conf.settings.ZENDESK_API_KEY")
