# Data

Valuesets, code systems, etc.


## Valuesets

* Download FHIR valuesets

```
wget https://raw.githubusercontent.com/hapifhir/hapi-fhir/master/hapi-fhir-validation-resources-dstu3/src/main/resources/org/hl7/fhir/dstu3/model/valueset/valuesets.xml


cat valuesets.xml | xq . > valuesets.json

```

* Load into a sqlite database

```
python3 valuesets.py -v --initialize
python3 valuesets.py -v --load_curated
```



## TODO



Notes:

```
http://hl7.org/fhir/R4/definitions.json.zip


https://loinc.org/file-access/download-id/17912/
    Loinc_2.71_LoincTableCore/LoincTableCore.csv

```

