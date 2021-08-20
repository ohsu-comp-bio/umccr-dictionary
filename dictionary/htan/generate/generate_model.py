import graphviz
import json
from yaml import dump
import click
from pprint import pprint
import re
import inflection

class HTANSchema(object):

    def __init__(self, path="HTAN.jsonld") -> None:
        """Load schema."""
        self._json_schema = json.load(open(path, 'r'))
        self._nodes = {n['@id']:n for n in self._json_schema['@graph']}
        self._rangeMembers = []
        self._dependencies = []
        for n in self._nodes.values():
            if "schema:rangeIncludes" in n:
                rangeIncludes = n["schema:rangeIncludes"]
                if not isinstance(rangeIncludes, list):
                    rangeIncludes = [rangeIncludes]
                for i in rangeIncludes:
                    self._rangeMembers.append(i['@id'])
            if "sms:requiresDependency" in n:
                dependencies = n["sms:requiresDependency"]
                if not isinstance(dependencies, list):
                    dependencies = [dependencies]
                for d in dependencies:
                    self._dependencies.append(d['@id'])

        self._rangeMembers = set(self._rangeMembers)                    
        self._dependencies = set(self._dependencies)                    
        

    @property
    def nodes(self):
        """All nodes."""
        return self._nodes

    def node(self, id):
        """A node."""
        if id in self._nodes:
            return self._nodes[id]
        return None

    def _subclasses(self, id):
        """Properties for a node."""
        _ids = []
        for n in self._nodes.values():
            if "rdfs:subClassOf" in n and "sms:requiresComponent" in n:
                if id in [i['@id'] for i in n.get("rdfs:subClassOf",[])]:
                    if id in [i['@id'] for i in n.get("sms:requiresComponent",[])]:
                        _ids.append(n['@id'])
        return set(_ids)    

    def properties(self, node=None, id=None):
        """Properties for a node."""
        if id in self._nodes:
            node = self._nodes[id]
        id = node['@id']
        dependencies = set([d['@id'] for d in node.get("sms:requiresDependency",[])])    
        includes = []
        superClassOf = []
        for n in self._nodes.values():
            if "schema:domainIncludes" in n:
                include = n["schema:domainIncludes"]
                if not isinstance(include, list):
                    include = [include]
                for i in include:    
                    if id == i['@id']:
                        includes.append(n['@id'])
            if "rdfs:subClassOf" in n:
                subclass = n["rdfs:subClassOf"]
                if not isinstance(subclass, list):
                    subclass = [subclass]
                for s in subclass:    
                    if id == s['@id']:
                        superClassOf.append(n['@id'])

        includes = set(includes)
        components = set([d['@id'] for d in node.get("sms:requiresComponent",[])])
        subclassOf = set([d['@id'] for d in node.get("rdfs:subClassOf",[])])
        neighbors = set([d for d in components if len(self._nodes[d].get("sms:requiresDependency", [])) > 0 ])
        subclasses = self._subclasses(id)
        subclasses = set(list(subclasses) + superClassOf) - self._rangeMembers - self._dependencies
        neighbors = neighbors - subclassOf
        return {'@id':id,
                'properties':sorted(list(dependencies) + list(includes)),
                'subclasses': sorted(list(subclasses)),
                'super': subclassOf,
                'neighbors': sorted(list(neighbors)),
                'comment': node.get("rdfs:comment", "")
        }


class HTANSchemaFigure(object):

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


 

class Gen3Configuration(object):
    def __init__(self, schema, node, parent=None) -> None:
        super().__init__()
        self.schema = schema
        self.node = node
        self.parent = parent
        self.template = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "id": None,
            "title": None,
            "type": "object",
            "namespace": "http://gdc.nci.nih.gov",
            "category": "clinical",
            "program": "*",
            "project": "*",
            "description": f'{self.node["comment"]}',
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
                    "enum": []
                },
                "subtype": {
                    "enum": []
                },
                "id": {
                    "$ref": "_definitions.yaml#/UUID",
                    "systemAlias": "node_id"
                },
                "state": {
                    "$ref": "_definitions.yaml#/state"
                },
                "submitter_id": {
                    "type": [
                        "string",
                        "null"
                    ]
                },
                "projects": {
                    "$ref": "_definitions.yaml#/to_many_project"
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

    def _name(self, _node):
        n = inflection.underscore(inflection.singularize(_node.get('rdfs:label', _node['@id']).split(':')[-1]))
        if n == 'biospeciman':
            n = 'biospecimen'
        return n

    def link(self, id):
        _neighbor = self.schema.node(id)
        _me = self.node
        target_type = self._name(_neighbor)
        backref = inflection.pluralize(self._name(_me))
        name = inflection.pluralize(target_type)
        return {
            'name': inflection.pluralize(name),
            'backref': backref,
            'label': 'refers_to',
            'target_type': target_type,
            'multiplicity': 'many_to_many',
            'required': True,
        }

    def parent_link(self):
        _me = self.node
        target_type = self._name(self.parent)
        backref = inflection.pluralize(self._name(_me))
        name = inflection.pluralize(target_type)
        # links:
        #   - name: subjects
            #   backref: families
            #   label: member_of
            #   target_type: subject
            #   multiplicity: many_to_many
            #   required: true
        return {
            'name': inflection.pluralize(name),
            'backref': backref,
            'label': 'refers_to',
            'target_type': target_type,
            'multiplicity': 'many_to_many',
            'required': True,
        }


    def links(self):
        return [self.link(l) for l in self.node['neighbors']]

    def properties(self, template,node):
        """Render gen3 properties."""
        schema_node = self.schema.node(node['@id'])
        template["properties"][f"comment_{schema_node['rdfs:label']}"] = f'{schema_node["rdfs:label"]}'
        for p in node['properties']:
            schema_node = self.schema._nodes[p]
            if "schema:rangeIncludes" not in schema_node:
                template["properties"][schema_node['rdfs:label']] = {
                    'type': 'string',
                    'description': f'{schema_node["rdfs:comment"]}'
                }
            else:
                if not isinstance(schema_node["schema:rangeIncludes"], list):
                    schema_node["schema:rangeIncludes"] = [schema_node["schema:rangeIncludes"]]
                template["properties"][schema_node['rdfs:label']] = {
                    'description': f"{schema_node['rdfs:comment']}",
                    'enum': [e['@id'].split(':')[-1] for e in schema_node["schema:rangeIncludes"]]
                }
                # raise Exception(f'{template["properties"][schema_node["rdfs:label"]]}')

    def category(self, id):
        if id == 'file':
            return 'data_file'
        return 'clinical'


    def save(self):
        node = self.node
        template = self.template
        schema_node = self.schema.node(node['@id'])
        template['id'] = self._name(schema_node)
        template['title'] = schema_node['rdfs:label']
        # template['description'] = schema_node['rdfs:comment']
        template['category'] = self.category(template['id'])
        # template['links'] = self.links()
        template["properties"]["type"]["enum"].append(schema_node['rdfs:label'])
        for st in node['subclasses']:
            schema_node = self.schema._nodes[st]
            template["properties"]["subtype"]["enum"].append(schema_node['rdfs:label'])
            st_node = self.schema.properties(id=st)
            self.properties(template,st_node)
        for neighbor_id in self.node['neighbors']:
            _neighbor = self.schema.node(neighbor_id)
            _backref = inflection.pluralize(self._name(_neighbor))
            if _backref == 'patients':
                print(f"Skipping link {template['id']}->{_backref}")
                continue
            template["properties"][_backref] = {
                "$ref": "_definitions.yaml#/to_many"}

        if len(node['properties']) > 0:  # len(node['subclasses']) == 0 and
            self.properties(template, node)

        if self.parent:
            parent_link = self.parent_link()
            if parent_link['name'] == 'biospecimen' and parent_link['backref']:
                print(f"Skipping link {parent_link['name']}->{parent_link['backref']}")
            else:
                template['links'].append(parent_link)
                template['required'].append(parent_link['name'])
                template["properties"][parent_link['name']] = {
                    "$ref": "_definitions.yaml#/to_many"}

        # special case for patient, link back to project
        if template['id'] == 'patient':
            template["links"].append(
                {
                    "name": "projects",
                    "backref": "patients",
                    "label": "reference_to",
                    "target_type": "project",
                    "multiplicity": "many_to_one",
                    "required": True
                }
            )
        # special case for file, link back to assay
        if template['id'] == 'file':
            template["links"].append(
                {
                    "name": "assay",
                    "backref": "files",
                    "label": "reference_to",
                    "target_type": "assay",
                    "multiplicity": "many_to_one",
                    "required": True
                }
            )
            template["links"].append(
                {
                    "name": "core_metadata_collections",
                    "backref": "files",
                    "label": "data_from",
                    "target_type": "core_metadata_collection",
                    "multiplicity": "many_to_one",
                    "required": False
                }
            )
            template["properties"]["assay"] = {
                "$ref": "_definitions.yaml#/to_one"
            }
            template["properties"]["core_metadata_collections"] = {
                "$ref": "_definitions.yaml#/to_many"
            }
            template["properties"]["$ref"] =  "_definitions.yaml#/data_file_properties"
            template["properties"]["data_format"] = {
                "term": {
                    "$ref": "_terms.yaml#/data_format"
                },
                "enum": [
                    "VCF",
                    "junc",
                    "tbi",
                    "txt",
                    "tsv",
                    "xlsx",
                    "bam",
                    "bai",
                    "fastq",
                    "bigWig",
                    "crai",
                    "cram",
                    "bed",
                    "bim",
                    "fam",
                    "pdf",
                    "idat",
                    "svs",
                    "tab",
                    "gds",
                    "other"
                ]
            }
            # move HTAN fileFormat to gen3 required field data_type
            template["properties"]["data_type"] = template["properties"]["fileFormat"]
            del template["properties"]["fileFormat"]
            template["properties"]["data_category"] = {
                "term": {
                    "$ref": "_terms.yaml#/data_category"
                },
                "enum": [
                    "Analysis",
                    "Sequencing Reads",
                    "Single Nucleotide Variation",
                    "Simple Nucleotide Variation",
                    "Transcriptome Profiling",
                    "Clinical",
                    "Imaging",
                    "Supplemental",
                    "Other"
                ]
            }
            template["required"].extend(['data_type', 'data_format', 'data_category'])
        # special case for assay, link back to biospecimen
        if template['id'] == 'assay':
            template["links"].append(
                {
                    "name": "biospecimen",
                    "backref": "files",
                    "label": "reference_to",
                    "target_type": "biospecimen",
                    "multiplicity": "many_to_many",
                    "required": True
                }
            )
            template["properties"]["biospecimen"] = {
                "$ref": "_definitions.yaml#/to_one"
            }
        # special case for biospecimen, link back to patient
        if template['id'] == 'biospecimen':
            template["links"].append(
                {
                    "name": "patient",
                    "backref": "biospecimens",
                    "label": "reference_to",
                    "target_type": "patient",
                    "multiplicity": "one_to_many",
                    "required": True
                }
            )
            template["properties"]["patient"] = {
                "$ref": "_definitions.yaml#/to_one"
            }



        # save this node
        yaml_string = dump(template, sort_keys=False)
        yaml_string = re.sub(r'comment_.* ', '# ', yaml_string)
        with open(f"../gdcdictionary/schemas/{template['id']}.yaml", "w") as output:
            output.write(yaml_string)
        print(f"wrote ../gdcdictionary/schemas/{template['id']}.yaml")

@click.command()
@click.option('--id', help='Entity ID, e.g "bts:BulkRNA-seqLevel1"')
@click.option('--path', default="HTAN.jsonld", help='e.g. wget https://raw.githubusercontent.com/ncihtan/schematic/main/data/schema_org_schemas/HTAN.jsonld')
@click.option('--figure/--no-figure', default=False, help='Generate PDF Figure')

def view(id, path, figure):
    assert id, 'Please specify an @id found in the schema, e.g "--id bts:BulkRNA-seqLevel1"'
    # Read the schema
    schema = HTANSchema(path=path)
    # Find the desired node
    node = schema.properties(id=id)
    # raise Exception(f"{node}")

    # Create the PDF view
    if figure:
        HTANSchemaFigure(schema, node).view()
    
    # Export to gen3
    gen3_config = Gen3Configuration(schema, node)
    gen3_config.save()
    for neighbor in gen3_config.node['neighbors']:
        neighbor_node = schema.properties(id=neighbor)
        # if 'Exposure' in neighbor:
        #     raise Exception(f"{neighbor_node}")
        neighbor_config = Gen3Configuration(schema, neighbor_node, parent=node)
        neighbor_config.save()


if __name__ == '__main__':
    view()



# fields = ['bts:HTANDataFileID', 'bts:HTANParticipantID']
# for f in fields:
#     print(f"Entities that link via {f}")
#     for n in schema._nodes.values():
#         if "sms:requiresDependency" in n:
#             requiresDependency = n["sms:requiresDependency"]
#             if not isinstance(requiresDependency, list):
#                 requiresDependency = [requiresDependency]
#             for i in requiresDependency:
#                 if i['@id'] == f:
#                     isA = n["rdfs:subClassOf"][-1]['@id']
#                     print(f"\t{n['@id']} is a/part of {isA}")


# last_words = set()
# for n in schema._nodes.values():    
#     if "rdfs:comment" in n and n["rdfs:comment"]:
#         last_words.add(n["rdfs:comment"].split()[-1])
# sorted(list(last_words))

# sms_keys = set()
# for n in schema._nodes.values():    
#     for k in n.keys():
#         if k.startswith('sms'):
#             sms_keys.add(k)
# sorted(list(sms_keys))
