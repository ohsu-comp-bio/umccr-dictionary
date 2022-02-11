# fhir-to-gen3

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