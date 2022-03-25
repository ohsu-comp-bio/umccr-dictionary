# fhir-to-pfb

> A practical implementation of FHIR for research projects

All bioinformatics projects have meta data that describes commonly used entities, e.g. subjects, samples, demographics, diagnoses, measurements, etc.  Each project describes how those samples were processed and how genomics, microscopy and analysis digital artifacts are linked to that meta data.

Informaticians can bring value and contribute to overall project success with a standards based meta data implementation.

These contributions fall into specific areas:

* Meta data model selection
* Data use and accession 
* Description of data object location
* Practical sharing and serialization of both meta data and data objects


Here we focus on opinionated conventions for each of these areas and provide practical examples and tooling.

Consideration of these approaches will:

* Increase the value of a project by freeing it's data for downstream analysis and reproducibility
* Reduce waste and re-work both for the sponsoring project and data producers and consumers
* //TODO FAIR principle ? Findable, Accessible Interoperable Reusabe


## Meta data model

Readers have probably all experienced first hand the challenges with research project setup and integration:

* Subject data is trapped in different silos, depending on data producer institution, decisions made at project start-up, inertia, etc.
* Each project absorbs waste increasing costs as they re-invent the wheel, choosing arbitrary data structures and conventions

FHIR in the unification of this data, how it is presented and how it is exchanged.  It addresses the need for a "USB for research", just as you can move data to different devices for different use cases via a usb,  effective standards allow projects to quickly form cohorts with data objects supported with rich meta data.  Because it came out of the healthcare clinical space with its compliance requirements, the designers of FHIR pulled in best practices and real world concepts from the facets of human clinical care, public health and analytics.

FHIR reifies these decisions in data formats and elements (Resources), APIs and exchange standards.

FHIR is not a database, ie it does not support joins in the traditional RDBMS sense. It more closely resembles a document database, when querying data entities that are related to each other, one way to simulate a join is to search from one entity to one another (i.e. Bundle of related documents). This is similar to materialized view in the relational database world.

One weakness to the FHIR is it’s verbosity, the number of calls that one needs to make searching for resources, examining their contents and the querying again for related documents.

This is compounded in the research setting, especially for cross cohort builders, since FHIR repositories are segregated by accession and data use restriction; queries must be re-run on multiple endpoints. In the AnVIL use case, we are likely to see 100+ endpoints.

FHIR addresses this in several ways, fundamentally at the [search](https://www.hl7.org/fhir/search.html#revinclude) parameter. **If we have confidence that the search parameter fields are uniformly populated, we can build constructions such as Composition and GraphDefinitions **

Clients may request that the engine return resources related to the search results, in order to reduce the overall network delay of repeated retrievals of related resources. 

Ideally, the user should be able to specify a Resource type and an identifier (aka natural key, submitter id) and retrieve pertinent descendants and ancestors with a minimum of ambiguity and a maximum of efficiency.

In addition, we should ensure the semantics of the relationships are as clear as possible. We should also strive to remain as close to the letter and intent of the base FHIR without introducing an excess of special cases.

The following are identified as typical entrypoints into the FHIR graph and apply to ad-hoc, etl, analysis and workflow use cases:

* Given a Patient Identifier return ResearchSubject, Observations, Specimens, Tasks and DocumentReferences
* Given a Specimen Identifier return Patient, Tasks and DocumentReferences
* Given a Task Identifier return the Specimen
* Given a DocumentReference Identifier return the Task, Specimen and Patient
* Others...

A tightly defined, dependable bundle of these core resources will enable “top down” queries from the ResearchStudy or “bottom up” queries from the Observation or other downstream resources such as Gene.

For the Resources mentioned above, the solution is straightforward; ensure the search fields are populated, probably by defining Profiles.

One exception is the relationship between DocumentReference and Task. Semantically, the natural parameter is author, however the base reference restricts that field to Reference(Practitioner | PractitionerRole | Organization). The base reference does include a DocumentReference.context that we could use, with some semantic ambiguity.


![image](https://user-images.githubusercontent.com/47808/137189758-117650e7-c59d-4580-a171-b2b90e28b749.png)



## Data use and accession

## Description of data object location

## Practical sharing


## Summary

In the short term these approaches provide utility for researchers to create essentially a unified of the data, a longitudinal view of data from many providers.   In the long term, as more projects publish using these models and technology choices, the community forms a virtual cohort of interoperable studies.




----

# README


> A way to convert FHIR entities to Gen3

* See 
    * http://hl7.org/fhir/
    * https://www.youtube.com/watch?v=cVTvzP-li0M


## Getting started

* Setup venv
    ```
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Features

* Plucks entities and properties from FHIR
    * See [config](config.yaml)
* Converts FHIR vocabularies to Gen3
    * See [data](data/README.md)

## Create a json schema

```

# convert and redirect stderr to log

./model.py  2> /tmp/model.log.txt 

# manually examine log 

grep INFO /tmp/model.log.txt
>>> 
INFO:Wrote schema to ./schemas/dump.json

# json schema in ./schemas/*.yaml,

ls -1 ./schemas/*.yaml
>>>
./schemas/DocumentReference.yaml
./schemas/FamilyRelationship.yaml
./schemas/Observation.yaml
./schemas/Organization.yaml
./schemas/Patient.yaml
./schemas/PractitionerRole.yaml
./schemas/Questionnaire.yaml
./schemas/QuestionnaireResponse.yaml
./schemas/ResearchStudy.yaml
./schemas/ResearchSubject.yaml
./schemas/Specimen.yaml
./schemas/SpecimenTask.yaml
./schemas/_definitions.yaml
./schemas/_settings.yaml
./schemas/_terms.yaml
./schemas/project.yaml

# and resulting json schema

jq ". | keys" schemas/dump.json
>>> 
[
  "DocumentReference.yaml",
  "FamilyRelationship.yaml",
  "Observation.yaml",
  "Organization.yaml",
  "Patient.yaml",
  "PractitionerRole.yaml",
  "Questionnaire.yaml",
  "QuestionnaireResponse.yaml",
  "ResearchStudy.yaml",
  "ResearchSubject.yaml",
  "Specimen.yaml",
  "SpecimenTask.yaml",
  "_definitions.yaml",
  "_settings.yaml",
  "_terms.yaml",
  "project.yaml"
]
```



## Create a PFB with the schema

```
pfb from -o ncpi.schema.avro dict ./schemas/dump.json
```

## View the schema, confirm entities and attributes 

### Using native avro cli

```
java -jar ~/Downloads/avro-tools-1.11.0.jar  getschema pfb.avro  | \
  jq '.fields[] | select(.name == "object") | .type[]  | .name   '
>>>
"Metadata"
"root"
"data_release"
"DocumentReference"
"Observation"
"project"
"Patient"
"PractitionerRole"
"Organization"
"QuestionnaireResponse"
"ResearchStudy"
"Specimen"
"Questionnaire"
"ResearchSubject"
"SpecimenTask"
"FamilyRelationship"
```

### Using Gen3's pfb 

```
pfb show -i ncpi.schema.avro  schema | jq ".[] | .name"
>>> 
"root"
"data_release"
"DocumentReference"
"Observation"
"project"
"Patient"
"PractitionerRole"
"Organization"
"QuestionnaireResponse"
"ResearchStudy"
"Specimen"
"Questionnaire"
"ResearchSubject"
"SpecimenTask"
"FamilyRelationship"

```

## Transform data 

```
./transform.py --input_path ~/client-apis/pyAnVIL/DATA/Public/1000G-high-coverage-2019
>>>
INFO:wrote ./output/Patient.json
...
```

## Load data

 



```

# flatten the model
./model.py

# transform the data and create json schema: creates [schema/, output/]
./transform.py --input_path $DATA/Public/1000G-high-coverage-2019 

#
# reshape schema
# * avro delivers records to its reader in the order they were defined in the schema
# * terra processes the file a page at a time, so all records must be read in a specific order
#
jq '. |   {"Practitioner.yaml": .["Practitioner.yaml"],
  "Organization.yaml": .["Organization.yaml"],
  "PractitionerRole.yaml": .["PractitionerRole.yaml"] ,
  "ResearchStudy.yaml": .["ResearchStudy.yaml"],
  "Patient.yaml": .["Patient.yaml"],
  "ResearchSubject.yaml": .["ResearchSubject.yaml"],
  "Specimen.yaml": .["Specimen.yaml"],
  "DocumentReference.yaml": .["DocumentReference.yaml"],
  "SpecimenTask.yaml": .["SpecimenTask.yaml"],
  "Observation.yaml": .["Observation.yaml"],
  "_definitions.yaml": .["_definitions.yaml"],
  "_settings.yaml": .["_settings.yaml"],
  "_terms.yaml": .["_terms.yaml"]} ' ./schemas/dump.json  > ./schemas/dump-ordered.json

# to verify
# jq '. | keys_unsorted' ./schemas/dump-ordered.json


# load our schema and data into an avro file
rm 1000G-refactored.pfb.avro

pfb from -o 1000G-refactored.pfb.avro dict ./schemas/dump-ordered.json

pfb add -i ./output/Practitioner.json 1000G-refactored.pfb.avro
pfb add -i ./output/Organization.json 1000G-refactored.pfb.avro
pfb add -i ./output/PractitionerRole.json 1000G-refactored.pfb.avro
pfb add -i ./output/ResearchStudy.json 1000G-refactored.pfb.avro
pfb add -i ./output/Patient.json 1000G-refactored.pfb.avro
pfb add -i ./output/ResearchSubject.json 1000G-refactored.pfb.avro
pfb add -i ./output/Specimen.json 1000G-refactored.pfb.avro
pfb add -i ./output/DocumentReference.json 1000G-refactored.pfb.avro
pfb add -i ./output/SpecimenTask.json 1000G-refactored.pfb.avro
 
# In addition to the schema validation that avro provides, test the data locally
./test-enforce-order.py --file_name 1000G-refactored.pfb.avro 

# upload that PFB to google storage
gsutil cp 1000G-refactored.pfb.avro gs://fhir-test-16-342800
# TODO - why do we need to make it public? 
# https://cloud.google.com/storage/docs/gsutil/commands/signurl
gsutil acl ch -u AllUsers:R  gs://fhir-test-16-342800/1000G-refactored.pfb.avro
 
gsutil -i <service-account-email> signurl --use-service-account  gs://fhir-test-16-342800/1000G-refactored.pfb.avro

# note you will need to url-encode the signed url

# follow prompts in terra to import it into workspace
open 'https://app.terra.bio/#import-data?format=PFB&url={uuencoded-signed-url}'
 
open 'https://app.terra.bio/#import-data?format=PFB&url=https://storage.googleapis.com/fhir-test-16-342800/1000G-refactored.pfb.avro?x-goog-signature=b688a7fe945caf8302e9ebe7ff8bc2c96ecc74c6e751321dbb9d7e6828c804e4392cb709b037e65ec452242fc3a1b647a38f9749d9ddc07c452c90b1d180080c87f4611e87cf6cb90f1646e1e7597cfccf0cf8848fe85d26108abec683e06929d653c57bfb0f43ae9d59138a031f54a5799613c90f8efdae5aed22b0200cf40565e797c1fea7e5151b39bd25c834f854f6ef9e570dc921d6bd49c6ac37adf948ecdeaa27e90d218c1eb2a8602f6b122efdfeb9aa0ae77f715490afde2f98dc3b1c6dc912c97078c5b5352efe67aa9198ae609822f94712c6974d946d3d449b64930b3ff6d206f5e3c360a49cef551a6f27e8c0135873523d4ea61a285a82b9b2&x-goog-algorithm=GOOG4-RSA-SHA256&x-goog-credential=fhir-admin%40fhir-test-16-342800.iam.gserviceaccount.com%2F20220324%2Fus-west2%2Fstorage%2Fgoog4_request&x-goog-date=20220324T200220Z&x-goog-expires=43200&x-goog-signedheaders=host'

```


open 'https://app.terra.bio/#import-data?format=PFB&url=https://storage.googleapis.com/fhir-test-16-342800/1000G-truncated-private.pfb.avro'


pfb from -o 1000G-no-trim.pfb.avro json -s ncpi.schema.avro --program DEV --project test  ./output


# upload that PFB to google storage
gsutil cp 1000G-no-trim.pfb.avro gs://fhir-test-16-342800
# TODO - why do we need to make it public?
gsutil acl ch -u AllUsers:R  gs://fhir-test-16-342800/1000G-no-trim.pfb.avro
open 'https://app.terra.bio/#import-data?format=PFB&url=https://storage.googleapis.com/fhir-test-16-342800/1000G-no-trim.pfb.avro'



#### Visualize 

# deploy, in this case to dictionary tool
cp output/*.yaml ~/umccr-dictionary/dictionary/aced/gdcdictionary/schemas


#### Resources

https://www.youtube.com/watch?v=CKPVK-9m6dI
https://www.youtube.com/watch?v=x-plS1Ihugw

https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/textanalytics/azure-ai-textanalytics/samples/sample_analyze_healthcare_entities.py