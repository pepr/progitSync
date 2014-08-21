#!python3
# -*- coding: utf-8 -*-

import docelement
import gen
import os



class Parser:
    '''Pass1 parser checks for synchronicity of the original sources with the lang sources.

       This parser consumes the `progit/en` and `progit/xx` (where `xx` is
       the target language abbreviation), and reports if there is any difference
       in the structure of the coduments.'''

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

        # Create the auxiliary directories if they does not exist.
        if not os.path.isdir(self.en_aux_dir):
            os.makedirs(self.en_aux_dir)

        if not os.path.isdir(self.xx_aux_dir):
            os.makedirs(self.xx_aux_dir)


        self.en_lst = None  # elements from the English original
        self.xx_lst = None  # elements from the target language

        self.info_lines = []    # lines for displaying through the stdout


    def short_name(self, fname):
        '''Returns tail of the fname -- for log info.'''
        lst = fname.split(os.sep)
        if lst[-2] == self.lang:
            return '/'.join(lst[-3:])
        else:
            return '/'.join(lst[-2:])


    def writePass1txtFiles(self):
        # Copy the target language sources with chapter/line info into a single
        # file -- mostly for debugging, not consumed later.
        xx_single_fname = os.path.join(self.xx_aux_dir, 'pass1.txt')
        with open(xx_single_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Do the same with the original.
        en_single_fname = os.path.join(self.en_aux_dir, 'pass1.txt')
        with open(en_single_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_src_dir):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Capture the info about the generated files.
        self.info_lines.append(self.short_name(xx_single_fname))
        self.info_lines.append(self.short_name(en_single_fname))


    def loadElementLists(self):
        '''Loads elements of the source documents to the lists.

           As a side effect, the representation of the elements is saved
           into pass1elem.txt (mostly for debugging purpose).'''

        # The target-language sources may contain some extra parts used
        # as translator notes or some other explanations of the English
        # original. When compared with the original, the parts must be
        # skipped. The `exceptions/xx/extras.txt` stores the definitions
        # of the skipped parts in the form that can be cut/pasted from
        # other logs (UTF-8). If the extras.txt file does not exist,
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
        path, scriptname = os.path.split(__file__)
        extras_fname = os.path.join(path, 'exceptions', self.lang, 'extras.txt')

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
        self.info_lines.append(self.short_name(extras_fname))

        # Loop through the elements and build the lists of element objects
        # from the original and from the translation. The extra sequences
        # from the target languages are reported and skipped. They will be
        # deleted from the list.
        self.xx_lst = []
        for relname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
            elem = docelement.Element(relname, lineno, line)
            self.xx_lst.append(elem)

        # Delete and report the extra elements.
        xx_extra_fname = os.path.join(self.xx_aux_dir, 'pass1extras.txt')
        with open(xx_extra_fname, 'w', encoding='utf-8', newline='\n') as fout:
            index = 0                       # index the processed element
            while index < len(self.xx_lst): # do not optimize, the length can change
                elem = self.xx_lst[index]   # current element
                if elem.line in extras:     # is current line recognized as extra?
                    # I could be the extra sequence. Compare the other lines
                    # in the length of the sequence. Firstly, extract the following
                    # lines in the length of the extras list.
                    extra_lines = extras[elem.line]
                    src_lines = [e.line for e in self.xx_lst[index:index+len(extra_lines)]]

                    # If the list have the same content, delete the source elements.
                    if src_lines == extra_lines:
                        # Report the skipped lines.
                        fout.write('{}/{}:\n'.format(elem.fname, elem.lineno))
                        fout.write(''.join(src_lines))
                        fout.write('====================\n\n')

                        # Delete the lines via deleting their elements.
                        del self.xx_lst[index:index+len(extra_lines)]

                        # Decrement the index -- i.e. correction as
                        # it will be incremented later.
                        index -= 1

                # Jump to the next checked element.
                index += 1

        # Capture the info about the report file.
        self.info_lines.append(self.short_name(xx_extra_fname))

        # Report the remaining target-language elements.
        xx_elem_fname = os.path.join(self.xx_aux_dir, 'pass1elem.txt')
        with open(xx_elem_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for elem in self.xx_lst:
                fout.write(repr(elem) + '\n')

        # Capture the info about the report file.
        self.info_lines.append(self.short_name(xx_elem_fname))

        # Report the structure of the English original.
        self.en_lst = []
        en_elem_fname = os.path.join(self.en_aux_dir, 'pass1elem.txt')
        with open(en_elem_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for relname, lineno, line in gen.sourceFileLines(self.en_src_dir):
                elem = docelement.Element(relname, lineno, line)
                self.en_lst.append(elem)
                fout.write(repr(elem) + '\n')

        # Capture the info about the report file.
        self.info_lines.append(self.short_name(en_elem_fname))


    def checkStructDiffs(self):
        '''Reports differences of the structures of the sources.'''

        sync_flag = True   # optimistic initialization

        # When comparing code snippets, the exact content is required.
        # The exception is when the comments in the examples were translated.
        # Load the structure for the exceptions from the language dependent
        # file.
        #
        # The key is the first line of the original, the value is a couple
        # with lists of related line sequences from the original and from
        # the translated sources.
        path, scriptname = os.path.split(__file__)
        translated_snippets_fname = os.path.join(path, 'exceptions',
                                        self.lang, 'translated_snippets.txt')

        # Create the empty file if it does not exist.
        if not os.path.isfile(translated_snippets_fname):
            f = open(translated_snippets_fname, 'w')
            f.close()

        # Load the snippet definitions.
        translated_snippets = {}
        status = 0
        en_lst = None
        xx_lst = None
        with open(translated_snippets_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # First line is the key.
                    en_lst, xx_lst = translated_snippets.setdefault(line, ([], []))
                    assert len(en_lst) == 0 # duplicities not allowed, split
                    assert len(xx_lst) == 0 # the definitions if necessary
                    en_lst.append(line)     # first line of the original
                    status = 1

                elif status == 1:
                    # Lines of the original until the separator.
                    if line.startswith('-----'):    # at least 5 from beginning
                        en_lst = None               # collected, done
                        status = 2
                    else:
                        en_lst.append(line)         # another line of the original

                elif status == 2:
                    # Lines of the translated sources until the separator.
                    if line.startswith('====='):    # at least 5 from first pos
                        xx_lst = None               # collected, done
                        status = 0
                    else:
                        xx_lst.append(line)         # another line of the translation

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Capture the info about the file with definitions.
        self.info_lines.append(self.short_name(translated_snippets_fname))

        # Compare the document structures. (The para_len report is for future
        # to detect whether the *content* of the paragraph is reasonably different
        # than the original based on heuristics -- ratio of the length in the original
        # and in the translation.)
        struct_diff_fname = os.path.join(self.xx_aux_dir, 'pass1struct_diff.txt')
        para_len_fname = os.path.join(self.xx_aux_dir, 'pass1paralen.txt')
        translated_snippets_fname = os.path.join(self.xx_aux_dir, 'pass1translated_snippets.txt')
        with open(struct_diff_fname, 'w', encoding='utf-8', newline='\n') as f, \
             open(translated_snippets_fname, 'w', encoding='utf-8', newline='\n') as ftransl, \
             open(para_len_fname, 'w', encoding='utf-8', newline='\n') as flen:

            # Jumping around, we need the while loop and indexes.
            en_i = 0
            xx_i = 0
            while en_i < len(self.en_lst) and xx_i < len(self.xx_lst):

                # Shortcut to element on indexes.
                en_elem = self.en_lst[en_i]
                xx_elem = self.xx_lst[xx_i]

                if en_elem.line in translated_snippets:
                    # It could be the translated sequence. Get the definition lists.
                    # The line from the original is the key.
                    enlst, xxlst = translated_snippets[en_elem.line]

                    # Lengths of both sequences.
                    enlen = len(enlst)
                    xxlen = len(xxlst)

                    # Compare the definitions with the sources.
                    is_enseq = [e.line for e in self.en_lst[en_i:en_i+enlen]] == enlst
                    is_xxseq = [e.line for e in self.xx_lst[xx_i:xx_i+xxlen]] == xxlst

                    # If both flags are set then the translated sequence was found.
                    # Report it and delete the elements from both original and translation.
                    if is_enseq and is_xxseq:
                        # Report the differences. The lines below tildas has the form
                        # to be possibly copy/pasted to the translated snippets file later.
                        ftransl.write('{}/{}:\n'.format(en_elem.fname, en_elem.lineno))
                        ftransl.write('{}/{}:\n'.format(xx_elem.fname, xx_elem.lineno))
                        ftransl.write('~~~~~~~~~~~~~~~\n')
                        ftransl.write(''.join(enlst))
                        ftransl.write('-----\n')
                        ftransl.write(''.join(xxlst))
                        ftransl.write('========================== {}\n\n'.format(en_elem.fname))

                        # Delete the elements from the member lists.
                        del self.en_lst[en_i:en_i+enlen]
                        del self.xx_lst[xx_i:xx_i+xxlen]

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
                           and en_elem.line.rstrip() != xx_elem.line.rstrip()):
                        # Not in sync -- reset the optimistic value of the flag.
                        sync_flag = False

                        # Report the difference: heading contains file/lineno.
                        f.write('\nen {}/{} -- {} {}/{}:\n'.format(
                                en_elem.fname,
                                en_elem.lineno,
                                self.lang,
                                xx_elem.fname,
                                xx_elem.lineno))

                        # The type and the value of the English element.
                        f.write('\t{}:\t{}\n'.format(en_elem.type,
                                                     en_elem.line.rstrip()))

                        # The type and the value of the translated element.
                        f.write('\t{}:\t{}\n'.format(xx_elem.type,
                                                     xx_elem.line.rstrip()))

                    # The basics of the heuristic analysis (planned for future)
                    # to detect some stranegeness of the *content* of the texts.
                    # Here the lengths from the original and the translation.
                    elif en_elem.type in ('para', 'uli', 'li'):
                        # Chapter ID, language, line no., lengths ratio as a text,
                        # lengths ratio as the calculated value.
                        flen.write('{} en/{} -- {}/{}:\t{}:{}\t({})\n'.format(
                                   os.path.split(xx_elem.fname)[0],
                                   en_elem.lineno,
                                   self.lang,
                                   xx_elem.lineno,
                                   len(en_elem.line),
                                   len(xx_elem.line),
                                   len(en_elem.line) / len(xx_elem.line)))

                # Jump to the next elements.
                en_i += 1
                xx_i += 1

        # Capture the info about the report files. (The translated_snippets_fname
        # identifier is reused -- here for the output file.)
        self.info_lines.append(self.short_name(translated_snippets_fname))
        self.info_lines.append(self.short_name(struct_diff_fname))
        self.info_lines.append(self.short_name(para_len_fname))

        # The information about the result of the check.
        self.info_lines.append(('-'*30) + ' structure of the doc is ' +
                               ('the same' if sync_flag else ' DIFFERENT'))


    def run(self):
        '''Launcher of the parser phases.'''

        self.writePass1txtFiles()
        self.loadElementLists()
        self.checkStructDiffs()

        return '\n\t'.join(self.info_lines)
