# *******************************************************************************
# **
# **  Author: Michael Lomnitz (mrlomnitz@lbl.gov)                               
# **  Python module used to download and load text8 dataset for embedding module
# **  un Udacity course
# **
# *******************************************************************************
import os
import zipfile
import collections
import tensorflow as tf
from urllib.request import urlretrieve

url = 'http://mattmahoney.net/dc/'
expected_bits = 31344016

# Read data from a downloaded .zip
def read_data(file):
    with zipfile.ZipFile(file) as f:
        data = tf.compat.as_str(f.read(f.namelist()[0])).split()
    return data

# Data object
class text_8(object):
    def __init__(self,  vocabulary = 200000):
        filename  = 'text8.zip'
        # Init the data set, if file is absent download it
        if not os.path.exists(filename):
            print('File is missing, retrieving ', url+filename)
            filename, _ = urlretrieve(url+filename,filename)
        # Verify that datasert was correctly loaded by checking bits.
        if os.stat(filename).st_size != expected_bits:
            print('Cannot load & verify. Please sort this out')
            return
        print('Found and verified %s ' % filename)
        words = read_data(filename)
        print('Words in file ', len(words))
        self.data, self.count, self.dictionary, self.reverse_dictionary = self.build_dataset(words, vocabulary)
    # Build dictionary of most common words from the loaded word set. This is done to speed up and reduce memory usage.
    def build_dataset(self, words, vocabulary):
        count = [['UNK', -1]]
        count.extend(collections.Counter(words).most_common(vocabulary - 1))
        dictionary = dict()
        for word, _ in count:
            dictionary[word] = len(dictionary)
        data = list()
        unk_count = 0
        for word in words:
            if word in dictionary:
                index = dictionary[word]
            else:
                index = 0  # dictionary['UNK']
                unk_count = unk_count + 1
            data.append(index)
        count[0][1] = unk_count
        reverse_dictionary = dict(zip(dictionary.values(), dictionary.keys())) 
        return data, count, dictionary, reverse_dictionary

    
