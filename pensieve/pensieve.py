from __future__ import unicode_literals
import spacy
import os
import textacy
from collections import Counter

nlp = spacy.load('en')


class Corpus(object):

    def __init__(self, corpus_dir=None):
        """
        Corpus to extract mems from

        Args:
            corpus_dir: Directory containing all corpus files

        Attributes:
            docs: List of Doc objects from corpus
            paragraphs: List of Paragraph objects from corpus
        """
        self.corpus_dir = corpus_dir
        self.docs = self.read_corpus()
        self.paragraphs = [doc.paragraphs for doc in self.docs]

    def read_corpus(self):
        """
        Get a list of Doc objects for every file in the corpus.

        Returns:
            docs: list of pensieve.Doc objects
        """
        file_list = os.listdir(self.corpus_dir)
        file_paths = [os.path.join(self.corpus_dir, f) for f in file_list]
        docs = []
        for file_path in file_paths:
            print('Loading '+file_path)
            docs.append(Doc(file_path, self))
        return docs

    def find_character_paragraphs(self, char_name, density_cut):
        """
        Find paragraphs in the corpus where character is mentioned heavily.

        Args:
            char_name:   Name of character to search for. Can also
                         accept a list of aliases
            density_cut: Only return paragraphs that pass this cut on
                         (number of mentions)/(number of sentences)

        Returns:
            character_paragraphs: dict of (doc_number, par_info) pairs that
                                  pass density_cut
        """
        if isinstance(char_name, str):
            char_name = [char_name]
        char_pars = []
        for doc in self.docs:
            for par in doc.paragraphs:
                n_sentences = len(list(par.doc.sents))
                if n_sentences == 0:
                    continue
                mentions = 0
                for alias in char_name:
                    mentions += len(par.words['names'][alias])
                density = mentions/n_sentences
                if density > density_cut:
                    char_pars.append(par)
        return char_pars

    def build_corpus_memories(self, char_name, density_cut=0.8,
                              verb_cut=500, name_cut=100):
        """
        Builds memories from character paragraphs.

        Args:
            char_name: Name of character to build memories for
            density_cut: mentions/sentences cut to select paragraphs
                         constituting memory
            verb_cut: frequency of verb appearence in corpus. If
                      verb_freq < verb_cut, the verb stays in the
                      memory
            name_cut: like verb_cut, but for people, places, and things

        Returns:
            memories: list of sanitized memories, ready to be put in DB
        """
        memories = []
        char_pars = self.find_character_paragraphs(char_name, density_cut)
        for par in char_pars:
            memories.append(par.culled_words_dict())
        return memories


class Doc(object):

    def __init__(self, path_to_text, corpus=None):
        """
        Document level object

        Args:
            path_to_text: file path to txt of document
            corpus: Corpus object containing document
                    [default: None]

        Attributes:
            text: unicode string of text in document
            paragraphs: list of Paragraph objects for paragraph in doc
            words: dictionary of mem words extracted from doc
        """
        self.path_to_text = path_to_text
        self.text = open(path_to_text, 'r').read()
        self.paragraphs = []
        for p in self.text.split('\n'):
            self.paragraphs.append(Paragraph(p, self))

        self.words = {'times': Counter(),
                      'verbs': Counter(),
                      'names': Counter(),
                      'places': Counter(),
                      'objects': Counter()}
        for p in self.paragraphs:
            for key in p.words:
                self.words[key] = self.words[key]+p.words[key]


class Paragraph(object):

    def __init__(self, text, doc=None):
        """
        Paragraph level object

        Args:
            text: text of paragraph
            doc: Document object containing paragraph
                 [default: None]

        Attributes:
            spacy_doc: spaCy Doc object
            words: dictionary of all words extracted with spaCy
            culled_words: dictionary of words passing importance cuts
        """
        self.spacy_doc = nlp(text)
        self.text = text
        self.words = self.build_words_dict()
        self.culled_words = self.culled_words_dict()

    def build_words_dict(self):
        """
        Use textacy to extract entities and main verbs from the paragraph.
        """
        words_dict = {'times': Counter(),
                      'verbs': Counter(),
                      'names': Counter(),
                      'places': Counter(),
                      'objects': Counter()}
        times = textacy.extract.named_entities(self.spacy_doc, include_types=['DATE', 'TIME', 'EVENT'])
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.spacy_doc)
        names = textacy.extract.named_entities(self.spacy_doc, include_types=['PERSON'])
        places = textacy.extract.named_entities(self.spacy_doc, include_types=['LOC', 'GPE', 'FACILITY'])
        objects = textacy.extract.named_entities(self.spacy_doc, include_types=['ORG', 'NORP', 'WORK_OF_ART', 'PRODUCT'])
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

    def sanitize_places_and_objects(self, freq_cut=100):
        """
        Get a sanitized version of paragraph places and objects.
        Get places that don't appear in the most common doc names, and
        objects that don't appear in the most common doc places.

        NOTE: I'm not really sure what this function is actually doing...

        Args:
            freq_cut: frequency to define "commonness" within the doc

        Returns:
            places: sanitized place names
            objects: sanitized object names
        """
        doc_names = dict(self.doc.words['names'].most_common(freq_cut))
        doc_places = dict(self.doc.words['places'].most_common(freq_cut))
        places = []
        objects = []
        for place in self.words['places']:
            if place not in doc_names:
                places.append(place)
        for obj in self.words['objects']:
            if obj not in doc_places and obj not in places:
                objects.append(obj)
        return places, objects

    def gen_mem_activity(self, verbs_cut=500):
        """
        Determine the key activities in a paragraph by removing
        verbs commonly used in the doc

        Args:
            verbs_cut: frequency of verb in doc to cut on

        Returns:
            activities: list of key activity strings
        """
        activities = []
        doc_verbs = dict(self.doc.words['verbs'].most_common(verbs_cut))
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.doc)
        for verb in main_verbs:
            if (verb.text in doc_verbs) and (doc_verbs[verb.text] < verbs_cut):
                span = textacy.spacy_utils.get_span_for_verb_auxiliaries(verb)
                complex_verb = self.doc[span[0]].text
                span_end = 1
                if textacy.spacy_utils.is_negated_verb(verb) is True:
                    complex_verb = complex_verb+' not '
                    span_end = 0
                for a in range(span[0]+1, span[1]+span_end):
                    complex_verb += " "+self.doc[span[1]].text
                subjects = textacy.spacy_utils.get_subjects_of_verb(verb)
                objects = textacy.spacy_utils.get_objects_of_verb(verb)
                if len(subjects) > 0 and len(objects) > 0:
                    activities.append([subjects, complex_verb, objects])
        return activities

    def culled_words_dict(self, character, verb_cut, name_cut):
        """
        Determine the most important words of those collected.

        Args:
            character: character name string or list of aliases
            verb_cut: frequency of verb in doc to cut on
            name_cut: frequency of name in doc to cut on

        Returns:
            culled_output: dictionary of most important people, places,
                           and activities
        """
        mem_people = []
        if isinstance(character, str):
            character = [character]
        for name in self.words['names']:
            if name not in character:  # Ignore redundant mention of subject
                mem_people.append(name)
        mem_places, mem_objects = self.sanitize_places_and_objects(name_cut)
        mem_activities = self.gen_mem_activity(self.doc.words, verb_cut)
        culled_output = {'people': mem_people,
                         'places': mem_places,
                         'activities': mem_activities}
        return culled_output
