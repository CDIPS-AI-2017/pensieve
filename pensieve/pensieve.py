from __future__ import unicode_literals
import spacy
import os
import textacy
from collections import defaultdict
from collections import Counter

nlp = spacy.load('en')


class Corpus(object):

    def __init__(self, corpus_dir=None):
        self.corpus_dir = corpus_dir
        self.docs = self.read_corpus(corpus_dir)
        self.paragraphs = [doc.paragraphs for doc in self.docs]

    def read_corpus(self, corpus_dir):
        """
        Get a list of Doc objects for every file in the corpus directory.
        """
        file_list = os.listdir(corpus_dir)
        file_paths = [os.path.join(corpus_dir, f) for f in file_list]
        docs = []
        for file_path in file_paths:
            print('Loading '+file_path)
            docs.append(Doc(file_path))
        return docs


class Doc(object):

    def __init__(self, path_to_text, corp_id=None):
        self.path_to_text = path_to_text
        self.text = open(path_to_text, 'r').read()
        self.corp_id = corp_id
        self.par_info = {'time': corp_id}
        self.paragraphs = []
        for p in self.text.split('\n\n'):
            self.paragraphs.append(Paragraph(p, self.par_info))
        
        self.words = {'times':Counter(), 'verbs':Counter(), 'names':Counter(), 'places':Counter(), 'objects':Counter()}
        for p in self.paragraphs:
            for key in p.words:
                self.words[key] =self.words[key]+p.words[key]

class Paragraph(object):

    def __init__(self, text, mem_info=defaultdict(list)):
        self.doc = nlp(text)
        self.text = text
        self.mem_info = mem_info
        self.words = self.build_words_dict()

    def build_words_dict(self):
        doc_times = Counter()
        doc_verbs = Counter()
        doc_names = Counter()
        doc_places = Counter()
        doc_objects = Counter()

        times =  textacy.extract.named_entities(self.doc,include_types ={'DATE', 'TIME', 'EVENT'})
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.doc)
        names = textacy.extract.named_entities(self.doc,include_types ={'PERSON'})
        places = textacy.extract.named_entities(self.doc,include_types ={'LOC','GPE','FACILITY'})
        objects = textacy.extract.named_entities(self.doc,include_types ={'ORG', 'NORP', 'WORK_OF_ART', 'PRODUCT'})
        for time in times:
            doc_times[time.text]+=1
        for verb in main_verbs:
            doc_verbs[verb.text]+=1
        for name in names:
            doc_names[name.text]+=1
        for place in places:
            doc_places[place.text] +=1
        for object in objects:
            doc_objects[object.text]+=1

        return {'times':doc_times, 'verbs':doc_verbs, 'names':doc_names, 'places':doc_places, 'objects':doc_objects}
