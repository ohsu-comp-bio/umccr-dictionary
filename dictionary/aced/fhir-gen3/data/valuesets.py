"""Load valuesets into sqlite"""

import sqlite3
import json
import os
import logging
import click
import requests

logger = logging.getLogger("valuesets")
# logger.setLevel(logging.INFO)

DEFAULT_DATABASE_PATH = "./valuesets.sqlite"
DEFAULT_JSON_PATH = "./valuesets.json"

_create_valuesets_table_sql = """
-- projects table
CREATE TABLE IF NOT EXISTS valuesets (
	fullUrl text PRIMARY KEY,
	type text NOT NULL,
    id text NOT NULL,
    url text NOT NULL,
	resource json
    
);
"""

# items not found in valuesets.json
_curated_valuesets = [
    {
        'fullUrl': 'http://hl7.org/fhir/ValueSet/research-study-prim-purp-type',
        'valueset': 'http://hl7.org/fhir/R4/valueset-research-study-prim-purp-type.json', 
        'codesystem':  'https://terminology.hl7.org/3.0.0/CodeSystem-research-study-prim-purp-type.json'
    },
    {
        'fullUrl': 'http://hl7.org/fhir/ValueSet/observation-interpretation',
        'valueset': 'http://hl7.org/fhir/R4/valueset-observation-interpretation.json', 
        'codesystem':  'https://terminology.hl7.org/3.0.0/CodeSystem-v3-ObservationInterpretation.json'
    },
    {
        'fullUrl': 'http://hl7.org/fhir/ValueSet/task-intent',
        'valueset': 'http://hl7.org/fhir/R4/valueset-task-intent.json', 
        'codesystem':  'http://hl7.org/fhir/R4/codesystem-task-intent.json'
    },
    {
        'fullUrl': 'http://hl7.org/fhir/ValueSet/task-code',
        'valueset': 'http://hl7.org/fhir/R4/valueset-task-code.json',
        'codesystem': 'http://hl7.org/fhir/R4/codesystem-task-code.json'
    },
    {
        'fullUrl': 'http://terminology.hl7.org/ValueSet/v2-0487',
        'valueset': 'https://terminology.hl7.org/3.0.0/ValueSet-v2-0487.json',
        'codesystem': 'https://terminology.hl7.org/3.0.0/CodeSystem-v2-0487.json'
    },
    {
        'fullUrl': 'http://terminology.hl7.org/ValueSet/v3-FamilyMember',
        'valueset': 'https://terminology.hl7.org/3.0.0/ValueSet-v3-FamilyMember.json',
        'codesystem': 'https://terminology.hl7.org/3.0.0/CodeSystem-v3-RoleCode.json'
    }
]


def _dict_factory(cursor, row):
    """Return dicts from db"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def _resource_count(database_path):
    """Load the json into a sqlite table"""

    conn = _create_connection(database_path)
    conn.row_factory = _dict_factory

    c = conn.cursor()
    c.execute("SELECT count(*) as \"resource_count\" FROM valuesets")
    data = c.fetchone()
    return data['resource_count']


def _load(database_path, json_path):
    """Load the json into a sqlite table"""

    conn = _create_connection(database_path)
    _create_table(conn, _create_valuesets_table_sql)

    with open(json_path, "r") as input_stream:
        valuesets = json.load(input_stream)

    resource_count = 0
    # expect [CodeSystem, ValueSet] as types
    for entry in valuesets['Bundle']['entry']:
        type = list(entry['resource'].keys())[0]
        id = entry['resource'][type]['id']['@value']
        fullUrl = entry['fullUrl']['@value']
        url = entry['resource'][type]['url']['@value']
        body = entry['resource'][type]
        logger.debug(f"{type}, {id}, {fullUrl}, {url}")
        c = conn.cursor()
        c.execute("insert into valuesets values (?, ?, ?, ?, ?)", [fullUrl, type, id, url, json.dumps(body)])
        resource_count += 1
        conn.commit()
    return resource_count    


def _load_curated(database_path):
    """Load a manually curated list of valuesets into db."""
    for pair in _curated_valuesets:
        conn = _create_connection(database_path)
        c = conn.cursor()

        logger.debug(f"Loading {pair['valueset']}")        
        valueset = requests.get(pair['valueset']).json()
        type = valueset['resourceType']
        id = valueset['id']
        fullUrl = pair['fullUrl']
        url = valueset['url']

        # wrangle to match shape of codesystems in valuesets.json
        codesystem_fullUrl = valueset['compose']['include']
        if isinstance(codesystem_fullUrl, list):
            codesystem_fullUrl = codesystem_fullUrl[0]['system']
        logger.debug(f"Replacing old include: {valueset['compose']['include']}")
        new_include = {k:valueset['compose']['include'][0][k] for k in valueset['compose']['include'][0]}
        new_include['system'] =  {'@value': codesystem_fullUrl}
        valueset['compose']['include'] = [new_include]
        
        logger.debug(f"{type}, {id}, {fullUrl}, {url} {codesystem_fullUrl}")
        c.execute("replace into valuesets values (?, ?, ?, ?, ?)", [fullUrl, type, id, url, json.dumps(valueset)])
        conn.commit()


        logger.debug(f"Loading {pair['codesystem']}")        
        codesystem = requests.get(pair['codesystem']).json()
        type = codesystem['resourceType']
        id = codesystem['id']
        fullUrl = codesystem_fullUrl
        url = codesystem['url']

        logger.debug(f"{type}, {id}, {fullUrl}, {url}")
        c.execute("replace into valuesets values (?, ?, ?, ?, ?)", [fullUrl, type, id, url, json.dumps(codesystem)])
        conn.commit()



def _create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    conn = sqlite3.connect(db_file)
    return conn


def _create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    c = conn.cursor()
    c.execute(create_table_sql)


class ValueSets(object):
    """Lookup FHIR ValueSet and Codeset from sqlite."""
    def __init__(self,database_path=DEFAULT_DATABASE_PATH, json_path="./valuesets.json", initialize=False) -> None:
        """Load table."""
        self.database_path = database_path
        self.json_path = json_path
        self.resource_count = 0
        if not os.path.isfile(self.database_path) or initialize:
            if os.path.isfile(self.database_path):
                logger.debug(f"Deleting existing db file {self.database_path}")
                os.unlink(self.database_path)
            logger.debug(f"Loading from {self.json_path} into {self.database_path}")
            self.resource_count = _load(self.database_path, self.json_path)
        else:
            logger.debug("Counting existing resources")
            self.resource_count = _resource_count(self.database_path)
            
    def resource(self, fullUrl):
        """Lookup."""

        logger.debug(f"Looking up {fullUrl}")
        conn = _create_connection(self.database_path)
        conn.row_factory = _dict_factory

        c = conn.cursor()
        c.execute("SELECT * FROM valuesets WHERE fullUrl=?;", [fullUrl])
        data = c.fetchone()
        if not data:
            logger.error(f"did not find valuset for {fullUrl}")
            return None
        data['resource'] = json.loads(data['resource'])
        includes = data['resource']['compose']['include']
        if not isinstance(includes, list):
            includes = [includes]
        for include in includes:            
            if 'concept' not in include:
                # logger.debug(f"include {list(include.keys())}")
                if 'system' in include:
                    codesystem_url = include['system']['@value']
                else:
                    codesystem_url = include['valueSet']['@value']
                filter = None
                if 'filter' in include:
                    # logger.debug(f"Need to apply filter {include['filter']}")
                    filter = include['filter']
                    if not isinstance(filter, list):
                        filter = [filter]
                logger.debug(f"Found {fullUrl} linking to {codesystem_url}")
                c.execute("SELECT * FROM valuesets WHERE url=?;", [codesystem_url])
                codesystem_data = c.fetchone()
                if codesystem_data:
                    codesystem_data['resource'] = json.loads(codesystem_data['resource'])
                    if filter:
                        # logger.debug(codesystem_data['resource'].keys())
                        # logger.debug(filter)
                        if isinstance(filter[0]['value'], dict):
                            filter_value = filter[0]['value']['@value']
                        else:
                            filter_value = filter[0]['value']
                        filter_values = set([filter_value])
                        new_concepts = []
                        if 'concept' not in codesystem_data['resource']:
                            logger.warning(f"No concepts found for filter in {codesystem_url}")
                            return None
                        for concept in codesystem_data['resource']['concept']:
                            value_codes = set([p.get('valueCode', None) for p in concept['property']])
                            if len(filter_values.intersection(value_codes)) > 0 :
                                # logger.debug(f"filter included {concept['code']}")
                                filter_values.add(concept['code'])

                        for concept in codesystem_data['resource']['concept']:
                            value_codes = set([p.get('valueCode', None) for p in concept['property']])
                            if len(filter_values.intersection(value_codes)) > 0 :
                                # logger.debug(f"filter included {concept['code']}")
                                new_concepts.append(concept)
                                filter_values.add(concept['code'])
                        codesystem_data['resource']['concept'] = new_concepts
                    return codesystem_data
                logger.warning(f"did not find codesystem for {codesystem_url}")
            else:
                new_data = {'resource': {'concept': []}}
                for include in includes:
                    if 'concept' in include:
                        for concept in include['concept']:
                            new_data['resource']['concept'].append(concept)
                return new_data



@click.command()
@click.option('--json_path', default=DEFAULT_JSON_PATH, help='Path of input json file.')
@click.option('--database_path', default=DEFAULT_DATABASE_PATH, help='Path of output sqlite file.')
@click.option('--initialize', default=False, help='Recreate sqlite database', is_flag=True)
@click.option('--load_curated', default=None, help='Load curated valuesets', is_flag=True)
@click.option('-v', '--verbose', count=True)
def importer(json_path, database_path, initialize, load_curated, verbose):
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
    logger = logging.getLogger("valuesets")
    if verbose == 0:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
    value_sets = ValueSets(database_path=database_path, json_path=json_path, initialize=initialize)
    logger.info(f"There are {value_sets.resource_count} resources.")

    if load_curated:
        _load_curated(database_path)

if __name__ == '__main__':
    importer()