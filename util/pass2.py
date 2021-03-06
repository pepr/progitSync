#!python3
# -*- coding: utf-8 -*-

import os
import re


class Parser:
    '''Pass 2 parser for markup checking.

       Consumes the result of the pass1 parser.'''

    # Regular expression for detecting sequences in backticks.
    rexBackticked = re.compile(r'`(\S.*?\S?)`')

    def __init__(self, pass1):
        self.lang = pass1.lang

        # Important directories.
        self.en_src_dir = pass1.en_src_dir
        self.xx_src_dir = pass1.xx_src_dir
        self.en_aux_dir = pass1.en_aux_dir
        self.xx_aux_dir = pass1.xx_aux_dir
        self.root_definitions_dir = pass1.root_definitions_dir
        self.lang_definitions_dir = pass1.lang_definitions_dir

        # Lists of elements (some elements were
        # processed and deleted in the pass1).
        self.en_elements = pass1.en_elements
        self.xx_elements = pass1.xx_elements

        self.log_info = []                # lines for logging
        self.backticked_set = set()


    def short_name(self, fname):
        '''Returns tail of the fname -- for log info.'''
        lst = fname.split(os.sep)
        if lst[-2] == self.lang:
            return '/'.join(lst[-3:])
        else:
            return '/'.join(lst[-2:])


    def checkImages(self):
        '''Checks if the documents use the same images.'''

        sync_flag = True  # Optimistic initialization
        images_fname = os.path.join(self.xx_aux_dir, 'pass2img_diff.txt')
        with open(images_fname, 'w', encoding='utf-8') as f:
            for en_e, xx_e in zip(self.en_elements, self.xx_elements):
                if en_e.type == 'img' and en_e.attrib != xx_e.attrib \
                   or en_e.type == 'imgcaption' \
                      and en_e.attrib[0] != xx_e.attrib[0]:

                    # Out of sync, reset the flag...
                    sync_flag = False

                    # ... and report to the file.
                    f.write('\n{} {}/{} -- en {}/{}:\n'.format(
                            self.lang,
                            xx_e.fname,
                            xx_e.lineno(),
                            en_e.fname,
                            en_e.lineno()))

                    # Type and value of the translated element.
                    f.write('\t{}:\t{}\n'.format(xx_e.type,
                                                 xx_e.value()))

                    # Type and value of the English element.
                    f.write('\t{}:\t{}\n'.format(en_e.type,
                                                 en_e.value()))

        # Capture the info about the report file.
        self.log_info.append(self.short_name(images_fname))
        self.log_info.append(('-'*30) + ' image info is ' +
                               ('the same' if sync_flag else 'DIFFERENT'))


    def buildRex(self, lst):
        '''Build a regular expression matching substrings from the lst.'''

        # Build a list of escaped unique substrings from the input list.
        # The order is not important now as it must be corrected later.
        lst2 = [re.escape(s) for s in set(lst)]

        # Join the escaped substrings to form the regular expression
        # pattern, build the regular expression, and return it. There could
        # be longer paterns that contain shorter patterns. The longer patterns
        # should be matched first. This way, the lst2 must be reverse sorted
        # by the length of the patterns.
        pat = '|'.join(sorted(lst2, key=len, reverse=True))
        rex = re.compile(pat)
        return rex


    def fixParaBackticks(self):
        '''Checks the bakctick markup in paragraphs, list items...

           The results reported to pass2backticks.txt.'''

        async_cnt = 0     # init -- "not synchronous lines" counter
        anomaly_cnt = 0   # init -- anomaly counter (with respect to the markup in both cases)
        btfname = os.path.join(self.xx_aux_dir, 'pass2backticks.txt')
        btfname_skipped = os.path.join(self.xx_aux_dir, 'pass2backticks_skiped.txt')
        btfname_anomaly = os.path.join(self.xx_aux_dir, 'pass2backticks_anomaly.txt')

        # Some backtick markup (difference, missing, extra) may be intentional
        # by the translator (human) and as such is captured in the file with
        # exceptions. The original line is the key, the translated form
        # is the value. In the exception file, the values are separated by
        # at least five dashes, and the records by at least five equal signs
        # -- as in previous cases. See the `definitions/cs` examples if in doubt.
        backtick_exceptions_fname = os.path.join(self.lang_definitions_dir,
                                                 'backtick_exceptions.txt')

        # Create the empty file if it does not exist.
        if not os.path.isfile(backtick_exceptions_fname):
            f = open(backtick_exceptions_fname, 'w')
            f.close()

        # Load the exceptions.
        backtick_exceptions = {}
        status = 0
        original = None
        with open(backtick_exceptions_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    original = line     # will be the key later
                    status = 1

                elif status == 1:
                    assert line.startswith('-----')
                    status = 2

                elif status == 2:
                    backtick_exceptions[original] = line    # translation
                    original = None
                    status = 3

                elif status == 3:
                    assert line.startswith('=====')
                    status = 0

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Capture the info about the definition file.
        self.log_info.append(self.short_name(backtick_exceptions_fname))

        with open(btfname, 'w', encoding='utf-8') as fout, \
             open(btfname_skipped, 'w', encoding='utf-8') as fskip, \
             open(btfname_anomaly, 'w', encoding='utf-8') as fa:

            # The content is expected to be already synchronized; therefore,
            # looping using the for-loop.
            for en_e, xx_e in zip(self.en_elements, self.xx_elements):
                # Process only the text from paragraphs and list items.
                if en_e.type in ['para', 'uli', 'li']:
                    # If in exceptions, set the flag, but examine anyway.
                    skipped = xx_e._line() == backtick_exceptions.get(en_e._line(), '!@#$%^&*')

                    # Find all symbols in backticks.
                    enlst = self.rexBackticked.findall(en_e._line())
                    xxlst = self.rexBackticked.findall(xx_e._line())

                    # The marked items may appear in different order
                    # in the translated text. This way, sets of the marked
                    # items should be compared. But also, some list may be longer
                    # because of repetitions of the same marked items.
                    # There may be also other situations, but consider them
                    # less probable.
                    if set(enlst) != set(xxlst) or len(enlst) != len(xxlst):

                        # Create the list of differences that contains only
                        # the strings that are in en, but not in xx. That is,
                        # remove the elements used in the translated language
                        # from the English list.
                        dlst = enlst[:]   # copy
                        for s in xxlst:
                            if s in dlst:
                                dlst.remove(s)

                        # Report the skipped lines. Report separately the
                        # lines that are not captured as exceptions, and
                        # increase the counter of problems in the later case.
                        if skipped:
                            fskip.write('\n{} {}/{} -- en {}/{}:\n'.format(
                                self.lang,
                                xx_e.fname,
                                xx_e.lineno(),
                                en_e.fname,
                                en_e.lineno()))
                        else:
                            async_cnt += 1
                            fout.write('\n{} {}/{} -- en {}/{}:\n'.format(
                                self.lang,
                                xx_e.fname,
                                xx_e.lineno(),
                                en_e.fname,
                                en_e.lineno()))

                        # Translated value before the suggested fix.
                        xxpara1 = xx_e.value()

                        # If the list of differences is empty, we do not want
                        # to fix anything. Actually we cannot fix anything
                        # as it would lead to construction of the bad regular
                        # expression that would lead to markup of unwanted pieces.
                        # But we still consider this anomaly, report it
                        # to the separate log file, and count it separately.
                        #
                        # If the list of differences is not empty, the translated
                        # source does not follow the original markup. Then build
                        # the regular expression and suggest the markup. Get
                        # also the number of replacements.
                        n = 0            # init -- number of replacements
                        xx_suggested_value = xx_e.value()
                        if len(dlst) != 0:
                            rex = self.buildRex(dlst)
                            xx_suggested_value, n = rex.subn(r'`\g<0>`', xx_e.value())

                        # Now we have the list of differences, the original line,
                        # the translated line before the replacements (xxpara1)
                        # the replaced line in the self.xx_elements.
                        # Report the information differently
                        if skipped:
                            fskip.write('{}\n'.format(repr(dlst)))
                            fskip.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                            fskip.write('{}\n'.format(en_e.value()))
                            fskip.write('---------------\n')
                            fskip.write('{}\n'.format(xxpara1)) # from translated sources
                            fskip.write('====================================== {}\n'.format(en_e.fname))
                        else:
                            fout.write('{}\n'.format(repr(dlst)))
                            fout.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                            fout.write('{}\n'.format(en_e.value()))
                            fout.write('---------------\n')
                            fout.write('{}\n'.format(xxpara1))  # from translated sources
                            fout.write('====================================== {}\n'.format(en_e.fname))
                            fout.write('Suggested markup:\n')
                            fout.write('{}\n'.format(xx_suggested_value)) # suggested markup

                        # The suggested markup may be wrong because of non-human processing
                        # implementation that is not perfect. Calculate the difference list
                        # again based on the suggested markup of the translated value.
                        xxlst2 = self.rexBackticked.findall(xx_suggested_value)
                        dlst2 = enlst[:]   # copy
                        for s in xxlst2:
                            if s in dlst2:
                                dlst2.remove(s)

                        # The anomaly happens when at least one of the cases happens:
                        # - the sets of substrings in original and in the translation differ,
                        # - the difference list is not empty (that is missing markup
                        #   in the translation),
                        # - the length of lists differs for the original and for
                        #   the translation (that is, the translation marks up different
                        #   number of substrings),
                        # - the number of replacements differ from the length of
                        #   the first difference list (that is too much markups
                        #   were suggested).
                        if set(enlst) != set(xxlst2) or len(dlst2) > 0 \
                           or len(enlst) != len(xxlst2) or len(dlst) != n:

                            # It is an anomaly only if it not an explicit exception.
                            if not skipped:
                                anomaly_cnt += 1

                            # Report to the log file with anomalies.
                            fa.write('\n{} {} -- en {}/{}:\n'.format(
                                self.lang,
                                xx_e.lineno(),
                                en_e.fname[:2],
                                en_e.lineno()))

                            # To the report of anomalies insert all values that can
                            # help to spot the problem.
                            fa.write('\t[en] markup               = {} {}\n'.format(len(enlst), repr(enlst)))
                            fa.write('\t[{}] markup               = {} {}\n'.format(self.lang, len(xxlst), repr(xxlst)))
                            fa.write('\tmissing in [{}]           = {} {}\n'.format(self.lang, len(dlst), repr(dlst)))
                            fa.write('\tsuggested [{}] markup     = {} {}\n'.format(self.lang, len(xxlst2), repr(xxlst2)))
                            fa.write('\tmissing in suggested [{}] = {} {}\n'.format(self.lang, len(dlst2), repr(dlst2)))
                            fa.write('\tnumber of suggested replacement in [{}] = {}\n'.format(self.lang, n))
                            fa.write('Original [en]:\n\t{}\n'.format(en_e.value()))
                            fa.write('Translation [{}]:\n\t{}\n'.format(self.lang, xxpara1))
                            if n > 0:
                                fa.write('Suggested translation [{}]:\n\t{}\n'.format(self.lang, xx_suggested_value))
                            fa.write('-'*50 + '\n')

        # Capture the info about the report log files and about the result.
        self.log_info.append(self.short_name(btfname))
        self.log_info.append(self.short_name(btfname_skipped))
        self.log_info.append(('-'*30) + \
                         ' asynchronous backticks: {}'.format(async_cnt))
        self.log_info.append(self.short_name(btfname_anomaly))
        self.log_info.append(('-'*30) + \
                         ' backtick anomalies: {}'.format(anomaly_cnt))


    def reportBadDoubleQuotes(self):
        '''Checks usage of the correct version of double quotes.

           There should be “these” in the text to be typeset
           as paragraph or list item. And there should be "these"
           in the code snippets.

           Results are reported to pass2dquotes.txt.'''

        cnt = 0         # init -- counter of improper usage
        fname = os.path.join(self.xx_aux_dir, 'pass2dquotes.txt')

        with open(fname, 'w', encoding='utf-8', newline='\n') as f:

            # Only plain ASCII double quotes are allowed in code snippets.
            rexBadCodeQuotes = re.compile(r'[„“”]')

            # The paragraphs should contain the typesetting-ready
            # double quotes that are language dependent.
            if self.lang == 'cs':
                rexBadParaQuotes = re.compile(r'["”]')  # Czech ones must be „this way“
            elif self.lang == 'fr':
                rexBadParaQuotes = re.compile(r'["”]')  # I do not know for French
            else:   # as in 'en'
                rexBadParaQuotes = re.compile(r'["„]')  # English uses “these”

            for en_e, xx_e in zip(self.en_elements, self.xx_elements):

                # Depending on the element type...
                if xx_e.type in ('para', 'li', 'uli', 'imgcaption', 'title'):
                    # The elements that should use *nice* double quotes.

                    if rexBadParaQuotes.search(xx_e.value()) is not None:
                        # Improper double quote found. Count it and report it.
                        cnt += 1

                        f.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                self.lang,
                                xx_e.fname,
                                xx_e.lineno(),
                                en_e.fname,
                                en_e.lineno(),
                                repr(xx_e.type)))

                        f.write('\t{}\n'.format(en_e.value()))
                        f.write('\t{}\n'.format(xx_e.value()))

                elif xx_e.type == 'code':
                    # Code should use the ASCII double quotes.

                    if rexBadCodeQuotes.search(xx_e.value()) is not None:

                        # Unwanted double quote found.
                        cnt += 1

                        f.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                self.lang,
                                xx_e.fname,
                                xx_e.lineno(),
                                en_e.fname,
                                en_e.lineno(),
                                repr(xx_e.type)))

                        f.write('\t{}\n'.format(en_e.value()))
                        f.write('\t{}\n'.format(xx_e.value()))

                elif xx_e.type not in ('empty', 'img'):
                        # No double quotes should be in that type of element.
                        cnt += 1

                        f.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                self.lang,
                                xx_e.fname,
                                xx_e.lineno(),
                                en_e.fname,
                                en_e.lineno(),
                                repr(xx_e.type)))

                        f.write('\t{}\n'.format(en_e.value()))
                        f.write('\t{}\n'.format(xx_e.value()))


        # Capture the info about the log file and the result message.
        self.log_info.append(self.short_name(fname))
        self.log_info.append(('-'*30) + \
               ' elements with bad double quotes: {}'.format(cnt))


    def reportEmAndStrong(self):
        '''Compares the usage of *emphasize* and **strong** markup.

           The comparison is based on the same number of usage of
           the markup in the English original and in the translated
           source. From the point of checking, there is no difference
           between *em* and **strong** as some human languages
           may tend to use it differently than the English original.
           All elements with markups are reported to pass2em_strong.txt,
           if the number of marked substrings differ, the report
           goes also to pass2em_strong_diff.txt.'''

        cnt = 0         # init -- počet odhalených chyb
        fname = os.path.join(self.xx_aux_dir, 'pass2em_strong.txt')
        fname_diff = os.path.join(self.xx_aux_dir, 'pass2em_strong_diff.txt')

        with open(fname, 'w', encoding='utf-8', newline='\n') as f,\
             open(fname_diff, 'w', encoding='utf-8', newline='\n') as fdiff:

            # Regular expression for single or double stars around
            # a text. The underscore can also be used instead of
            # the star..
            rexEmStrong = re.compile(r'([*_]{1,2})([^*_]+?)\1')

            for en_e, xx_e in zip(self.en_elements, self.xx_elements):

                # Only for elements with a typeset text (that is not
                # inside code snippets)...
                if xx_e.type in ('para', 'li', 'uli', 'imgcaption', 'title'):

                    # Build the lists of marked substrings.
                    enlst = rexEmStrong.findall(en_e.value())
                    xxlst = rexEmStrong.findall(xx_e.value())

                    # If any markup was found, show the original and
                    # the translation in the log. If lengths of the lists
                    # differ, report to the difference log.
                    if enlst or xxlst:
                        f.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                self.lang,
                                xx_e.fname,
                                xx_e.lineno(),
                                en_e.fname,
                                en_e.lineno(),
                                repr(xx_e.type)))

                        # Numbers of marked substrings.
                        f.write('\t{} : {}\n'.format(len(enlst), len(xxlst)))

                        # The lines.
                        f.write('\t{}\n'.format(en_e.value()))
                        f.write('\t{}\n'.format(xx_e.value()))

                        # If the number of marked substrings differ,
                        # report also to the difference log.
                        if len(enlst) != len(xxlst):
                            cnt += 1
                            fdiff.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                        self.lang,
                                        xx_e.fname,
                                        xx_e.lineno(),
                                        en_e.fname,
                                        en_e.lineno(),
                                        repr(xx_e.type)))

                            # Numbers of marked substrings.
                            fdiff.write('\t{} : {}\n'.format(len(enlst), len(xxlst)))

                            # The lines.
                            fdiff.write('\t{}\n'.format(en_e.value()))
                            fdiff.write('\t{}\n'.format(xx_e.value()))

        # Capture the info about the logs and the result.
        self.log_info.append(self.short_name(fname))
        self.log_info.append(self.short_name(fname_diff))
        self.log_info.append(('-'*30) + \
               ' differences in *em* and **strong**: {}'.format(cnt))


    def run(self):
        '''Launcher of the parser phases.'''

        self.checkImages()
        self.fixParaBackticks()
        self.reportBadDoubleQuotes()
        self.reportEmAndStrong()

        return '\n\t'.join(self.log_info)

