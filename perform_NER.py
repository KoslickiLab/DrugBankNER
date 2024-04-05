import os
import xmltodict
from node_synonymizer import NodeSynonymizer
import NER
import json
import spacy
import scispacy
import sys
import pickle
import concurrent.futures
from multiprocessing import Pool
from utils import extract_text, process_drug, get_xml_data, process_drugbank_data
from CONSTANTS import MECHANISTIC_CATEGORIES, DB_PREFIX, MOSTLY_TEXT_FIELDS

# TODO: note! The pathways are all associated with identifiers, so probably only need to align them with KG2,
#  no need to perform NER on them. Same with targets and transporters

spacy.require_gpu()

# Directly use the node synonymizer
synonymizer = NodeSynonymizer("./data", "node_synonymizer_v1.0_KG2.8.4.sqlite")

# Chunyu's NER; different models have different strengths and weaknesses. Through trial and error, I decided on these
# five, since each results in matches the other models don't get.
ners = []
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                    linker_name=['umls', 'mesh'], spacy_model='en_core_sci_lg', threshold=0.70,
                              num_neighbors=15, max_entities_per_mention=1)
ners.append(trapi_ner)
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                              linker_name=['umls', 'mesh'], spacy_model='en_core_sci_scibert', threshold=0.75,
                              num_neighbors=10, max_entities_per_mention=1)
ners.append(trapi_ner)
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                          linker_name=['rxnorm'], spacy_model='en_core_sci_lg', threshold=0.70,
                          num_neighbors=15, max_entities_per_mention=1)
ners.append(trapi_ner)
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                          linker_name=['go'], spacy_model='en_core_sci_lg', threshold=0.70,
                          num_neighbors=15, max_entities_per_mention=1)
ners.append(trapi_ner)
trapi_ner = NER.TRAPI_NER(synonymizer_dir='./data', synonymizer_dbname='node_synonymizer_v1.0_KG2.8.4.sqlite',
                          linker_name=['hpo'], spacy_model='en_core_sci_lg', threshold=0.70,
                          num_neighbors=15, max_entities_per_mention=1)


def delete_long_tokens(text, max_length=100):
    """
    This function deletes tokens that are longer than 100 characters
    :param text: str
    :return: str
    """
    tokens = text.split(" ")
    return ' '.join([token for token in tokens if len(token) < max_length])


def text_to_kg2_mechanistic_nodes(text):
    potential_mechanistic_matched_nodes = {}
    # split the text into sentences
    sentences = text.split('.')
    for sentence in sentences:
        # omit very long sequences and very short ones
        if len(sentence) > 1000 or len(sentence) < 15:
            continue
        # omit very long tokens/words
        sentence = delete_long_tokens(sentence)
        print(f"on sentence: {sentence}")
        for trapi_ner in ners:
            try:
                res = trapi_ner.get_kg2_match(sentence, remove_mark=True)
            except RuntimeError:
                continue
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


def main():
    # After running download_data.sh, the data will be in the data/ directory
    # convert the xml to dicts
    doc = get_xml_data()
    drug_dict = process_drugbank_data(doc, MOSTLY_TEXT_FIELDS)

    print("Number of drugs with info:", len(drug_dict))

    # Let's start the dictionary that will be keyed by the KG2 drug identifiers and will have the drug info as values
    kg2_drug_info = {}
    # convert all the drugbank IDs to KG2 IDs
    i = 0
    max_i = len(drug_dict.keys())
    for drug in drug_dict.keys():
        if i % 100 == 0:
            print(f"Processing drug {i} of {max_i}")
        i += 1
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
    # While I am at it, also add the intermediate mechanistic nodes to the kg2_drug_info dictionary
    i = 0
    max_i = len(kg2_drug_info.keys())
    for kg2_drug in kg2_drug_info.keys():
        #if i % 100 == 0:
        print(f"Processing drug {i} of {max_i}")
        i += 1
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



    # Now, let's write this to a JSON file
    with open('./data/kg2_drug_info.json', 'w') as f:
        json.dump(kg2_drug_info, f, indent=4)

    # also save as a pickle file for fast loading
    with open('./data/kg2_drug_info.pkl', 'wb') as f:
        pickle.dump(kg2_drug_info, f)


if __name__ == "__main__":
    main()
