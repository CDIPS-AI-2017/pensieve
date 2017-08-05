from __future__ import unicode_literals
import spacy
import os
import textacy
import string
from .json_dump import dump_mem_to_json
from .find_images import search_bing_for_image, search_np_for_image
import json
from tqdm import tqdm
from collections import Counter
from collections import defaultdict
import pandas
import numpy

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
        for file_path in file_paths:
            i = int( file_path[-5:-4] ) -1
            print('Loading '+file_path, 'Book id ',i)
            docs.append(Doc(file_path, i, self))
        return docs

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
        for doc in self.docs:
            char_pars += doc.find_character_paragraphs(char_name,
                                                       density_cut)
        return char_pars

    def gather_corpus_memories(self, char_name, density_cut=0.8,
                               n_verbs=3, save=None, get_img=False):
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
            get_img: get an image url (set to False by default to avoid
                     using up all the API calls)

        Returns:
            memories: list of memories, ready to be put in DB
        """
        memories = []
        char_pars = self.find_character_paragraphs(char_name, density_cut)
        for par in char_pars:
            mem_dict = par.gen_mem_dict(char_name, n_verbs, get_img=get_img)            
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
        # Hardcoded path to book_emo.h5 file. Method to generate this file needs to be implemented
        # in extract_mood_words
        self.mood_weights = pandas.read_hdf('C:/Users/jingjing/Desktop/cdips-ai/pensieve/pensieve/book_emo.h5',key='book'+str(self.id+1))


    @property
    def paragraphs(self):
        if not self._paragraphs:
            print('Generating paragraphs for doc '+str(self.id))
            self._paragraphs = []
            line_list = self.text.split('\n')
            myIterator = iter(enumerate(line_list))
            tuple = next(myIterator, None)
            j = 0
            while tuple is not None:
                i, line = tuple
                if len(line.strip()) == 0:
                    pass
                elif len(line.split(' ')) >= 25:
                    self._paragraphs.append(Paragraph(line, j, self))
                    j += 1
                else:
                    chunk = ""
                    while (tuple is not None) and (len(line.split(' ')) < 25 or line[0] == "'" or line[0] == '"'):
                        chunk = chunk + "\n" + line
                        tuple = next(myIterator, None)
                        if tuple is not None:
                            i, line = tuple
                    self._paragraphs.append(Paragraph(chunk, j, self))
                    j += 1
                    continue
                tuple = next(myIterator, None)
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
            for key in self.words['people']:
                # people are not places
                if (2.5)*(self.words['people'][key]) > self.words['places'][key]:
                    del self.words['places'][key]
                # people are not things
                if self.words['people'][key] > 5:
                    del self.words['things'][key]
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
                            n_verbs=3, save=None, get_img=False):
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
            get_img: get an image url (set to False by default to avoid
                     using up all the API calls)

        Returns:
            memories: list of sanitized memories, ready to be put in DB
        """
        memories = []
        char_pars = self.find_character_paragraphs(char_name, density_cut)
        for par in tqdm(char_pars):
            mem_dict = par.gen_mem_dict(char_name, n_verbs, get_img=get_img)
            memories.append(dump_mem_to_json(mem_dict))
        if save is not None:
            if isinstance(char_name, str):
                filebase = char_name.replace(' ', '_').lower().strip()
            else:
                filebase = '_'.join(char_name)+'_book'+str(self.id)
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
        
        Returns: List of strings representing times
        """
        times = []
        include_types = ['DATE', 'TIME', 'EVENT']
        for time in textacy.extract.named_entities(self.spacy_doc,
                                                   include_types=include_types):
            times.append(time.text)
        times.append('Book '+str(self.doc.id))
        times.append('Par. '+str(self.id))
        return times

    def extract_activities(self, n_verbs = 5):
        """
        Extract verbs in the paragraph
        
        Returns: List of strings representing verbs
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
        
        Returns: List of strings representing people
        """
        names = []
        for name in textacy.extract.named_entities(self.spacy_doc,
                                                   include_types=['PERSON']):
            # Exclude words too short to be names and strange characters
            if len(name.text) < 3:
                continue
            # objects should not be people
            if (name.doc[name.start - 1].text == 'the') or (name.doc[name.start - 1].text == 'a') or (name.doc[name.start - 1].text == 'an'):
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
        
        Returns: List of strings representing places
        """
        places = []
        include_types = ['LOC', 'GPE', 'FACILITY']
        for place in textacy.extract.named_entities(self.spacy_doc,
                                                include_types=include_types):
            places.append(place.text)
        return places

    def extract_things(self):
        """
        Extract things mentioned in paragraph
        
        Returns: List of strings representing things
        """
        # Get named objects
        include_types = ['ORG', 'NORP', 'WORK_OF_ART', 'PRODUCT']
        things = []
        for obj in textacy.extract.named_entities(self.spacy_doc,
                                                  include_types=include_types):
            things.append(obj.text.strip())
        # Get noun chunks
        for nch in textacy.extract.noun_chunks(self.spacy_doc, drop_determiners=True):
            if len(nch) == 1 and nch[0].pos == spacy.parts_of_speech.PRON:
                continue
            things.append(nch.text.strip())
        return things

    def extract_mood_words(self):
        """
        Extract the mood/emotion of the paragraph using EMO-Lexicon
        """
        pass

    def extract_mood_weights(self):
        """
        Extract normalized paragraph mood weights from h5 file
        """
        para_emotions = self.doc.mood_weights.iloc[self.id]
        norm = numpy.sum( para_emotions )
        if norm == 0:
            return para_emotions
        else:
            return dict(para_emotions/norm)

    def extract_img_url(self):
        """
        Use the keyterms from the text to get a relevant image.
        The decisions behind this function can be found in the
        image_search_query notebook
        """
        keyterms = textacy.keyterms.textrank(self.spacy_doc)
        best_keyterm = None
        for keyterm, rank in keyterms:
            if keyterm.title() not in self.doc.words['people']:
                best_keyterm = keyterm
                break
        try:
            urls = search_np_for_image(best_keyterm)
        except Exception as e:
            urls = search_bing_for_image(best_keyterm)
        img_url = urls[0]
        return img_url

    def build_words_dict(self):
        """
        Extract main words from the paragraph.
        """
        words_dict = {'times': Counter(),
                      'people': Counter(),
                      'places': Counter(),
                      'things': Counter(),
                      'activities': Counter(),
                      'mood_weight': defaultdict()}

        for time in self.extract_times():
            time = time.strip()
            words_dict['times'][time] += 1
        for name in self.extract_people():
            name = name.strip()
            words_dict['people'][name] += 1
        for place in self.extract_places():
            place = place.strip()
            # Places are often misidentified as people
            if place in words_dict['people']:
                continue
            words_dict['places'][place] += 1
        for thing in self.extract_things():
            thing = thing.strip()
            # People are picked up when iterating over noun chunks
            if thing in words_dict['people']:
                continue
            words_dict['things'][thing] += 1
        for verb in self.extract_activities():
            verb = verb.strip()
            words_dict['activities'][verb] += 1
        words_dict['mood_weight'].update(self.extract_mood_weights()) 
        words_dict['mood_weight']['overall_weight'] = 0.5 #this implementantion is still pending
        return words_dict

    def gen_mem_dict(self, character, n_verbs, get_img=False):
        """
        Determine the most important words of those collected.

        Args:
            character: character name string or list of aliases
            verb_cut: frequency of verb in doc to cut on
            name_cut: frequency of name in doc to cut on
            get_img: get an image url (set to False by default to avoid
                     using up all the API calls)

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
        mem_activities = self.extract_activities(n_verbs)
        mem_weights = defaultdict()
        mem_weights.update( self.extract_mood_weights() )
        mem_weights.update({'overall_weight': 0.5}) #still needs to be implemented
        if get_img:
            mem_img_url = self.extract_img_url()
        else:
            mem_img_url = None
        culled_output = {'people': mem_people,
                         'places': mem_places,
                         'activities': mem_activities,
                         'things': mem_things,
                         'mood_weight':mem_weights,
                         'img_url': mem_img_url,
                         'narrative': self.text}
        return culled_output

if __name__ == '__main__':
    book4 = Doc('/Users/samdixon/repos/cdips_data_science/pensieve/hp_corpus/book4.txt', doc_id=4)
    print(book4.gather_doc_memories(['Harry', 'Potter'], save='./'))
