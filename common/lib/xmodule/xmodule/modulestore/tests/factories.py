from factory import Factory
from time import gmtime
from uuid import uuid4
from xmodule.modulestore import Location
from xmodule.modulestore.django import modulestore
from xmodule.timeparse import stringify_time
from xmodule.modulestore.inheritance import own_metadata


def XMODULE_COURSE_CREATION(class_to_create, **kwargs):
    return XModuleCourseFactory._create(class_to_create, **kwargs)


def XMODULE_ITEM_CREATION(class_to_create, **kwargs):
    return XModuleItemFactory._create(class_to_create, **kwargs)


class XModuleCourseFactory(Factory):
    """
    Factory for XModule courses.
    """

    ABSTRACT_FACTORY = True
    _creation_function = (XMODULE_COURSE_CREATION,)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        # This logic was taken from the create_new_course method in
        # cms/djangoapps/contentstore/views.py
        template = Location('i4x', 'edx', 'templates', 'course', 'Empty')
        org = kwargs.get('org')
        number = kwargs.get('number')
        display_name = kwargs.get('display_name')
        location = Location('i4x', org, number,
                            'course', Location.clean(display_name))

        store = modulestore('direct')

        # Write the data to the mongo datastore
        new_course = store.clone_item(template, location)

        # This metadata code was copied from cms/djangoapps/contentstore/views.py
        if display_name is not None:
            new_course.display_name = display_name

        new_course.start = gmtime()

        new_course.tabs = [{"type": "courseware"},
                           {"type": "course_info", "name": "Course Info"},
                           {"type": "discussion", "name": "Discussion"},
                           {"type": "wiki", "name": "Wiki"},
                           {"type": "progress", "name": "Progress"}]

        # Update the data in the mongo datastore
        store.update_metadata(new_course.location.url(), own_metadata(new_course))

        return new_course


class Course:
    pass


class CourseFactory(XModuleCourseFactory):
    FACTORY_FOR = Course

    template = 'i4x://edx/templates/course/Empty'
    org = 'MITx'
    number = '999'
    display_name = 'Robot Super Course'


class XModuleItemFactory(Factory):
    """
    Factory for XModule items.
    """

    ABSTRACT_FACTORY = True
    _creation_function = (XMODULE_ITEM_CREATION,)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        """
        kwargs must include parent_location, template. Can contain display_name
        target_class is ignored
        """

        DETACHED_CATEGORIES = ['about', 'static_tab', 'course_info']

        parent_location = Location(kwargs.get('parent_location'))
        template = Location(kwargs.get('template'))
        display_name = kwargs.get('display_name')

        store = modulestore('direct')

        # This code was based off that in cms/djangoapps/contentstore/views.py
        parent = store.get_item(parent_location)
        dest_location = parent_location._replace(category=template.category, name=uuid4().hex)

        new_item = store.clone_item(template, dest_location)

        # replace the display name with an optional parameter passed in from the caller
        if display_name is not None:
            new_item.display_name = display_name

        store.update_metadata(new_item.location.url(), own_metadata(new_item))

        if new_item.location.category not in DETACHED_CATEGORIES:
            store.update_children(parent_location, parent.children + [new_item.location.url()])

        return new_item


class Item:
    pass


class ItemFactory(XModuleItemFactory):
    FACTORY_FOR = Item

    parent_location = 'i4x://MITx/999/course/Robot_Super_Course'
    template = 'i4x://edx/templates/chapter/Empty'
    display_name = 'Section One'
