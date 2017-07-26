# *******************************************************************************
# **
# **  Author: Michael Lomnitz (mrlomnitz@lbl.gov)                               
# **  Python module to run word embedding (word2vec) using skipgram or continuos
# **  bag of words (CBOW) models. Output is then plotted using SKlearn tSNE 
# **  for visualization.
# **
# *******************************************************************************
# Load modules
import tensorflow as tf
import numpy as np
import random
from matplotlib import pylab
from sklearn.manifold import TSNE
# Local modules
import Load_Text_Set as ld
import tf_Word2Vec as w2v
# plotting amcro
def plot(embeddings, labels, name):
    assert embeddings.shape[0] >= len(labels), 'More labels than embeddings'
    fig = pylab.figure(figsize=(15,15))  # in inches
    for i, label in enumerate(labels):
        x, y = embeddings[i,:]
        pylab.scatter(x, y)
        pylab.annotate(label, xy=(x, y), xytext=(5, 2), textcoords='offset points',
                   ha='right', va='bottom')
        #pylab.show()
    fig.savefig('./'+name+'.pdf')

# Model constants 
batch_size = 128 # Training batch. Reduces overtraining and training time
skip_window = 1 # How many words to consider left and right.
num_skips = 2 # How many times to reuse an input to generate a label.
# Cosmntruct random validation sample from the loaded dataset. Limit ourselves
# to a sample of words that have a low numeric ID, which by (i.e. frequent)
valid_size = 16 # Random set of words to evaluate similarity on.
valid_window = 100 # Only pick dev samples in the head of the distribution.
valid_examples = np.array(random.sample(range(valid_window), valid_size))
vocabulary_size = 200000
# Switch betweenskipgram and CBOW models
use_CBOW = True
#
graph = tf.Graph()
words = ld.text_8(vocabulary_size)
#
def run_embeddings():
    with graph.as_default(), tf.device('/cpu:0'):
        # Input data.
        if use_CBOW == False:
            train_dataset = tf.placeholder(tf.int32, shape=[batch_size])
        else: 
            train_dataset = tf.placeholder(tf.int32, shape=[batch_size,num_skips])
        train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
        valid_dataset = tf.constant(valid_examples, dtype=tf.int32)
    #
        embeddings = w2v.word_embedding(vocabulary_size, use_CBOW)
        optimizer,loss = embeddings.train(train_dataset, train_labels)
    
        num_steps = 100001

    with tf.Session(graph=graph) as session:
        tf.global_variables_initializer().run()
        print('Initialized')
        average_loss = 0
        for step in range(num_steps):
            if use_CBOW == False:
                batch_data, batch_labels = w2v.generate_batch(
                    batch_size, num_skips, skip_window, words.data)
            else:
                batch_data, batch_labels = w2v.generate_batch_CBOW(
                    batch_size, num_skips, skip_window, words.data)
        #
            feed_dict = {train_dataset : batch_data, train_labels : batch_labels}
            _, l = session.run([optimizer, loss], feed_dict=feed_dict)
            average_loss += l
        # The followign are just to keep track of the training and the performance
            if step % 2000 == 0:
                if step > 0:
                    average_loss = average_loss / 2000
                # The average loss is an estimate of the loss over the last 2000 batches.
                print('Average loss at step %d: %f' % (step, average_loss))
                average_loss = 0
        # note that this is expensive (~20% slowdown if computed every 500 steps)
            if step % 10000 == 0:
            #sim = similarity.eval()
                sim = embeddings.similarity(valid_dataset)
                for i in range(valid_size):
                    valid_word = words.reverse_dictionary[valid_examples[i]]
                    top_k = 8 # number of nearest neighbors
                    nearest = (-sim[i, :]).argsort()[1:top_k+1]
                    log = 'Nearest to %s:' % valid_word
                    for k in range(top_k):
                        close_word = words.reverse_dictionary[nearest[k]]
                        log = '%s %s,' % (log, close_word)
                    print(log)
        final_embeddings = embeddings.normalized_embeddings.eval()
        return(final_embeddings)
# plot output results
