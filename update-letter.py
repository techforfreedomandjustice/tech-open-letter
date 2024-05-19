
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

target_name = 'Paul Graham'

def ensure_dict_in_top_n(lst, target_name):
    # Insert name between 1 and n
    n=10

    # Step 1: Shuffle the list
    shuffle(lst)

    # Step 2: Check if the dictionary with the target_name is in the top n positions
    is_in_top_n = any(d['fields']['Full name'] == target_name for d in lst[:n])
    
    if not is_in_top_n:
        # Step 3: Find and remove the dictionary with the target_name from its current position
        target_dict = next(d for d in lst if d['fields']['Full name'] == target_name)
        lst.remove(target_dict)
        
        # Insert the dictionary into a random position within the top n
        random_position = randint(0, n-1)
        lst.insert(random_position, target_dict)

    return lst

signatures = ensure_dict_in_top_n(signatures, target_name)

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
