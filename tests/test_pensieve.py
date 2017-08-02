"""Test jsonschema use with API calls.
# python -m pytest tests/test_pensieve.py
"""
import os
import pytest
import pensieve



@pytest.fixture
def corpus_dir():
    cwd = os.getcwd()
    return os.path.join(cwd, 'tests', 'test_data')


def test_corpus(corpus_dir):
    print('testing', corpus_dir)
    corpus = pensieve.Corpus(corpus_dir)
    print(corpus.docs[0].text)
    print(corpus.paragraphs)
    assert 3 == len(corpus.paragraphs)

