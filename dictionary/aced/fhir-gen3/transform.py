#!/usr/bin/env python3

"""Flatten FHIR json for PFB, per config.yaml."""

from tokenize import Name
from unicodedata import name
import yaml
import os
import click
import glob
import json
import logging
from flatten_json import flatten
import csv
from collections import defaultdict
import re
from dictionaryutils import dump_schemas_from_dir
import importlib

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
logger = logging.getLogger("transform")
logger.setLevel(logging.INFO)

class MissingConfig(Exception):
    pass

class MissingProperty(Exception):
    pass

class MissingLink(Exception):
    pass

class MissingId(Exception):
    pass


def class_for_name(type_from_path):
    """Load the module, will catch and log ModuleNotFoundError if module cannot be loaded."""
    if isinstance(type_from_path, list):
        module_name = type_from_path[0]
        class_name = type_from_path[1]
    else:
        class_name = type_from_path.split('.')[0]
        module_name = f"fhirclient.models.{class_name.lower()}"
        class_name = type_from_path
    try:
        m = importlib.import_module(module_name)
        c = getattr(m, class_name)
        return c
    except Exception as e:
        logger.error((type_from_path, module_name, class_name,e ))
        raise e    
    # except ModuleNotFoundError as e:
    #     pass
    # try:        
    #     return eval(class_name, {})
    # except ModuleNotFoundError as e:
    #     logger.warning(f"{module_name}, {class_name}, {e}")


class FHIRResource:

    def __init__(self, file_path, config) -> None:
        self.file_path = file_path
        assert os.path.isfile(self.file_path), f"{file_path} MUST exist"
        self.config = config
        assert config, "config MUST be set"
        self.reported_warnings = []
        resource = next(self._sniff())
        self.resourceType = resource['resourceType']
        self.name = resource['resourceType']
        self.resource_config = None
        if self.resourceType in self.config:
            self.resource_config = self.config[self.resourceType]
        else:
            for k, config in self.config.items():
                if config.get('subtype_of', None) == self.resourceType:
                    self.resource_config = config
                    self.resourceType = k

        if not self.resource_config:
            raise MissingConfig(f"Missing config for {self.resourceType} {file_path}")
        
    def _link(self, fhir_reference):
        """Transform to PFB friendly submitter_id link."""
        if 'reference' in fhir_reference:
            return {'submitter_id': fhir_reference['reference'].split('/')[-1]}   
        if 'valueReference' in fhir_reference:
            return {'submitter_id': fhir_reference['valueReference']['reference'].split('/')[-1]}   
        raise f'Not supported pfb link {fhir_reference}'

    def _transform(self, fhir_resource):
        """Prune and flatten."""

        assert 'resourceType' in fhir_resource, f"missing resourceType {fhir_resource}"
        resource_config = None
        if fhir_resource['resourceType'] in self.config:
            resource_config = self.config[fhir_resource['resourceType']]
        else:
            for config in self.config.values():
                if config.get('subtype_of', None) == fhir_resource['resourceType']:
                    resource_config = config

        if not resource_config:
            raise MissingConfig(f"Could not find config for {fhir_resource} {fhir_resource['resourceType']}")
        
        self.resourceType = fhir_resource['resourceType']

        assert 'links' in resource_config, f"missing 'links' in {resource_config}"
        links = {}
        for link in resource_config['links']:
            if link.startswith(fhir_resource['resourceType']):
                link = link.replace(f"{fhir_resource['resourceType']}.", '')
            if link in fhir_resource:
                if isinstance(fhir_resource[link], dict):
                    links[link] = self._link(fhir_resource[link])                  
                else:
                    for l in fhir_resource[link]:
                        links[link] = self._link(l)
        if len(links) == 0 and 'project' not in resource_config['links']:
            logger.warning(f"Could not find any of {resource_config['links']} in {fhir_resource}")
            # raise MissingLink(f"Could not find any of {resource_config['links']} in {fhir_resource}")

        # # retrieve property value
        # properties = {}
        
        # # simple 
        # for property in resource_config['properties']['include']:
        #     if property in fhir_resource:
        #         properties[property] = fhir_resource[property]
        # # nested lists, etc.
        # if 'accessor' in resource_config['properties']:
        #     for accessor in resource_config['properties']['accessor']:
        #         if 'pydash' not in accessor:
        #             # user can provide a pydash path
        #             property = re.sub('\[.*?\]', '',accessor)
        #             assert property in resource_config['properties']['include'], f"Accessor to property name regexp failed. {accessor} {property}"
        #             properties[property] = pydash.objects.get(fhir_resource, accessor)
        #         else:
        #             # or a pydash function call 
        #             # e.g. ('foo', pydash.objects.get('foo', fhir_resource))
        #             (property, value) = eval(accessor,{'pydash': pydash, 'fhir_resource': fhir_resource})
        #             properties[property] = value
        # if len(properties.keys()) != len(resource_config['properties']['include']):
        #     if 'MissingProperty' not in self.reported_warnings:
        #         missing = set(resource_config['properties']['include']) - set(properties.keys()) 
        #         logging.warning(f"MissingProperty {missing} {resource_config['properties']['include']} in {fhir_resource}")
        #         self.reported_warnings.append('MissingProperty')

        # set identifier using the fhir id
        # alternate strategy would be to use the identifier[].value
                
        assert 'id' in fhir_resource, f"missing 'id' in {fhir_resource}"
        id = fhir_resource['id']

        # flatten the results, use underscores
        pruned = {'submitter_id': id}
        logger.debug((fhir_resource['resourceType'], links))
        pruned.update(fhir_resource)
        # for more information on the flatten method see https://towardsdatascience.com/flattening-json-objects-in-python-f5343c794b10
        flattened = flatten(pruned, '_')
        flattened.update(links)

        # # xlate . notation to _ underscore 
        # old_keys = []
        # updated_keys = {}
        # for p in flattened:
        #     new_key = p.replace('.', '_')
        #     updated_keys[new_key] = flattened[p]
        #     old_keys.append(p)
        # for p in old_keys:
        #     del flattened[p]
        # flattened.update(updated_keys)

        return flattened

    def _sniff(self):
        """Sniff json or ndjson, yield row."""
        with open(self.file_path, "r") as fhir_resource_file:
            try:
                fhir_resources = json.load(fhir_resource_file)
                if isinstance(fhir_resources, dict):
                    yield fhir_resources
                    return
                for fhir_resource in fhir_resources:
                    yield fhir_resource
                    return
            except json.decoder.JSONDecodeError:
                fhir_resource_file.seek(0)                
                for line in fhir_resource_file:
                    yield json.loads(line)

    def read(self):
        """Sniff json or ndjson, return transformed resource."""
        for fhir_resource in self._sniff():
            yield self._transform(fhir_resource)


INDEX_PATTERN = re.compile("_[0-9]*_")
def _make_schema_key(key):
    """Make a flattened key compliant with the key created by model/paths."""
    return re.sub(INDEX_PATTERN, '.', key).replace('_', '.')

@click.command()
@click.option('--config_path', default="./config.yaml", help='Location of config file.')
@click.option('--input_path', help='Location of input FHIR resources directory.')
@click.option('--output_path', default="./output", help='Where to place output files.')
@click.option('--output_type', default="json", type=click.Choice(['json', 'tsv']), help='Output file format.')
@click.option('--limit', default=None, type=int, help='Maximum number of resources per entity.')
@click.option('--schemas_path', default="./schemas", help='Where to place schema files.')
def transform(config_path, input_path, output_path, output_type, limit, schemas_path):
    """ Reads config file, transforms from FHIR Resources into simplified, flattened json."""
    assert os.path.isfile(config_path), "Please specify a configuration path"
    with open(config_path, "r") as input_stream:
        config = yaml.safe_load(input_stream)

    assert os.path.isdir(input_path), "Please specify a directory path"
    input_path = f"{input_path}/**/*.*json"
    files = glob.glob(input_path)
    assert len(files) > 0, f"Did not find any json files in {input_path}"

    for file in files:
        try:
            try:
                resources = FHIRResource(file, config)
            except MissingConfig as e:
                logger.warning(e)
                continue
            resourceType = resources.resourceType
            output_file_path = f"{output_path}/{resourceType}.{output_type}"
            dict_writer = None
            resource_keys = defaultdict(set)
            with open(output_file_path, "w") as output_file:
                logger.debug(resources.file_path)
                count = 0
                for resource in resources.read():
                    for k in resource.keys():
                        resource_keys[_make_schema_key(k)].add(k)
                    if output_type == "json":
                        id = resource['id']
                        name = resource['resourceType']
                        del resource['id']
                        del resource['resourceType']
                        _obj = {'id': id, 'name': name}
                        if 'links' in resource:
                            relations = resource['links']
                            del resource['links']
                            _obj['relations'] = relations
                        _obj['object'] =  resource                        
                        json.dump(_obj, output_file)                        
                        output_file.write('\n')
                    else:
                        if not dict_writer:
                            dict_writer = csv.DictWriter(output_file, resource.keys(), delimiter='\t')
                            dict_writer.writeheader()
                        dict_writer.writerow(resource)
                    count += 1
                    if limit and count == limit:
                        break
                    
            logger.info(f"Wrote data to {output_file_path}")

            # correlate keys in paths with keys we found in fhir resource
            file_name = f"./paths/{resourceType}.paths.json"
            if not os.path.isfile(file_name):
                raise Exception(f"{file_name} {resources.name}")
            with open(file_name) as input_stream:
                paths = json.load(input_stream)
            # rehydrate type
            for path in paths.values():
                path['type'] = class_for_name(path['type'])
            
            assert '_root' in paths, f"Missing paths for {resources.resourceType}"
            resource_path_keys = set(resource_keys.keys())
            path_keys = set(paths.keys())
            key_diff = resource_path_keys - path_keys
            ignore_me = ['resourceType', 'identifier', 'submitter', 'meta']
            for k in list(key_diff):
                for ignore in ignore_me:
                    if k.startswith(ignore):
                        key_diff.remove(k)
            if len(key_diff) != 0:
                logger.debug(f"No paths for: {key_diff}")
            assert len(resource_path_keys) > 1, "No paths at all?" 

            for k in resource_keys:
                if k not in paths:
                    continue
                paths[k]['_instances'] = list(resource_keys[k])

            
            from model import Gen3Configuration
            file_name = f"./{schemas_path}/{resourceType}.yaml"
            with open(file_name, "w") as output_stream:
                gen3_config = Gen3Configuration(config)
                yaml_string = yaml.dump(gen3_config.transform_instances(paths), sort_keys=False)
                output_stream.write(yaml_string)
                logger.info(f"Wrote schema fragment to {file_name}")            


        except MissingConfig as e:
            logger.error(f"{file} has no config {e}")
        except MissingLink as e:
            logger.error(f"{file} {e}")
        
    file_name = f'{schemas_path}/dump.json'
    with open(file_name, 'w') as f:
        json.dump(dump_schemas_from_dir(schemas_path), f)
    logger.info(f"Wrote schema to {file_name}")


if __name__ == '__main__':
    transform()

