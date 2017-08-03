import json
import os
from datetime import datetime

CONCEPT_MAP = {'people': 'Person',
               'places': 'Place',
               'things': 'Thing',
               'activities': 'Activity',
               'times': 'Time'}


def dump_mem_to_json(mem_dict, save=None):
    """
    Convert mem_dict into a JSON file following the schema and write

    Args:
        mem_dict: dictionary of mem information
        save: path to save JSON to [default: None]

    Returns:
        mem_json: JSON object for memory
    """
    node = {'name': '',
            'label': '',
            'imageURL': mem_dict['img_url'],
            'iconURL': '',
            'created': '',
            'updated': ''}
    relation = {'weight': 0.5,
                'joy': 0.0,
                'fear': 0.0,
                'surprise': 0.0,
                'sadness': 0.0,
                'disgust': 0.0,
                'anger': 0.0}
    concepts = []
    for concept_type, concept_items in mem_dict.items():
        if concept_items is None:
            continue
        if concept_type in ('mood', 'img_url', 'narrative'):
            continue
        for concept_item in concept_items:
            clean_text = concept_item.replace(' ', '_')
            clean_text = clean_text.lower()
            concept = {'node': {}, 'relation': {}}
            concept['node'] = {'concept': CONCEPT_MAP[concept_type],
                               'name': clean_text,
                               'label': '',
                               'iconURL': '',
                               'imageURL': ''}
            concept_relation = 'Has_{}'.format(concept['node']['concept'])
            concept['relation'] = {'relation': concept_relation,
                                   'name': '',
                                   'iconURL': '',
                                   'imageURL': '',
                                   'weight': 0.5,
                                   'created': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                                   'updated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                                   'originType': 'OriginUserDefined',
                                   'joy': 0.0,
                                   'fear': 0.0,
                                   'surprise': 0.0,
                                   'sadness': 0.0,
                                   'disgust': 0.0,
                                   'anger': 0.0}
            concepts.append(concept)
    narrative = {'node': {'name': '',
                          'label': 'title',
                          'text': mem_dict['narrative']},
                 'relation': {'weight': 0.5}}
    mem = {'memory': '',
           'node': node,
           'relation': relation,
           'concepts': concepts,
           'narrative': narrative}

    if save is not None:
        with open(os.path.abspath(save), 'w') as f:
            json.dump(mem, f)

    return mem
