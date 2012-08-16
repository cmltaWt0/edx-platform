import pymongo

from nose.tools import assert_equals, assert_raises, assert_not_equals, with_setup
from path import path
from pprint import pprint

from xmodule.modulestore import Location
from xmodule.modulestore.exceptions import InvalidLocationError, ItemNotFoundError, NoPathToItem
from xmodule.modulestore.mongo import MongoModuleStore
from xmodule.modulestore.xml_importer import import_from_xml
from xmodule.modulestore.search import path_to_location

# from ~/mitx_all/mitx/common/lib/xmodule/xmodule/modulestore/tests/
# to   ~/mitx_all/mitx/common/test
TEST_DIR = path(__file__).abspath().dirname()
for i in range(5):
    TEST_DIR = TEST_DIR.dirname()
TEST_DIR = TEST_DIR / 'test'

DATA_DIR = TEST_DIR / 'data'


HOST = 'localhost'
PORT = 27017
DB = 'test'
COLLECTION = 'modulestore'
FS_ROOT = DATA_DIR  # TODO (vshnayder): will need a real fs_root for testing load_item
DEFAULT_CLASS = 'xmodule.raw_module.RawDescriptor'


class TestMongoModuleStore(object):
    '''Tests!'''
    @classmethod
    def setupClass(cls):
        cls.connection = pymongo.connection.Connection(HOST, PORT)
        cls.connection.drop_database(DB)

        # NOTE: Creating a single db for all the tests to save time.  This
        # is ok only as long as none of the tests modify the db.
        # If (when!) that changes, need to either reload the db, or load
        # once and copy over to a tmp db for each test.
        cls.store = cls.initdb()

    @classmethod
    def teardownClass(cls):
        pass

    @staticmethod
    def initdb():
        # connect to the db
        store = MongoModuleStore(HOST, DB, COLLECTION, FS_ROOT, default_class=DEFAULT_CLASS)
        # Explicitly list the courses to load (don't want the big one)
        courses = ['toy', 'simple']
        import_from_xml(store, DATA_DIR, courses)
        return store

    @staticmethod
    def destroy_db(connection):
        # Destroy the test db.
        connection.drop_database(DB)

    def setUp(self):
        # make a copy for convenience
        self.connection = TestMongoModuleStore.connection

    def tearDown(self):
        pass

    def test_init(self):
        '''Make sure the db loads, and print all the locations in the db.
        Call this directly from failing tests to see what is loaded'''
        ids = list(self.connection[DB][COLLECTION].find({}, {'_id': True}))

        pprint([Location(i['_id']).url() for i in ids])

    def test_get_courses(self):
        '''Make sure the course objects loaded properly'''
        courses = self.store.get_courses()
        assert_equals(len(courses), 2)
        courses.sort(key=lambda c: c.id)
        assert_equals(courses[0].id, 'edX/simple/2012_Fall')
        assert_equals(courses[1].id, 'edX/toy/2012_Fall')

    def test_loads(self):
        assert_not_equals(
            self.store.get_item("i4x://edX/toy/course/2012_Fall"),
            None)

        assert_not_equals(
            self.store.get_item("i4x://edX/simple/course/2012_Fall"),
            None)

        assert_not_equals(
            self.store.get_item("i4x://edX/toy/video/Welcome"),
            None)

    def test_find_one(self):
        assert_not_equals(
            self.store._find_one(Location("i4x://edX/toy/course/2012_Fall")),
            None)

        assert_not_equals(
            self.store._find_one(Location("i4x://edX/simple/course/2012_Fall")),
            None)

        assert_not_equals(
            self.store._find_one(Location("i4x://edX/toy/video/Welcome")),
            None)

    def test_path_to_location(self):
        '''Make sure that path_to_location works'''
        should_work = (
            ("i4x://edX/toy/video/Welcome",
             ("edX/toy/2012_Fall", "Overview", "Welcome", None)),
            ("i4x://edX/toy/chapter/Overview",
             ("edX/toy/2012_Fall", "Overview", None, None)),
            )
        for location, expected in should_work:
            assert_equals(path_to_location(self.store, location), expected)

        not_found = (
            "i4x://edX/toy/video/WelcomeX", "i4x://edX/toy/course/NotHome"
            )
        for location in not_found:
            assert_raises(ItemNotFoundError, path_to_location, self.store, location)

        # Since our test files are valid, there shouldn't be any
        # elements with no path to them.  But we can look for them in
        # another course.
        no_path = (
            "i4x://edX/simple/video/Lost_Video",
            )
        for location in no_path:
            assert_raises(NoPathToItem, path_to_location, self.store, location, "toy")

