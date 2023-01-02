import csv
from pprint import pprint
model = {}
input_file = csv.DictReader(open("HTAN.model.csv"))
for row in input_file:
    model[row['Attribute']] = row

has_dependencies = {a:model[a]  for a in model if model[a]['DependsOn'] != '' }

dependencies = [d.strip() for d in has_dependencies['Patient']['DependsOn'].split(',')] +  [d.strip() for d in has_dependencies['Patient']['DependsOn Component'].split(',')]

for d in dependencies:
    assert d in model, f"{d} not in model"