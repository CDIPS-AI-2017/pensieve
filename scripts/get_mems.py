import argparse
import os

parser = argparse.ArgumentParser(description='Collect memories from a corpus')
parser.add_argument('-c', '--corpus_dir', default='hp_corpus',
                    type=str, help='Path to corpus directory')
parser.add_argument('-n', '--name', default='harry potter',
                    type=str, help='Character name')
parser.add_argument('-m', '--mood_dir', default='mood_files',
                    type=str, help='Path to mood file directory')
parser.add_argument('-i', '--images', action='store_true',
                    help='Get images')
parser.add_argument('-s', '--save_dir', default='memories')

args = parser.parse_args()
print('Extracting memories for {} from text in directory:'.format(args.name))
print(os.path.abspath(args.corpus_dir))
print()
print('Mood files are found in directory:')
print(os.path.abspath(args.mood_dir))
print()
print('Get images is set to '+str(args.images))
print()
print('Memories will be saved to:')
print(os.path.abspath(args.save_dir))
print()

if not os.path.isdir(os.path.abspath(args.save_dir)):
    os.makedirs(os.path.abspath(args.save_dir))

import pensieve
corpus = pensieve.Corpus(corpus_dir=os.path.abspath(args.corpus_dir))
corpus.gather_corpus_memories(char_name=args.name.title().split(),
                              save=os.path.abspath(args.save_dir),
                              get_img=args.images)
