#!/usr/bin/env python3

from hashlib import new
import yaml
import click
import re
import inflection
import requests
from pprint import pprint
import logging
from data.valuesets import ValueSets
from pprint import pprint
import pydash
import json
import flatdict
import copy

PRIMITIVE_TYPES = [
    'integer', 'uri', 'boolean', 'string', 'time', 'dateTime', 'instant', 'http://hl7.org/fhirpath/System.String',
    'http://hl7.org/fhirpath/System.Integer', 'http://hl7.org/fhirpath/System.Decimal', 'http://hl7.org/fhirpath/System.Boolean',
     'http://hl7.org/fhirpath/System.Date'
]

DONT_FOLLOW_TYPES = [ 'Extension', 'Identifier']

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
logger = logging.getLogger("model")
logger.setLevel(logging.DEBUG)



class FHIRSchema(object):

    def __init__(self, profile_name, url=None) -> None:
        """Load schema."""
        self.profiles = {}
        self.primitives = []
        self.profile_name = profile_name
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
            logger.debug(f"fetching {url} got {response.status_code}")
            return None
        self.profiles[profile_name] = response.json()
        return self.profiles[profile_name]


class Gen3Configuration(object):

    def __init__(self, fhir_schema, resource_name, config) -> None:
        super().__init__()        
        self.fhir_schema = fhir_schema
        self._schema = fhir_schema._schema
        self._config = config
        self._resource_name = resource_name
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
        white_list = self._config.get('links', [])        
        for el in schema['snapshot']['element']:
            if el['id'] in white_list:
                links.append(self.link(el, base, white_list[el['id']]))
                white_list.pop(el['id'])
        for name in white_list:
            links.append(self.link(el, base, white_list[name]))

        logger.debug(f"links: {base} {links}")
        return links


    def properties(self, schema, property_graph={}, paths={}, base=None, parent_node_name=None):
        """Recurse through properties."""
        if not base:
            base = schema['type']
        property_graph['_name'] = base

        # break apart dot notation element ids
        parent_set = False

        # deal with multi value types
        elements = schema['snapshot']['element']
        elements_to_delete = []
        elements_to_add = []
        for el in elements:
            name = el['id'].replace(f"{schema['type']}.", '')
            if '[x]' in name:
                multi_value_type_codes = [t['code'] for t in el['type']]
                logger.debug(f"{name} is multi-valued {multi_value_type_codes}")
                elements_to_delete.append(el['id'])
                for multi_value_type_code in multi_value_type_codes:
                    value_definition = copy.deepcopy(el)
                    name = name.replace('[x]', '') 
                    # new_id = f"{schema['type']}.{name}_{multi_value_type_code}"
                    new_id = f"{name}_{multi_value_type_code}"
                    logger.debug(f"multi-valued: {el['id']} --> {new_id}")
                    value_definition['id'] = new_id
                    value_definition['type'] = [{'code': multi_value_type_code}] 
                    elements_to_add.append(value_definition)
        if len(elements_to_add) > 0:
            logger.debug(f"adding multi-valued {[el['id'] for el in elements_to_add]}")       
            elements.extend(elements_to_add)
        if len(elements_to_delete) > 0:
            logger.debug(f"delete multi-valued {[el['id'] for el in elements if el['id']  in elements_to_delete]}")
            elements = [el for el in elements if el['id'] not in elements_to_delete]


        logger.debug(f"start loop base:{base} parent_node_name:{parent_node_name} first:{elements[0]['id']} last:{elements[-1]['id']}")
        for el in elements:
            logger.debug(f"\nloop current: {el['id']} parent_node_name:{parent_node_name} {property_graph.keys()}")
            if el['id'] == base:
                logger.debug(f"skipping {el['id']}")
                continue
            if 'contentReference' in el:
                logger.debug(f"contentReference ??? {el['id']} {el['contentReference']}")
                continue
            if 'type' not in el:
                logger.warning(f"'type' not found. skipping {el}")
                continue
            name = el['id'].replace(f"{schema['type']}.", '')
            type = el['type'][0]['code'] 

            parent_node = property_graph
            parent_paths = paths

            # deal with dot notation
            if '.' in name:
                if len(name.split('.')) != 2:
                    logger.warning(f"Deeply nested backbone element not supported (yet) {name} skipping")
                    continue
                parent_name = name.split('.')[0]
                new_name = name.split('.')[1]
                logger.debug(f"loop {name} has dot notation? is a {type}. Assume that {parent_name} is a BackboneElement new_name: {new_name}")
                assert name.split('.')[0] in property_graph, property_graph.keys()                
                name = new_name 
                parent_node = property_graph[parent_name]
                if not parent_set:
                    parent_paths[parent_name] = {}
                    parent_paths = parent_paths[parent_name]
                    logger.debug(f"loop  dot notation base:{base} parent_node:{parent_node_name} {parent_name}")
                    parent_set = True
        
            logger.debug(f"working on {name} {type}")
            if type in PRIMITIVE_TYPES or type in DONT_FOLLOW_TYPES:
                parent_node[name] = {'_code': type}
                parent_node[name]['element'] = el
                parent_node[name]['_name'] = name
                parent_paths[name] = {}
                logger.debug(f"loop  leaf node  base:{base} parent_node:{parent_node_name}  {name} {type}")
                continue
            
            type_schema = self.fhir_schema.add_profile(type)
            assert type_schema, el['type']
            # recurse down the graph
            parent_paths[name] = {}
            logger.debug(f"loop  parent node  base:{base} parent_node:{parent_node_name} {name} {type}")
            type_properties = self.properties(type_schema, property_graph={},  paths=paths[name], parent_node_name=name)
            parent_node[name] = type_properties
            parent_node[name] = {}
            parent_node[name]['element'] = el
            parent_node[name]['_name'] = name
            parent_node[name]['_code'] = type
            assert parent_node[name]['_code'], el
            if type == 'BackboneElement':
                logger.debug(f"recurse adding {type_schema['type']} {type_schema.keys()} {type_properties.keys()} to {name}")

        return property_graph
    
    def normalize(self, template, properties):
        """Clean up, strict gen3 conformance, remove temporary attributes."""


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
            # 'enum': d.get('enum', 'WARNING_MISSING_ENUM')
            d.update({'format': 'code'})
            return d

        def update_datetime_ref(d):
            d.update(
                {
                    'oneOf': [{'type': 'string', 'format': 'date-time'}, {'type': 'null'}],
                    'term': {'$ref': '_terms.yaml#/datetime'}
                }
            )
            return d

        def update_date_ref(d):
            # todo?  add `date` to _terms ([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?
            d.update(
                {
                    'oneOf': [{'type': 'string', 'format': 'date'}, {'type': 'null'}],
                    # 'term': {'$ref': '_terms.yaml#/date'}
                }
            )
            return d

        def update_time_ref(d):
            # todo? add `time` to _terms ([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?
            d.update(
                {
                    'oneOf': [{'type': 'string', 'format': 'time'}, {'type': 'null'}],
                    # 'term': {'$ref': '_terms.yaml#/time'}
                }
            )
            return d

        # xlate types to gen3 types with formatting
        special_mapping = {
            'uri': update_uri,
            'url': update_uri,
            'code': update_enum,
            'http://hl7.org/fhirpath/System.DateTime': update_datetime_ref,
            'http://hl7.org/fhirpath/System.Time': update_time_ref,
            'http://hl7.org/fhirpath/System.Date': update_date_ref,
            'instant': update_datetime_ref
        }


        for name, property in properties.items():

            if name not in self._config['properties']['include']:
                logger.debug(f"{name} not in include.")
                continue

            is_array = False
            is_required = False
            for max in property.get('max',[]):
                if max == '*' or int(max) > 1:
                    is_array = True
            for min in property.get('min',[]):
                if min > 0:
                    is_required = True
            
            if is_required:
               template['required'].append(name)

            assert '_code' in property, f"{name} {property}"
            assert property['_code'], f"{name} {property}"
            
            if property['_code'] in PRIMITIVE_TYPES:
                logger.debug(f"PRIMITIVE_TYPES {name} {property['_code']}")


            template['properties'][name] = {'_code': property['_code']}

            mapped = simple_mapping.get(property['_code'], None)
            if mapped:
                template['properties'][name]['type'] = mapped
            else:
                mapped = special_mapping.get(property['_code'], None)
                if not mapped:
                    logger.error(f"No mapping for type {property['_code']}")
                else:
                    template['properties'][name] = mapped(template['properties'][name])
            
            system = None
            for b in property.get('binding', []):
                if b:
                    # for e in b.get('extension', []):
                    #     valueSet = e.get('valueSet', None)
                    system = b.get('valueSet', None)
                    # logger.debug(f"{name} valueSet {system}")
            code = None
            if 'patternCodeableConcept' in property:
                for patternCodeableConcept in property['patternCodeableConcept']:
                    if patternCodeableConcept:
                        assert isinstance(patternCodeableConcept, dict), f"patternCodeableConcept={patternCodeableConcept} {name} {property}"
                        for coding in patternCodeableConcept['coding']:
                            logger.debug(f"{name} patternCodeableConcept {coding}")
                            system = coding['system']
                            code = coding['code']
                            logger.debug(f"{name} patternCodeableConcept {system} {code}")

            if system:
                template['properties'][name]['system'] = system
            if code:
                template['properties'][name]['code'] = code

            if 'definition' in property:
                template['properties'][name]['description'] = ' '.join([d for d in property['definition'] if d])


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
            if 'system' not in template['properties'][p]:
                continue

            # logger.debug(f"{p} {template['properties'][p]}")
            system = template['properties'][p]['system']
            template['properties'][p]['description'] = f"{template['properties'][p]['description']}  Vocabulary from {system}"

            if 'code' in template['properties'][p]:
                template['properties'][p]['enum'] = [template['properties'][p]['code']]
                del template['properties'][p]['code']
            else:

                if template['properties'][p]['_code'] == 'code':
                    codeset = value_sets.resource(template['properties'][p]['system'].split('|')[0])

                    if not codeset:
                        logger.error(f"No codeset found for {template['properties'][p]['system']}")
                        template['properties'][p]['comment_enum'] = f"No-codeset-found-for-{template['properties'][p]['system']}"                        
                        template['properties'][p]['type'] = 'string'
                    else:
                        if 'concept' not in codeset['resource']:
                            logger.error(f"No concepts found in codeset {codeset['fullUrl']}")
                            template['properties'][p]['comment_enum'] = f"No-concepts-found-in-codeset-{template['properties'][p]['system']}|codeset-{codeset['fullUrl']}"
                            template['properties'][p]['type'] = 'string'
                        else:
                            if len(codeset['resource']['concept']) > 1000:
                                logger.error(f"More than 1000 concepts in codeset {template['properties'][p]['system']}")
                                template['properties'][p]['comment_enum'] = f"More-than-1000-concepts-{template['properties'][p]['system']}"
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
                    'term_url': system,
                }
            }
            del template['properties'][p]['description']

        # clean up type
        for p in template['properties']:
            if 'type' not in template['properties'][p]:
                continue
            if template['properties'][p]['type'] in ['uri']:
                template['properties'][p]['type'] = 'string'
            if template['properties'][p]['type'] in ['code']:
                del template['properties'][p]['type']
                del template['properties'][p]['format']

        for p in template['properties']:
            keys_to_delete = []
            for k in template['properties'][p]:
                if k not in ['description', 'type', 'format', '$ref', 'term', 'enum', 'oneOf']:
                    if k.startswith('comment'):
                        continue
                    keys_to_delete.append(k)
            for k in keys_to_delete:
                logger.debug(f"keys_to_delete deleting {p}.{k}")
                del template['properties'][p][k]

        return template

    def transform(self):
        """Generate schema for all properties in config."""
        schema = self._schema
        
        def get_nodes(property_graph, path):
            """Grab all parts of the path in the property_graph."""
            properties = {}
            path_parts = []
            for path_part in path.split('.'):
                path_parts.append(path_part)
                partial_path = '.'.join(path_parts)
                node = pydash.get(property_graph, partial_path)
                if node:
                    assert 'id' in node['element'], node
                    properties[partial_path] =  {
                        'id': node['element']['id'],
                        'definition': node['element'].get('definition', 'no-definition?'), 
                        'keys': list(node['element'].keys()),
                        '_code': node['_code']
                    }
                else:
                    logger.warning(f"partial_path missing: {self._resource_name}.{partial_path}")
            return properties

        def get_node_values(property_graph, path, key):
            """Grab values from all parts of the path in the property_graph."""
            path_parts = []
            path_values = []
            for path_part in path.split('.'):
                path_parts.append(path_part)
                partial_path = '.'.join(path_parts)
                node = pydash.get(property_graph, partial_path)
                if node:
                    path_values.append(node['element'].get(key, None))
                else:
                    logger.warning(f"partial_path missing: {self._resource_name}.{partial_path}")
            return {path: {key: path_values}}

        def get_node_value(property_graph, path, key):
            """Grab values from the path in the property_graph."""
            node = pydash.get(property_graph, path)
            return {path: {key: pydash.get(node, key)}}

        def get_node(property_graph, path):
            """Grab values from the path in the property_graph."""
            return pydash.get(property_graph, path) 

        paths = {}
        property_graph = self.properties(schema, paths=paths, base=self._resource_name)

        with open("property_graph.json", "w") as output_stream:
            yaml_string = json.dumps(property_graph,sort_keys=False, indent=2)
            output_stream.write(yaml_string)            


        properties = {}
        for include_path in self._config['properties']['include']:
            properties.update(get_nodes(property_graph, include_path, ))
        yaml_string = yaml.dump(properties, sort_keys=False)
        # print(yaml_string)


        for include_path in self._config['properties']['include']:
            node = get_node(property_graph, include_path)
            if not node:
                logger.warning(f"include_path={include_path}")
                continue
            logger.debug(f"include_path={include_path} {node.keys()}")
            _code = node['_code']
            pydash.objects.merge(properties, {include_path: {'_code': _code}})
            pydash.objects.merge(properties, get_node_values(property_graph, include_path,'id' ))
            pydash.objects.merge(properties, get_node_values(property_graph, include_path,'definition' ))
            pydash.objects.merge(properties, get_node_values(property_graph, include_path,'min' ))
            pydash.objects.merge(properties, get_node_values(property_graph, include_path,'max' ))
            pydash.objects.merge(properties, get_node_values(property_graph, include_path,'binding' ))
            pydash.objects.merge(properties, get_node_values(property_graph, include_path,'patternCodeableConcept' ))

        yaml_string = yaml.dump(properties, sort_keys=False)
        with open("properties.yaml", "w") as output_stream:
            yaml_string = yaml.dump(properties, sort_keys=False)
            output_stream.write(yaml_string)            


        for include_path in self._config['properties']['include']:
            if include_path not in properties:
                logger.warning(f"include_path={include_path}")
                continue
            assert properties[include_path]
            assert properties[include_path]['_code'], include_path


        template = self.template
        template['title'] = schema.get('title', schema['id'])
        template['description'] = schema.get('description', f"//TODO {schema['id']} description goes here.")          
        template["properties"]["type"]["enum"].append(schema['name'])

        base = property_graph['_name']
        template['id'] = base
        template['category'] =  self._config.get('category', '//TODO')

        
        template = self.normalize(template, properties)
        template['links'] = self.links(schema, base)

        return template, paths

        

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
        gen3_schema, paths = Gen3Configuration(schema, resource, config[resource]).transform()
        file_name = f"./output/{resource}.yaml"
        if 'alias' in config[resource]:
            file_name = f"./output/{config[resource]['alias']}.yaml"

        with open(file_name, "w") as output_stream:
            yaml_string = yaml.dump(gen3_schema, sort_keys=False)
            yaml_string = re.sub(r'comment_.* ', '# ', yaml_string)
            output_stream.write(yaml_string)
            logger.info(f"Wrote gen3 config to {file_name}")

        file_name = f"./output/paths/{resource}.txt"
        with open(file_name, "w") as output_stream:
            d = flatdict.FlatDict(paths, delimiter='.')
            output_stream.write('\n'.join([k for k in d.keys()]))    
            # json.dump(paths, output_stream, sort_keys=False)        
            logger.info(f"Wrote nested property names to {file_name}")


if __name__ == '__main__':
    transform()
    
