#!/usr/bin/env python3

from hashlib import new
import graphviz
import yaml
import click
import re
import inflection
import requests
from pprint import pprint
import logging
from data.valuesets import ValueSets


logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
logger = logging.getLogger("model")
logger.setLevel(logging.DEBUG)


class FHIRSchemaFigure(object):

    def __init__(self, schema, node) -> None:
        super().__init__()
        self.schema = schema
        self.node = node
        self.dot = None

    def view(self):

        node = self.node
        schema = self.schema

        def graph_node(node):    
            id = node['@id']
            def prop(p):
                return f'''<TR><TD>{p}</TD></TR>'''
            props = ''.join([prop(p)for p in node['properties']])
            return f'''"{id}" [label=< <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"> <TR><TD PORT="id"><B>{id}</B></TD></TR> {props} </TABLE>>];'''

        def subclass_edge(_from, _to):
            return f'''"{_from}" -> "{_to}" [ arrowhead=onormal];'''

        def neighbor_edge(_from, _to):
            return f'''"{_from}" -> "{_to}" [ style=dashed ];'''

        graph_nodes = "\n".join([graph_node(node)] 
                                + [graph_node(schema.properties(schema, id=sc)) for sc in node['subclasses']]
                                + [graph_node(schema.properties(schema, id=n)) for n in node['neighbors']]
                                )
        edges = "\n".join([subclass_edge(sc, node['@id']) for sc in node['subclasses']]
                        + [neighbor_edge(node['@id'], n) for n in node['neighbors']]
                        )

        dot = f'''
        digraph g {{
            graph [ rankdir = "BT" ];    
            node [ fontsize = "12" shape = "plaintext"  ];    
            edge [ ];
            {graph_nodes}
            {edges}
        }}
        '''
        self.dot = dot
        label = node['@id'].split(':')[-1]
        graphviz.Source(dot).view(filename=label)

 
class FHIRSchema(object):

    def __init__(self, profile_name, url=None) -> None:
        """Load schema."""
        self.profiles = {}
        self.primitives = []
        self._schema = self.add_profile(profile_name, url)

    def add_profile(self, profile_name, url=None):
        if profile_name in self.profiles:
            return self.profiles[profile_name]
        if profile_name in self.primitives:
            return None
        if not url:    
            url = f"https://www.hl7.org/fhir/{profile_name}.profile.json"
        if 'ncpi-fhir.github.io' in url:
            # logger.debug('patching ncpi host name')
            url = url.replace('ncpi-fhir.github.io', 'nih-ncpi.github.io')
        if 'StructureDefinition/ncpi' in url:
            # logger.debug('patch profile path')
            url = url.replace('StructureDefinition/ncpi', 'StructureDefinition-ncpi')
        if not url.endswith('json'):
            url = url + '.json'
        logger.debug(f"fetching {url}")    
        response = requests.get(url)
        if response.status_code != 200:
            self.primitives.append(profile_name)
            return None
        self.profiles[profile_name] = response.json()
        return self.profiles[profile_name]


class Gen3Configuration(object):
    def __init__(self, fhir_schema, resource_name, config) -> None:
        super().__init__()        
        self.fhir_schema = fhir_schema
        self._schema = fhir_schema._schema
        self._config = {resource_name: config}
        self._recursion_guard = []
        self._parent_element = None

        schema = self._schema
        self.template = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "id": None,
            "title": None,
            "type": "object",
            "namespace": "http://aced-idp.org",
            "category": "administrative",
            "program": "*",
            "project": "*",
            "description": f'> {schema["description"]}',
            "additionalProperties": False,
            "submittable": True,
            "validators": None,
            "systemProperties": [
                "id",
                "project_id",
                "state",
                "created_datetime",
                "updated_datetime"
            ],
            "links": [],
            "required": [
                "submitter_id",
                "type",
                "projects"
            ],
            "uniqueKeys": [
                [
                    "id"
                ],
                [
                    "project_id",
                    "submitter_id"
                ]
            ],
            "properties": {
                "type": {
                    "enum": [],
                    "description": "Gen3's type field."
                },
                "id": {
                    "$ref": "_definitions.yaml#/UUID",
                    "systemAlias": "node_id"
                },
                "state": {
                    "$ref": "_definitions.yaml#/state"
                },
                "submitter_id": {
                    "description": "Each record in every node will have a \"submitter_id\", which is a unique alphanumeric identifier for that record and is specified by the data submitter, and a \"type\", which is simply the node name.",
                    "type": [
                        "string",
                        "null"
                    ]
                },
                "projects": {
                    "$ref": "_definitions.yaml#/to_many_project",
                    "description": "Link to Gen3's project."
                },
                "project_id": {
                    "type": "string"
                },
                "created_datetime": {
                    "$ref": "_definitions.yaml#/datetime"
                },
                "updated_datetime": {
                    "$ref": "_definitions.yaml#/datetime"
                }
            }
        }

    def _name(self, valid_reference):
        """Get name from url."""
        return valid_reference.split('/')[-1]

    def link(self, el, base, config):
        """Generate individual link."""
        name = '.'.join(el['id'].split('.')[1:])
        ## Read target profile from config
        _neighbor = config['targetProfile']

        assert _neighbor, 'Please configure links'
        target_type = self._name(_neighbor)
        backref = inflection.pluralize(base)
        name = inflection.pluralize(target_type)
        return {
            f'comment_link{name}': el['id'].split('.')[-1],
            'name': inflection.pluralize(name),
            'backref': backref,
            'label': el['id'].split('.')[-1],
            'target_type': target_type,
            'multiplicity': 'many_to_many',
            'required': config.get('required', False),
        }

    def links(self, schema, base):
        """Generate links from config.links."""
        links = []
        white_list = self._config.get(base, {}).get('links', [])
        for el in schema['snapshot']['element']:
            # logger.debug(f"{el['id']} {white_list}")
            if el['id'] in white_list:
                links.append(self.link(el, base, white_list[el['id']]))
                white_list.pop(el['id'])
        for name in white_list:
            links.append(self.link(el, base, white_list[name]))

        return links

    def properties(self, template, schema, parent=None, black_list=None, white_list=[], parent_description=None, type_offset=0, is_root=False):
        """Render gen3 properties."""
        base = schema['name']
        id = schema['snapshot']['element'][0]['id']
        if not black_list:
            black_list = self._config.get(base, {}).get('properties', {}).get('exclude', None)
        if not white_list:    
            white_list = self._config.get(base, {}).get('properties', {}).get('include', None)
        # print("====", id, base, white_list)
        for el in schema['snapshot']['element']:
            # skip base extension (not really a path)
            if '.' not in el['id']:
                continue
            name = '.'.join(el['id'].split('.')[1:])
            if name in ['type']:
                continue

            if '[x]' in name:
                # logger.debug(f"multivalued field {name}")
                name = name.replace('[x]', '')

            # check property name against black_list
            name_base = name.split('.')[0]
            if black_list and (name_base in black_list or name in black_list or f"{parent}.{name}" in black_list):
                continue

            if is_root:
                self._parent_element = el

            full_name = name
            if parent:
                full_name = f"{parent}.{name}"

            # logger.debug(f"??? white_list check full_name:{full_name}")
            if white_list:
                skip = True
                for white_list_name in white_list:
                    if full_name == white_list_name:
                        skip = False
                    if full_name in white_list_name:
                        skip = False
                    for white_list_name_part in white_list_name.split('.'):
                        if full_name == white_list_name_part:
                            skip = False
                        if parent == white_list_name_part \
                            and full_name == parent:
                                skip = False
                if skip:
                    # print(f">>> white_list parent:{parent} name_base:{name_base} name:{name} full_name:{full_name}")
                    continue
            
            description = el['definition']
            if self._parent_element:
                description = f"{self._parent_element['definition']} {el['definition']}"
            if parent_description:
                description = f"{self._parent_element['definition']} {parent_description} {el['definition']}"


            template["properties"][name] = {
                'description': description
            }
            

            property_attributes = template["properties"][name]            

            # logger.debug(f">>> white_list pass parent:{parent} name_base:{name_base} name:{name} full_name:{full_name}")        

            if 'type' in el:
                property_attributes['type'] = el['type'][type_offset]['code']
                if len(el['type']) > 1:
                    # logger.debug(f"length of type {len(el['type'])} casting to string.")
                    property_attributes['type'] = 'string'
                    property_attributes['multiple_types'] = [t['code'] for t in el['type']]
                    
                if el['type'][type_offset]['code'] in ['code', 'CodeableConcept']:
                    # logger.debug(f"+++ {el.get('binding', '*no binding*')}")
                    if 'binding' in el:
                        # if 'valueSet' not in el['binding']:
                            # logger.debug(f"code missing valueSet {el.get('binding', '*no binding*')}")
                        property_attributes['enum'] = el['binding'].get('valueSet', 'WARNING_MISSING_ENUM_IN_ELEMENT')
                        # logger.debug(f"{property_attributes['type']} {name} set enum from el {property_attributes['enum']}")
                    else:
                        if 'binding' in self._parent_element:
                            property_attributes['enum'] = self._parent_element['binding'].get('valueSet', 'WARNING_MISSING_ENUM_IN_PARENT')
                            # logger.debug(f"{property_attributes['type']} {name} set enum from parent {property_attributes['enum']}")
                    if 'WARNING' in property_attributes.get('enum', ''):
                        logger.debug(f"Find in config??? {base} {name} {self._config.get('enums', {})}")
                        if template['properties'][name].get('enum', None) == 'WARNING_MISSING_ENUM':
                            if 'enums' in self._config[base] and name in self._config[base]['enums']:
                                template['properties'][name]['enum'] = self._config[base]['enums'][name]
                            else:
                                logger.warning(f"WARNING_MISSING_ENUM  {base} {type} {name}")

                if el['type'][type_offset]['code'] not in ['code', 'CodeableConcept', 'Reference']:
                    property_attributes['is_embedded'] = True
                if 'profile' in el['type'][type_offset]:
                    property_attributes['profile'] = el['type'][type_offset]['profile'][0]

            if 'type' not in property_attributes:
                logger.debug(f"{el['id']} missing type")
                del template["properties"][name]
                continue

            if el['max'] == '*' or int(el['max']) > 1:
                property_attributes['is_array'] = True
            if int(el['min']) > 0:
                property_attributes['is_required'] = True                
            if self._parent_element and int(self._parent_element['min']) > 0:
                property_attributes['is_required'] = True
            else:
                property_attributes['is_required'] = False

            def expand_types(type):
                if type == 'Reference':
                    property_attributes['is_resource'] = True
                if type == 'Extension':
                    # print(f"??? skipping Extension {name}")
                    del template['properties'][name]
                    return
                if type in ['String', "http://hl7.org/fhirpath/System.String", "uri", "string",  "boolean", "http://hl7.org/fhirpath/System.DateTime", "http://hl7.org/fhirpath/System.Date", "code"]:
                    # print(f"**** {parent} {name} {type} {el['id']} is_primitive")
                    property_attributes['is_primitive'] = True
                    if type == 'code':
                        if 'binding' in el:
                            property_attributes['enum'] = el['binding'].get('valueSet', 'WARNING_MISSING_ENUM_IN_ELEMENT')
                            # logger.debug(f"{type} {name} set enum from binding {property_attributes['enum']}")
                        else:
                            if self._parent_element and 'binding' in self._parent_element:
                                property_attributes['enum'] = self._parent_element['binding'].get('valueSet', 'WARNING_MISSING_ENUM_IN_PARENT')
                                # logger.debug(f"{type} {name} set enum from parent {property_attributes['enum']}")
                        if 'WARNING' in property_attributes.get('enum', ''):
                            _base = base
                            if _base not in self._config:
                                _base = self._parent_element['id'].split('.')[0]
                            if 'enums' in self._config[_base]:
                                _full_name = full_name
                                if _full_name not in self._config[_base]['enums']:
                                    _full_name = f"{self._parent_element['id'].split('.')[1]}.{_full_name}"
                                if _full_name in self._config[_base]['enums']:
                                    property_attributes['enum'] = self._config[_base]['enums'][_full_name]
                                else:
                                    logger.warning(f"WARNING_MISSING_ENUM normalize {_base} {type} {_full_name}")

                    return
                profile_schema = self.fhir_schema.add_profile(type, property_attributes.get('profile', None))
                if not profile_schema:
                    logger.debug(f'profile_schema missing for {type}')
                    return
                # if type == profile_schema['id']:
                if f"{parent}::{parent}::{name}::{type}" in self._recursion_guard:
                    # logger.debug(f">>> prevent recursion {parent}::{name}::{type}")                    
                    return

                self._recursion_guard.append(f"{parent}::{parent}::{name}::{type}")
                property_attributes['is_profile'] = True
                profile_template = {'properties': {}}
                # logger.debug(f"recursing {name} {type} {self._parent_element}")
                self.properties(profile_template, profile_schema, name, black_list, white_list, el['definition'])
                for k in list(profile_template['properties'].keys()):
                    new_key = f"{name}.{k}"
                    template['properties'][new_key] = profile_template['properties'][k]
                if name in template['properties']:    
                    # delete the name we recursed on    
                    del template['properties'][name]

            if 'type' in property_attributes:
                expand_types(property_attributes['type'])

            if 'multiple_types' in property_attributes:                
                for type in property_attributes['multiple_types']:
                    # logger.debug(f"multiple_types {name}{type.capitalize()} {template['properties'][name]['description']}")    
                    profile_template = {'properties': {}}
                    profile_schema = self.fhir_schema.add_profile(type, None)
                    self.properties(profile_template, profile_schema, name, [], [], template['properties'][name]['description'])
                    for k in list(profile_template['properties'].keys()):
                        if k.endswith('id'):
                            continue
                        new_key = f"{name}{type.capitalize()}.{k}"
                        # logger.debug(f"new_key {new_key}")
                        include = True
                        if black_list:
                            for black_list_item in black_list:
                                if black_list_item in new_key:
                                    # logger.debug(f"<<< black_list {new_key} {black_list_item}")
                                    include = False
                        if include:
                            template['properties'][new_key] = profile_template['properties'][k]
                del template['properties'][name]

        return base

    def normalize(self, template, base):
        """Clean up, strict gen3 conformance, remove temporary attributes."""
        for p in template['properties']:
            if template['properties'][p].get('is_required', False):
                template['required'].append(p)
            for k in ['is_embedded', 'is_primitive', 'is_required']:
                if k in template['properties'][p]:                
                    del template['properties'][p][k]

        # xlate types to gen3 types
        simple_mapping = {
            'http://hl7.org/fhirpath/System.Integer': 'integer',
            'http://hl7.org/fhirpath/System.Decimal': 'float',
            'http://hl7.org/fhirpath/System.Boolean': 'boolean',
            'boolean': 'boolean',
            'string': 'string',
            'http://hl7.org/fhirpath/System.String': 'string',
        }
        
        def update_uri(d):
            # d.update({'pattern': 'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'}) or d 
            # todo add `uri` to _terms '\S*'
            d.update({'format': 'uri'}) or d 
            return d

        def update_enum(d):
            # todo add `code` to _terms [^\s]+(\s[^\s]+)*
            d.update({'enum': d.get('enum', 'WARNING_MISSING_ENUM'), 'format': 'code'})
            return d

        def update_datetime_ref(d):
            d.update(
                {
                    'oneOf': [{'type': 'string', 'format': 'date-time'}, {'type': 'null'}],
                    'term': {'$ref': '_terms.yaml#/datetime'}
                }
            )
            del d['type']
            return d

        def update_date_ref(d):
            # todo?  add `date` to _terms ([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?
            d.update(
                {
                    'oneOf': [{'type': 'string', 'format': 'date'}, {'type': 'null'}],
                    # 'term': {'$ref': '_terms.yaml#/date'}
                }
            )
            del d['type']
            return d

        def update_time_ref(d):
            # todo? add `time` to _terms ([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?
            d.update(
                {
                    'oneOf': [{'type': 'string', 'format': 'time'}, {'type': 'null'}],
                    # 'term': {'$ref': '_terms.yaml#/time'}
                }
            )
            del d['type']
            return d

        # xlate types to gen3 types with formatting
        special_mapping = {
            'uri': update_uri,
            'code': update_enum,
            'http://hl7.org/fhirpath/System.DateTime': update_datetime_ref,
            'http://hl7.org/fhirpath/System.Time': update_time_ref,
            'http://hl7.org/fhirpath/System.Date': update_date_ref
        }

        for p in template['properties']:
            if 'type' not in template['properties'][p]:
                continue
            type = template['properties'][p]['type']
            if isinstance(type, list):
                continue
            # logger.debug(type)
            mapped = simple_mapping.get(type, None)
            if mapped:
                template['properties'][p]['type'] = mapped
            else:
                mapped = special_mapping.get(type, None)
                if not mapped:
                    logger.error(f"No mapping for type {type}")
                else:
                    template['properties'][p] = mapped(template['properties'][p])
            if template['properties'][p].get('enum', None) == 'WARNING_MISSING_ENUM':
                if 'enums' in self._config[base] and p in self._config[base]['enums']:
                    template['properties'][p]['enum'] = self._config[base]['enums'][p]
                else:
                    logger.warning(f"WARNING_MISSING_ENUM normalize {base} {type} {p}")


        # xlate . notation to _ underscore 
        # remove extraneous _value postscript
        old_keys = []
        updated_keys = {}
        for p in template['properties']:
            new_key = p.replace('.', '_')
            new_key = new_key.replace('_value','')
            updated_keys[new_key] = template['properties'][p]
            old_keys.append(p)
        for p in old_keys:
            del template['properties'][p]
        template['properties'].update(updated_keys)

        for required in template['required']:
            new_key = required.replace('.', '_')
            new_key = new_key.replace('_value','')
            template['required'].remove(required)
            template['required'].append(new_key)

        # add in enums
        value_sets = ValueSets(database_path="data/valuesets.sqlite", json_path="data/valuesets.json")

        def code_value(concept_code):
            if isinstance(concept_code, str):
                return concept_code
            return concept_code['@value']

        for p in template['properties']:
            if p in ['type', 'subtype']:
                continue
            if 'enum' not in template['properties'][p]:
                continue
            # logger.debug(f"??? {p} {template['properties'][p]['enum']}")
            docstring = template['properties'][p]['enum']
            template['properties'][p]['description'] = f"{template['properties'][p]['description']}  Vocabulary from {docstring}"
            codeset = value_sets.resource(template['properties'][p]['enum'].split('|')[0])
            source = template['properties'][p]['enum']

            if not codeset:
                logger.error(f"No codeset found for {template['properties'][p]['enum']}")
                template['properties'][p]['comment_enum'] = f"No-codeset-found-for-{template['properties'][p]['enum']}"
                del template['properties'][p]['enum']
                template['properties'][p]['type'] = 'string'
            else:
                if 'concept' not in codeset['resource']:
                    logger.error(f"No concepts found in codeset {codeset['fullUrl']}")
                    template['properties'][p]['comment_enum'] = f"No-concepts-found-in-codeset-{template['properties'][p]['enum']}|codeset-{codeset['fullUrl']}"
                    del template['properties'][p]['enum']
                    template['properties'][p]['type'] = 'string'
                else:
                    if len(codeset['resource']['concept']) > 1000:
                        logger.error(f"More than 1000 concepts in codeset {template['properties'][p]['enum']}")
                        template['properties'][p]['comment_enum'] = f"More-than-1000-concepts-{template['properties'][p]['enum']}"
                        del template['properties'][p]['enum']
                        template['properties'][p]['type'] = 'string'
                    else:    
                        template['properties'][p]['enum'] = [code_value(concept['code']) for concept in codeset['resource']['concept']]

            template['properties'][p]['term'] = {
                'description': template['properties'][p]['description'],
                'termDef': {
                    'term': p,
                    'source': 'fhir',
                    'cde_id': p,
                    'cde_version': None,                
                    'term_url': source,
                }
            }

        # clean up type
        for p in template['properties']:
            if 'type' not in template['properties'][p]:
                continue
            if template['properties'][p]['type'] in ['uri']:
                template['properties'][p]['type'] = 'string'
            if template['properties'][p]['type'] in ['code']:
                del template['properties'][p]['type']
                del template['properties'][p]['format']

        return template

    def transform(self):
        """Generate schema for all properties in config."""
        template = self.template
        schema = self._schema
        template['title'] = schema.get('title', schema['id'])
        template['description'] = schema.get('description', f"//TODO {schema['id']} description goes here.")
          
        template["properties"]["type"]["enum"].append(schema['name'])
        base =  self.properties(template,schema, is_root=True)
        template['id'] = base
        template['category'] =  self._config.get(base, {}).get('category', '//TODO')
        template['links'] = self.links(schema, base)
        
        template = self.normalize(template, base)


        return template

        

@click.command()
@click.option('--path', default="./config.yaml", help='Location of config file.')

def transform(path):
    """ Reads config file, transforms from FHIR to Gen3 data model."""
    with open(path, "r") as input_stream:
        config = yaml.safe_load(input_stream)
    for resource in config:
        logger.debug(f"working on {resource}")
        # Read the schema
        schema = FHIRSchema(resource, config[resource].get('source', None))
        # Export to gen3
        gen3_schema = Gen3Configuration(schema, resource, config[resource]).transform()
        file_name = f"./output/{resource}.yaml"
        if 'alias' in config[resource]:
            file_name = f"./output/{config[resource]['alias']}.yaml"
        with open(file_name, "w") as output_stream:
            yaml_string = yaml.dump(gen3_schema, sort_keys=False)
            yaml_string = re.sub(r'comment_.* ', '# ', yaml_string)
            output_stream.write(yaml_string)


if __name__ == '__main__':
    transform()
    
