import os
import xmltodict
from node_synonymizer import NodeSynonymizer
import NER
import json


DB_PREFIX = 'DRUGBANK:'

# Directly use the node synonymizer
synonymizer = NodeSynonymizer("./data", "node_synonymizer_v1.0_KG2.8.4.sqlite")

# Chunyu's NER
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                linker_name=['umls', 'mesh'])

def get_preferred_name(curie):
    results = synonymizer.get_canonical_curies(curies=curie)
    return results[curie]['preferred_name']

def extract_text(value):
    """
    Traverses a nested dictionary/list-of*-lists and extracts all the text values
    :param value:
    :return: big-ol-string
    """
    if isinstance(value, list):
        res = ' '.join(extract_text(v) for v in value)
    elif isinstance(value, dict):
        res = ' '.join(extract_text(v) for k, v in value.items() if not k.startswith('@'))
    else:
        res = str(value)
    if res != 'None':
        return res
    else:
        return ''


def process_drug(drug):
    fields = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
              'metabolism', 'protein-binding', 'pathways', 'reactions', 'targets',
              'enzymes', 'carriers', 'transporters']  # From what I can see, these are the most relevant to us

    drug_data = {}
    for field in fields:
        value = drug.get(field, '')
        drug_data[field] = extract_text(value)

    return drug_data


# After running download_data.sh, the data will be in the data/ directory
# convert the xml to dicts
with open('data/full_database.xml') as fd:
    doc = xmltodict.parse(fd.read())

drugs = doc['drugbank']['drug']
drug_dict = {}

# loop over all the drugs, extract the relevant information and store it in a dictionary
for drug in drugs:
    # This handles the case where there are multiple drugbank-ids and chooses the primary one
    drug_ids = drug['drugbank-id']
    try:
        primary_id = [d['#text'] for d in drug_ids if isinstance(d, dict) and d.get('@primary', '') == 'true'][0]
    except IndexError:
        primary_id = drug_ids['#text'] if isinstance(drug_ids, dict) and drug_ids.get('@primary', '') == 'true' else ''
    if primary_id:
        drug_info = process_drug(drug)
        # check if some field is not empty
        if any(drug_info.values()):
            drug_dict[primary_id] = drug_info

print("Number of drugs with info:", len(drug_dict))

# Let's start the dictionary that will be keyed by the KG2 drug identifiers and will have the drug info as values
kg2_drug_info = {}
for drug in drug_dict.keys():
    query_CURIE = DB_PREFIX + drug
    norm_results = synonymizer.get_canonical_curies(query_CURIE)
    if norm_results[query_CURIE]:
        identifier = norm_results[query_CURIE]['preferred_curie']
        name = norm_results[query_CURIE]['preferred_name']
        category = norm_results[query_CURIE]['preferred_category']
        if identifier:
            kg2_drug_info[identifier] = {}
            kg2_drug_info[identifier]['KG2_ID'] = identifier
            if name:
                kg2_drug_info[identifier]['name'] = get_preferred_name(identifier)
            if category:
                kg2_drug_info[identifier]['category'] = category
            kg2_drug_info[identifier]["drug_bank_id"] = drug

# So now we have the KG2 identifiers for the drugs, as well as the category, name, and drugbank id
# Now, I would like to NER the indications to add to a "indication" field in the kg2_drug_info dictionary

# test out the NER
indication = drug_dict['DB00001']['indication']
res = trapi_ner.get_kg2_match(indication, remove_mark=True)
json_string = json.dumps(res, indent=4)
print(json_string)

# For each entry in res, return the key and preferred_name of those entries where the preferred_category is
# biolink:Disease
potential_indications_id_to_name = {}
for key, value in res.items():
    for v in value:
        if v[1]['preferred_category'] in {'biolink:Disease', 'biolink:PhenotypicFeature', 'biolink:DiseaseOrPhenotypicFeature'}:
            if v[0] not in potential_indications_id_to_name:
                potential_indications_id_to_name[v[0]] = key
            elif v[0] in potential_indications_id_to_name and len(key) > len(potential_indications_id_to_name[v[0]]):
                potential_indications_id_to_name[v[0]] = key
print(potential_indications_id_to_name)
# TODO I would then add this back into the kg2_drug_info dict, and do this for all drugs with indications
