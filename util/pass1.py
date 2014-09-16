#!python3
# -*- coding: utf-8 -*-

import doc
import gen
import hashlib
import os


class Parser:
    '''Pass1 parser checks for synchronicity of the original sources with the lang sources.

       This parser consumes the `progit/en` and `progit/xx` (where `xx` is
       the target language abbreviation), and reports if there is any difference
       in the structure of the documents.'''

    def __init__(self, lang, root_src_dir, root_aux_dir):
        self.lang = lang    # the language abbrev. like 'cs', 'fr', 'ru', etc.
        self.root_src_dir = os.path.realpath(root_src_dir)
        self.root_aux_dir = os.path.realpath(root_aux_dir)

        # Location of the root directory with the English original.
        self.en_src_dir = os.path.join(self.root_src_dir, 'en')

        # Derive the location of the directory for the target language.
        self.xx_src_dir = os.path.join(self.root_src_dir, lang)

        # Location of the root for the generated files for English.
        self.en_aux_dir = os.path.join(self.root_aux_dir, 'en_aux')

        # Derive the auxiliary directory for the target language.
        self.xx_aux_dir = os.path.join(self.root_aux_dir, lang + '_aux')

        # Root directory for the language-dependent definition files.
        path, scriptname = os.path.split(__file__)
        self.root_definitions_dir = os.path.abspath(os.path.join(path, 'definitions'))

        # Directory with the language dependent definitions.
        self.lang_definitions_dir = os.path.join(self.root_definitions_dir, self.lang)

        # Create the directories if they does not exist.
        if not os.path.isdir(self.en_aux_dir):
            os.makedirs(self.en_aux_dir)

        if not os.path.isdir(self.xx_aux_dir):
            os.makedirs(self.xx_aux_dir)

        if not os.path.isdir(self.lang_definitions_dir):
            os.makedirs(self.lang_definitions_dir)


        self.en_doclines = None  # list of Line objects from the English original
        self.xx_doclines = None  # ... and from the target language

        self.en_elements = None  # list of Element objects from English
        self.xx_elements = None  # ... and from the target language

        self.en_sha_to_elem = {} # reverse lookup table
        self.xx_sha_to_elem = {} # reverse lookup table

        self.log_info = []       # lines for displaying or logging


    def short_name(self, fname):
        '''Returns tail of the fname -- for log info.'''
        lst = fname.split(os.sep)
        if lst[-2] == self.lang:
            return '/'.join(lst[-3:])
        else:
            return '/'.join(lst[-2:])


    def writePass1txtFiles(self):
        # Copy the target language sources into the `single.markdown`.
        # This can be useful when converting the whole book using the PanDoc utility.
        fnameout = os.path.join(self.xx_aux_dir, 'single.markdown')
        with open(fnameout, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
                fout.write(line)

        # Capture the info about the generated file.
        self.log_info.append(self.short_name(fnameout))

        # Copy the target language sources with chapter/line info into a single
        # file -- mostly for debugging, not consumed later.
        fnameout = os.path.join(self.xx_aux_dir, 'pass1.txt')
        with open(fnameout, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
                fout.write('{}/{}:\t{}'.format(fname[:2], lineno, line))

        # Capture the info about the generated file for logging.
        self.log_info.append(self.short_name(fnameout))

        # Do the same with the English original -- the `single.markdown`.
        # This can be useful when converting the whole book using the PanDoc utility.
        fnameout = os.path.join(self.en_aux_dir, 'single.markdown')
        with open(fnameout, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_src_dir):
                fout.write(line)
        self.log_info.append(self.short_name(fnameout))

        # ... and `pass1.txt` with chapter/line info.
        fnameout = os.path.join(self.en_aux_dir, 'pass1.txt')
        with open(fnameout, 'w', encoding='utf-8') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_src_dir):
                fout.write('{}/{}:\t{}'.format(fname[:2], lineno, line))
        self.log_info.append(self.short_name(fnameout))


    def loadDoclineLists(self):
        '''Loads document line objects of the source documents to the lists.

           As a side effect, the representations of the lines
           is saved into pass1doclines.txt (mostly for debugging purpose).'''

        # The target-language sources may contain some extra parts used
        # as translator notes or some other explanations of the English
        # original. When compared with the original, the parts must be
        # skipped. The `definitions/xx/extra_lines.txt` stores the definitions
        # of the skipped parts in the form that can be cut/pasted from
        # other logs (UTF-8). If the extra_lines.txt file does not exist,
        # the empty one is created.
        #
        # The definitions are loaded to the dictionary where the key
        # is the first line of the extra sequence, and the value is
        # the list of lines of the sequence.
        #
        # Note: If it happens and there are two or more sequences
        # with the same line (say some title of the included sequence),
        # just split the extra sequences to one extra sequence for
        # the first line, and the two or more sequences of the rest lines
        # (without that first line).
        extras_fname = os.path.join(self.lang_definitions_dir,
                                    'extra_lines.txt')

        # Create the empty file if it does not exist.
        if not os.path.isfile(extras_fname):
            f = open(extras_fname, 'w')
            f.close()

        # Load the content to the `extras` dictionary.
        extras = {}
        status = 0
        lst = None
        with open(extras_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # First line is the key, the list is the value.
                    lst = extras.setdefault(line, [])
                    assert len(lst) == 0    # duplicity raises the exception
                    lst.append(line)        # first line repeated in the list
                    status = 1

                elif status == 1:
                    # The sequence until the separator.
                    if line.startswith('====='):    # 5 at minimum
                        lst = None
                        status = 0
                    else:
                        lst.append(line)    # next of the sequence

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Capture the info about the input file with the definitions.
        self.log_info.append(self.short_name(extras_fname))

        # Loop through the lines and build the lists of Line objects
        # from the original and from the translation. The extra sequences
        # from the target languages are reported and skipped. They will be
        # deleted from the list.
        self.xx_doclines = []
        for relname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
            docline = doc.Line(relname, lineno, line)
            self.xx_doclines.append(docline)

        # Delete and report the extra lines.
        xx_extra_fname = os.path.join(self.xx_aux_dir, 'pass1extra_lines.txt')
        with open(xx_extra_fname, 'w', encoding='utf-8') as fout:
            index = 0                       # index the processed element
            while index < len(self.xx_doclines): # do not optimize, the length can change
                docline = self.xx_doclines[index]# current element
                if docline.line in extras:  # is current line recognized as extra?
                    # I could be the extra sequence. Compare the other lines
                    # in the length of the sequence. Firstly, extract the following
                    # lines in the length of the extras list.
                    extra_lines = extras[docline.line]
                    src_lines = [e.line for e in self.xx_doclines[index:index+len(extra_lines)]]

                    # If the list have the same content, delete the source elements.
                    if src_lines == extra_lines:
                        # Report the skipped lines.
                        fout.write('{}/{}:\n'.format(docline.fname, docline.lineno))
                        fout.write(''.join(src_lines))
                        fout.write('====================\n\n')

                        # Delete the lines via deleting their elements.
                        del self.xx_doclines[index:index+len(extra_lines)]

                        # Decrement the index -- i.e. correction as
                        # it will be incremented later.
                        index -= 1

                # Jump to the next checked element.
                index += 1

        # Capture the info about the report file.
        self.log_info.append(self.short_name(xx_extra_fname))

        # Report the remaining target-language elements.
        xx_doclines_fname = os.path.join(self.xx_aux_dir, 'pass1doclines.txt')
        with open(xx_doclines_fname, 'w', encoding='utf-8') as fout:
            for docline in self.xx_doclines:
                fout.write('{}/{} {}: {!r}\n'.format(
                           docline.fname[:2], docline.lineno,
                           docline.type, docline.attrib))

        # Capture the info about the report file.
        self.log_info.append(self.short_name(xx_doclines_fname))

        # Report the structure of the English original.
        self.en_doclines = []
        en_doclines_fname = os.path.join(self.en_aux_dir, 'pass1doclines.txt')
        with open(en_doclines_fname, 'w', encoding='utf-8') as fout:
            for relname, lineno, line in gen.sourceFileLines(self.en_src_dir):
                docline = doc.Line(relname, lineno, line)
                self.en_doclines.append(docline)
                fout.write('{}/{} {}: {!r}\n'.format(
                           docline.fname[:2], docline.lineno,
                           docline.type, docline.attrib))

        # Capture the info about the report file.
        self.log_info.append(self.short_name(en_doclines_fname))


    def convertDoclinesToElements(self):
        '''Some elements glue more doclines together.'''

        def aux_convert(self, aux_dir, doclines):
            '''Returns the list of elements and the reverse table.

            The reverse table uses the element SHA digest as a key,
            and the reference to the element object as the value.
            The core used for both English and the target language.'''

            fname = os.path.join(aux_dir, 'pass1elements.txt')

            # As some elements contain more doclines, the list
            # must be constructed first and only then it can
            # be written to the fname file.
            elements = []       # init -- empty list of elements
            sha_to_elem = {}    # init -- empty reverse table
            status = 0          # finite automaton
            for docline in doclines:
                if status == 0:     # no expectations
                    docelem = doc.Element(docline)  # new one
                    elements.append(docelem)        # appended
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
                        elements.append(docelem)        # appended
                        if docelem.type in ('para', 'uli', 'li'):
                            status = 1  # i.e. stay here
                        elif docelem.type == 'code':
                            status = 2
                        else:
                            status = 0

                elif status == 2:   # after 'code'
                    docelem = doc.Element(docline)  # new one
                    elements.append(docelem)        # appended
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
                    elements.append(docelem)        # appended

                    # If the element is different than 'empty' or 'code', shrink
                    # the previous 'empty' element (if any) to a single one.
                    if docelem.type not in ('empty', 'code'):
                        prev = elements[-3] # previous to the 'empty'
                        while prev.type == 'empty':
                            # Extend the doclist of the previous by doclines
                            # from the last 'empty' element (not to loose
                            # the source lines representation). Then delete
                            # the absorbed empty element.
                            prev.extend_lines_from(elements[-2])
                            del elements[-2]

                            # There may be more 'empty' elements because
                            # we did not know they are not part of
                            # the code snippet.
                            prev = elements[-3]

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
                        elements[-1].extend_lines_from(docelem) # absorbed
                    else:
                        elements.append(docelem)    # appended

                    # Now decide the next status based on the last
                    # appended element type.
                    e = elements[-1]
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
                for e in elements:
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
                    sha_to_elem[e.sha] = e

                    # Report the content of the element.
                    f.write('{}/{} {} {}: {!r}\n'.format(
                            e.fname[:2], e.lineno(),
                            e.sha[:6], e.type, e.value()))
            self.log_info.append(self.short_name(fname))

            # Return the collected result list, and the reverse table.
            return elements, sha_to_elem

        # The target language.
        self.xx_elements, self.xx_sha_to_elem = aux_convert(self,
                                                            self.xx_aux_dir,
                                                            self.xx_doclines)

        # English original.
        self.en_elements, self.en_sha_to_elem = aux_convert(self,
                                                            self.en_aux_dir,
                                                            self.en_doclines)


    def checkStructDiffs(self):
        '''Reports differences of the structures of the sources.

        Returns True if the source structures are synchronized.'''

        sync_flag = True   # optimistic initialization

        # When comparing code snippets, the exact content is required.
        # The exception is when the comments in the examples were translated.
        # Load the structure for the exceptions from the language dependent
        # file.
        #
        # The key is the first line of the original, the value is a couple
        # with lists of related line sequences from the original and from
        # the translated sources.
        translated_snippets_fname = os.path.join(self.lang_definitions_dir,
                                                 'translated_snippets.txt')

        # Create the empty file if it does not exist.
        if not os.path.isfile(translated_snippets_fname):
            f = open(translated_snippets_fname, 'w')
            f.close()

        # Load the snippet definitions.
        translated_snippets = {}
        status = 0
        en_lines = None
        xx_lines = None
        with open(translated_snippets_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # First line is the key.
                    en_lines, xx_lines = translated_snippets.setdefault(line, ([], []))
                    assert len(en_lines) == 0 # duplicities not allowed, split
                    assert len(xx_lines) == 0 # the definitions if necessary
                    en_lines.append(line)     # first line of the original
                    status = 1

                elif status == 1:
                    # Lines of the original until the separator.
                    if line.startswith('-----'):    # at least 5 from beginning
                        en_lines = None             # collected, done
                        status = 2
                    else:
                        en_lines.append(line)       # another line of the original

                elif status == 2:
                    # Lines of the translated sources until the separator.
                    if line.startswith('====='):    # at least 5 from first pos
                        xx_lines = None             # collected, done
                        status = 0
                    else:
                        xx_lines.append(line)       # another line of the translation

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Capture the info about the file with definitions.
        self.log_info.append(self.short_name(translated_snippets_fname))

        # Compare the document structures.
        struct_diff_fname = os.path.join(self.xx_aux_dir, 'pass1struct_diff.txt')
        translated_snippets_fname = os.path.join(self.xx_aux_dir,
                                                 'pass1translated_snippets.txt')
        with open(struct_diff_fname, 'w', encoding='utf-8') as f, \
             open(translated_snippets_fname, 'w', encoding='utf-8') as ftransl:

            # Jumping around, we need the while loop and indexes.
            en_i = 0
            xx_i = 0
            while en_i < len(self.en_elements) and xx_i < len(self.xx_elements):

                # Shortcut to element on indexes.
                en_elem = self.en_elements[en_i]
                xx_elem = self.xx_elements[xx_i]

                if en_elem._line() in translated_snippets:
                    # It could be the translated sequence. Get the definition lists.
                    # The line from the original is the key.
                    enlst, xxlst = translated_snippets[en_elem._line()]

                    # Lengths of both sequences.
                    enlen = len(enlst)
                    xxlen = len(xxlst)

                    # Compare the definitions with the sources.
                    is_enseq = [e._line() for e in self.en_elements[en_i:en_i+enlen]] == enlst
                    is_xxseq = [e._line() for e in self.xx_elements[xx_i:xx_i+xxlen]] == xxlst

                    # If both flags are set then the translated sequence was found.
                    # Report it and delete the elements from both original and translation.
                    if is_enseq and is_xxseq:
                        # Report the differences. The lines below tildas has the form
                        # to be possibly copy/pasted to the translated snippets file later.
                        ftransl.write('en/{}/{}:\n'.format(en_elem.fname, en_elem.lineno()))
                        ftransl.write('{}/{}/{}:\n'.format(
                            self.lang, xx_elem.fname, xx_elem.lineno()))
                        ftransl.write('~~~~~~~~~~~~~~~\n')
                        ftransl.write(''.join(enlst))
                        ftransl.write('-----\n')
                        ftransl.write(''.join(xxlst))
                        ftransl.write('========================== ch.{}\n\n'.format(en_elem.fname[:2]))

                        # Delete the elements from the member lists.
                        del self.en_elements[en_i:en_i+enlen]
                        del self.xx_elements[xx_i:xx_i+xxlen]

                        # Corrections of the indexes as they will be incremented later.
                        en_i -= 1
                        xx_i -= 1

                else:
                    # This is not the case of the translated snippet. Compare the structure.
                    # The more benevolent comparison requires only types of the elements
                    # to be equal. If the element is a code snippet, it must have exactly
                    # the same content.
                    if en_elem.type != xx_elem.type \
                       or (en_elem.type == 'code'
                           and en_elem.value() != xx_elem.value()):
                        # Not in sync -- reset the optimistic value of the flag.
                        sync_flag = False

                        # Report the difference: heading contains
                        # chapter no., lineno, type, and the value.
                        # English...
                        f.write('\nen {}/{} [{}] {}:\n\t{}\n'.format(
                                en_elem.fname[:2],
                                en_elem.lineno(),
                                en_elem.sha[:6],
                                en_elem.type,
                                en_elem.value()))

                        # The target language...
                        f.write('{} {}/{} [{}] {}:\n\t{}\n'.format(
                                self.lang,
                                xx_elem.fname[:2],
                                xx_elem.lineno(),
                                xx_elem.sha[:6],
                                xx_elem.type,
                                xx_elem.value()))

                # Jump to the next elements.
                en_i += 1
                xx_i += 1

        # Capture the info about the report files. (The translated_snippets_fname
        # identifier is reused -- here for the output file.)
        self.log_info.append(self.short_name(translated_snippets_fname))
        self.log_info.append(self.short_name(struct_diff_fname))

        # The information about the result of the check.
        self.log_info.append(('-'*30) + ' structure of the book is ' +
                               ('the same' if sync_flag else 'DIFFERENT'))
        if not sync_flag:
            self.log_info.append(
                "Have a look at the following report file:\n\t'{}'\n"
                .format(struct_diff_fname))

        return sync_flag


    def checkContentChanges(self):
        '''Compares content with the last known -- based on SHA-1.

        '''
        # Load the last known content definitions. If the file does not exist,
        # create the empty one.
        fname = os.path.join(self.lang_definitions_dir, 'content_sha.txt')
        if not os.path.isfile(fname):
            f = open(fname, 'w', encoding='utf-8')
            f.close()

        en_chl_to_shas = {}
        en_chl_to_shas = {}
        with open(fname, encoding='utf-8') as f:
            for line in f:
                en_ch_lineno, xx_ch_lineno, en_sha, xx_sha = line.split()
                en_chl_to_shas[en_ch_lineno] = (en_sha, xx_sha)

        # Capture the definition file to the log.
        self.log_info.append(self.short_name(fname))

        # Loop through all elements in both languages. It is assumed that
        # the structures were already synchronized. Generate the `content_sha.txt`
        # in the *auxiliary* directory -- it can be later moved to `definitions`
        # directory. Report the differences to the file.
        fname_new_sha = os.path.join(self.xx_aux_dir, 'content_sha.txt')
        fname_diff = os.path.join(self.xx_aux_dir, 'pass1content_diff.txt')
        cnt_en_changed = 0      # init -- number of changes in original
        cnt_xx_changed = 0      # init -- number of changes in target
        cnt_unchecked = 0       # init -- number of unchecked translations
        with open(fname_new_sha, 'w', encoding='utf-8') as fsha, \
             open(fname_diff, 'w', encoding='utf-8') as fdiff:

            for en_el, xx_el in zip(self.en_elements, self.xx_elements):

                # Ignore the elements with number zero as they are used
                # only as artificial separators between the chapters.
                if en_el.lineno() == '0':
                    continue

                # Get the SHA-1 for the original and for the translated.
                en_sha = en_el.sha
                xx_sha = xx_el.sha

                # The chapter and lineno combination.
                en_ch_lineno = '{}/{}'.format(en_el.fname[:2], en_el.lineno())
                xx_ch_lineno = '{}/{}'.format(xx_el.fname[:2], xx_el.lineno())

                # Write the new values to the new definitions file
                # (in the auxiliary directory). The chapter and lineno
                # informations for both languages are used when the move
                # of the element is detected. It also helps to copy/paste
                # the sha lines to the definition file when manually
                # checking parts of the book.
                fsha.write('{} {} {} {}\n'.format(
                    en_ch_lineno, xx_ch_lineno, en_sha, xx_sha))

                # Get the last SHA's from the definition. If the record
                # was not defined, the empty strings are returned.
                en_last_sha, xx_last_sha = en_chl_to_shas.get(en_ch_lineno, ('', ''))

                # The element contents are reported as changed only if at least one
                # of the SHA's differ from the definition.
                if en_sha != en_last_sha or xx_sha != xx_last_sha:

                    # English.
                    if en_last_sha == '':
                        note = ' unchecked'
                        cnt_unchecked += 1
                    elif en_sha != en_last_sha:
                        note = ' changed'
                        cnt_en_changed += 1
                    else:
                        note = ''
                    fdiff.write('en {}/{}{}\n'.format(
                                en_el.fname[:2], en_el.lineno(), note))
                    fdiff.write('\t{}\n'.format(en_el.value()))

                    # The target language.
                    if xx_last_sha == '':
                        note = ' unchecked'
                    elif xx_sha != xx_last_sha:
                        note = ' changed'
                        cnt_xx_changed += 1
                    else:
                        note = ''
                    fdiff.write('{} {}/{}{}\n'.format(
                                self.lang, xx_el.fname[:2], xx_el.lineno(), note))
                    fdiff.write('\t{}\n'.format(xx_el.value()))
                    fdiff.write('\n')

        # Capture the new definition file to the log, the report file,
        # and the result.
        self.log_info.append(self.short_name(fname_new_sha))
        self.log_info.append(self.short_name(fname_diff))

        if cnt_en_changed > 0:
            note = ' [en] content changed: {}'.format(cnt_en_changed)
            self.log_info.append(('-'*30) + note)

        if cnt_xx_changed > 0:
            note = ' [{}] content changed: {}'.format(self.lang, cnt_xx_changed)
            self.log_info.append(('-'*30) + note)

        if cnt_unchecked > 0:
            note = ' content unchecked: {}'.format(cnt_unchecked)
            self.log_info.append(('-'*30) + note)

        if (cnt_en_changed + cnt_xx_changed + cnt_unchecked) > 0:
            self.log_info.append(
                "Have a look at the following report file:\n\t'{}'\n"
                .format(fname_diff))


    def run(self):
        '''Launcher of the parser phases.'''

        self.writePass1txtFiles()
        self.loadDoclineLists()
        self.convertDoclinesToElements()
        sync_flag = self.checkStructDiffs()
        self.checkContentChanges()

        return '\n\t'.join(self.log_info)
