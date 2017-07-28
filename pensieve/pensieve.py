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

    def find_character_paragraphs(self, character_name, density_cut):
        """
        Find paragraphs in the corpus where character is mentioned.
        TODO: We want to have some metric for selecting paragraphs that are
        likely to be about the character, not paragraphs where they're
        just mentioned.
        """
        charater_paragraphs = {}
        for i_doc, doc in enumerate(self.docs):
            this_p = {}
            for i_p, p in enumerate(doc.paragraphs):
                no_sentences = len(list(p.doc.sents))
                if no_sentences == 0:
                    continue
                char_density = p.words['names'][character_name]/no_sentences
                if char_density > density_cut:
                    this_p.update({i_p:char_density})
            charater_paragraphs.update({i_doc: this_p})

        return charater_paragraphs

    def build_corpus_memories(self, character_name, density_cut = 0.8, verb_cut = 500, name_cut = 100):
        """
        Builds memories from charactrer paragraphs. Inputs are character name, the density_cut = character freq/# sentences 
        to select character paragraphs. Verb cut is used to select meaningful verbs (frequency in doc < verb_cut) and name
        cut used to sanitize places and objects (make sure they do not appear in name_cut most frequent 'names')
        """
        memories = []
        character_paragraphs  = self.find_character_paragraphs(character_name, density_cut)
        for doc_id in character_paragraphs:
            for para_id in character_paragraphs[doc_id]:
                people, places, activities = self.docs[doc_id].paragraphs[para_id].culled_words_dict(self.docs[doc_id].words,character_name)
                if len(activities) != 0:
                    memories.append( {'People':people,'Places':places,'Activity':activities } )
        return memories

class Doc(object):

    def __init__(self, path_to_text, corp_id=None):
        self.path_to_text = path_to_text
        self.text = open(path_to_text, 'r').read()
        self.corp_id = corp_id
        self.par_info = {'time': corp_id}
        self.paragraphs = []
        for p in self.text.split('\n'):
            self.paragraphs.append(Paragraph(p, self.par_info))

        self.words = {'times': Counter(),
                      'verbs': Counter(),
                      'names': Counter(),
                      'places': Counter(),
                      'objects': Counter()}
        for p in self.paragraphs:
            for key in p.words:
                self.words[key] = self.words[key]+p.words[key]
                

class Paragraph(object):

    def __init__(self, text, mem_info=None):
        self.doc = nlp(text)
        self.text = text
        self.mem_info = mem_info if mem_info is not None else defaultdict(list)
        self.words = self.build_words_dict()

    def build_words_dict(self):
        """
        Use textacy to extract entities and main verbs from the paragraph.
        """
        words_dict = {'times': Counter(),
                      'verbs': Counter(),
                      'names': Counter(),
                      'places': Counter(),
                      'objects': Counter()}
        times = textacy.extract.named_entities(self.doc, include_types=['DATE', 'TIME', 'EVENT'])
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.doc)
        names = textacy.extract.named_entities(self.doc, include_types=['PERSON'])
        places = textacy.extract.named_entities(self.doc, include_types=['LOC', 'GPE', 'FACILITY'])
        objects = textacy.extract.named_entities(self.doc, include_types=['ORG', 'NORP', 'WORK_OF_ART', 'PRODUCT'])
        for time in times:
            words_dict['times'][time.text] += 1
        for verb in main_verbs:
            words_dict['verbs'][verb.text] += 1
        for name in names:
            words_dict['names'][name.text] += 1
        for place in places:
            words_dict['places'][place.text] += 1
        for obj in objects:
            words_dict['objects'][obj.text] += 1
        return words_dict

    def culled_words_dict(self, doc_words, character):
        """
        Determine the most important words of those collected.
        """
        mem_people = []
        for name in self.words['names']:
            if name != character: # All memories clearly include the character, so don't include it in mem object itself
                mem_people.append(name)
        mem_places, mem_objects = self.sanitized_places_and_objects(doc_words)
        mem_activities = self.gen_mem_activity(doc_words)
        return mem_people, mem_places, mem_activities

    def sanitized_places_and_objects(self, doc_words, freq_cut = 100):
        """
        Returns a sanitized version of paragraph places. We remove any word that appears in commonly
        in document as name. We assume that sPacy flagged names will be purer than the places or objects
        """
        doc_names = dict(doc_words['names'].most_common(freq_cut))
        doc_places = dict(doc_words['places'].most_common(freq_cut))
        places = []
        objects = []
        for place in self.words['places']:
            if place not in doc_names:
                places.append(place)
        for obj in self.words['objects']:
            if obj not in doc_places and obj not in places:
                objects.append(obj)
        return places, objects

    def gen_mem_activity(self, doc_words, verbs_cut = 500):
        """
        Determine the activities in a paragraph. The dict doc verbs is passed as it is used to choose
        significant verbs. The cut is set to frequency < 500 over the full document, but this can be set 
        """
        results = []
        doc_verbs = dict(doc_words['verbs'].most_common(verbs_cut))
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.doc)
        for verb in main_verbs:
            if verb.text not in doc_verbs or doc_verbs[verb.text] < verbs_cut:
                # --- Getting the auxiliary verbs
                span = textacy.spacy_utils.get_span_for_verb_auxiliaries(verb)
                complex_verb = self.doc[span[0]].text
                span_end = 1
                if textacy.spacy_utils.is_negated_verb(verb) is True:
                    complex_verb = complex_verb+' not '
                    span_end = 0
                for a in range(span[0]+1,span[1]+span_end):
                    complex_verb +=" "+self.doc[span[1]].text
                # ---
                subjects = textacy.spacy_utils.get_subjects_of_verb(verb)
                objects = textacy.spacy_utils.get_objects_of_verb(verb)
                if len(subjects)>0 and len(objects)>0:
                    results.append([subjects,complex_verb,objects])
        return results

    def words_dict_to_json(self):
        """
        Dump the words_dict to JSON using the mem schema
        """
        pass

