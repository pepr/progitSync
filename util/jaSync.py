#!python3
# -*- coding: utf-8 -*-

'''Script to help manual synchronization of the translation with the original.'''

import pass1
import pass2


# You should have the fresh sources of the original and of the translation.
#
# The first pass collects information from both original and the translation
# and checks for the sameness of the structure. The elements of the docs
# headings, paragraphs, images, code snippets) should appear synchronously.
# Some elements are required only to exist (headings, paragraphs, list items),
# some elements should have the exactly same content (code snippets, image
# identifiers).
#
# Set the language identifier as the first argument, path to the root of
# the source documents (absolutely or relatively to this script), and
# path to the root of the auxiliary directories -- they will contain the reports.
print('pass 1:')
parser1 = pass1.Parser('ja', '../../progit/', '../')
msg = parser1.run()
print('\t' + msg)

# The second path consumes the result of the first one. It assumes the
# structure is already synchronized; otherwise, ignore the reports until
# it IS synchronized.
print('pass 2:')
parser2 = pass2.Parser(parser1)
msg = parser2.run()
print('\t' + msg)
