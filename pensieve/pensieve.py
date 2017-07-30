from __future__ import unicode_literals
import spacy
import os
import textacy
import _pickle as pickle
from numpy.random import randint
from collections import Counter
from IPython import embed

print('Loading spaCy...')
NLP = spacy.load('en')


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
        self.docs = None
        self.paragraphs = None

    @property
    def docs(self):
        if not self._docs:
            self._docs = self.read_corpus()
        return self._docs

    @property
    def paragraphs(self):
        if not self._paragraphs:
            self._paragraphs = [doc.paragraphs for doc in self.docs]
        return self._paragraphs

    def read_corpus(self):
        """
        Get a list of Doc objects for every file in the corpus.

        Returns:
            docs: list of pensieve.Doc objects
        """
        file_list = os.listdir(self.corpus_dir)
        file_paths = [os.path.join(self.corpus_dir, f) for f in file_list]
        docs = []
        for i, file_path in enumerate(file_paths):
            print('Loading '+file_path)
            docs.append(Doc(file_path, i, self))
        return docs

    def find_character_paragraphs(self, char_name, density_cut):
        """
        Find paragraphs in the corpus where character is mentioned
        heavily.

        Args:
            char_name:   Name of character to search for. Can also
                         accept a list of aliases
            density_cut: Only return paragraphs that pass this cut on
                         (number of mentions)/(number of sentences)

        Returns:
            character_paragraphs: list of Paragraph objects in doc that
                                  pass the density cut
        """
        if isinstance(char_name, str):
            char_name = [char_name]
        char_pars = []
        for doc in self.docs:
            char_pars += doc.find_character_paragraphs(char_name,
                                                       density_cut)
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
            memories.append(par.culled_words_dict)
        return memories


class Doc(object):

    def __init__(self, path_to_text, doc_id=None, corpus=None):
        """
        Document level object

        Args:
            path_to_text: file path to txt of document
            id: index of doc in corpus [default: None]
            corpus: Corpus object containing document
                    [default: None]

        Attributes:
            text: unicode string of text in document
            paragraphs: list of Paragraph objects for paragraph in doc
            words: dictionary of mem words extracted from doc
        """
        self.path_to_text = path_to_text
        self.id = doc_id
        self.corpus = corpus
        self.text = open(path_to_text, 'r').read()
        self.paragraphs = None
        self.words = {'times': Counter(),
                      'verbs': Counter(),
                      'names': Counter(),
                      'places': Counter(),
                      'things': Counter(),
                      'mood': None}

    def read_paragraphs(self):
        """
        Update self.paragraphs and self.words attributes

        Args:
            None

        Returns:
            None
        """
        self.paragraphs = []
        for i, p in enumerate(self.text.split('\n')):
            if len(p.split(' ')) < 30:
                continue
            self.paragraphs.append(Paragraph(p, i, self))

    def find_character_paragraphs(self, char_name, density_cut=0.4):
        """
        Find paragraphs in the corpus where character is mentioned
        heavily.

        Args:
            char_name:   Name of character to search for. Can also
                         accept a list of aliases
            density_cut: Only return paragraphs that pass this cut on
                         (number of mentions)/(number of sentences)

        Returns:
            character_paragraphs: list of Paragraph objects in doc that
                                  pass the density cut
        """
        if isinstance(char_name, str):
            char_name = [char_name]
        char_pars = []
        if self.paragraphs is None:
            self.read_paragraphs()
        for par in self.paragraphs:
            n_sentences = len(list(par.spacy_doc.sents))
            if n_sentences == 0:
                continue
            mentions = 0
            for alias in char_name:
                mentions += par.words['names'][alias]
            density = mentions/n_sentences
            if density > density_cut:
                char_pars.append(par)
        return char_pars

    def build_doc_memories(self, char_name, density_cut=0.8,
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
            memories.append(par.culled_words_dict)
        return memories


class Paragraph(object):

    def __init__(self, text, par_id=None, doc=None):
        """
        Paragraph level object

        Args:
            text: text of paragraph
            par_id: index of paragraph in doc
            doc: Document object containing paragraph
                 [default: None]

        Attributes:
            spacy_doc: spaCy Doc object
            words: dictionary of all words extracted with spaCy
        """
        self.doc = doc
        self.text = text
        self.id = par_id
        self.spacy_doc = NLP(text)
        self.words = self.build_words_dict()
        self.culled_words_dict = None

    def build_words_dict(self):
        """
        Use textacy to extract entities and main verbs from the paragraph.
        """
        words_dict = {'times': Counter(),
                      'verbs': Counter(),
                      'names': Counter(),
                      'places': Counter(),
                      'things': Counter(),
                      'mood': None,
                      'img_url': None}
        times = textacy.extract.named_entities(self.spacy_doc, include_types=['DATE', 'TIME', 'EVENT'])
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.spacy_doc)
        names = textacy.extract.named_entities(self.spacy_doc, include_types=['PERSON'])
        places = textacy.extract.named_entities(self.spacy_doc, include_types=['LOC', 'GPE', 'FACILITY'])
        things = textacy.extract.named_entities(self.spacy_doc, include_types=['ORG', 'NORP', 'WORK_OF_ART', 'PRODUCT'])
        for time in times:
            words_dict['times'][time.text] += 1
        for verb in main_verbs:
            words_dict['verbs'][verb.text] += 1
        for name in names:
            words_dict['names'][name.text] += 1
        for place in places:
            words_dict['places'][place.text] += 1
        for thing in things:
            words_dict['things'][thing.text] += 1
        return words_dict

    def sanitize_places_and_things(self, freq_cut=100):
        """
        Get a sanitized version of paragraph places and things.
        Get places that don't appear in the most common doc names, and
        things that don't appear in the most common doc places.

        Args:
            freq_cut: frequency to define "commonness" within the doc

        Returns:
            places: sanitized place names
            things: sanitized thing names
        """
        doc_names = dict(self.doc.words['names'].most_common(freq_cut))
        doc_places = dict(self.doc.words['places'].most_common(freq_cut))
        places = []
        things = []
        for place in self.words['places']:
            if place not in doc_names:
                places.append(place)
        for thing in self.words['things']:
            if thing not in doc_places and thing not in places:
                things.append(thing)
        return places, things

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
        main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.spacy_doc)
        for verb in main_verbs:
            if (verb.text in doc_verbs) and (doc_verbs[verb.text] < verbs_cut):
                span = textacy.spacy_utils.get_span_for_verb_auxiliaries(verb)
                complex_verb = self.spacy_doc[span[0]].text
                span_end = 1
                if textacy.spacy_utils.is_negated_verb(verb) is True:
                    complex_verb = complex_verb+' not '
                    span_end = 0
                for a in range(span[0]+1, span[1]+span_end):
                    complex_verb += " "+self.spacy_doc[span[1]].text
                subjects = textacy.spacy_utils.get_subjects_of_verb(verb)
                objects = textacy.spacy_utils.get_objects_of_verb(verb)
                if len(subjects) > 0 and len(objects) > 0:
                    for subject in subjects:
                        for obj in objects:
                            svo = [subject.text, complex_verb, obj.text]
                            activities.append(' '.join(svo))
        return activities

    def gen_mem_dict(self, character, verb_cut=500, name_cut=100):
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
        if len(mem_people) == 0:
            mem_people.append('alone')  # Some scenes have no other names
        mem_places, mem_things = self.sanitize_places_and_things(name_cut)
        mem_activities = self.gen_mem_activity(verb_cut)
        culled_output = {'people': mem_people,
                         'places': mem_places,
                         'activities': mem_activities,
                         'things': mem_things,
                         'times': self.words['times'],
                         'mood': self.words['mood'],
                         'img_url': self.words['img_url']}
        return culled_output

    def search_for_images(self):
        """
        Determine a query to use to search Bing for images
        """
        pass


if __name__ == '__main__':
    try:
        harry_pars = pickle.load(open('harry_pars_full_corpus.pkl', 'rb'))
    except IOError:
        corpus = Corpus('../corpus/')
        harry_pars = corpus.find_character_paragraphs(['Harry', 'Potter'], 0.4)
        pickle.dump(harry_pars, open('harry_pars_full_corpus.pkl', 'wb'))

    from pprint import pprint
    print('{} paragraphs found'.format(len(harry_pars)))
    rand_index = randint(0, len(harry_pars)-1)
    test_par = harry_pars[rand_index]
    print('Book '+str(test_par.doc.id+1))
    print('Paragraph '+str(test_par.id))
    print(test_par.text)
    pprint(test_par.words)
    # embed()

