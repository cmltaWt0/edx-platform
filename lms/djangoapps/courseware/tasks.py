
import json
from time import time

from django.contrib.auth.models import User
from django.db import transaction
from celery import task, current_task
from celery.utils.log import get_task_logger

from xmodule.modulestore.django import modulestore

import mitxmako.middleware as middleware
from track.views import task_track

from courseware.models import StudentModule
from courseware.model_data import ModelDataCache
from courseware.module_render import get_module_for_descriptor_internal


# define different loggers for use within tasks and on client side
task_log = get_task_logger(__name__)


class UpdateProblemModuleStateError(Exception):
    """
    Error signaling a fatal condition while updating problem modules.

    Used when the current module cannot be processed and that no more
    modules should be attempted.
    """
    pass


def _update_problem_module_state(course_id, module_state_key, student, update_fcn, action_name, filter_fcn,
                                 xmodule_instance_args):
    """
    Performs generic update by visiting StudentModule instances with the update_fcn provided.

    StudentModule instances are those that match the specified `course_id` and `module_state_key`.
    If `student` is not None, it is used as an additional filter to limit the modules to those belonging
    to that student. If `student` is None, performs update on modules for all students on the specified problem.

    If a `filter_fcn` is not None, it is applied to the query that has been constructed.  It takes one
    argument, which is the query being filtered.

    The `update_fcn` is called on each StudentModule that passes the resulting filtering.
    It is passed three arguments:  the module_descriptor for the module pointed to by the
    module_state_key, the particular StudentModule to update, and the xmodule_instance_args being
    passed through.

    Because this is run internal to a task, it does not catch exceptions.  These are allowed to pass up to the
    task-running level, so that it can set the failure modes and capture the error trace in the result object.
    """
    task_id = current_task.request.id
    fmt = 'Starting to update problem modules as task "{task_id}": course "{course_id}" problem "{state_key}": nothing {action} yet'
    task_log.info(fmt.format(task_id=task_id, course_id=course_id, state_key=module_state_key, action=action_name))

    # get start time for task:
    start_time = time()

    # add task_id to xmodule_instance_args, so that it can be output with tracking info:
    xmodule_instance_args['task_id'] = task_id

    # Hack to get mako templates to work on celery worker server's worker thread.
    # The initialization of Mako templating is usually done when Django is
    # initializing middleware packages as part of processing a server request.
    # When this is run on a celery worker server, no such initialization is
    # called. Using @worker_ready.connect doesn't run in the right container.
    #  So we look for the result: the defining of the lookup paths
    # for templates.
    if 'main' not in middleware.lookup:
        task_log.info("Initializing Mako middleware explicitly")
        middleware.MakoMiddleware()

    # find the problem descriptor:
    module_descriptor = modulestore().get_instance(course_id, module_state_key)

    # find the module in question
    modules_to_update = StudentModule.objects.filter(course_id=course_id,
                                                     module_state_key=module_state_key)

    # give the option of regrading an individual student. If not specified,
    # then regrades all students who have responded to a problem so far
    if student is not None:
        modules_to_update = modules_to_update.filter(student_id=student.id)

    if filter_fcn is not None:
        modules_to_update = filter_fcn(modules_to_update)

    # perform the main loop
    num_updated = 0
    num_attempted = 0
    num_total = modules_to_update.count()

    def get_task_progress():
        """Return a dict containing info about current task"""
        current_time = time()
        progress = {'action_name': action_name,
                    'attempted': num_attempted,
                    'updated': num_updated,
                    'total': num_total,
                    'start_ms': int(start_time * 1000),
                    'duration_ms': int((current_time - start_time) * 1000),
                    }
        return progress

    for module_to_update in modules_to_update:
        num_attempted += 1
        # There is no try here:  if there's an error, we let it throw, and the task will
        # be marked as FAILED, with a stack trace.
        if update_fcn(module_descriptor, module_to_update, xmodule_instance_args):
            # If the update_fcn returns true, then it performed some kind of work.
            num_updated += 1

        # update task status:
        # TODO: decide on the frequency for updating this:
        #  -- it may not make sense to do so every time through the loop
        #  -- may depend on each iteration's duration
        current_task.update_state(state='PROGRESS', meta=get_task_progress())

    task_progress = get_task_progress()
    current_task.update_state(state='PROGRESS', meta=task_progress)

    fmt = 'Finishing task "{task_id}": course "{course_id}" problem "{state_key}": final: {progress}'
    task_log.info(fmt.format(task_id=task_id, course_id=course_id, state_key=module_state_key, progress=task_progress))
    return task_progress


def _update_problem_module_state_for_student(course_id, problem_url, student_identifier,
                                             update_fcn, action_name, filter_fcn=None, xmodule_instance_args=None):
    """
    Update the StudentModule for a given student.  See _update_problem_module_state().
    """
    msg = ''
    success = False
    # try to uniquely id student by email address or username
    try:
        if "@" in student_identifier:
            student_to_update = User.objects.get(email=student_identifier)
        elif student_identifier is not None:
            student_to_update = User.objects.get(username=student_identifier)
        return _update_problem_module_state(course_id, problem_url, student_to_update, update_fcn,
                                            action_name, filter_fcn, xmodule_instance_args)
    except User.DoesNotExist:
        msg = "Couldn't find student with that email or username."

    return (success, msg)


def _update_problem_module_state_for_all_students(course_id, problem_url, update_fcn, action_name, filter_fcn=None, xmodule_instance_args=None):
    """
    Update the StudentModule for all students.  See _update_problem_module_state().
    """
    return _update_problem_module_state(course_id, problem_url, None, update_fcn, action_name, filter_fcn, xmodule_instance_args)


def _get_module_instance_for_task(course_id, student, module_descriptor, module_state_key, xmodule_instance_args=None,
                                  grade_bucket_type=None):
    """
    Fetches a StudentModule instance for a given course_id, student, and module_state_key.

    Includes providing information for creating a track function and an XQueue callback,
    but does not require passing in a Request object.
    """
    # reconstitute the problem's corresponding XModule:
    model_data_cache = ModelDataCache.cache_for_descriptor_descendents(course_id, student, module_descriptor)

    # get request-related tracking information from args passthrough, and supplement with task-specific
    # information:
    request_info = xmodule_instance_args.get('request_info', {}) if xmodule_instance_args is not None else {}
    task_info = {"student": student.username, "task_id": xmodule_instance_args['task_id']}

    def make_track_function():
        '''
        Make a tracking function that logs what happened.
        For insertion into ModuleSystem, and use by CapaModule.
        '''
        def f(event_type, event):
            return task_track(request_info, task_info, event_type, event, page='x_module_task')
        return f

    xqueue_callback_url_prefix = ''
    if xmodule_instance_args is not None:
        xqueue_callback_url_prefix = xmodule_instance_args.get('xqueue_callback_url_prefix')

    return get_module_for_descriptor_internal(student, module_descriptor, model_data_cache, course_id,
                                              make_track_function(), xqueue_callback_url_prefix,
                                              grade_bucket_type=grade_bucket_type)


@transaction.autocommit
def _regrade_problem_module_state(module_descriptor, student_module, xmodule_instance_args=None):
    '''
    Takes an XModule descriptor and a corresponding StudentModule object, and
    performs regrading on the student's problem submission.

    Throws exceptions if the regrading is fatal and should be aborted if in a loop.
    '''
    # unpack the StudentModule:
    course_id = student_module.course_id
    student = student_module.student
    module_state_key = student_module.module_state_key

    instance = _get_module_instance_for_task(course_id, student, module_descriptor, module_state_key, xmodule_instance_args, grade_bucket_type='regrade')

    if instance is None:
        # Either permissions just changed, or someone is trying to be clever
        # and load something they shouldn't have access to.
        msg = "No module {loc} for student {student}--access denied?".format(loc=module_state_key,
                                                                             student=student)
        task_log.debug(msg)
        raise UpdateProblemModuleStateError(msg)

    if not hasattr(instance, 'regrade_problem'):
        # if the first instance doesn't have a regrade method, we should
        # probably assume that no other instances will either.
        msg = "Specified problem does not support regrading."
        raise UpdateProblemModuleStateError(msg)

    result = instance.regrade_problem()
    if 'success' not in result:
        # don't consider these fatal, but false means that the individual call didn't complete:
        task_log.warning("error processing regrade call for problem {loc} and student {student}: "
                 "unexpected response {msg}".format(msg=result, loc=module_state_key, student=student))
        return False
    elif result['success'] != 'correct' and result['success'] != 'incorrect':
        task_log.warning("error processing regrade call for problem {loc} and student {student}: "
                  "{msg}".format(msg=result['success'], loc=module_state_key, student=student))
        return False
    else:
        task_log.debug("successfully processed regrade call for problem {loc} and student {student}: "
                  "{msg}".format(msg=result['success'], loc=module_state_key, student=student))
        return True


def filter_problem_module_state_for_done(modules_to_update):
    """Filter to apply for regrading, to limit module instances to those marked as done"""
    return modules_to_update.filter(state__contains='"done": true')


@task
def regrade_problem_for_student(course_id, problem_url, student_identifier, xmodule_instance_args):
    """Regrades problem `problem_url` in `course_id` for specified student."""
    action_name = 'regraded'
    update_fcn = _regrade_problem_module_state
    filter_fcn = filter_problem_module_state_for_done
    return _update_problem_module_state_for_student(course_id, problem_url, student_identifier,
                                                    update_fcn, action_name, filter_fcn, xmodule_instance_args)


@task
def regrade_problem_for_all_students(course_id, problem_url, xmodule_instance_args):
    """Regrades problem `problem_url` in `course_id` for all students."""
    action_name = 'regraded'
    update_fcn = _regrade_problem_module_state
    filter_fcn = filter_problem_module_state_for_done
    return _update_problem_module_state_for_all_students(course_id, problem_url, update_fcn, action_name, filter_fcn,
                                                         xmodule_instance_args)


@transaction.autocommit
def _reset_problem_attempts_module_state(module_descriptor, student_module, xmodule_instance_args=None):
    """
    Resets problem attempts to zero for specified `student_module`.

    Always returns true, if it doesn't throw an exception.
    """
    problem_state = json.loads(student_module.state)
    if 'attempts' in problem_state:
        old_number_of_attempts = problem_state["attempts"]
        if old_number_of_attempts > 0:
            problem_state["attempts"] = 0
            # convert back to json and save
            student_module.state = json.dumps(problem_state)
            student_module.save()
            # get request-related tracking information from args passthrough,
            # and supplement with task-specific information:
            request_info = xmodule_instance_args.get('request_info', {}) if xmodule_instance_args is not None else {}
            task_id = xmodule_instance_args['task_id'] if xmodule_instance_args is not None else "unknown-task_id"
            task_info = {"student": student_module.student.username, "task_id": task_id}
            event_info = {"old_attempts": old_number_of_attempts, "new_attempts": 0}
            task_track(request_info, task_info, 'problem_reset_attempts', event_info, page='x_module_task')

    # consider the reset to be successful, even if no update was performed.  (It's just "optimized".)
    return True


@task
def reset_problem_attempts_for_student(course_id, problem_url, student_identifier, xmodule_instance_args):
    """Resets problem attempts to zero for `problem_url` in `course_id` for specified student."""
    action_name = 'reset'
    update_fcn = _reset_problem_attempts_module_state
    return _update_problem_module_state_for_student(course_id, problem_url, student_identifier,
                                                    update_fcn, action_name,
                                                    xmodule_instance_args=xmodule_instance_args)


@task
def reset_problem_attempts_for_all_students(course_id, problem_url, xmodule_instance_args):
    """Resets problem attempts to zero for `problem_url` in `course_id` for all students."""
    action_name = 'reset'
    update_fcn = _reset_problem_attempts_module_state
    return _update_problem_module_state_for_all_students(course_id, problem_url,
                                                         update_fcn, action_name,
                                                         xmodule_instance_args=xmodule_instance_args)


@transaction.autocommit
def _delete_problem_module_state(module_descriptor, student_module, xmodule_instance_args=None):
    """Delete the StudentModule entry."""
    student_module.delete()
    # get request-related tracking information from args passthrough,
    # and supplement with task-specific information:
    request_info = xmodule_instance_args.get('request_info', {}) if xmodule_instance_args is not None else {}
    task_id = xmodule_instance_args['task_id'] if xmodule_instance_args is not None else "unknown-task_id"
    task_info = {"student": student_module.student.username, "task_id": task_id}
    task_track(request_info, task_info, 'problem_delete_state', {}, page='x_module_task')
    return True


@task
def delete_problem_state_for_student(course_id, problem_url, student_ident, xmodule_instance_args):
    """Deletes problem state entirely for `problem_url` in `course_id` for specified student."""
    action_name = 'deleted'
    update_fcn = _delete_problem_module_state
    return _update_problem_module_state_for_student(course_id, problem_url, student_ident,
                                                    update_fcn, action_name,
                                                    xmodule_instance_args=xmodule_instance_args)


@task
def delete_problem_state_for_all_students(course_id, problem_url, xmodule_instance_args):
    """Deletes problem state entirely for `problem_url` in `course_id` for all students."""
    action_name = 'deleted'
    update_fcn = _delete_problem_module_state
    return _update_problem_module_state_for_all_students(course_id, problem_url,
                                                         update_fcn, action_name,
                                                         xmodule_instance_args=xmodule_instance_args)


# Using @worker_ready.connect was an effort to call middleware initialization
# only once, when the worker was coming up.  However, the actual worker task
# was not getting initialized, so it was likely running in a separate process
# from the worker server.
#@worker_ready.connect
#def initialize_middleware(**kwargs):
#    # Initialize Django middleware - some middleware components
#    # are initialized lazily when the first request is served. Since
#    # the celery workers do not serve requests, the components never
#    # get initialized, causing errors in some dependencies.
#    # In particular, the Mako template middleware is used by some xmodules
#    task_log.info("Initializing all middleware from worker_ready.connect hook")
#
#    from django.core.handlers.base import BaseHandler
#    BaseHandler().load_middleware()
