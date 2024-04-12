# I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
import xmltodict
import json
import pickle
import pandas as pd
from node_synonymizer import NodeSynonymizer
import re
from utils import extract_text, process_drug, get_xml_data, process_drugbank_data, drug_dict_to_kg2_drug_info
from CONSTANTS import MECHANISTIC_CATEGORIES, DB_PREFIX, MOSTLY_TEXT_FIELDS, ALL_FIELDS, DATABASE_PREFIXES, \
    DATABASE_NAMES, REGEX_PATTERNS

doc = get_xml_data()
drug_dict = process_drugbank_data(doc, ALL_FIELDS)
kg2_drug_info = drug_dict_to_kg2_drug_info(drug_dict)


