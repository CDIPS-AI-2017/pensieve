from __future__ import unicode_literals
import spacy
import os
from collections import defaultdict


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


class Paragraph(object):

    def __init__(self, text, mem_info=defaultdict(list)):
        self.doc = nlp(text)
        self.text = text
        self.mem_info = mem_info