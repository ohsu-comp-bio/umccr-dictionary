# AnVIL Data Dictionary

The [AnVIL](https://www.genome.gov/Funded-Programs-Projects/Computational-Genomics-and-Data-Science-Program/Genomic-Analysis-Visualization-Informatics-Lab-space-AnVIL) data dictionary provides the first level of validation for genomic data and clinical elements managed by the NHGRI Genomic Data Science Analysis, Visualization and Informatics Lab-space (AnVIL). AnVIL is a scalable and interoperable resource for the genomic scientific community, that leverages a cloud-based infrastructure for democratizing genomic data access, sharing and computing across large genomic, and genomic-related data sets. The general structure and concepts derive from the [GDC Data Dictionary](https://github.com/nci-gdc/gdcdictionary) JSON schemas define all the individual entities (nodes) in the data model. Moreover, these schemas define all of the relationships (links) between the nodes. Finally, the schemas define the valid key-value pairs that can be used to describe the nodes. 

--------------------------

## Datasets

### [CCDG](https://www.genome.gov/Funded-Programs-Projects/NHGRI-Genome-Sequencing-Program/Centers-for-Common-Disease-Genomics)
The Centers for Common Disease Genomics are a collaborative large-scale genome sequencing effort to comprehensively identify rare risk and protective variants contributing to multiple common disease phenotypes.

### [CMG](https://www.genome.gov/Funded-Programs-Projects/NHGRI-Genome-Sequencing-Program/Centers-for-Mendelian-Genomics-CMG)
The Centers for Mendelian Genomics is a multi-center collaboration aimed at identifying the genes responsible for Mendelian phenotypes by whole exome and whole genome sequencing

### [GTEx](https://gtexportal.org/home/)
The Genotype-Tissue Expression (GTEx) project is an ongoing effort to build a comprehensive public resource to study tissue-specific gene expression and regulation. Samples were collected from 54 non-diseased tissue sites across nearly 1000 individuals, primarily for molecular assays including WGS, WES, and RNA-Seq.

### [1000 G](https://www.internationalgenome.org/)
The 1000 Genomes Project, launched in January 2008, is an international research effort to establish variation profiles across the human population. This open access data set continues to be a valuable resource to geneticists.

### [eMERGE](https://emerge-network.org/)
The Electronic and MEdical Records and Genomics project (eMERGE) is a national network organized and funded by the NHGRI that combines DNA biorepositories with electronic medical record (EMR) systems for large scale, high-throughput genetic research in support of implementing genomic medicine.

-------------------------------

## Data Dictionary Structure 

The Data Model covers all of the nodes within the as well as the relationships between
the different types of nodes. All of the nodes in the data model are strongly typed and individually
defined for a specific data type. For example, submitted files can come in different forms, such as
aligned or unaligned reads; within the model we have two separately defined nodes for
`Submitted Unaligned Reads` and `Submitted Aligned Reads`. Doing such allows for faster querying of
the data model as well as providing a clear and concise representation of the data in the BPA.

Beyond node type, there are also a number of extensions used to further define the nodes within
the data model. Nodes are grouped up into categories that represent broad roles for the node such
as `analysis` or `biospecimen`. Additionally, nodes are defined within their `Program` or `Project`
and have descriptions of their use. All nodes also have a series of `systemProperties`; these
properties are those that will be automatically filled by the system unless otherwise defined by
the user.  These basic properties define the node itself but still need to be placed into the model.

The model itself is represented as a graph. Within the schema are defined `links`; these links
point from child to parent with Program being the root of the graph. The links also contain a
`backref` that allows for a parent to point back to a child. Other features of the link include a
semantic `label` that describes the relationship between the two nodes, a `multiplicity` property
that describes the numeric relationship from the child to the parent, and a requirement property
to define whether a node must have that link. Taken all together the nodes and links create the
directed graph of the Data Model.

-------------------------------

## Node Properties and Examples

Each node contains a series of potential key-value pairs (`properties`) that can be used to
characterize the data they represent. Some properties are categorized as `required` or `preferred`.
If a submission lacks a required property, it cannot be accepted. Preferred properties can denote
two things: the property is being highlighted as it has become more desired by the community or
the property is being promoted to required. All properties not designated either `required` or
`preferred` are still sought by BPA, but submissions without them are allowed. 

The properties have further validation through their entries. Legal values are defined in each
property. For the most part these are represented in the `enum` categories although some keys,
such as `submitter_id`, will allow any string value as a valid entry. Other numeric properties
can have maximum and minimum values to limit valid entries.  For examples of what a valid entry
would look like, each node has a mock submission located in the `examples/valid/` directory. 

-------------------

## Contributing

Read how to contribute [here](https://github.com/NCI-GDC/portal-ui/blob/develop/CONTRIBUTING.md).
# aced-dictionary
