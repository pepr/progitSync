#!python3
# -*- coding: utf-8 -*-

import doc
import gen
import hashlib
import os


class LangDoc:
    '''Pass1 parser checks for synchronicity of the original sources with the lang sources.

       This parser consumes the `progit/en` and `progit/xx` (where `xx` is
       the target language abbreviation), and reports if there is any difference
       in the structure of the documents.'''

    def __init__(self, lang, root_src_dir, root_aux_dir):
        self.lang = lang    # the language abbrev. like 'cs', 'fr', 'ru', etc.
        self.root_src_dir = os.path.realpath(root_src_dir)
        self.root_aux_dir = os.path.realpath(root_aux_dir)

        # Derive the location of the directory for the language.
        self.src_dir = os.path.join(self.root_src_dir, lang)

        # Derive the auxiliary directory for the language.
        self.aux_dir = os.path.join(self.root_aux_dir, lang + '_aux')

        # Root directory for the language-dependent definition files.
        path, scriptname = os.path.split(__file__)
        self.root_definitions_dir = os.path.abspath(os.path.join(path, 'definitions'))

        # Directory with the language dependent definitions.
        self.lang_definitions_dir = os.path.join(self.root_definitions_dir, self.lang)

        # Create the directories if they does not exist.
        if not os.path.isdir(self.aux_dir):
            os.makedirs(self.aux_dir)

        if not os.path.isdir(self.lang_definitions_dir):
            os.makedirs(self.lang_definitions_dir)

        self.doclines = None  # list of Line objects the language
        self.elements = None  # list of Element objects from the language
        self.sha_to_elem = {} # reverse lookup table

        self.log_info = []       # lines for displaying or logging


    def short_name(self, fname):
        '''Returns tail of the fname -- for log info.'''
        lst = fname.split(os.sep)
        if lst[-2] == self.lang:
            return '/'.join(lst[-3:])
        else:
            return '/'.join(lst[-2:])


    def writePass1txtFiles(self):
        # Copy the language sources into the `single.markdown`.
        # This can be useful when converting the whole book using the PanDoc utility.
        fnameout = os.path.join(self.aux_dir, 'xx_single.markdown')
        with open(fnameout, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.src_dir):
                fout.write(line)

        # Capture the info about the generated file.
        self.log_info.append(self.short_name(fnameout))

        # Copy the language sources with chapter/line info into a single
        # file -- mostly for debugging, not consumed later.
        fnameout = os.path.join(self.aux_dir, 'xx_pass1.txt')
        with open(fnameout, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.src_dir):
                fout.write('{}/{}:\t{}'.format(fname[:2], lineno, line))

        # Capture the info about the generated file for logging.
        self.log_info.append(self.short_name(fnameout))


    def loadDoclineList(self):
        '''Loads document line objects of the source documents to the lists.

           As a side effect, the representations of the lines
           is saved into pass1doclines.txt (mostly for debugging purpose).'''

        # Loop through the lines and build the lists of Line objects
        # from the language sources.
        self.doclines = []
        for relname, lineno, line in gen.sourceFileLines(self.src_dir):
            docline = doc.Line(relname, lineno, line)
            self.doclines.append(docline)

        # Report the language elements.
        xx_doclines_fname = os.path.join(self.aux_dir, 'xx_pass1doclines.txt')
        with open(xx_doclines_fname, 'w', encoding='utf-8') as fout:
            for docline in self.doclines:
                fout.write('{}/{} {}: {!r}\n'.format(
                           docline.fname[:2], docline.lineno,
                           docline.type, docline.attrib))

        # Capture the info about the report file.
        self.log_info.append(self.short_name(xx_doclines_fname))


    def convertDoclinesToElements(self):
        '''Some elements glue more doclines together.

        Fills the list of elements and the reverse table.
        The reverse table uses the element SHA digest as a key,
        and the reference to the element object as the value.'''

        fname = os.path.join(self.aux_dir, 'xx_pass1elements.txt')

        # As some elements contain more doclines, the list
        # must be constructed first and only then it can
        # be written to the fname file.
        self.elements = []       # init -- empty list of elements
        self.sha_to_elem = {}    # init -- empty reverse table
        status = 0          # finite automaton
        for docline in self.doclines:
            if status == 0:     # no expectations
                docelem = doc.Element(docline)  # new one
                self.elements.append(docelem)        # appended
                if docelem.type in ('para', 'uli', 'li'):
                    status = 1
                elif docelem.type == 'code':
                    status = 2
                elif docelem.type == 'empty':
                    status = 3

            elif status == 1:   # accumulate 'text'
                if docline.type == 'text':
                    docelem.append(docline)     # append to the last one
                else:
                    docelem = doc.Element(docline)  # new one
                    self.elements.append(docelem)        # appended
                    if docelem.type in ('para', 'uli', 'li'):
                        status = 1  # i.e. stay here
                    elif docelem.type == 'code':
                        status = 2
                    else:
                        status = 0

            elif status == 2:   # after 'code'
                docelem = doc.Element(docline)  # new one
                self.elements.append(docelem)        # appended
                if docelem.type in ('para', 'uli', 'li'):
                    status = 1
                elif docelem.type == 'code':
                    status = 2      # i.e. stay here
                elif docelem.type == 'empty':
                    status = 3
                else:
                    status = 0

            elif status == 3:   # was 'empty' after 'code'
                # The earlier 'empty' may actually be part
                # of the code snippet.
                docelem = doc.Element(docline)  # new one
                self.elements.append(docelem)        # appended

                # If the element is different than 'empty' or 'code', shrink
                # the previous 'empty' element (if any) to a single one.
                if docelem.type not in ('empty', 'code'):
                    prev = self.elements[-3] # previous to the 'empty'
                    while prev.type == 'empty':
                        # Extend the doclist of the previous by doclines
                        # from the last 'empty' element (not to loose
                        # the source lines representation). Then delete
                        # the absorbed empty element.
                        prev.extend_lines_from(self.elements[-2])
                        del self.elements[-2]

                        # There may be more 'empty' elements because
                        # we did not know they are not part of
                        # the code snippet.
                        prev = self.elements[-3]

                # Now decide the next status based on the last
                # element type.
                if docelem.type == 'code':
                    status = 2
                elif docelem.type == 'empty':
                    status = 3  # i.e. stay here
                elif docelem.type in ('para', 'uli', 'li'):
                    status = 1
                else:
                    status = 0

            elif status == 4:   # after 'empty'
                # The earlier 'empty' is not part of the code snippet.
                # Do not append the element if it is 'empty' again.
                # Absorb the lines instead.
                docelem = doc.Element(docline)  # new one
                if docelem.type == 'empty':
                    self.elements[-1].extend_lines_from(docelem) # absorbed
                else:
                    self.elements.append(docelem)    # appended

                # Now decide the next status based on the last
                # appended element type.
                e = self.elements[-1]
                if e.type == 'code':
                    status = 2
                elif e.type == 'empty':
                    status = 4  # i.e. stay here
                elif e.type in ('para', 'uli', 'li'):
                    status = 1
                else:
                    status = 0

            else:
                raise NotImplementedError('status = {}'.format(status))

        # Add sha to the elements, fill the reverse lookup table,
        # and report their content.
        with open(fname, 'w', encoding='utf-8') as f:
            for e in self.elements:
                # Calculate the SHA-1 for the original line(s)
                # encoded in UTF-8 (including newlines, no rstrips).
                e.sha = hashlib.sha1(e.value(False).encode('utf-8')).hexdigest()

                # Insert the record to the reverse lookup table.
                # There may be repeated items: empty elements are
                # all the same elsewhere, the code elements, may
                # often repeat as the same lines may appear easily
                # in more snippets, the titles like "Summary" also
                # repeat. Ignore the cases. The last known repeated
                # element with the same value will be captured
                # in the reverse lookup table.
                self.sha_to_elem[e.sha] = e

                # Report the content of the element.
                f.write('{}/{} {} {}: {!r}\n'.format(
                        e.fname[:2], e.lineno(),
                        e.sha[:6], e.type, e.value()))
        self.log_info.append(self.short_name(fname))


    def run(self):
        '''Launcher of the phases.'''

        self.writePass1txtFiles()
        self.loadDoclineList()
        self.convertDoclinesToElements()

        return '\n\t'.join(self.log_info)
