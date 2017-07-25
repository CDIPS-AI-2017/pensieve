from setuptools import setup, find_packages

setup(name='pensieve',
      version='0.0.1',
      description=u"A Python package to extract character mems from a corpus of text",
      author=u"CDIPS-AI 2017",
      author_email='sam.dixon@berkeley.edu',
      url='https://github.com/CDIPS-AI-2017/pensieve',
      license='Apache 2.0',
      packages=['pensieve',],
      install_requires=[
          'spacy',
          'textacy'
          ]
      )