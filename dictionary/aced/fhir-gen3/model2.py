
import os
import logging
from re import L
import requests
import json
import inspect
import importlib
from copy import deepcopy
from pprint import pprint
from data.valuesets import ValueSets
# for distinct, separate Resources
from fhirclient.models.domainresource import DomainResource 
from fhirclient.models.element import Element
# for embedded types
from fhirclient.models.backboneelement  import BackboneElement

from dictionaryutils import dump_schemas_from_dir
import flatdict
import yaml
import click



logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
logger = logging.getLogger("model")
logger.setLevel(logging.DEBUG)


# see https://github.com/smart-on-fhir/fhir-parser/blob/master/Default/mappings.py

# Properties that need to be renamed because of language keyword conflicts
reservedmap = {
    'for': 'for_fhir',
    'from': 'from_fhir',
    'class': 'class_fhir',
    'import': 'import_fhir',
    'global': 'global_fhir',
    'assert': 'assert_fhir',
    'except': 'except_fhir',
}
reservedmap_inverted = {v:k for (k,v)in reservedmap.items()}

def class_for_name(module_name, class_name):
    """Load the module, will catch and log ModuleNotFoundError if module cannot be loaded."""
    try:
        m = importlib.import_module(module_name)
        # get the class, will raise AttributeError if class cannot be found
        c = getattr(m, class_name)
        return c
    except ModuleNotFoundError as e:
        logger.warning(f"{module_name}, {class_name}, {e}")


class FHIRSchema(object):
    """Fetch and cache schemas."""


    def __init__(self) -> None:
        """Load schema."""
        self.primitives = []

    def get_profile(self, profile_name, url=None):
        """Retrieve schema."""
        if profile_name in self.primitives:
            return None
        if profile_name == 'FHIRReference':
            profile_name = 'reference'
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

        file_name = f'cache/{profile_name}.profile.json'    
        if os.path.isfile(file_name):
            with open(file_name, 'r') as input:
                logger.debug(f'found in cache {file_name}')
                return json.load(input)

        logger.debug(f"fetching {url}")
        response = requests.get(url)
        if response.status_code != 200:
            self.primitives.append(profile_name)
            logger.debug(f"fetching {url} got {response.status_code}")
            return None

        profile =  response.json()
        file_name = f"cache/{profile['name']}.profile.json"
        with open(file_name, 'w') as output:
            logger.debug(f'wrote to cache {file_name}')
            json.dump(profile, output)

        return profile


# from anvil.clients.fhir_client import DispatchingFHIRClient
# from anvil.clients.smart_auth import GoogleFHIRAuth


# token = None

# settings = {
#     'app_id': __name__,
#     'api_bases': [
#         'https://healthcare.googleapis.com/v1beta1/projects/fhir-test-16-342800/locations/us-west2/datasets/anvil-test/fhirStores/public/fhir',
#     ]
# }
# client =  DispatchingFHIRClient(settings=settings, auth=GoogleFHIRAuth(access_token=token))

# document_references = DocumentReference.where(struct={}).perform_resources(client.server)
# document_reference = document_references[0]

# for name, jsname, typ, is_list, of_many, not_optional in document_reference.elementProperties():
#     if not_optional:
#         print(name,typ,  issubclass(typ, FHIRAbstractBase))

# elementProperties
# ("name", "json_name", type, is_list, "of_many", not_optional)






class Gen3Configuration(object):

    def __init__(self, config) -> None:
        super().__init__()        
        self._schema = FHIRSchema()
        self._config = config
        self.template = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "id": None,
            "title": None,
            "type": "object",
            "namespace": "http://aced-idp.org",
            "category": "administrative",
            "program": "*",
            "project": "*",
            "description": 'description goes here',
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

    def _get_type_from_source(self, source):
        """Get structure definition and class from source"""
        structure_definition = self._schema.get_profile(None, url=source)
        assert structure_definition
        resource = structure_definition['type']
        clazz = class_for_name(f"fhirclient.models.{resource.lower()}", resource)
        assert clazz
        logger.info(f"Based on {clazz.__name__} on {resource} from {source}")
        return (clazz, structure_definition)


    # def show_paths_resource(self, parent_type, source=None):
    #     """Get the StructureDefinition, and it's properties so we can get property types, docs, enum etc."""
    #     if not parent_type and not source:
    #         raise Exception("Missing both parent_type and source")

    #     if not parent_type:
    #         clazz, structure_definition = self._get_type_from_source(source)
    #         parent_type = clazz
        
    #     assert issubclass(parent_type, DomainResource)

    #     if not parent_name:
    #         parent_name = parent_type.__name__

    #     structure_definition = self._schema.get_profile(parent_type.__name__, url=source)
        
    #     assert structure_definition, parent_type

    #     # instantiate it so we can use smart-on-fhir's parser
    #     obj = parent_type()

    #     # minimal information about root
    #     paths = {'_root': {}}
    #     for p in ['id', 'description']:
    #         paths['_root'][p] = structure_definition[p]

    #     # loop through all properties
    #     for name, jsname, typ, is_list, of_many, not_optional in obj.elementProperties():
    #         # don't follow
    #         if typ.__name__ in  ['Extension', 'Meta']:
    #             continue
        
    #         if issubclass(typ, DomainResource) or issubclass(typ, Element) and typ.__name__ not in  ['Identifier', 'Extension', 'Meta']:




    def show_paths(self, parent_type, source=None, indent_level=0, parent_structure_definitions=[], processed_names=[], parent_name=None):
        """Get the StructureDefinition, so we can get attribute docs, enum etc."""

        if not parent_type and not source:
            raise Exception("Missing both parent_type and source")

        if not parent_type:
            clazz, structure_definition = self._get_type_from_source(source)
            parent_type = clazz

        if not parent_name:
            parent_name = parent_type.__name__

        if issubclass(parent_type, DomainResource):
            structure_definition = self._schema.get_profile(parent_type.__name__, url=source)
            
            assert structure_definition, parent_type

            # pass to children
            parent_structure_definitions.insert(0, structure_definition)

            # # get formal name
            # resourceType = structure_definition['id']
            logger.debug(f"is domain {parent_name}")
        else:
            # use parent's embedded definitions
            structure_definition = parent_structure_definitions[0]     
            logger.debug(f"is backboneelement {parent_name}")

        # instantiate it so we can use smart-on-fhir's parser
        obj = parent_type()
        
        # minimal information about root
        paths = {'_root': {}}
        for p in ['id', 'description']:
            paths['_root'][p] = structure_definition[p]

        

        for name, jsname, typ, is_list, of_many, not_optional in obj.elementProperties():
                if typ.__name__ in  ['Extension', 'Meta']:
                    continue
                my_definition = None
                for sd in parent_structure_definitions:
                    # logger.warning(sd['id'])
                    for el in sd['snapshot']['element']:
                        # logger.warning(f"simple match {sd['id']} {el['id']} {name}")
                        if el['id'] == f"{parent_name}.{name}":
                        # if el['id'].endswith(name):
                            my_definition = el 
                            break
                    if my_definition:
                        break                               
                    if of_many:
                        # logger.warning(f"multivalued {name} {of_many}")
                        for el in sd['snapshot']['element']:
                            # logger.warning(f"of many {sd['id']} {el['id']} {of_many}")
                            if el['id'] == f"{parent_name}.{of_many}[x]":
                            # if el['id'].endswith(f"{of_many}[x]"):
                                my_definition = el
                                break
                    if my_definition:
                        break                               
                    if name in reservedmap_inverted:
                        # logger.error(f"reserved map {name} {reservedmap_inverted[name]}")
                        for el in sd['snapshot']['element']:
                            # logger.warning(f"reserved map {sd['id']} {el['id']} {reservedmap_inverted[name]}")
                            if el['id'] == f"{parent_name}.{reservedmap_inverted[name]}":
                            # if el['id'].endswith(reservedmap_inverted[name]):
                                my_definition = el
                                break
                    if my_definition:
                        break                               

                if not my_definition:
                    logger.warning(f"SHOULD find a definition for {obj.__class__.__name__}.{name}, did not find it {parent_name} .")
                    continue

                # print(' ' * indent_level, name,typ.__name__, my_definition['short'])
                if parent_name:
                    recursion_check = f"{parent_name}.{name}"
                else:
                    recursion_check = f"{structure_definition['id']}.{name}"

                if issubclass(typ, DomainResource) or issubclass(typ, Element) and typ.__name__ not in  ['Identifier', 'Extension', 'Meta']:
                    if  recursion_check not in processed_names:
                        processed_names.append(recursion_check)
                        child_names = self.show_paths(
                            typ,
                            indent_level=indent_level + 2,
                            parent_structure_definitions=parent_structure_definitions,
                            processed_names=processed_names,
                            parent_name=recursion_check
                        )
                        for child_name, child_property_def in child_names.items():
                            paths[f"{name}.{child_name}"] = child_property_def
                    else:
                        logger.error(f"{recursion_check} found in processed_names, breaking recursion")
                elif issubclass(typ, BackboneElement):

                    child_names = self.show_paths(
                        typ,
                        indent_level=indent_level + 2,
                        parent_structure_definitions=parent_structure_definitions,
                        processed_names=processed_names,
                        parent_name=recursion_check
                    )
                    for child_name, child_property_def in child_names.items():
                        paths[f"{name}.{child_name}"] = child_property_def                    
                else:
                    paths[name] = {
                        'name': name,
                        'jsname': jsname,
                        'type': typ,
                        'is_list': is_list,
                        'of_many': of_many,
                        'not_optional': not_optional,
                        'definition': my_definition    
                    }
        return paths

    def normalize(self, template, properties):
        """Clean up, strict gen3 conformance, remove temporary attributes."""

        # xlate types to gen3 types
        simple_mapping = {
            'http://hl7.org/fhirpath/System.Integer': 'integer',
            'http://hl7.org/fhirpath/System.Decimal': 'float',
            'http://hl7.org/fhirpath/System.Boolean': 'boolean',
            'boolean': 'boolean',
            'string': 'string',
            'str': 'string',
            'http://hl7.org/fhirpath/System.String': 'string',
            'bool': 'boolean',
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
            'url': update_uri,
            'code': update_enum,
            'http://hl7.org/fhirpath/System.DateTime': update_datetime_ref,
            'http://hl7.org/fhirpath/System.Time': update_time_ref,
            'http://hl7.org/fhirpath/System.Date': update_date_ref,
            'instant': update_datetime_ref,
            'FHIRDate': update_datetime_ref,
        }


        for name, property in properties.items():
            _definition = property['_definition']
            
            if _definition['not_optional']:
               template['required'].append(name)

            _type = _definition['type'].__name__
            template['properties'][name] = {
                'type': _type,
                'description': _definition['definition']['definition'],                
            }


            mapped = simple_mapping.get(_type, None)
            if mapped:
                template['properties'][name]['type'] = mapped
            else:
                mapped = special_mapping.get(_type, None)
                if not mapped:
                    logger.error(f"No mapping for type {_type}")
                else:
                    template['properties'][name] = mapped(template['properties'][name])
            
            system = None
            
            bindings = _definition['definition'].get('binding', [])
            if not isinstance(bindings, list):
                bindings = [bindings]
            for b in bindings:
                system = b.get('valueSet', None)
                logger.debug(f"{name} valueSet {system}")
            code = None
            if 'patternCodeableConcept' in _definition['definition']:
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
                if 'system' in  template['properties'][p]:
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

    def transform(self, parent_type, source, resource):
        """Render a gen3 schema."""

        if not parent_type and not source:
            raise Exception("Missing both parent_type and source")

        if not parent_type:
            clazz, _ = self._get_type_from_source(source)
            parent_type = clazz


        # resource = parent_type.__name__
        config = self._config[resource]
        logger.debug(f"working on {parent_type.__name__} {resource} {config}")
        paths = self.show_paths(parent_type, source)

        properties = {}
        for include_property in config['properties']['include']:
            assert include_property in paths, f"{include_property} not found in {resource}\n{paths.keys()}"
            properties[include_property] = paths[include_property]

        template = deepcopy(self.template)
        template['title'] = resource
        _root = paths['_root']
        template['description'] = _root.get('description', f"//TODO {_root['id']} description goes here.")          
        template["properties"]["type"]["enum"].append(resource)
        template["category"] = config.get("category", "//TODO")

        template_properties = {}
        for property in properties:
            template_properties[property] = {
                '_definition': properties[property]
            }
        template = self.normalize(template, template_properties)


        return template

    


@click.command()
@click.option('--path', default="./config.yaml", help='Location of config file.')
@click.option('--output_path', default="./schemas", help='Location of output schemas.')

def transform(path, output_path):
    """ Reads config file, transforms from FHIR to Gen3 data model."""
    with open(path, "r") as input_stream:
        config = yaml.safe_load(input_stream)

    for resource in config:
        gen3_config = Gen3Configuration(config)
        # TODO move this to show paths
        clazz = class_for_name(f"fhirclient.models.{resource.lower()}", resource)
        source = config[resource].get('source', None)
        logger.info(f"working on {resource} {clazz} {source}")

        # paths = gen3_config.show_paths(clazz, source)
        # file_name = f"./{output_path}/{resource}.paths.yaml"
        # with open(file_name, "w") as output_stream:
        #     yaml_string = yaml.dump(paths, sort_keys=False)
        #     output_stream.write(yaml_string)
        #     logger.info(f"Wrote paths to {file_name}")


        gen3_schema = gen3_config.transform(clazz, source, resource=resource)
        file_name = f"./{output_path}/{resource}.yaml"
        with open(file_name, "w") as output_stream:
            yaml_string = yaml.dump(gen3_schema, sort_keys=False)
            print(gen3_schema.__class__)
            output_stream.write(yaml_string)
            logger.info(f"Wrote gen3 config to {file_name}")
 
    # file_name = f'{output_path}/dump.json'
    # with open(file_name, 'w') as f:
    #     json.dump(dump_schemas_from_dir(output_path), f)
    # logger.info(f"wrote schema to {file_name}")

if __name__ == '__main__':
    transform()
    
