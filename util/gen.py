#!python3
# -*- coding: utf-8 -*-

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


def sourceFileLines(name):
    '''Generator of source-file lines as they should appear in the book.

       If name is a directory (let's call it text_dir), then it contains
       subdirectories with the source files. It returns 
       the (filename, lineno, line) tuple where filename is relative 
       to the text_dir.

       If name is a filename, then the lines of the file are returned.
       In the case, it returns tuples (filename, lineno, line) where 
       filename is the name in the untouched form.
       
       Line numbering is 1-based (human oriented).
    '''

    if os.path.isdir(name):
        # It is a directory. Rename it to reuse the older code.
        text_dir = name

        # Loop through the source files in the order, open them,
        # and yield their lines.
        for fname in sourceFiles(text_dir):
            # Build the relname relative to the text_dir. We know there is one
            # subdir level and then the files inside.
            path, name = os.path.split(fname)
            subdir = os.path.basename(path)
            relname = '/'.join((subdir, name))  # subdir/souce_file.markdown
            with open(fname, encoding='utf-8') as f:
                for lineno, line in enumerate(f, 1):
                    yield relname, lineno, line
            yield relname, 0, '\n'    # to be sure the last line of the previous is separated
    else:
        # It should be a file name.
        assert os.path.isfile(name)
        with open(name, encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                yield name, lineno, line


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
