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

## cp to s3 for deployment

```
gsutil  cp schema/htan.json s3://htan-testing/schema.json
gsutil acl ch -u AllUsers:R 

```

## help...

### Delete project
```
select table_name from information_schema.tables
WHERE table_schema = 'public' and table_name like 'node%'
;



tables = """node_acutelymphoblasticleukemiatier3
node_biospecimen
node_braincancertier3
node_breastcancertier3
node_bulkrnaseqlevel1
node_bulkrnaseqlevel2
node_bulkrnaseqlevel3
node_bulkweslevel1
node_bulkweslevel2
node_bulkweslevel3
node_clinicaldatatier2
node_colorectalcancertier3
node_demographic
node_diagnosis
node_exposure
node_familyhistory
node_file
node_coremetadatacollection
node_followup
node_lungcancertier3
node_melanomatier3
node_moleculartest
node_ovariancancertier3
node_pancreaticcancertier3
node_prostatecancertier3
node_sarcomatier3
node_scatacseqlevel1
node_scrnaseqlevel1
node_scrnaseqlevel2
node_scrnaseqlevel3
node_scrnaseqlevel4
node_therapy
node_patient
node_workflowparametersdescription
node_workflowtype
node_assay
node_imagingassaytype
node_imaginglevel2channel
node_imaginglevel2
""".split()


# note [node_project node_program] not touched.

for t in tables:
    print(f"delete from {t} where _props->>'project_id' = 'htan-OMSAtlasDev'  ;")


-- repeat until all nodes deleted
-- this list should be in reverse order; e.g. leaf nodes first
delete from node_acutelymphoblasticleukemiatier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_biospecimen where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_braincancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_breastcancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_bulkrnaseqlevel1 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_bulkrnaseqlevel2 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_bulkrnaseqlevel3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_bulkweslevel1 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_bulkweslevel2 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_bulkweslevel3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_clinicaldatatier2 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_colorectalcancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_demographic where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_diagnosis where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_exposure where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_familyhistory where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_file where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_coremetadatacollection where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_followup where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_lungcancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_melanomatier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_moleculartest where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_ovariancancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_pancreaticcancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_prostatecancertier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_sarcomatier3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_scatacseqlevel1 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_scrnaseqlevel1 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_scrnaseqlevel2 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_scrnaseqlevel3 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_scrnaseqlevel4 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_therapy where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_patient where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_workflowparametersdescription where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_workflowtype where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_assay where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_imagingassaytype where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_imaginglevel2channel where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
delete from node_imaginglevel2 where _props->>'project_id' = 'htan-OMSAtlasDev'  ;
```