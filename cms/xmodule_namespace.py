import datetime

from xblock.core import Namespace, Boolean, Scope, ModelType, String


class StringyBoolean(Boolean):
    def from_json(self, value):
        if isinstance(value, basestring):
            return value.lower() == 'true'
        return value

class DateTuple(ModelType):
    """
    ModelType that stores datetime objects as time tuples
    """
    def from_json(self, value):
        return datetime.datetime(*value[0:6])

    def to_json(self, value):
        return list(value.timetuple())


class CmsNamespace(Namespace):
    is_draft = Boolean(help="Whether this module is a draft", default=False, scope=Scope.settings)
    published_date = DateTuple(help="Date when the module was published", scope=Scope.settings)
    published_by = String(help="Id of the user who published this module", scope=Scope.settings)
    empty = StringyBoolean(help="Whether this is an empty template", scope=Scope.settings, default=False)
