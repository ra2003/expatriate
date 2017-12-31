# Copyright 2016 Casey Jaymes

# This file is part of Expatriate.
#
# Expatriate is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Expatriate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Expatriate.  If not, see <http://www.gnu.org/licenses/>.

import expatriate
import importlib
import logging
import os.path
import re
import sys

from .decorators import *
from .exceptions import *

logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO)

@attribute(namespace='http://www.w3.org/XML/1998/namespace', local_name='lang', type=('expatriate.model.xs.StringType', 'StringType'), into='_xml_lang')
@attribute(namespace='http://www.w3.org/XML/1998/namespace', local_name='space', enum=('default', 'preserve'), into='_xml_space')
@attribute(namespace='http://www.w3.org/XML/1998/namespace', local_name='base', type=('expatriate.model.xs.AnyUriType', 'AnyUriType'), into='_xml_base')
@attribute(namespace='http://www.w3.org/XML/1998/namespace', local_name='id', type=('expatriate.model.xs.IdType', 'IdType'), into='_xml_id')
@attribute(namespace='http://www.w3.org/2000/xmlns/', local_name='*', into='_xmlns')
@attribute(namespace='http://www.w3.org/2001/XMLSchema-instance', local_name='type', type=('expatriate.model.xs.QNameType', 'QNameType'), into='_xsi_type')
@attribute(namespace='http://www.w3.org/2001/XMLSchema-instance', local_name='nil', type=('expatriate.model.xs.BooleanType', 'BooleanType'), into='_xsi_nil', default=False)
@attribute(namespace='http://www.w3.org/2001/XMLSchema-instance', local_name='schemaLocation', type=('expatriate.model.xs.AnyUriType', 'AnyUriType'), into='_xsi_schemaLocation')
@attribute(namespace='http://www.w3.org/2001/XMLSchema-instance', local_name='noNamespaceSchemaLocation', type=('expatriate.model.xs.AnyUriType', 'AnyUriType'), into='_xsi_noNamespaceSchemaLocation')
class Model(object):
    ANY_NAMESPACE = '*'
    ANY_LOCAL_NAME = '*'

    XML_SPACE_ENUMERATION = (
        'default',
        # The value "default" signals that applications' default white-space
        # processing modes are acceptable for this element
        'preserve',
        # the value "preserve" indicates the intent that applications preserve all
        # the white space
    )

    __namespace_to_package = {
        'http://www.w3.org/XML/1998/namespace': 'expatriate.model.xml',
        'http://www.w3.org/2001/XMLSchema': 'expatriate.model.xs',
        'http://www.w3.org/2001/XMLSchema-hasFacetAndProperty': 'expatriate.model.xs.hfp',
        'http://www.w3.org/2001/XMLSchema-instance': 'expatriate.model.xs.i',
    }
    __package_to_namespace = {
        'expatriate.model.xml': 'http://www.w3.org/XML/1998/namespace',
        'expatriate.model.xs': 'http://www.w3.org/2001/XMLSchema',
        'expatriate.model.xs.hfp': 'http://www.w3.org/2001/XMLSchema-hasFacetAndProperty',
        'expatriate.model.xs.i': 'http://www.w3.org/2001/XMLSchema-instance',
    }

    _attribute_mappers = {}
    _element_mappers = {}
    _element_mapper_order = {}
    _content_mappers = {}

    @staticmethod
    def _map_element_to_module_name(model_package, el):
        '''
        discover the model package and model name corresponding to an element
        '''
        pkg_mod = importlib.import_module(model_package)

        if not hasattr(pkg_mod, 'ELEMENT_MAP'):
            raise ElementMappingException(pkg_mod.__name__
                + ' does not define ELEMENT_MAP; cannot load ' + el)
        if (el.namespace, el.local_name) not in pkg_mod.ELEMENT_MAP:
            raise ElementMappingException(pkg_mod.__name__
                + ' does not define mapping for ' + el.namespace + ', '
                + el.local_name + ' element')

        return pkg_mod.__name__, pkg_mod.ELEMENT_MAP[el.namespace, el.local_name]

    @classmethod
    def _get_model_namespace(cls):
        '''
        determine a model's namespace from a class
        '''
        namespace = None

        # determine from package
        if namespace is None:
            namespace = Model.package_to_namespace(cls.class_from_module())

        return namespace

    @classmethod
    def _get_attribute_mappers(cls):
        '''
        get all the attribute definitions for a model class
        '''

        mappers = []

        for cls_ in reversed(cls.__mro__):
            if issubclass(cls_, Model):
                try:
                    logger.debug('Adding attribute mappers from superclass '
                        + cls_.__name__)
                    mappers.extend(cls_._attribute_mappers[cls_.__name__])
                except KeyError:
                    logger.debug('Class ' + cls_.__name__
                        + ' does not define attributes')

        return mappers

    @classmethod
    def _add_attribute_mapper(cls, mapper):
        '''
        set the model attribute definition for an attribute
        '''

        if cls.__name__ not in cls._attribute_mappers:
            cls._attribute_mappers[cls.__name__] = []

        cls._attribute_mappers[cls.__name__].append(mapper)

    @classmethod
    def _get_element_mappers(cls):
        '''
        get all the element definitions for a model class
        '''

        mappers = []

        for cls_ in reversed(cls.__mro__):
            if issubclass(cls_, Model):
                try:
                    logger.debug('Adding element mappers from superclass '
                        + cls_.__name__)
                    mappers.extend(cls_._element_mappers[cls_.__name__])
                except KeyError:
                    logger.debug('Class ' + cls_.__name__
                        + ' does not define elements')

        return mappers

    @classmethod
    def _add_element_mapper(cls, mapper):
        '''
        set the model element definition for an element
        '''

        if cls.__name__ not in cls._element_mappers:
            cls._element_mappers[cls.__name__] = []

        cls._element_mappers[cls.__name__].append(mapper)

        # now set the order that this element was defined
        if cls.__name__ not in cls._element_mapper_order:
            cls._element_mapper_order[cls.__name__] = []

        # have to insert at the front because decorators are applied in reverse
        # order
        cls._element_mapper_order[cls.__name__].insert(0, (mapper.get_namespace(), mapper.get_local_name()))

    @classmethod
    def _get_element_lookup(cls):
        '''
        get the element lookup dict for a class
        '''

        el_lookup = {}

        for mapper in cls._get_element_mappers():
            if mapper.get_namespace() is None and mapper.get_local_name() == Model.ANY_LOCAL_NAME:
                logger.debug('Adding element lookup for ' + str(Model.ANY_NAMESPACE, Model.ANY_LOCAL_NAME))
                el_lookup[Model.ANY_NAMESPACE, Model.ANY_LOCAL_NAME] = mapper
            elif mapper.get_namespace() is None:
                # try using element's namespace
                namespace = cls._get_model_namespace()
                logger.debug('Adding element lookup for ' + str(namespace, mapper.get_local_name()))
                el_lookup[namespace, mapper.get_local_name()] = mapper
            else:
                logger.debug('Adding element lookup for ' + str(mapper.get_namespace(), mapper.get_local_name()))
                el_lookup[mapper.get_namespace(), mapper.get_local_name()] = mapper

        return el_lookup

    @classmethod
    def _add_model_content_mapper(cls, kwargs):
        '''
        add a model content definition for the class
        '''

        logger.debug('Setting ' + str(cls) + ' content def to ' + str(kwargs))
        cls.__content_mappers = kwargs
        if cls.__name__ not in cls._content_mappers:
            cls._content_mappers[cls.__name__] = []

        logger.debug('Adding ' + str(cls) + ' content def: ' + str(kwargs))
        cls._content_mappers[cls.__name__].append(kwargs)

    @classmethod
    def _get_content_mappers(cls):
        '''
        get the model content definitions
        '''

        if cls.__name__ not in cls._content_mappers:
            return ()

        return cls._content_mappers[cls.__name__]

    @staticmethod
    def register_namespace(model_package, namespace):
        '''
        register a namespace for use
        '''
        Model.__namespace_to_package[namespace] = model_package
        Model.__package_to_namespace[model_package] = namespace

    @staticmethod
    def unregister_namespace(model_package):
        '''
        unregister a namespace; throws UnregisteredNamespaceException if
        namespace isn't registered
        '''
        try:
            namespace = Model.__package_to_namespace[model_package]
        except KeyError:
            raise UnregisteredNamespaceException('Unregistered namespace: '
                + model_package)

        del Model.__package_to_namespace[model_package]
        del Model.__namespace_to_package[namespace]

    @staticmethod
    def package_to_namespace(model_package):
        '''
        find namespace corresponding to package
        '''
        logger.debug('Looking for xml namespace for model package '
            + model_package)
        if model_package not in Model.__package_to_namespace:
            raise UnregisteredNamespaceException('Namespace ' + model_package
                + ' is not in registered namespaces')

        return Model.__package_to_namespace[model_package]

    @staticmethod
    def namespace_to_package(namespace):
        '''
        find package corresponding to namespace
        '''
        logger.debug('Looking for model package for xml namespace ' + str(namespace))
        if namespace not in Model.__namespace_to_package:
            raise UnregisteredNamespaceException('XML namespace ' + str(namespace)
                + ' is not in registered namespaces')

        return Model.__namespace_to_package[namespace]

    @classmethod
    def class_from_module(cls):
        return cls.__module__.rpartition('.')[0]

    @staticmethod
    def load(parent, el):
        '''
        load a Model given an expatriate Element
        '''

        # try to load the element's module
        if parent is None:
            if el.namespace is None:
                raise UnregisteredNamespaceException(
                    'Unable to determine namespace without fully qualified element ('
                    + str(el) + ') and parent model')

            model_package = Model.namespace_to_package(el.namespace)
            model_package, module_name = Model._map_element_to_module_name(
                model_package, el)
        else:
            if el.namespace is None:
                model_package = parent.class_from_module()
                ns_any = parent.namespace, Model.ANY_LOCAL_NAME
                fq_name = parent.namespace, el.local_name
            else:
                model_package = Model.namespace_to_package(el.namespace)
                ns_any = el.namespace, Model.ANY_LOCAL_NAME
                fq_name = el.namespace, el.local_name

            element_lookup = Model._get_element_lookup(parent.__class__)

            logger.debug('Checking ' + parent.__class__.__name__
                + ' for element ' + str(el))
            module_name = None
            for name in [
                fq_name,
                (Model.ANY_NAMESPACE, el.local_name),
                ns_any,
                (Model.ANY_NAMESPACE, Model.ANY_LOCAL_NAME)
            ]:
                if name not in element_lookup:
                    continue

                logger.debug(str(el) + ' matched ' + str(name)
                    + ' mapping in ' + parent.__class__.__name__)
                if name[1] == Model.ANY_LOCAL_NAME:
                    model_package, module_name = Model._map_element_to_module_name(
                        model_package, el)
                    break
                elif 'class' in element_lookup[name]:
                    module_name = element_lookup[name]['class']
                    break

            if module_name is None:
                raise ElementMappingException(parent.__class__.__name__
                    + ' does not define mapping for '
                    + str(el) + ' element')

        # qualify module name if needed
        if '.' not in module_name:
            model_module = model_package + '.' + module_name
        else:
            model_module = module_name
            module_name = module_name.rpartition('.')[2]

        # use cached copy of module if possible
        if model_module not in sys.modules:
            logger.debug('Loading module ' + model_module)
            mod = importlib.import_module(model_module)
        else:
            mod = sys.modules[model_module]

        # instantiate an instance of the class & load it
        class_ = getattr(mod, module_name)
        inst = class_()
        inst.from_xml(parent, el)

        return inst

    @staticmethod
    def find_content(uri):
        '''
        locates content & loads it, returning the root Model
        '''

        if os.path.isfile(uri):
            try:
                doc = expatriate.Document()
                doc.parse_file(uri)
                return Model.load(None, doc.root_element)
            except:
                raise ReferenceException('Could not find content for: ' + uri)
        else:
            raise NotImplementedError('URI loading is not yet implemented')

        raise ReferenceException('Could not find content for: ' + uri)

    def __init__(self):
        self._parent = None

        # initialize attribute values
        for mapper in self._get_attribute_mappers():
            mapper.initialize(self)

        # initialize elements; if subclass defined the corresponding attribute,
        # we don't re-define
        for mapper in self._get_element_mappers():
            mapper.initialize(self)

        # initialize content
        for mapper in self._get_content_mappers():
            mapper.initialize(self)

    def is_nil(self):
        '''
        determine if the model's xsi nil is set
        '''
        return self._xsi_nil

    def set_nil(self):
        '''
        set model's xsi nil
        '''
        self._xsi_nil = True
        self.set_value(None)

    def get_value(self):
        #TODO replace for content
        logger.debug(self.__class__.__name__ + ' value currently '
            + str(self.text))
        return self.text

    def set_value(self, value):
        #TODO replace for content
        if self._value_enum is not None:
            if value not in self._value_enum:
                raise ValueError(self.__class__.__name__ + ' Invalid value '
                    + str(value) + '; not in ' + str(self._value_enum))
        if self._value_pattern is not None:
            if (
                not isinstance(value, str)
                or not re.fullmatch(self._value_pattern, value)
            ):
                raise ValueError(self.__class__.__name__ + ' Invalid value '
                    + str(value) + '; does not match ' + self._value_pattern)
        self.text = value
        logger.debug(self.__class__.__name__ + ' value set to '
            + str(self.text))

    def parse_value(self, value):
        '''
        parse the given *value* and return; overriden for value-limiting
        subclasses
        '''
        return value

    def produce_value(self, value):
        '''
        produce the given *value* and return; overriden for value-limiting
        subclasses
        '''
        if value is None:
            return value
        return str(value)

    def __str__(self):
        '''
        string representation of the model
        '''
        s = self.__class__.__module__ + '.' + self.__class__.__name__
        if hasattr(self, 'id') and self.id is not None:
            s += ' id: ' + self.id
        elif hasattr(self, 'Id') and self.Id is not None:
            s += ' Id: ' + self.Id
        elif hasattr(self, 'name') and self.name is not None:
            s += ' name: ' + self.name
        else:
            s += ' # ' + str(id(self))

        return s

    def find_reference(self, ref):
        '''
        find child that matches reference *ref*
        '''

        try:
            if self.id == ref:
                return self
        except AttributeError:
            pass

        # check element mappers for ref
        for mapper in self._get_element_mappers():
            try:
                return mapper.find_reference_in(ref, self)
            except ReferenceException:
                pass

        raise ReferenceException('Could not find reference ' + ref
            + ' within ' + str(self))

    def from_xml(self, parent, el):
        '''
        create model instance from xml element *el*
        '''

        self._parent = parent

        logger.debug('Parsing ' + str(el) + ' element into '
            + self.__class__.__module__ + '.' + self.__class__.__name__
            + ' class')

        for name, attr in el.attribute_nodes.items():
            for mapper in self._get_attribute_mappers():
                if mapper.matches(attr):
                    mapper.parse_in(self, attr)
                    break
            else:
                # if we didn't find a match for the attribute, raise
                raise UnknownAttributeException('Unknown ' + str(self)
                + ' attribute ' + str(attr))

        for child in el.children:
            if isinstance(child, expatriate.Element):
                for mapper in self._get_element_mappers():
                    if mapper.matches(child):
                        mapper.parse_in(self, child)
                        break
                else:
                    raise UnknownElementException('Unknown ' + str(self)
                        + ' child ' + str(child) + ' does not match any mappers')
            else:
                for mapper in self._get_content_mappers().values():
                    mapper.parse_in(self, child)

        for mapper in self._get_attribute_mappers():
            mapper.validate(self)

        for mapper in self._get_element_mappers():
            mapper.validate(self)

        for mapper in self._get_content_mappers():
            mapper.validate(self)

    def to_xml(self):
        '''
        generate xml representation of the model
        '''

        logger.debug(str(self) + ' to xml')
        el = expatriate.Element(self.local_name, namespace=self.namespace)

        for (namespace, local_name), at_def in self._get_attribute_mappers().items():
            value = self._produce_attribute(el, namespace, local_name, at_def)

        for (namespace, local_name), el_def in self._get_element_mappers().items():
            if el_def['local_name'] == Model.ANY_LOCAL_NAME:
                if 'into' in el_def:
                    lst = getattr(self, el_def['into'])
                else:
                    lst = getattr(self, '_elements')

                # check minimum element count
                if 'min' in el_def and el_def['min'] > len(lst):
                    raise MinimumElementException(str(self)
                        + ' must have at least ' + str(el_def['min'])
                        + ' ' + el_def['local_name'] + ' elements; '
                        + str(len(lst)) + ' found')

                # check maximum element count
                if (
                    'max' in el_def
                    and el_def['max'] is not None
                    and el_def['max'] < len(lst)
                ):
                    raise MaximumElementException(str(self)
                        + ' may have at most ' + str(el_def['max'])
                        + ' ' + el_def['local_name'] + ' elements; '
                        + str(len(lst)) + ' found')

            elif 'list' in el_def:
                lst = getattr(self, el_def['list'])

                # check minimum element count
                if 'min' in el_def and el_def['min'] > len(lst):
                    raise MinimumElementException(str(self)
                        + ' must have at least ' + str(el_def['min'])
                        + ' ' + el_def['local_name'] + ' elements; '
                        + str(len(lst)) + ' found')

                # check maximum element count
                if (
                    'max' in el_def
                    and el_def['max'] is not None
                    and el_def['max'] < len(lst)
                ):
                    raise MaximumElementException(str(self)
                        + ' may have at most ' + str(el_def['max'])
                        + ' ' + el_def['local_name'] + ' elements; '
                        + str(len(lst)) + ' found')

            elif 'dict' in el_def:
                dct = getattr(self, el_def['dict'])

                # check minimum element count
                if 'min' in el_def and el_def['min'] > len(dct):
                    raise MinimumElementException(str(self)
                        + ' must have at least ' + str(el_def['min']) + ' '
                        + el_def['local_name'] + ' elements; '
                        + str(len(dct)) + ' found')

                # check maximum element count
                if (
                    'max' in el_def
                    and el_def['max'] is not None
                    and el_def['max'] < len(dct)
                ):
                    raise MaximumElementException(str(self)
                        + ' may have at most ' + str(el_def['max'])
                        + ' ' + el_def['local_name'] + ' elements; '
                        + str(len(dct)) + ' found')

        for i in range(0, len(self._children_values)):
            self._produce_child(i, el)

        el.text = self.produce_value(self.get_value())

        if self.tail is not None:
            el.tail = str(self.tail)

        return el

    def _produce_attribute(self, el, namespace, local_name, at_def):
        '''
        produce an attribute for xml
        '''
        if local_name == Model.ANY_LOCAL_NAME:
            return

        if 'into' in at_def:
            value_name = at_def['into']
        else:
            value_name = local_name.replace('-', '_')

        if not hasattr(self, value_name):
            if 'required' in at_def and at_def['required']:
                raise RequiredAttributeException(str(self)
                    + ' must assign required attribute ' + local_name)
            elif 'prohibited' in at_def and at_def['prohibited']:
                logger.debug('Skipping prohibited attribute ' + local_name)
                return
            else:
                logger.debug('Skipping undefined attribute ' + local_name)
                return
        else:
            if 'prohibited' in at_def and at_def['prohibited']:
                raise ProhibitedAttributeException(str(self)
                    + ' must not assign prohibited attribute '
                    + local_name)
            value = getattr(self, value_name)

        # TODO nillable for attrs?
        if value is None:
            if 'required' in at_def and at_def['required']:
                raise RequiredAttributeException(str(self)
                    + ' must assign required attribute ' + local_name)
            else:
                logger.debug(str(self) + ' Skipping unassigned attribute '
                    + local_name)
                return

        if 'default' in at_def and value == at_def['default']:
            logger.debug('Skipping attribute ' + local_name
                + '; remains at default ' + str(at_def['default']))
            return

        # # if model's namespace doesn't match attribute's, then we need to include it
        # if namespace is not None and self.namespace != namespace:
        #     attr_name = name

        if 'type' in at_def:
            logger.debug(str(self) + ' Producing ' + str(value) + ' as '
                + at_def['type'] + ' type')
            type_ = at_def['type']()
            v = type_.produce_value(value)

            el.set(attr_name, v)

        elif 'enum' in at_def:
            if value not in at_def['enum']:
                raise EnumerationException(str(self) + '.' + name
                    + ' attribute must be one of ' + str(at_def['enum'])
                    + ': ' + str(value))
            el.set(attr_name, value)

        else:
            # otherwise, we default to producing as string
            logger.debug(str(self) + ' Producing ' + str(value)
                + ' as String type')
            type_ = StringType()
            v = type_.produce_value(value)
            el.set(attr_name, v)

    def _produce_child(self, child_index, el):
        '''
        produce child element for xml
        '''

        child = self._children_values[child_index]
        el_def = self._children_el_defs[child_index]

        logger.debug(str(self) + ' producing ' + str(child) + ' according to ' + str(el_def))
        if el_def['local_name'] == Model.ANY_LOCAL_NAME:
            if 'type' in el_def and child.local_name is None:
                raise ValueError('Unable to produce wildcard elements with only "type" in the model map, because local_name is not defined')

            # TODO nillable
            el.append(child.to_xml())

        elif 'list' in el_def:
            if 'namespace' in el_def:
                namespace = el_def['namespace']
            else:
                namespace = self.namespace
            local_name = el_def['local_name']

            if 'type' in el_def:
                if child is None:
                    sub_el = expatriate.Element(local_name, namespace=namespace)
                    sub_el.set('{http://www.w3.org/2001/XMLSchema-instance}nil', 'true')
                    el.append(sub_el)
                else:
                    # wrap value in xs element
                    class_ = el_def['type']
                    child = class_(namespace=namespace, local_name=local_name, value=child)
                    el.append(child.to_xml())
            elif 'class' in el_def:
                if child is None:
                    sub_el = expatriate.Element(local_name, namespace=namespace)
                    sub_el.set('{http://www.w3.org/2001/XMLSchema-instance}nil', 'true')
                    el.append(sub_el)
                else:
                    el.append(child.to_xml())

            else:
                raise ValueError('"class" or "type" must be defined for "list" and "dict" model mapping')

        elif 'dict' in el_def:
            if 'namespace' in el_def:
                namespace = el_def['namespace']
            else:
                namespace = self.namespace
            local_name = el_def['local_name']

            # TODO: implement key_element as well
            key_name = 'id'
            if 'key' in el_def:
                key_name = el_def['key']

            if 'type' in el_def:
                sub_el = expatriate.Element(local_name, namespace=namespace)
                sub_el.set(key_name, self._children_keys[child_index])
                if 'value_attr' in el_def:
                    if child is None:
                        raise ValueError(str(self) + ' Cannot have none for a value_attr: ' + el_def['dict'] + '[' + self._children_keys[child_index] + ']')
                    type_ = el_def['type']()
                    value = type_.produce_value(child)
                    sub_el.set(el_def['value_attr'], value)
                else:
                    if child is None:
                        sub_el.set('{http://www.w3.org/2001/XMLSchema-instance}nil', 'true')
                    else:
                        type_ = el_def['type']()
                        sub_el.text = type_.produce_value(child)
                el.append(sub_el)

            elif 'class' in el_def:
                if child is None:
                    sub_el = expatriate.Element(local_name, namespace=namespace)
                    sub_el.set(key_name, self._children_keys[child_index])
                    sub_el.set('{http://www.w3.org/2001/XMLSchema-instance}nil', 'true')
                    el.append(sub_el)
                else:
                    setattr(child, key_name, self._children_keys[child_index])
                    el.append(child.to_xml())

            else:
                raise ValueError('"class" or "type" must be defined for "list" and "dict" model mapping')

        elif 'class' in el_def:
            if child is None:
                return

            el.append(child.to_xml())

        elif 'type' in el_def:
            if child is None:
                return

            if 'namespace' in el_def:
                namespace = el_def['namespace']
            else:
                namespace = self.namespace
            local_name = el_def['local_name']
            class_ = el_def['type']
            child = class_(namespace=namespace, local_name=local_name, value=child)

            el.append(child.to_xml())

        elif 'enum' in el_def:
            if child is None:
                return

            if child not in el_def['enum']:
                raise EnumerationException(str(namespace, local_name) + ' value must be one of ' + str(el_def['enum']))

            if 'namespace' in el_def:
                namespace = el_def['namespace']
            else:
                namespace = self.namespace
            local_name = el_def['local_name']
            child = String(namespace=namespace, local_name=local_name, value=child)

            el.append(child.to_xml())

        else:
            raise UnknownElementException(str(self) + ' could not produce ' + str(namespace, local_name) + ' element')