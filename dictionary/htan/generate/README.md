# Generate - reads HTAN schema and generates Gen3 model


## Setup

```
$ dictionary/htan/generate/
$ python3.7 -m venv   venv
```

## Fetch HTAN datamodel 

> Note this is not versioned - upstream changes may break generation

```
wget https://raw.githubusercontent.com/ncihtan/schematic/main/data/schema_org_schemas/HTAN.jsonld

```

## Generate gen3 schema entities

```
cd dictionary/htan/generate/ ;\
    python3  generate_model.py --id bts:Patient ;\
    python3  generate_model.py --id bts:Biospecimen ;\
    python3  generate_model.py --id bts:Assay ;\
    python3  generate_model.py --id bts:File ;\
    python3  generate_model.py --id bts:Demographics ;\
    cd ../../.. ;
```

## Test, compile and view datamodel
```
make test dd=htan ;  make compile dd=htan ;  make load dd=htan
```

## View datamodel

Navigate to `http://localhost:8080/#schema/htan.json`
