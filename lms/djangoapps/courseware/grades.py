"""
Course settings module. The settings are based of django.conf. All settings in
courseware.global_course_settings are first applied, and then any settings
in the settings.DATA_DIR/course_settings.py are applied. A setting must be
in ALL_CAPS.

Settings are used by calling

from courseware import course_settings

Note that courseware.course_settings is not a module -- it's an object. So
importing individual settings is not possible:

from courseware.course_settings import GRADER  # This won't work.

"""

import random
import imp
import logging
import types

from django.conf import settings

from courseware import global_course_settings
from xmodule import graders
from xmodule.graders import Score
from models import StudentModule

_log = logging.getLogger("mitx.courseware")


class Settings(object):
    def __init__(self):
        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_course_settings):
            if setting == setting.upper():
                setattr(self, setting, getattr(global_course_settings, setting))

        data_dir = settings.DATA_DIR

        fp = None
        try:
            fp, pathname, description = imp.find_module("course_settings", [data_dir])
            mod = imp.load_module("course_settings", fp, pathname, description)
        except Exception as e:
            _log.exception("Unable to import course settings file from " + data_dir + ". Error: " + str(e))
            mod = types.ModuleType('course_settings')
        finally:
            if fp:
                fp.close()

        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)
                setattr(self, setting, setting_value)

        # Here is where we should parse any configurations, so that we can fail early
        self.GRADER = graders.grader_from_conf(self.GRADER)

course_settings = Settings()


def grade_sheet(student, course, student_module_cache):
    """
    This pulls a summary of all problems in the course. It returns a dictionary with two datastructures:

    - courseware_summary is a summary of all sections with problems in the course. It is organized as an array of chapters,
    each containing an array of sections, each containing an array of scores. This contains information for graded and ungraded
    problems, and is good for displaying a course summary with due dates, etc.

    - grade_summary is the output from the course grader. More information on the format is in the docstring for CourseGrader.

    Arguments:
        student: A User object for the student to grade
        course: An XModule containing the course to grade
        student_module_cache: A StudentModuleCache initialized with all instance_modules for the student
    """
    totaled_scores = {}
    chapters = []
    for c in course.get_children():
        sections = []
        for s in c.get_children():
            def yield_descendents(module):
                yield module
                for child in module.get_display_items():
                    for module in yield_descendents(child):
                        yield module

            graded = s.metadata.get('graded', False)
            scores = []
            for module in yield_descendents(s):
                (correct, total) = get_score(student, module, student_module_cache)

                if correct is None and total is None:
                    continue

                if settings.GENERATE_PROFILE_SCORES:
                    if total > 1:
                        correct = random.randrange(max(total - 2, 1), total + 1)
                    else:
                        correct = total

                if not total > 0:
                    #We simply cannot grade a problem that is 12/0, because we might need it as a percentage
                    graded = False

                scores.append(Score(correct, total, graded, module.metadata.get('display_name')))

            section_total, graded_total = graders.aggregate_scores(scores, s.metadata.get('display_name'))
            #Add the graded total to totaled_scores
            format = s.metadata.get('format', "")
            if format and graded_total.possible > 0:
                format_scores = totaled_scores.get(format, [])
                format_scores.append(graded_total)
                totaled_scores[format] = format_scores

            sections.append({
                'section': s.metadata.get('display_name'),
                'scores': scores,
                'section_total': section_total,
                'format': format,
                'due': s.metadata.get("due", ""),
                'graded': graded,
            })

        chapters.append({'course': course.metadata.get('display_name'),
                         'chapter': c.metadata.get('display_name'),
                         'sections': sections})

    grader = course_settings.GRADER
    grade_summary = grader.grade(totaled_scores)

    return {'courseware_summary': chapters,
            'grade_summary': grade_summary}


def get_score(user, problem, cache):
    """
    Return the score for a user on a problem

    user: a Student object
    problem: an XModule
    cache: A StudentModuleCache
    """
    correct = 0.0

    # If the ID is not in the cache, add the item
    instance_module = cache.lookup(problem.type, problem.id)
    if instance_module is None:
        instance_module = StudentModule(module_type=problem.type,
                                        module_state_key=problem.id,
                                        student=user,
                                        state=None,
                                        grade=0,
                                        max_grade=problem.max_score(),
                                        done='i')
        cache.append(instance_module)
        instance_module.save()

    # If this problem is ungraded/ungradable, bail
    if instance_module.max_grade is None:
        return (None, None)

    correct = instance_module.grade if instance_module.grade is not None else 0
    total = instance_module.max_grade

    if correct is not None and total is not None:
        #Now we re-weight the problem, if specified
        weight = getattr(problem, 'weight', 1)
        if weight != 1:
            correct = correct * weight / total
            total = weight

    return (correct, total)
