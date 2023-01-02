#!/usr/bin/env python3

from fastavro import reader
import click
from pprint import pprint
from collections import defaultdict
    

@click.command()
@click.option('--file_name', default="1000G.pfb.avro", help='Location of PFB avro file.')
@click.option('--expected_patient_count', default=199, help='Minimum number of Patients')

def cli(file_name, expected_patient_count):

    # raw records
    records = []

    with open(file_name, 'rb') as fo:
        records = [record for record in reader(fo)]

    # print("Record Order:")
    # seen_already = set()
    # for r in records:
    #     if r['name'] not in seen_already:
    #         print(r['name'])
    #         seen_already.add(r['name'])

    # ensure loaded in the correct order

    def recursive_default_dict():
        """Recursive default dict."""
        return defaultdict(recursive_default_dict)

    seen_already = set()
    def log_first_occurence(obj):
        if obj['name'] not in seen_already:
            print(obj['name'])
        seen_already.add(obj['name'])

    def check_links(obj, graph):
        """Make sure relations from obj exist in graph."""
        assert 'relations' in obj
        for r in obj['relations']:
            assert graph[r['dst_name']][r['dst_id']], f"{r['dst_name']}.{r['dst_id']} , referenced from {obj['name']}.{obj['id']} not found in Graph "    

    G = recursive_default_dict()

    for obj in records:
        log_first_occurence(obj)
        G[obj['name']][obj['id']] = obj
        check_links(obj, G)

    # ensure no duplicates
    seen_already = set()
    def check_duplicates(obj):
        if obj['id'] in seen_already:
            print(f"{obj['name']}/{obj['id']}")
        seen_already.add(obj['id'])

    for obj in records:
        check_duplicates(obj)


if __name__ == '__main__':
    cli()
