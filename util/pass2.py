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
        self.root_exceptions_dir = pass1.root_exceptions_dir

        # Lists of elements (some elements were
        # processed and deleted in the pass1).
        self.en_lst = pass1.en_lst
        self.xx_lst = pass1.xx_lst

        self.info_lines = []                # lines for logging
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
        with open(images_fname, 'w', encoding='utf-8', newline='\n') as f:
            for en_el, xx_el in zip(self.en_lst, self.xx_lst):
                if en_el.type == 'img' and en_el.attrib != xx_el.attrib \
                   or en_el.type == 'imgcaption' \
                      and en_el.attrib[0] != xx_el.attrib[0]:

                    # Out of sync, reset the flag...
                    sync_flag = False

                    # ... and report to the file.
                    f.write('\n{} {}/{} -- en {}/{}:\n'.format(
                            self.lang,
                            xx_el.fname,
                            xx_el.lineno,
                            en_el.fname,
                            en_el.lineno))

                    # Type and value of the translated element.
                    f.write('\t{}:\t{}\n'.format(xx_el.type,
                                                 xx_el.line.rstrip()))

                    # Type and value of the English element.
                    f.write('\t{}:\t{}\n'.format(en_el.type,
                                                 en_el.line.rstrip()))

        # Capture the info about the report file.
        self.info_lines.append(self.short_name(images_fname))
        self.info_lines.append(('-'*30) + ' image info is ' +
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
        anomaly_cnt = 0   # init -- anomally counter (with respect to the markup in both cases)
        btfname = os.path.join(self.xx_aux_dir, 'pass2backticks.txt')
        btfname_skipped = os.path.join(self.xx_aux_dir, 'pass2backticks_skiped.txt')
        btfname_anomaly = os.path.join(self.xx_aux_dir, 'pass2backticks_anomaly.txt')

        # Some backtick markup (difference, missing, extra) may be intentional
        # by the translator (human) and as such is captured in the file with
        # exceptions. The original line is the key, the translated form
        # is the value. In the exception file, the values are separated by
        # at least five dashes, and the records by at least five equal signs
        # -- as in previous cases. See the `exceptions/cs` examples if in doubt.
        backtick_exceptions_fname = os.path.join(self.root_exceptions_dir,
                                    self.lang, 'backtick_exceptions.txt')

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
        self.info_lines.append(self.short_name(backtick_exceptions_fname))

        with open(btfname, 'w', encoding='utf-8', newline='\n') as fout, \
             open(btfname_skipped, 'w', encoding='utf-8', newline='\n') as fskip, \
             open(btfname_anomaly, 'w', encoding='utf-8', newline='\n') as fa:

            # The content is expected to be already synchronized; therefore,
            # looping using the for-loop.
            for en_el, xx_el in zip(self.en_lst, self.xx_lst):
                # Process only the text from paragraphs and list items.
                if en_el.type in ['para', 'uli', 'li']:
                    # If in exceptions, set the flag, but examine anyway.
                    skipped = xx_el.line == backtick_exceptions.get(en_el.line, '!@#$%^&*')

                    # Find all symbols in backticks.
                    enlst = self.rexBackticked.findall(en_el.line)
                    xxlst = self.rexBackticked.findall(xx_el.line)

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
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno))
                        else:
                            async_cnt += 1
                            fout.write('\n{} {}/{} -- en {}/{}:\n'.format(
                                self.lang,
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno))

                        # Translated line before the suggested fix.
                        xxpara1 = xx_el.line.rstrip()

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
                        if len(dlst) != 0:
                            rex = self.buildRex(dlst)
                            xx_el.line, n = rex.subn(r'`\g<0>`', xx_el.line)

                        # Now we have the list of differences, the original line,
                        # the translated line before the replacements (xxpara1)
                        # the replaced line in the self.xx_lst.
                        # Report the information differently
                        if skipped:
                            fskip.write('{}\n'.format(repr(dlst)))
                            fskip.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                            fskip.write('{}\n'.format(en_el.line.rstrip()))
                            fskip.write('---------------\n')
                            fskip.write('{}\n'.format(xxpara1)) # from translated sources
                            fskip.write('====================================== {}\n'.format(en_el.fname))
                        else:
                            fout.write('{}\n'.format(repr(dlst)))
                            fout.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                            fout.write('{}\n'.format(en_el.line.rstrip()))
                            fout.write('---------------\n')
                            fout.write('{}\n'.format(xxpara1))  # from translated sources
                            fout.write('====================================== {}\n'.format(en_el.fname))
                            fout.write('Suggested markup:\n')
                            fout.write('{}\n'.format(xx_el.line.rstrip())) # suggested markup

                        # The suggested markup may be wrong because of non-human processing
                        # implementation that is not perfect. Calculate the difference list
                        # again based on the suggested markup of the translated line.
                        xxlst2 = self.rexBackticked.findall(xx_el.line)
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
                                xx_el.lineno,
                                en_el.fname[1:2],
                                en_el.lineno))

                            # To the report of anomalies insert all values that can
                            # help to spot the problem.
                            fa.write('\t[en] markup               = {} {}\n'.format(len(enlst), repr(enlst)))
                            fa.write('\t[{}] markup               = {} {}\n'.format(self.lang, len(xxlst), repr(xxlst)))
                            fa.write('\tmissing in [{}]           = {} {}\n'.format(self.lang, len(dlst), repr(dlst)))
                            fa.write('\tsuggested [{}] markup     = {} {}\n'.format(self.lang, len(xxlst2), repr(xxlst2)))
                            fa.write('\tmissing in suggested [{}] = {} {}\n'.format(self.lang, len(dlst2), repr(dlst2)))
                            fa.write('\tnumber of suggested replacement in [{}] = {}\n'.format(self.lang, n))
                            fa.write('Original [en]:\n\t{}\n'.format(en_el.line.rstrip()))
                            fa.write('Translation [{}]:\n\t{}\n'.format(self.lang, xxpara1))
                            if n > 0:
                                fa.write('Suggested translation [{}]:\n\t{}\n'.format(self.lang, xx_el.line.rstrip()))
                            fa.write('-'*50 + '\n')

        # Capture the info about the report log files and about the result.
        self.info_lines.append(self.short_name(btfname))
        self.info_lines.append(self.short_name(btfname_skipped))
        self.info_lines.append(('-'*30) + \
                         ' asynchronous backticks: {}'.format(async_cnt))
        self.info_lines.append(self.short_name(btfname_anomaly))
        self.info_lines.append(('-'*30) + \
                         ' backtick anomalies: {}'.format(anomaly_cnt))


    def reportBadDoubleQuotes(self):
        '''Kontroluje použití správných uvozovek v českých elementech.

           V 'para' elementech musí být „takové“, v 'code' elementech
           zase "takové" a v ostatních elementech uvidíme.

           Výsledky zapisuje do pass2dquotes.txt.'''

        cnt = 0         # init -- počet odhalených chyb
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

            for en_el, xx_el in zip(self.en_lst, self.xx_lst):

                # Zpracováváme jen odstavce textu.
                if xx_el.type in ('para', 'li', 'uli', 'imgcaption', 'title'):

                    if rexBadParaQuotes.search(xx_el.line) is not None:

                        # Našla se nevhodná uvozovka. Započítáme ji
                        # a zapíšeme do souboru.
                        cnt += 1

                        f.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                self.lang,
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(xx_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(xx_el.line.rstrip()))

                elif xx_el.type == 'code':

                    if rexBadCodeQuotes.search(xx_el.line) is not None:

                        # Našla se nevhodná uvozovka. Započítáme ji
                        # a zapíšeme do souboru.
                        cnt += 1

                        f.write('\n{} {}/{} -- en {}/{}, {}:\n'.format(
                                self.lang,
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(xx_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(xx_el.line.rstrip()))

                elif xx_el.type not in ('empty', 'img'):
                        # Neznámý typ elementu.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(xx_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(xx_el.line.rstrip()))


        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        self.info_lines.append(self.short_name(fname))
        self.info_lines.append(('-'*30) + \
               ' elements with bad double quotes: {}'.format(cnt))


    def reportEmAndStrong(self):
        '''Sbírá odstavce s *emphasize* a **strong** vyznačením.

           Výsledky zapisuje do pass2em_strong.txt.'''

        cnt = 0         # init -- počet odhalených chyb
        fname = os.path.join(self.xx_aux_dir, 'pass2em_strong.txt')
        fname_diff = os.path.join(self.xx_aux_dir, 'pass2em_strong_diff.txt')

        with open(fname, 'w', encoding='utf-8', newline='\n') as f,\
             open(fname_diff, 'w', encoding='utf-8', newline='\n') as fdiff:

            # Regulární výraz pro jednoduché nebo dvojité hvězdičky.
            rexEmStrong = re.compile(r'([*_]{1,2})([^*_]+?)\1')

            for en_el, xx_el in zip(self.en_lst, self.xx_lst):

                # Pokud jde o typ elementu s běžným textem...
                if xx_el.type in ('para', 'li', 'uli', 'imgcaption', 'title'):

                    # Najdeme všechny označkované řetězce z originálního
                    # a z českého odstavce.
                    enlst = rexEmStrong.findall(en_el.line)
                    xxlst = rexEmStrong.findall(xx_el.line)

                    # Pokud se něco našlo, zobrazíme originál a český vedle sebe.
                    # Pokud se liší počet označkovaných posloupností, započítáme
                    # to jako další problém k vyřešení a zobrazíme podobu odstavců
                    # do souboru s rozdíly.
                    if enlst or xxlst:
                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(xx_el.type)))

                        # Počty označkovaných posloupností.
                        f.write('\t{} : {}\n'.format(len(enlst), len(xxlst)))

                        # Odstavce.
                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(xx_el.line.rstrip()))

                        # Pokud se počet liší, zaznamenáme totéž ještě jednou
                        # do souboru s předpokládanými rozdíly.
                        if len(enlst) != len(xxlst):
                            cnt += 1
                            fdiff.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                        xx_el.fname,
                                        xx_el.lineno,
                                        en_el.fname,
                                        en_el.lineno,
                                        repr(xx_el.type)))

                            # Počty označkovaných posloupností.
                            fdiff.write('\t{} : {}\n'.format(len(enlst), len(xxlst)))

                            # Odstavce.
                            fdiff.write('\t{}\n'.format(en_el.line.rstrip()))
                            fdiff.write('\t{}\n'.format(xx_el.line.rstrip()))

        # Přidáme informaci o provedení kontroly.
        self.info_lines.append(self.short_name(fname))
        self.info_lines.append(self.short_name(fname_diff))
        self.info_lines.append(('-'*30) + \
               ' elements with *em* and **strong**: {}'.format(cnt))


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.checkImages()
        self.fixParaBackticks()
        self.reportBadDoubleQuotes()
        self.reportEmAndStrong()

        return '\n\t'.join(self.info_lines)

