# *******************************************************************************
# **
# **  Author: Michael Lomnitz (mrlomnitz@lbl.gov)                               
# **  Python module defining embeddigns (word2vec) model using skipgram or 
# **  continuous bag or words to define word context. 
# **
# *******************************************************************************
# Modules
from __future__ import print_function
import math
import numpy as np
import random
import tensorflow as tf
import collections
from matplotlib import pylab
from six.moves import range
from itertools import compress

# Some model constants
data_index = 0
embedding_size = 128 # Dimension of the embedding vector.
num_sampled = 64 # Number of negative examples to sample.

# Generate the batch and associated labels for training in skipgram
def generate_batch(batch_size, num_skips, skip_window, data):
    global data_index
    assert batch_size % num_skips == 0
    assert num_skips <= 2 * skip_window
    batch = np.ndarray(shape=(batch_size), dtype=np.int32)
    labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
    span = 2 * skip_window + 1 # [ skip_window target skip_window ]
    buffer = collections.deque(maxlen=span)
    for _ in range(span):
        buffer.append(data[data_index])
        data_index = (data_index + 1) % len(data)
    for i in range(batch_size // num_skips):
        target = skip_window  # target label at the center of the buffer
        targets_to_avoid = [ skip_window ]
        for j in range(num_skips):
            while target in targets_to_avoid:
                target = random.randint(0, span - 1)
            targets_to_avoid.append(target)
            batch[i * num_skips + j] = buffer[skip_window]
            labels[i * num_skips + j, 0] = buffer[target]
        buffer.append(data[data_index])
        data_index = (data_index + 1) % len(data)
    return batch, labels

# Generate training batch for use in continuous bag of words model
def generate_batch_CBOW(batch_size, num_skips, skip_window, data):
    global data_index
    assert batch_size % num_skips == 0
    assert num_skips <= 2 * skip_window
    batch = np.ndarray(shape=(batch_size,num_skips), dtype=np.int32)
    labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
    span = 2 * skip_window + 1 # [ skip_window target skip_window ]
    buffer = collections.deque(maxlen=span)
    for _ in range(span): #coillecting first window of words
        buffer.append(data[data_index])
        data_index = (data_index + 1) % len(data)
    for i in range(batch_size):
        mask = [1]*span
        mask[skip_window] = 0
        batch[i,:] = list(compress(buffer,mask))
        labels[i,0] = buffer[skip_window]
        buffer.append(data[data_index])
        data_index = (data_index + 1) % len(data)

    return batch, labels

# Defione embeddings object
class word_embedding(object):
    def __init__(self, vocabulary_size, isCBOW = False):
        # Initialize variables.
        self.isCBOW = isCBOW
        self.vocabulary_size = vocabulary_size
        #
        self.embeddings = tf.Variable(
            tf.random_uniform([vocabulary_size, embedding_size], -1.0, 1.0))
        self.softmax_weights = tf.Variable(
            tf.truncated_normal([vocabulary_size, embedding_size],
                         stddev=1.0 / math.sqrt(embedding_size)))
        self.softmax_biases = tf.Variable(tf.zeros([vocabulary_size]))
        print('Initialized embeddings') 

    def train( self , train_dataset, train_labels, batch_size = 128, num_skips = 2):
        # Define models 
        if self.isCBOW == False:
            embed = tf.nn.embedding_lookup(self.embeddings, train_dataset)
        else:
            print(self.embeddings.shape)
            embed = tf.zeros([batch_size, embedding_size])
            for j in range(num_skips):
                embed+=tf.nn.embedding_lookup(self.embeddings, train_dataset[:, j])
        loss = tf.reduce_mean(
            tf.nn.sampled_softmax_loss(weights=self.softmax_weights, biases=self.softmax_biases, inputs=embed,
                                       labels=train_labels, num_sampled=num_sampled, num_classes=self.vocabulary_size))
        # Optimizer.
        # Note: The optimizer will optimize the softmax_weights AND the embeddings.
        # This is because the embeddings are defined as a variable quantity and the
        # optimizer's `minimize` method will by default modify all variable quantities 
        # that contribute to the tensor it is passed.
        # See docs on `tf.train.Optimizer.minimize()` for more details.
        optimizer = tf.train.AdagradOptimizer(1.0).minimize(loss)
        
        # Compute the similarity between minibatch examples and all embeddings.
        # We use the cosine distance:
        norm = tf.sqrt(tf.reduce_sum(tf.square(self.embeddings), 1, keep_dims=True))
        self.normalized_embeddings = self.embeddings / norm
        return optimizer, loss

    # Equivalent of prediction in other ML and DL procedures. Finds closest words given a validation
    # dataset
    def similarity(self, valid_dataset):
        valid_embeddings = tf.nn.embedding_lookup(
            self.normalized_embeddings, valid_dataset)
        sim = tf.matmul(valid_embeddings, tf.transpose(self.normalized_embeddings))
        return sim.eval()


