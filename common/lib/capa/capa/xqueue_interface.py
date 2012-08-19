#
#  LMS Interface to external queueing system (xqueue)
#
import hashlib
import json
import logging
import requests
import time


log = logging.getLogger('mitx.' + __name__)


def make_hashkey(seed=None):
    '''
    Generate a string key by hashing 
    '''
    h = hashlib.md5()
    if seed is not None:
        h.update(str(seed))
    h.update(str(time.time()))
    return h.hexdigest()


def make_xheader(lms_callback_url, lms_key, queue_name):
    '''
    Generate header for delivery and reply of queue request.

    Xqueue header is a JSON-serialized dict:
        { 'lms_callback_url': url to which xqueue will return the request (string),
          'lms_key': secret key used by LMS to protect its state (string), 
          'queue_name': designate a specific queue within xqueue server, e.g. 'MITx-6.00x' (string)
        }
    '''
    return json.dumps({ 'lms_callback_url': lms_callback_url,
                        'lms_key': lms_key,
                        'queue_name': queue_name })


def parse_xreply(xreply):
    '''
    Parse the reply from xqueue. Messages are JSON-serialized dict:
        { 'return_code': 0 (success), 1 (fail)
          'content': Message from xqueue (string)
        }
    '''
    try:
        xreply = json.loads(xreply)
    except ValueError, err:
        log.error(err)
        return (1, 'unexpected reply from server')

    return_code = xreply['return_code']
    content = xreply['content']
    return (return_code, content)


class XQueueInterface(object):
    '''
    Interface to the external grading system
    '''

    def __init__(self, url, django_auth, requests_auth=None):
        self.url  = url
        self.auth = django_auth
        self.session = requests.session(auth=requests_auth)
        
    def send_to_queue(self, header, body, files_to_upload=[]):
        '''
        Submit a request to xqueue.
        
        header: JSON-serialized dict in the format described in 'xqueue_interface.make_xheader'

        body: Serialized data for the receipient behind the queueing service. The operation of
                xqueue is agnostic to the contents of 'body'

        files_to_upload: List of file objects to be uploaded to xqueue along with queue request

        Returns (error_code, msg) where error_code != 0 indicates an error
        '''
        # Attempt to send to queue
        (error, msg) = self._send_to_queue(header, body, files_to_upload)

        if error and (msg == 'login_required'): # Log in, then try again
            self._login()
            (error, msg) = self._send_to_queue(header, body, files_to_upload)

        return (error, msg)


    def _login(self):
        payload = { 'username': self.auth['username'],
                    'password': self.auth['password'] }
        return self._http_post(self.url+'/xqueue/login/', payload)


    def _send_to_queue(self, header, body, files_to_upload):
        payload = {'xqueue_header': header,
                   'xqueue_body'  : body}
        files = None
        for f in files_to_upload:
            files.update({ f.name: f })

        return self._http_post(self.url+'/xqueue/submit/', payload, files)


    def _http_post(self, url, data, files=None):
        try:
            r = self.session.post(url, data=data, files=files)
        except requests.exceptions.ConnectionError, err:
            log.error(err)
            return (1, 'cannot connect to server')
        
        if r.status_code not in [200]:
            return (1, 'unexpected HTTP status code [%d]' % r.status_code)

        return parse_xreply(r.text)
