import pymongo

from nose.tools import assert_equals, assert_raises, assert_not_equals, with_setup
from path import path

from xmodule.modulestore import Location
from xmodule.modulestore.exceptions import InvalidLocationError, ItemNotFoundError
from xmodule.modulestore.mongo import MongoModuleStore
from xmodule.modulestore.xml_importer import import_from_xml

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

    @classmethod
    def setupClass(cls):
        cls.connection = pymongo.connection.Connection(HOST, PORT)
        cls.connection.drop_database(DB)

    @classmethod
    def teardownClass(cls):
        pass

    def setUp(self):
        # connect to the db
        self.store = MongoModuleStore(HOST, DB, COLLECTION, FS_ROOT, default_class=DEFAULT_CLASS)
        # Explicitly list the courses to load (don't want the big one)
        courses = ['toy', 'simple']
        import_from_xml(self.store, DATA_DIR, courses)
        self.connection = TestMongoModuleStore.connection
    
    def tearDown(self):
        # Destroy the test db.
        self.connection.drop_database(DB)
        self.store = None    

    def test_init(self):
        '''Just make sure the db loads'''
        ids = list(self.connection[DB][COLLECTION].find({}, {'_id': True}))
        print len(ids)
        
    def test_get_courses(self):
        '''Make sure the course objects loaded properly'''
        courses = self.store.get_courses()
        assert_equals(len(courses), 2)
        courses.sort(key=lambda c: c.id)
        assert_equals(courses[0].id, 'edX/simple/2012_Fall')
        assert_equals(courses[1].id, 'edX/toy/2012_Fall')

    def Xtest_path_to_location(self):
        '''Make sure that path_to_location works'''
        should_work = (
            ("i4x://edX/toy/video/Welcome", ("toy", "Overview", None, None)),
            )
        for location, expected in should_work:
            assert_equals(self.store.path_to_location(location), expected)

        not_found = (
            "i4x://edX/toy/video/WelcomeX",
            )
        for location in not_found:
            assert_raises(ItemNotFoundError, self.store.path_to_location, location)
            
        no_path = (
            "i4x://edX/toy/video/Lost_Video",
            )
        for location in not_found:
            assert_raises(ItemNotFoundError, self.store.path_to_location, location)
            
