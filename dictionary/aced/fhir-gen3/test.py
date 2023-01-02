#!/usr/bin/env python3

from fastavro import reader
import click
from pprint import pprint
from collections import defaultdict
    

@click.command()
@click.option('--file_name', default="1000G.pfb.avro", help='Location of PFB avro file.')
@click.option('--expected_patient_count', default=199, help='Minimum number of Patients')

def cli(file_name, expected_patient_count):

    records = []

    with open(file_name, 'rb') as fo:
        records = [record for record in reader(fo)]

    print("Record Order:")
    seen_already = set()
    for r in records:
        if r['name'] not in seen_already:
            print(r['name'])
            seen_already.add(r['name'])

    with_relations = [r for r in records if len(r['relations']) > 0]
    print(f"{file_name}\nRaw counts:")
    pprint ({
        'Records with relationships':len(with_relations),
        'Records': len(records)
    }, indent=4)


    counts = defaultdict(int)
    for r in records:
        counts[r['name']] +=1 


    print("Counts by type:")

    pprint (dict(counts), indent=4)

    def by_name(name):
        return [r for r in records if r['name'] == name]

    def by_id(id):
        return [r for r in records if r['id'] == id or r['object'].get('submitter_id') == id]  

    def check_links(obj, dst_names):
        assert 'relations' in obj
        for r in obj['relations']:
            assert r['dst_name'] in dst_names, f"{r['dst_name']} not expected in {dst_names}"
            assert G[r['dst_name']][r['dst_id']], f"{r['dst_name']}.{r['dst_id']} , referenced from {obj['name']}.{obj['id']} not found in Graph "    


    def recursive_default_dict():
        """Recursive default dict."""
        return defaultdict(recursive_default_dict)
        
    G = recursive_default_dict()

    R = recursive_default_dict()

    
    # create a graph of name->id->Obj
    for obj in records:
        G[obj['name']][obj['id']] = obj
        # create a relationship lookup
        for rel in obj['relations']:
            R[rel['dst_name']][rel['dst_id']][obj['name']][obj['id']] = obj


    

    # assert len(R['Organization']['1000G-high-coverage-2019']['Patient']) > expected_patient_count, len(R['Organization']['1000G-high-coverage-2019']['Patient'])

    # assert set(R['ResearchStudy']['1000G-high-coverage-2019'].keys()) == set(['Observation', 'ResearchSubject']), R['ResearchStudy']['1000G-high-coverage-2019'].keys()

    assert len(R['ResearchStudy']['1000G-high-coverage-2019']['ResearchSubject']) > expected_patient_count
    print("Has the minimum Patient count.")

    print("Check relationships:")

    for object_name in counts.keys():
        for obj in by_name(object_name):
            destination_names = [relation['dst_name'] for relation in obj['relations']]
            check_links(obj, destination_names)
        print(f"    {object_name} OK - all references found in graph")

if __name__ == '__main__':
    cli()
