# I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
import xmltodict
import json
import pickle
import pandas as pd
from node_synonymizer import NodeSynonymizer
import re
from utils import extract_text, process_drug, get_xml_data, process_drugbank_data
from CONSTANTS import MECHANISTIC_CATEGORIES, DB_PREFIX, MOSTLY_TEXT_FIELDS, ALL_FIELDS

doc = get_xml_data()
drug_dict = process_drugbank_data(doc, ALL_FIELDS)

# What I will need to do now is identify which CURIE prefixes to be looking for, and what their formats are
# Known databases: DrugBank ID,Name,CAS Number,Drug Type,KEGG Compound ID,KEGG Drug ID,PubChem Compound ID,
# PubChem Substance ID,ChEBI ID,PharmGKB ID,HET ID,UniProt ID,UniProt Title,GenBank ID,DPD ID,RxList Link,
# Pdrhealth Link,Wikipedia ID,Drugs.com Link,NDC ID,ChemSpider ID,BindingDB ID,TTD ID
db_pattern = r'DB\d+'
CAS_pattern = r'\d{2,7}-\d{2}-\d'
KEGG_Compound_pattern = r'C\d{5}'
KEGG_Drug_pattern = r'D\d{5}'
PubChem_Compound_pattern = r'\d{4,9}'
PubChem_Substance_pattern = r'\d{4,9}'
ChEBI_pattern = r'\d+'
PharmGKB_pattern = r'PA\d+'
HET_pattern = r'\w{3}'
UniProt_pattern = r'[OPQ][0-9][A-Z0-9]{3}[0-9]'
GenBank_pattern = r'\w{1}\d{3,7}'
DPD_pattern = r'\d+'
NDC_pattern = r'\d{4}-\d{4}-\d{2}'

# I will also need the CURIE prefixes. Will look them up from: https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml
