import json
import os
from tld import get_tld
import matplotlib.pyplot as plt

with open('entities.json', 'r') as f:
    ENTITIES = json.load(f)

def get_domain(url: str) -> str:
    return get_tld(url, as_object=True).fld

def get_entity_by_domain(domain: str) -> str:
    for entity, data in ENTITIES['entities'].items():
        if domain in data['resources'] or domain in data['properties']:
            return entity
    return None

def analyze_har(file_path: str) -> dict:
    results = {
        'num_reqs': 0,
        'num_third_party_requests': 0,
        'num_distinct_third_party_requests': 0,
        'num_distinct_entities': 0
    }

    with open(file_path, 'r') as f:
        har_data = json.load(f)
    
    entries = har_data.get('log', {}).get('entries', [])
    results['num_reqs'] = len(entries)

    first_party = get_domain(har_data['log']['entries'][0]['request']['url'])
    distinct_third_parties = set()
    distinct_entities = set()

    for entry in entries:
        response = entry.get('response', {})
        if response.get('status') and response.get('headers') and response.get('content'):
            if response.get('redirectURL'):
                response_domain = get_domain(response.get('redirectURL'))
                if response_domain and response_domain != first_party:
                    distinct_third_parties.add(response_domain)
                    results['num_third_party_requests'] += 1

    for third_party in distinct_third_parties:
        entity = get_entity_by_domain(third_party)
        if entity:
            distinct_entities.add(entity)

    results['num_distinct_third_party_requests'] = len(distinct_third_parties)
    results['num_distinct_entities'] = len(distinct_entities)

    return results

def draw_boxplot(ac_list: list, rej_list: list, blk_list: list, metric: str):
    ac_vals = [ r[metric] for r in ac_list ]
    rej_vals = [ r[metric] for r in rej_list ]
    blk_vals = [ r[metric] for r in blk_list ]

    plt.boxplot([ac_vals, rej_vals, blk_vals], labels=['Accept', 'Reject', 'Block'])
    plt.title(f'boxplot of {metric}')
    plt.xlabel('Decision')
    plt.ylabel(f'{metric} per website')
    plt.show()
    os.makedirs('boxplots', exist_ok=True)
    plt.savefig(f'boxplots/boxplot_{metric}.png')
    plt.close()
    
def test():
    ac_list = []
    rej_list = []
    blk_list = []

    for file in os.listdir('har_logs_accept'):
        if file.endswith('.har'):
            ac_list.append(analyze_har('har_logs_accept/' + file))
    
    for file in os.listdir('har_logs_reject'):
        if file.endswith('.har'):
            rej_list.append(analyze_har('har_logs_reject/' + file))

    for file in os.listdir('har_logs_block'):
        if file.endswith('.har'):
            blk_list.append(analyze_har('har_logs_block/' + file))

    draw_boxplot(ac_list, rej_list, blk_list, 'num_reqs')


if __name__ == '__main__':
    test()