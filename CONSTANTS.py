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
MOSTLY_TEXT_FIELDS = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
              'metabolism', 'protein-binding', 'reactions',
              'enzymes', 'carriers', 'transporters']
ALL_FIELDS = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
              'metabolism', 'protein-binding', 'pathways', 'reactions', 'targets',
              'enzymes', 'carriers', 'transporters']