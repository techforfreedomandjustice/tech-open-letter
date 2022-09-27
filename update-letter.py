import json
import os

from collections import defaultdict
from random import shuffle

from jinja2 import Template, Environment, FileSystemLoader
from pyairtable import Table

airtable_id = os.environ.get('AIRTABLE_ID')
airtable_api_key = os.environ.get('AIRTABLE_API_KEY')

# Read in the university domain names list from https://github.com/Hipo/university-domains-list
with open("./world_universities_and_domains.json", encoding='utf-8') as src_file:
    university_domains = json.load(src_file)

# Process domain names to get mappings from domains to countries and country counts
dom2uni = {}
dom2country = {}
for entry in university_domains:
    for domain in entry['domains']:
        dom2uni[domain] = entry['name']
        dom2country[domain] = entry['country']

# Load the signatures data from Airtable, and randomly order
table_name = 'Signatures'
signatures_table = Table(airtable_api_key, airtable_id, table_name)
signatures = signatures_table.all()
# Remove signatures that were withdrawn
signatures = [signature for signature in signatures if not signature['fields'].get('Removals', None)]
shuffle(signatures)

# Generate stats
country_counts = defaultdict(int)
position_counts = defaultdict(int)
for row in signatures:
    F = row['fields']
    if 'Email' in F:
        try:
            username, domain = F['Email'].split('@')
            if domain in dom2country:
                country_counts[dom2country[domain]] += 1
        except:
            pass
    if 'Status' in F:
        position_counts[F['Status']] += 1

# Run templates
env = Environment(loader=FileSystemLoader('templates'))
env.globals.update(
    signatures=signatures,
    country_counts=country_counts,
    position_counts=position_counts,
    sum=sum,
    )

for page in ['index.html', 'all_signatures.html', 'why.html', 'stats.html']:
    pagesrc = env.get_template(page).render(page=page)
    open(f'docs/{page}', 'w', encoding='utf-8').write(pagesrc)
