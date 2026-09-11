
import hashlib
import json
import os
import datetime
import dateutil

from dotenv import load_dotenv
from collections import defaultdict
from random import shuffle, randint

from jinja2 import Template, Environment, FileSystemLoader
from pyairtable import Table, Api

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

load_dotenv()

airtable_id = os.environ.get('AIR_TABLE_ID')
airtable_api_key = os.environ.get('AIR_TABLE_API_KEY')

# Load the signatures data from Airtable, and randomly order
table_name = os.environ.get('AIR_TABLE_NAME')
base_id = os.environ.get('AIR_TABLE_BASE_ID')
api = Api(airtable_api_key)
signatures_table = api.table(base_id, table_name)
signatures = signatures_table.all()

# Remove signatures that were withdrawn
signatures = [signature for signature in signatures if not signature['fields'].get('Removals', None)]

# Signatories who asked to be removed but whose row is still in Airtable, held
# as SHA-256 of the stripped, lowercased 'Full name' so that the source of the
# letter does not carry the name of someone who asked to be taken off it. Must
# stay above the dedupe below, so a withdrawn row cannot win the dedupe slot
# and mask a live one.
withdrawn_name_hashes = {
    '623cf9af0142763d462eafda08237a5a97258fafa255819c707ddb4b8e324744',
}

def withdrawn(signature):
    name = (signature['fields'].get('Full name') or '').strip().lower()
    return hashlib.sha256(name.encode('utf-8')).hexdigest() in withdrawn_name_hashes

signatures = [signature for signature in signatures if not withdrawn(signature)]

# Remove repeated signatures (use the last one)
sigs_with_email = dict()
sigs_without_email = []
for signature in signatures:
    F = signature['fields']
    if 'Email' in F:
        sigs_with_email[F['Email']] = signature # replace
    else:
        sigs_without_email.append(signature)
signatures = list(sigs_with_email.values())+sigs_without_email

# target_name = 'Paul Graham'
top_names = [
    "Paul Graham",
    "Amjad Masad",
    "Bilal Zuberi",
    "Deena Shakir",
    "Molly White",
    "Amir Nathoo",
    "Kirsty Nathoo",
    "James Slezak",
    "Ezra Goldman",
    "Chris Blauvelt",
    "Miguel de Icaza",
    "Aerica Shimizu Banks",
    "Idris Mokhtarzada",
    "Paul Biggar",
    "Christina Noren",
    "Sidra Qasim"
]

#prioritize signatures with Organizations
#get singatures with organizations and shuffle
#get signatures without organizations and shuffle
#combine the 2 lists

def ensure_dict_in_top_n(lst, specific_names):
    # Insert name between 1 and n
    n=50

    # Separate dictionaries with and without 'Organization' values
    with_org = [d for d in lst if 'Organization' in d['fields'] and d['fields']['Organization']]
    without_org = [d for d in lst if not ('Organization' in d['fields'] and d['fields']['Organization'])]

    # Shuffle both groups separately
    shuffle(with_org)
    shuffle(without_org)

    # Combine the groups, ensuring 'with_org' is at the top
    combined = with_org + without_org

    # Ensure specific names are in the top n results
    for name in specific_names:
        is_in_top_n = any(d['fields']['Full name'] == name for d in combined[:n])
        
        if not is_in_top_n:
            # Find and remove the dictionary with the specific name
            target_dict = next(d for d in combined if d['fields']['Full name'] == name)
            combined.remove(target_dict)
            
            # Insert it into a random position within the top n
            random_position = randint(0, n-1)
            combined.insert(random_position, target_dict)

    return combined

signatures = ensure_dict_in_top_n(signatures, top_names)

# Generate reverse ordered signatures
recent_signatures = signatures.copy()
recent_signatures.sort(reverse=True, key=lambda sig: sig['createdTime'])

# Run templates
env = Environment(loader=FileSystemLoader('templates'))
env.globals.update(
    signatures=signatures,
    recent_signatures=recent_signatures,
    sum=sum,
    )

for page in ['index.html', 'all_signatures.html']:    
    pagesrc = env.get_template(page).render(page=page)
    open(f'docs/{page}', 'w', encoding='utf-8').write(pagesrc)
