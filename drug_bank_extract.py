import os
import xmltodict
from node_synonymizer import NodeSynonymizer
import NER
import json
import spacy
import scispacy


DB_PREFIX = 'DRUGBANK:'
MECHANISTIC_CATEGORIES = {"biolink:BiologicalProcess", "biolink:BiologicalProcessOrActivity",
"biolink:Cell", "biolink:CellularComponent", "biolink:Drug",
"biolink:Disease", "biolink:DiseaseOrPhenotypicFeature",
"biolink:Gene", "biolink:GeneProduct", "biolink:GeneFamily",
"biolink:GeneGroupingMixin", "biolink:GeneOrGeneProduct",
"biolink:MolecularActivity", "biolink:NoncodingRNAProduct",
"biolink:PathologicalProcess", "biolink:PhenotypicFeature",
"biolink:Pathway", "biolink:PhenotypicFeature", "biolink:Protein",
"biolink:ProteinDomain", "biolink:ProteinFamily",
"biolink:PhysiologicalProcess", "biolink:RNAProduct",
"biolink:SmallMolecule", "biolink:Transcript"}

# for light NLP stuff
nlp = spacy.load("en_core_sci_lg")

# Directly use the node synonymizer
synonymizer = NodeSynonymizer("./data", "node_synonymizer_v1.0_KG2.8.4.sqlite")

# Chunyu's NER
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                linker_name=['umls', 'mesh'])


def text_to_kg2_mechanistic_nodes(text):
    potential_mechanistic_matched_nodes = {}
    # split the text into sentences
    #doc = nlp(text)  # turns out spacy is confused by things like: .[reference]
    # for sentence in doc.sents:
    sentences = text.split('.')
    for sentence in sentences:
        res = trapi_ner.get_kg2_match(sentence, remove_mark=True)
        # For each entry in res, return the key and preferred_name of those entries where the preferred_category is
        # in MECHANISTIC_CATEGORIES
        for key, value in res.items():  # keys are plain text names, values are lists of tuples
            for v in value:  # v[0] is the KG2 identifier, v[1] is the node info in the form of a dict
                if v[1]['preferred_category'] in MECHANISTIC_CATEGORIES:
                    if v[0] not in potential_mechanistic_matched_nodes:
                        potential_mechanistic_matched_nodes[v[0]] = {'name': key, 'category': v[1]['preferred_category']}
                    # replace name with longer name
                    elif v[0] in potential_mechanistic_matched_nodes and len(key) > len(
                            potential_mechanistic_matched_nodes[v[0]]['name']):
                        potential_mechanistic_matched_nodes[v[0]]['name'] = key
    return potential_mechanistic_matched_nodes

def drug_bank_id_to_kg2_indication(drug_bank_id, drug_dict):
    indication = drug_dict[drug_bank_id]['indication']
    res = trapi_ner.get_kg2_match(indication, remove_mark=True)
    # For each entry in res, return the key and preferred_name of those entries where the preferred_category is
    # biolink:Disease, phenotypicFeature, or DiseaseOrPhenotypicFeature
    potential_indications_id_to_name = {}
    for key, value in res.items():
        for v in value:
            if v[1]['preferred_category'] in {'biolink:Disease', 'biolink:PhenotypicFeature',
                                              'biolink:DiseaseOrPhenotypicFeature'}:
                if v[0] not in potential_indications_id_to_name:
                    potential_indications_id_to_name[v[0]] = key
                # replace name with longer name
                elif v[0] in potential_indications_id_to_name and len(key) > len(
                        potential_indications_id_to_name[v[0]]):
                    potential_indications_id_to_name[v[0]] = key
    return potential_indications_id_to_name


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
# Now, I would like to NER the indications to add to an "indication" field in the kg2_drug_info dictionary.
# While I am at it, also add the intermediate nodes
for kg2_drug in kg2_drug_info.keys():
    drug_bank_id = kg2_drug_info[kg2_drug]["drug_bank_id"]
    # NER and KG2 align the indications
    kg2_drug_info[kg2_drug]["indications"] = drug_bank_id_to_kg2_indication(drug_bank_id, drug_dict)
    # NER and KG2 align the mechanistic intermediate nodes
    all_intermediate_text = ""
    for field in drug_dict[drug_bank_id].keys():
        if field != "indication":
            all_intermediate_text += drug_dict[drug_bank_id][field]
    # then do the NER
    kg2_drug_info[kg2_drug]["mechanistic_intermediate_nodes"] = text_to_kg2_mechanistic_nodes(all_intermediate_text)



#######
# Just spot checking the results
res = kg2_drug_info['PUBCHEM.COMPOUND:118856773']
def extract_unique_names(obj, names_set):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'name':
                names_set.add(value)
            else:
                extract_unique_names(value, names_set)
    elif isinstance(obj, list):
        for item in obj:
            extract_unique_names(item, names_set)
unique_names = set()
extract_unique_names(res, unique_names)
for name in unique_names:
    print(name)
