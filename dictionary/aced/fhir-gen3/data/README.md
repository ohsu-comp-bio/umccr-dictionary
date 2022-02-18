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



* LOINC
LOINC Top 2000+ Lab Observations - US Version

https://loinc.org/file-access/?download-id=9008

* SNOMED Body site

https://phinvads.cdc.gov/vads/ViewValueSet.action?id=9A2D4051-3AA6-42EB-AE88-541C9094B0FB#


## TODO



Notes:

```
http://hl7.org/fhir/R4/definitions.json.zip


https://loinc.org/file-access/download-id/17912/
    Loinc_2.71_LoincTableCore/LoincTableCore.csv

```

