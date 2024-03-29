# DrugBankNER
ETL of DrugBank to recognize KG2 concepts in DrugBank entries for use as training data

# Prep work
1. Download DrugBank XML file from DrugBank.ca
    1. Make an account on DrugBank
    1. Run `./download_data.sh`, which will put the DrugBank XML file in the `data` directory
1. You will need to have a copy of the RTX/ARAX node synonymizer
    1. Easiest way is to ask a team member for a copy
    2. Otherwise, you will need to still ask a team member to add your RSA key to the database server
    5. After that, you can get the sqlite file via
    ```
    scp rtxconfig@arax.databases.rtx.ai:/translator/data/orangeboard/databases/KG2.8.4/node_synonymizer_v1.0_KG2.8.4.sqlite .
    ```
    Note that this path is via [this line in config_dbs.json](https://github.
    com/RTXteam/RTX/blob/master/code/config_dbs.json#L3C28-L3C111) in case it gets updated
1. Download ScispaCy training data
Please download the `en_core_sci_lg` model from [here](https://allenai.github.io/scispacy/). In short, this can be accomplished with
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_lg-0.5.3.tar.gz
```
