#!python3
'''Generators for gluing the source files into a stream of lines...
'''

import os
import re


def sourceFiles(text_dir):
    '''Generator of source-file names yielded in the sorted order.'''

    # Check the existence of the directory.
    assert os.path.isdir(text_dir)

    # Get the list of subdirectories with the source files.
    subdirs = []
    for sub in sorted(os.listdir(text_dir)):
        d = os.path.join(text_dir, sub)
        if os.path.isdir(d):
            subdirs.append(d)

    # Loop through subdirs and walk the sorted filenames.
    for sub in subdirs:
        for name in sorted(os.listdir(sub)):
            fname = os.path.join(sub, name)
            if os.path.isfile(fname):
                yield fname


def sourceFileLines(text_dir):
    '''Generator of source-file lines as they should appear in the book.

       It returns the (filename, line) tuple where filename is relative
       to the text_dir.
    '''

    # Loop through the source files in the order, open them,
    # and yield their lines.
    for fname in sourceFiles(text_dir):
        # Build the relname relative to the text_dir. We know there is one
        # subdir level and then the files inside.
        path, name = os.path.split(fname)
        subdir = os.path.basename(path)
        relname = '/'.join((subdir, name))  # subdir/souce_file.markdown
        with open(fname, encoding='utf-8') as f:
            for line in f:
                yield relname, line
        yield None, '\n'    # to be sure the last line of the previous is separated


def toc(text_dir, max_level=4):
    '''Generator that yields symbolic TOC items.

       The generator loops through the source lines and detect the lines
       that start and end with ## sequences. It yields tuples like
       ('rel_to_text_dir/filename', '###', 'title').

       The max_level equal to 3 means that only #, ##, and ### will be
       yielded. The #### will not be yielded.
    '''
    rex = re.compile(r'^(?P<num>#+)\s*(?P<title>.+?)(\s+(?P=num))?\s*$')
    for relname, line in sourceFileLines(text_dir):
        m = rex.match(line)
        if m:
            num = m.group('num')
            level = len(num)
            if level <= max_level:
                yield relname, num, m.group('title')
