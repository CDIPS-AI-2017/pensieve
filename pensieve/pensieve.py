from __future__ import unicode_literals
import spacy
import os
import textacy
import string
from .json_dump import dump_mem_to_json
import json
from collections import Counter

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
        self.corpus_dir = os.path.abspath(corpus_dir)
        self._docs = None
        self._paragraphs = None

    @property
    def docs(self):
        if not self._docs:
            self._docs = self.read_corpus()
        return self._docs

    @property
    def paragraphs(self):
        if not self._paragraphs:
            self._paragraphs = []
            for doc in self.docs:
                self._paragraphs += doc.paragraphs
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

    def gather_corpus_memories(self, char_name, density_cut=0.8,
                               verb_cut=500, name_cut=100, save=None):
        """
        Collects memories from all character paragraphs in the corpus.

        Args:
            char_name: Name of character to build memories for
                       Can be a list of aliases or a string
            density_cut: mentions/sentences cut to select paragraphs
                         constituting memory
            verb_cut: frequency of verb appearence in corpus. If
                      verb_freq < verb_cut, the verb stays in the
                      memory
            name_cut: like verb_cut, but for people, places, and things
            save: save mem JSON files to this path. If None, files are
                  not saved

        Returns:
            memories: list of memories, ready to be put in DB
        """
        memories = []
        char_pars = self.find_character_paragraphs(char_name, density_cut)
        for par in char_pars:
            mem_dict = par.gen_mem_dict(char_name, verb_cut, name_cut)
            memories.append(dump_mem_to_json(mem_dict))
        if save is not None:
            if isinstance(char_name, str):
                filebase = char_name.replace(' ', '_').lower().strip()
            else:
                filebase = '_'.join(char_name)
                filebase = filebase.replace(' ', '_').lower().strip()
            path = os.path.join(save, filebase+'.json')
            with open(path) as f:
                json.dump(memories, f)
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
        self._paragraphs = None
        self._words = None

    @property
    def paragraphs(self):
        if not self._paragraphs:
            print('Generating paragraphs for doc '+str(self.id))
            self._paragraphs = []
            for i, p in enumerate(self.text.split('\n')):
                if len(p.split(' ')) < 30:
                    continue
                self._paragraphs.append(Paragraph(p, i, self))
        return self._paragraphs

    @property
    def words(self):
        if not self._words:
            self._words = {'times': Counter(),
                           'activities': Counter(),
                           'people': Counter(),
                           'places': Counter(),
                           'things': Counter()}
            for par in self.paragraphs:
                for key in self._words:
                    self._words[key] += par.words[key]
        return self._words

    def find_character_paragraphs(self, char_name, density_cut=0.8):
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
        for par in self.paragraphs:
            n_sentences = len(list(par.spacy_doc.sents))
            if n_sentences == 0:
                continue
            mentions = 0
            for alias in char_name:
                mentions += par.words['people'][alias]
            density = mentions/n_sentences
            if density > density_cut:
                char_pars.append(par)
        return char_pars

    def gather_doc_memories(self, char_name, density_cut=0.8,
                            verb_cut=500, name_cut=100, save=None):
        """
        Collects memories from character paragraphs.

        Args:
            char_name: Name of character to build memories for
            density_cut: mentions/sentences cut to select paragraphs
                         constituting memory
            verb_cut: frequency of verb appearence in corpus. If
                      verb_freq < verb_cut, the verb stays in the
                      memory
            name_cut: like verb_cut, but for people, places, and things
            save: save mem JSON files to this path. If None, files are
                  not saved

        Returns:
            memories: list of sanitized memories, ready to be put in DB
        """
        memories = []
        char_pars = self.find_character_paragraphs(char_name, density_cut)
        for par in char_pars:
            mem_dict = par.gen_mem_dict(char_name, verb_cut, name_cut)
            memories.append(dump_mem_to_json(mem_dict))
        if save is not None:
            if isinstance(char_name, str):
                filebase = char_name.replace(' ', '_').lower().strip()
            else:
                filebase = '_'.join(char_name)
                filebase = filebase.replace(' ', '_').lower().strip()
            path = os.path.join(save, filebase+'.json')
            with open(path, 'w') as f:
                json.dump(memories, f, indent=4)
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

    def extract_times(self):
        """
        Extract times mentioned in the text and add book time information
        """
        times = []
        include_types = ['DATE', 'TIME', 'EVENT']
        for time in textacy.extract.named_entities(self.spacy_doc,
                                                   include_types=include_types):
            times.append(time)
        times.append('Book '+str(self.doc.id))
        times.append('Par. '+str(self.id))
        return times

    def extract_activities(self, n_verbs=3):
        """
        Extract verbs in the paragraph
        """
        verb_ranking = [(x, x.rank) for x in textacy.spacy_utils.get_main_verbs_of_sent(self.spacy_doc)]
        verbs = []
        for verb in sorted(verb_ranking, key=lambda x: -x[1])[:n_verbs]:
            text = verb[0].lemma_
            if text[0] in string.ascii_lowercase:
                verbs.append(text)
        return verbs

    def extract_people(self):
        """
        Extract names in paragraph
        """
        names = []
        for name in textacy.extract.named_entities(self.spacy_doc,
                                                   include_types=['PERSON']):
            # Exclude words too short to be names and strange characters
            if len(name.text) < 3:
                continue
            # Handle possessives
            if name.text[-2] not in string.ascii_lowercase:
                names.append(name.text[:-2])
            else:
                names.append(name.text)
        return names

    def extract_places(self):
        """
        Extract places in paragraph
        """
        places = []
        include_types = ['LOC', 'GPE', 'FACILITY']
        for place in textacy.extract.named_entities(self.spacy_doc,
                                                include_types=include_types):
            if place.text != 'Hagrid':
                places.append(place.text)
        return places

    def extract_things(self):
        """
        Extract things mentioned in paragraph
        """
        # Get named objects
        include_types = ['ORG', 'NORP', 'WORK_OF_ART', 'PRODUCT']
        things = []
        for obj in textacy.extract.named_entities(self.spacy_doc,
                                                  include_types=include_types):
            things.append(obj)
        # Get noun chunks
        for nch in textacy.extract.noun_chunks(self.spacy_doc, drop_determiners=True):
            if len(nch) == 1 and nch[0].pos == spacy.parts_of_speech.PRON:
                continue
            things.append(nch)
        return things

    def build_words_dict(self):
        """
        Extract main words from the paragraph.
        """
        words_dict = {'times': Counter(),
                      'people': Counter(),
                      'places': Counter(),
                      'things': Counter(),
                      'activities': Counter()}
        for time in self.extract_times():
            words_dict['times'][time] += 1
        for name in self.extract_people():
            words_dict['people'][name] += 1
        for place in self.extract_places():
            # Places are often misidentified as people
            if place in words_dict['people']:
                continue
            words_dict['places'][place] += 1
        for thing in self.extract_things():
            # People are picked up when iterating over noun chunks
            if thing in words_dict['people']:
                continue
            words_dict['things'][thing] += 1
        for verb in self.extract_activities():
            words_dict['activities'][verb] += 1
        return words_dict

    # def sanitize_places_and_objects(self, freq_cut=100):
    #     """
    #     Get a sanitized version of paragraph places and objects.
    #     Get places that don't appear in the most common doc names, and
    #     objects that don't appear in the most common doc places.

    #     NOTE: I'm not really sure what this function is actually doing...

    #     Args:
    #         freq_cut: frequency to define "commonness" within the doc

    #     Returns:
    #         places: sanitized place names
    #         objects: sanitized object names
    #     """
    #     doc_names = dict(self.doc.words['names'].most_common(freq_cut))
    #     doc_places = dict(self.doc.words['places'].most_common(freq_cut))
    #     places = []
    #     objects = []
    #     for place in self.words['places']:
    #         if place not in doc_names:
    #             places.append(place)
    #     for obj in self.words['objects']:
    #         if obj not in doc_places and obj not in places:
    #             objects.append(obj)
    #     return places, objects

    # def gen_mem_activity(self, verbs_cut=500):
    #     """
    #     Determine the key activities in a paragraph by removing
    #     verbs commonly used in the doc

    #     Args:
    #         verbs_cut: frequency of verb in doc to cut on

    #     Returns:
    #         activities: list of key activity strings
    #     """
    #     activities = []
    #     doc_verbs = dict(self.doc.words['verbs'].most_common(verbs_cut))
    #     main_verbs = textacy.spacy_utils.get_main_verbs_of_sent(self.spacy_doc)
    #     for verb in main_verbs:
    #         if (verb.text in doc_verbs) and (doc_verbs[verb.text] < verbs_cut):
    #             span = textacy.spacy_utils.get_span_for_verb_auxiliaries(verb)
    #             complex_verb = self.spacy_doc[span[0]].text
    #             span_end = 1
    #             if textacy.spacy_utils.is_negated_verb(verb) is True:
    #                 complex_verb = complex_verb+' not '
    #                 span_end = 0
    #             for a in range(span[0]+1, span[1]+span_end):
    #                 complex_verb += " "+self.spacy_doc[span[1]].text
    #             subjects = textacy.spacy_utils.get_subjects_of_verb(verb)
    #             objects = textacy.spacy_utils.get_objects_of_verb(verb)
    #             if len(subjects) > 0 and len(objects) > 0:
    #                 for subject in subjects:
    #                     for obj in objects:
    #                         svo = [subject.text, complex_verb, obj.text]
    #                         activities.append(' '.join(svo))
    #     return activities

    def culled_words_dict(self, character):
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
        for name in self.extract_people():
            if name not in character:
                mem_people.append(name)
        mem_places = self.extract_places()
        mem_things = self.extract_things()
        mem_activities = self.extract_activities()
        culled_output = {'people': mem_people,
                         'places': mem_places,
                         'activities': mem_activities,
                         'things': mem_things}
        return culled_output

if __name__ == '__main__':
    book4 = Doc('/Users/samdixon/repos/cdips_data_science/pensieve/hp_corpus/book4.txt')
    from pprint import pprint
    for k, v in book4.words.items():
        pprint({k: v.most_common(10)})
