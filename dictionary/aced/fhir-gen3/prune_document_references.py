#!/usr/bin/env python3

"""Trim limit downstream entities based on Patient list."""

import json

with open("./output/Patient.json") as input_stream:
    patients = json.load(input_stream)

with open("./output/DocumentReference.json") as input_stream:
    document_references = json.load(input_stream)

original_count = len(document_references)

patient_submitter_ids = [p['submitter_id']for p in patients]    

to_delete = []

for document_reference in document_references:
    if document_reference['subject']['submitter_id'] not in patient_submitter_ids:
        to_delete.append(document_reference['submitter_id'])

for submitter_id in to_delete:
    for document_reference in document_references:
        if document_reference['submitter_id'] == submitter_id:
            document_references.remove(document_reference)

with open("./output/DocumentReference.json", "w") as output_stream:
    json.dump(document_references, output_stream)

print(f"Pruned document_references started with {original_count} now has {len(document_references)}")    


with open("./output/SpecimenTask.json") as input_stream:
    specimen_tasks = json.load(input_stream)

original_count = len(specimen_tasks)

document_reference_submitter_ids = [dr['submitter_id']for dr in document_references]    

to_delete = []

for specimen_task in specimen_tasks:
    if specimen_task['output']['submitter_id'] not in document_reference_submitter_ids:
        to_delete.append(specimen_task['submitter_id'])

for submitter_id in to_delete:
    for specimen_task in specimen_tasks:
        if specimen_task['submitter_id'] == submitter_id:
            specimen_tasks.remove(specimen_task)


with open("./output/SpecimenTask.json", "w") as output_stream:
    json.dump(specimen_tasks, output_stream)

print(f"Pruned specimen_tasks started with {original_count} now has {len(specimen_tasks)}")    
