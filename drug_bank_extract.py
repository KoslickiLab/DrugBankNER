import os
import xmltodict

# NOTE: 'targets' also includes some amino acid sequences, so might need to dig into the targets subssubsections
# to see how to avoid those.

# Note: this assumes everything is text, but some fields are identifiers or references and these will need to be
# handled differently
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
