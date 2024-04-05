# The point of this script will be to use the drugbank_targets.csv to extract the identifiers from
# the free text in the drugbank data. This will be used to update/expand the NER extracted quantities.
import pandas as pd
import json
import pickle
from node_synonymizer import NodeSynonymizer

synonymizer = NodeSynonymizer("./data", "node_synonymizer_v1.0_KG2.8.4.sqlite")

# load the drugbank_targets.csv
# set all nan to None
drug_targets = pd.read_csv('./data/drugbank_targets.csv')
drug_targets.fillna(value=-1, inplace=True)
# Columns: Index(['ID', 'Name', 'Gene Name', 'GenBank Protein ID', 'GenBank Gene ID',
#        'UniProt ID', 'Uniprot Title', 'PDB ID', 'GeneCard ID', 'GenAtlas ID',
#        'HGNC ID', 'Species', 'Drug IDs'],
#       dtype='object')


def get_preferred_curie(curie):
    res = synonymizer.get_canonical_curies(curie)
    if res[curie]:
        return res[curie]['preferred_curie']
    else:
        return None


# first the drug targets: create a dictionary keyed by drugbank ID with values being a list of target curies using
# the KG2 preferred curie
db_id_to_target = {}
for i, row in drug_targets.iterrows():
    targets = []
    curie = None
    name = None
    symbol = None
    found = False
    # in order of preference, I will first look for an HGNC ID, then UniProt ID, then use the synonymizer on the name
    # and gene name
    if row['HGNC ID']:
        entry = str(row['HGNC ID'])
        if entry != '-1' and entry != 'nan':
            if entry.startswith('HGNC:'):
                curie = entry
            else:
                curie = f"HGNC:{entry}"
            preferred_curie = get_preferred_curie(curie)
            found = True
    if row['UniProt ID'] and not found:
        entry = str(row['UniProt ID'])
        if entry != '-1' and entry != 'nan':
            if entry.startswith('UNIPROTKB:'):
                curie = entry
            else:
                curie = f"UNIPROTKB:{entry}"
            preferred_curie = get_preferred_curie(curie)
            found = True
    if row['Name'] and not found:
        name = str(row['Name'])
        if row['Gene Name']:
            symbol = str(row['Gene Name'])
        if name == '-1' or name == 'nan':
            name = None
        if symbol == '-1' or symbol == 'nan':
            symbol = None
    # search on the name
    if not curie and (name or symbol):
        res = synonymizer.get_canonical_curies(names=name)
        if res[name]:
            curie = res[name]['preferred_curie']
        else:
            res = synonymizer.get_canonical_curies(names=symbol)
            if res[symbol]:
                curie = res[symbol]['preferred_curie']

    # If we found the curie, append to the list of targets for each drugbank ID in the Drug IDs column
    if curie:
        for db_id in row['Drug IDs'].split(';'):
            db_id_to_target.setdefault(db_id, []).append(curie)

# Later, I will then merge db_id_to_target with the NER extracted quantities
# export into json
with open('./data/drugbank_targets.json', 'w') as f:
    json.dump(db_id_to_target, f, indent=2)
# also dump to a pickle file
with open('./data/drugbank_targets.pkl', 'wb') as f:
    pickle.dump(db_id_to_target, f)
