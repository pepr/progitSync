#!python3
# -*- coding: utf-8 -*-

import re
'''Capturing one line of a document and converting it to an object.'''


class Line:
    '''One Line object is constructed from one markdown source line.'''

    # The following regular expressions are used for recognition
    # of the used markdown-syntax lines.

    # Title like ### Title ###.
    rexTitle = re.compile(r'^(?P<level>#+)\s+(?P<title>.+?)\s+\1\s*$')

    # Unnumbered list item.
    rexBullet = re.compile(r'^\*\s+(?P<uli>.+?)\s*$')

    # Image insertion (includes the filename).
    rexInsImg = re.compile(r'^Insert\s+(?P<img>\d+fig\d+\.png)\s*$')

    # Image caption.
    rexImgCaption = re.compile(r'^(Fig(ure)?|Obrázek)\.\s+(?P<num>\d+.+\d+).?\s+(?P<text>.+?)\s*$')

    # One code-snippet line.
    rexCode = re.compile(r'^( {4}|\t)(?P<code>.+?)\s*$')

    # Numbered list item.
    rexLi = re.compile(r'^(?P<num>\d+\.)\t(?P<text>.+?)\s*$')

    def __init__(self, fname, lineno, line):
        self.fname = fname      # the source file name
        self.lineno = lineno    # line number in the source file
        self.line = line        # the line from the source file

        self.type = None        # line type
        self.attrib = None      # init -- line attributes (the type dependent)

        # The line that contains only whitespaces is considered empty (separator).
        if self.line.isspace():
            self.type = 'empty'
            self.attrib = ''   # represented as empty string
            return

        # Line with the title.
        m = self.rexTitle.match(line)
        if m:
            self.type = 'title'
            self.attrib = (len(m.group('level')), m.group('title'))
            return

        # Unnumbered list item.
        m = self.rexBullet.match(line)
        if m:
            self.type = 'uli'
            self.attrib = m.group('uli')
            return

        # Numbered list item.
        m = self.rexLi.match(line)
        if m:
            self.type = 'li'
            self.attrib = (m.group('num'), m.group('text'))
            return

        # Image insertion.
        m = self.rexInsImg.match(line)
        if m:
            self.type = 'img'
            self.attrib = m.group('img')
            return

        # Image caption.
        m = self.rexImgCaption.match(line)
        if m:
            self.type = 'imgcaption'
            self.attrib = (m.group('num'), m.group('text'))
            return

        # Code-snippet line.
        m = self.rexCode.match(line)
        if m:
            self.type = 'code'
            self.attrib = m.group('code')
            return

        # The empty line should not happen, but it means that
        # there the content in the file was exhausted.
        # From the solved-problem point of view it is not a separator.
        if self.line == '':
            self.type = 'EOF'
            self.attrib = None
            return

        # The other cases are considered text lines.
        self.type = 'text'
        self.attrib = line.rstrip()


    def __repr__(self):
        return repr((self.fname, self.lineno, self.type, self.attrib))


    def __str__(self):
        return self.line


class Element:
    '''One Element object is constructed from one document lines.

    Implementation note: The earlier Element implementation was earlier
    what the Lines class is now. The Element was abstracted further to
    make the content less formatting-dependent. The main reason was that
    the translated paragraphs were often split to more physical lines
    than in the original. (The original typically contains paragraphs
    as one very long line.'''

    def __init__(self, docline):
        self.fname = docline.fname  # the source file name
        self.no = docline.lineno    # abstract element number
        self.doclines = [docline]   # list of lines object
        self.type = docline.type    # element type
        self.attrib = docline.attrib # init -- element attributes (the type dependent)

        # Initial implementation just wraps the doc.Line objects
        # as one-line lists. Then it corrects the 'text' type to 'para'.
        if self.type == 'text':
            self.type = 'para'


    def __repr__(self):
        return repr((self.fname, self.no, self.type,
                     self.attrib, self.doclines))


    def __str__(self):
        return ''.join.self.lines
