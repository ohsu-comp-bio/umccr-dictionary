To Run

```
wget https://raw.githubusercontent.com/ncihtan/schematic/main/data/schema_org_schemas/HTAN.jsonld

cd dictionary/htan/generate/ ; python3  generate_model.py --id bts:Patient ; cd ../../.. ; make test dd=htan ;  make compile dd=htan ;  make load dd=htan
cd dictionary/htan/generate/ ; python3  generate_model.py --id bts:Biospecimen ; cd ../../.. ; make test dd=htan ;  make compile dd=htan ;  make load dd=htan
cd dictionary/htan/generate/ ; python3  generate_model.py --id bts:Assay ; cd ../../.. ; make test dd=htan ;  make compile dd=htan ;  make load dd=htan
cd dictionary/htan/generate/ ; python3  generate_model.py --id bts:File ; cd ../../.. ; make test dd=htan ;  make compile dd=htan ;  make load dd=htan
  

```
