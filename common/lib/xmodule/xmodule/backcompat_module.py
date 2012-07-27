"""
These modules exist to translate old format XML into newer, semantic forms
"""
from x_module import XModuleDescriptor
from lxml import etree
from functools import wraps
import logging

log = logging.getLogger(__name__)


def process_includes(fn):
    """
    Wraps a XModuleDescriptor.from_xml method, and modifies xml_data to replace
    any immediate child <include> items with the contents of the file that they
    are supposed to include
    """
    @wraps(fn)
    def from_xml(cls, xml_data, system, org=None, course=None):
        xml_object = etree.fromstring(xml_data)
        next_include = xml_object.find('include')
        while next_include is not None:
            file = next_include.get('file')
            if file is not None:
                try:
                    ifp = system.resources_fs.open(file)
                except Exception:
                    msg = 'Error in problem xml include: %s\n' % (
                        etree.tostring(next_include, pretty_print=True))
                    msg += 'Cannot find file %s in %s' % (file, dir)
                    log.exception(msg)
                    system.error_handler(msg)
                    raise
                try:
                    # read in and convert to XML
                    incxml = etree.XML(ifp.read())
                except Exception:
                    msg = 'Error in problem xml include: %s\n' % (
                        etree.tostring(next_include, pretty_print=True))
                    msg += 'Cannot parse XML in %s' % (file)
                    log.exception(msg)
                    system.error_handler(msg)
                    raise
                # insert  new XML into tree in place of inlcude
                parent = next_include.getparent()
                parent.insert(parent.index(next_include), incxml)
            parent.remove(next_include)

            next_include = xml_object.find('include')
        return fn(cls, etree.tostring(xml_object), system, org, course)
    return from_xml


class SemanticSectionDescriptor(XModuleDescriptor):
    @classmethod
    @process_includes
    def from_xml(cls, xml_data, system, org=None, course=None):
        """
        Removes sections with single child elements in favor of just embedding
        the child element
        """
        xml_object = etree.fromstring(xml_data)

        if len(xml_object) == 1:
            for (key, val) in xml_object.items():
                xml_object[0].set(key, val)

            return system.process_xml(etree.tostring(xml_object[0]))
        else:
            xml_object.tag = 'sequence'
            return system.process_xml(etree.tostring(xml_object))


class TranslateCustomTagDescriptor(XModuleDescriptor):
    @classmethod
    def from_xml(cls, xml_data, system, org=None, course=None):
        """
        Transforms the xml_data from <$custom_tag attr="" attr=""/> to
        <customtag attr="" attr=""><impl>$custom_tag</impl></customtag>
        """

        xml_object = etree.fromstring(xml_data)
        tag = xml_object.tag
        xml_object.tag = 'customtag'
        impl = etree.SubElement(xml_object, 'impl')
        impl.text = tag

        return system.process_xml(etree.tostring(xml_object))
