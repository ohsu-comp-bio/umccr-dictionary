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

## Run your conversion

```

# convert and redirect stderr to log
./model.py  2> /tmp/model.log.txt 

# manually examine log and contents gen3 config in ./output/*.yaml

# deploy, in this case to dictionary tool
cp output/*.yaml ~/umccr-dictionary/dictionary/aced/gdcdictionary/schemas

```



#### Resources

https://www.youtube.com/watch?v=CKPVK-9m6dI
https://www.youtube.com/watch?v=x-plS1Ihugw

https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/textanalytics/azure-ai-textanalytics/samples/sample_analyze_healthcare_entities.py