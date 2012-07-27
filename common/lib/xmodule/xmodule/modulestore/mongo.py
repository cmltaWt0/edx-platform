import pymongo

from bson.objectid import ObjectId
from bson.son import SON
from fs.osfs import OSFS
from itertools import repeat

from importlib import import_module
from xmodule.errorhandlers import strict_error_handler
from xmodule.x_module import XModuleDescriptor
from xmodule.mako_module import MakoDescriptorSystem
from mitxmako.shortcuts import render_to_string

from . import ModuleStore, Location
from .exceptions import ItemNotFoundError, InsufficientSpecificationError

# TODO (cpennington): This code currently operates under the assumption that
# there is only one revision for each item. Once we start versioning inside the CMS,
# that assumption will have to change


class CachingDescriptorSystem(MakoDescriptorSystem):
    """
    A system that has a cache of module json that it will use to load modules
    from, with a backup of calling to the underlying modulestore for more data
    """
    def __init__(self, modulestore, module_data, default_class, resources_fs,
                 error_handler, render_template):
        """
        modulestore: the module store that can be used to retrieve additional modules

        module_data: a dict mapping Location -> json that was cached from the
            underlying modulestore

        default_class: The default_class to use when loading an
            XModuleDescriptor from the module_data

        resources_fs: a filesystem, as per MakoDescriptorSystem

        error_handler:

        render_template: a function for rendering templates, as per
            MakoDescriptorSystem
        """
        super(CachingDescriptorSystem, self).__init__(
                self.load_item, resources_fs, error_handler, render_template)
        self.modulestore = modulestore
        self.module_data = module_data
        self.default_class = default_class

    def load_item(self, location):
        location = Location(location)
        json_data = self.module_data.get(location)
        if json_data is None:
            return self.modulestore.get_item(location)
        else:
            return XModuleDescriptor.load_from_json(json_data, self, self.default_class)


def location_to_query(location):
    """
    Takes a Location and returns a SON object that will query for that location.
    Fields in location that are None are ignored in the query
    """
    query = SON()
    # Location dict is ordered by specificity, and SON
    # will preserve that order for queries
    for key, val in Location(location).dict().iteritems():
        if val is not None:
            query['_id.{key}'.format(key=key)] = val

    return query


class MongoModuleStore(ModuleStore):
    """
    A Mongodb backed ModuleStore
    """

    # TODO (cpennington): Enable non-filesystem filestores
    def __init__(self, host, db, collection, fs_root, port=27017, default_class=None):
        self.collection = pymongo.connection.Connection(
            host=host,
            port=port
        )[db][collection]

        # Force mongo to report errors, at the expense of performance
        self.collection.safe = True

        # Force mongo to maintain an index over _id.* that is in the same order
        # that is used when querying by a location
        self.collection.ensure_index(zip(('_id.' + field for field in Location._fields), repeat(1)))

        # TODO (vshnayder): default arg default_class=None will make this error
        module_path, _, class_name = default_class.rpartition('.')
        class_ = getattr(import_module(module_path), class_name)
        self.default_class = class_
        self.fs_root = fs_root

    def _clean_item_data(self, item):
        """
        Renames the '_id' field in item to 'location'
        """
        item['location'] = item['_id']
        del item['_id']

    def _cache_children(self, items, depth=0):
        """
        Returns a dictionary mapping Location -> item data, populated with json data
        for all descendents of items up to the specified depth.
        (0 = no descendents, 1 = children, 2 = grandchildren, etc)
        If depth is None, will load all the children.
        This will make a number of queries that is linear in the depth.
        """
        data = {}
        to_process = list(items)
        while to_process and depth is None or depth >= 0:
            children = []
            for item in to_process:
                self._clean_item_data(item)
                children.extend(item.get('definition', {}).get('children', []))
                data[Location(item['location'])] = item

            # Load all children by id. See
            # http://www.mongodb.org/display/DOCS/Advanced+Queries#AdvancedQueries-%24or
            # for or-query syntax
            if children:
                to_process = list(self.collection.find(
                    {'_id': {'$in': [Location(child).dict() for child in children]}}))
            else:
                to_process = []
            # If depth is None, then we just recurse until we hit all the descendents
            if depth is not None:
                depth -= 1

        return data

    def _load_item(self, item, data_cache):
        """
        Load an XModuleDescriptor from item, using the children stored in data_cache
        """
        resource_fs = OSFS(self.fs_root / item.get('data_dir',
                                                   item['location']['course']))
        system = CachingDescriptorSystem(
            self,
            data_cache,
            self.default_class,
            resource_fs,
            strict_error_handler,
            render_to_string,
        )
        return system.load_item(item['location'])

    def _load_items(self, items, depth=0):
        """
        Load a list of xmodules from the data in items, with children cached up to specified depth
        """
        data_cache = self._cache_children(items, depth)

        return [self._load_item(item, data_cache) for item in items]

    def get_courses(self):
        '''
        Returns a list of course descriptors.
        '''
        # TODO (vshnayder): Why do I have to specify i4x here?
        course_filter = Location("i4x", category="course")
        return self.get_items(course_filter)

    def get_item(self, location, depth=0):
        """
        Returns an XModuleDescriptor instance for the item at location.
        If location.revision is None, returns the item with the most
        recent revision.

        If any segment of the location is None except revision, raises
            xmodule.modulestore.exceptions.InsufficientSpecificationError
        If no object is found at that location, raises
            xmodule.modulestore.exceptions.ItemNotFoundError

        location: a Location object
        depth (int): An argument that some module stores may use to prefetch
            descendents of the queried modules for more efficient results later
            in the request. The depth is counted in the number of
            calls to get_children() to cache. None indicates to cache all descendents.

        """

        for key, val in Location(location).dict().iteritems():
            if key != 'revision' and val is None:
                raise InsufficientSpecificationError(location)

        item = self.collection.find_one(
            location_to_query(location),
            sort=[('revision', pymongo.ASCENDING)],
        )
        if item is None:
            raise ItemNotFoundError(location)
        return self._load_items([item], depth)[0]

    def get_items(self, location, depth=0):
        items = self.collection.find(
            location_to_query(location),
            sort=[('revision', pymongo.ASCENDING)],
        )

        return self._load_items(list(items), depth)

    def create_item(self, location):
        """
        Create an empty item at the specified location with the supplied editor

        location: Something that can be passed to Location
        """
        self.collection.insert({
            '_id': Location(location).dict(),
        })

    def update_item(self, location, data):
        """
        Set the data in the item specified by the location to
        data

        location: Something that can be passed to Location
        data: A nested dictionary of problem data
        """

        # See http://www.mongodb.org/display/DOCS/Updating for
        # atomic update syntax
        self.collection.update(
            {'_id': Location(location).dict()},
            {'$set': {'definition.data': data}},

        )

    def update_children(self, location, children):
        """
        Set the children for the item specified by the location to
        children

        location: Something that can be passed to Location
        children: A list of child item identifiers
        """

        # See http://www.mongodb.org/display/DOCS/Updating for
        # atomic update syntax
        self.collection.update(
            {'_id': Location(location).dict()},
            {'$set': {'definition.children': children}}
        )

    def update_metadata(self, location, metadata):
        """
        Set the metadata for the item specified by the location to
        metadata

        location: Something that can be passed to Location
        metadata: A nested dictionary of module metadata
        """

        # See http://www.mongodb.org/display/DOCS/Updating for
        # atomic update syntax
        self.collection.update(
            {'_id': Location(location).dict()},
            {'$set': {'metadata': metadata}}
        )

    def path_to_location(self, location, course=None):
        '''
        Try to find a course/chapter/section[/position] path to this location.

        raise ItemNotFoundError if the location doesn't exist.

        If course is not None, restrict search to paths in that course.
            
        raise NoPathToItem if the location exists, but isn't accessible via
        a chapter/section path in the course(s) being searched.

        In general, a location may be accessible via many paths. This method may
        return any valid path.

        Return a tuple (course, chapter, section, position).

        If the section a sequence, position should be the position of this location
        in that sequence.  Otherwise, position should be None.
        '''
        raise NotImplementedError

