#!python3
# -*- coding: utf-8 -*-

import os
import re


def short_name(fname):
    '''Vrací jméno pro log -- jen poslední podadresář s holým jménem.'''
    path, name = os.path.split(fname)
    subdir = os.path.basename(path)
    return '/'.join((subdir, name))


class Parser:
    '''Parser pro značkování a kontroly.

       Konzumuje výstup prvního průchodu přímo ve formě objektu pass1.'''

    # Regulární výraz pro rozpoznání znaků uzavřených v opačných apostrofech.
    rexBackticked = re.compile(r'`(\S.*?\S?)`')

    def __init__(self, pass1):
        self.lang = pass1.lang
        self.en_aux_dir = pass1.en_aux_dir  # pomocný adresář pro anglické výstupy
        self.xx_aux_dir = pass1.xx_aux_dir  # pomocný adresář pro české výstupy

        self.en_lst = pass1.en_lst
        self.xx_lst = pass1.xx_lst

        self.info_lines = []                # sběr řádků pro logování
        self.backticked_set = set()


    def checkImages(self):
        sync_flag = True  # optimistická inicializace
        images_fname = os.path.join(self.xx_aux_dir, 'pass2img_diff.txt')
        with open(images_fname, 'w', encoding='utf-8', newline='\n') as f:
            for en_el, xx_el in zip(self.en_lst, self.xx_lst):
                if    en_el.type == 'img' and en_el.attrib != xx_el.attrib \
                   or en_el.type == 'imgcaption' \
                      and en_el.attrib[0] != xx_el.attrib[0]:

                    # Není shoda. Shodíme příznak...
                    sync_flag = False

                    # ... a zapíšeme do souboru.
                    f.write('\ncs {}/{} -- en {}/{}:\n'.format(
                            xx_el.fname,
                            xx_el.lineno,
                            en_el.fname,
                            en_el.lineno))

                    # Typ a hodnota českého elementu.
                    f.write('\t{}:\t{}\n'.format(xx_el.type,
                                                 xx_el.line.rstrip()))

                    # Typ a hodnota anglického elementu.
                    f.write('\t{}:\t{}\n'.format(en_el.type,
                                                 en_el.line.rstrip()))

        # Přidáme informaci o synchronnosti obrázků.
        self.info_lines.append(short_name(images_fname))
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
        '''Kontroluje synchronnost použití zpětných apostrofů v 'para' elementech.

           Výsledky zapisuje do pass2backticks.txt.'''

        async_cnt = 0     # init -- počet nesynchronních výskytů
        anomally_cnt = 0  # init -- počet odhalených anomálií
        btfname = os.path.join(self.xx_aux_dir, 'pass2backticks.txt')
        btfname_skipped = os.path.join(self.xx_aux_dir, 'pass2backticks_skiped.txt')
        btfname_anomally = os.path.join(self.xx_aux_dir, 'pass2backticks_anomally.txt')

        # Při synchronizaci originálu s překladem je některé případy nutné
        # ošetřit jako výjimky. Dřívější implementace využívala
        # přeskakování těchto úseků uvedením řádků (odstavců) ve zdrojovém
        # textu. Problémy nastávají, když se originál mění a čísla přeskakovaných
        # řádků je nutné upravovat. Proto se nově buduje "překladový slovník"
        # těchto úseků z definičního souboru, kde řádek-odstavec uvádí
        # anglický originál, oddělovač s nejméně pěti pomlčkami
        # od začátku řádku, český překlad a oddělovač
        # s nejméně pěti rovnítky. Pomocný slovník používá první řádek
        # z originálu jako klíč překlad jako hodnotu.
        path, scriptname = os.path.split(__file__)
        backtick_exceptions_fname =  os.path.join(path, 
                                     '{}_backtick_exceptions.txt'.format(self.lang))
        backtick_exceptions = {}
        status = 0
        original = None
        with open(backtick_exceptions_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    original = line     # bude později klíčem
                    status = 1

                elif status == 1:
                    assert line.startswith('-----')
                    status = 2

                elif status == 2:
                    backtick_exceptions[original] = line    # překlad originálu
                    original = None
                    status = 3

                elif status == 3:
                    assert line.startswith('=====')
                    status = 0

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Přidáme informaci o souboru s definicemi.
        self.info_lines.append(short_name(backtick_exceptions_fname))

        with open(btfname, 'w', encoding='utf-8', newline='\n') as fout, \
             open(btfname_skipped, 'w', encoding='utf-8', newline='\n') as fskip, \
             open(btfname_anomally, 'w', encoding='utf-8', newline='\n') as fa:

            # V cyklu porovnáme a zpracujeme prvky z obou dokumentů.
            for en_el, xx_el in zip(self.en_lst, self.xx_lst):

                # Zpracováváme jen odstavce textu a testy z odrážek a číslovaných
                # seznamů. Odstavce vykazující známou anomálii ale přeskakujeme.
                if en_el.type in ['para', 'uli', 'li']:

                    # Nastavíme příznak přeskakování.
                    skipped = xx_el.line == backtick_exceptions.get(en_el.line, '!@#$%^&*')

                    # Najdeme všechny symboly uzavřené ve zpětných apostrofech
                    # v originálním odstavci.
                    enlst = self.rexBackticked.findall(en_el.line)
                    cslst = self.rexBackticked.findall(xx_el.line)

                    # Nestačí porovnávat délky seznamů, protože seznamy mohou
                    # obsahovat různé sekvence (což se díky modifikaci textu
                    # stalo). Proto musíme porovnat množiny. Ale nestačí porovnat
                    # jen množiny, protože některý seznam by mohl být delší
                    # (opakoval by se nějaký řetězec). Ostatní situace považujeme
                    # za málo pravděpodobné.
                    if set(enlst) != set(cslst) or len(enlst) != len(cslst):

                        # Vytvoříme rozdílový seznam, do kterého vložíme
                        # jen řetězce, které jsou v en navíc. To znamená,
                        # že z anglického seznamu odstraníme ty, které už
                        # jsou v českém odstavci označkované.
                        dlst = enlst[:]   # kopie
                        for s in cslst:
                            if s in dlst:
                                dlst.remove(s)

                        # Nepřeskakované odstavce započítáme,
                        # zapíšeme do příslušného souboru.
                        if skipped:
                            fskip.write('\ncs {}/{} -- en {}/{}:\n'.format(
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno))
                        else:
                            async_cnt += 1
                            fout.write('\ncs {}/{} -- en {}/{}:\n'.format(
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno))

                        # Český odstavec před úpravou.
                        cspara1 = xx_el.line.rstrip()

                        # Pokud je rozdílový seznam prázdný, nechceme nic
                        # nahrazovat. Vzhledem k dalšímu způsobu ani nesmíme
                        # nic nahrazovat, protože by se zkonstruoval nevhodný
                        # regulární výraz, který by způsobil obalení kde čeho.
                        # Náhradu tedy provádět nebudeme, ale považujeme to
                        # stále za anomálii, která musí být zkontrolována.
                        # V opačném případě vybudujeme regulární výraz
                        # a provedeme náhradu. Zjišťujeme také, kolik náhrad
                        # proběhlo.
                        n = 0            # init
                        if len(dlst) != 0:
                            rex = self.buildRex(dlst)
                            xx_el.line, n = rex.subn(r'`\g<0>`', xx_el.line)

                        # Do příslušného souboru zapisujeme záznam o všech nahrazovaných.
                        # Rozdílový seznam, anglický odstavec,
                        # český odstavec před náhradou a po ní.
                        if skipped:
                            fskip.write('{}\n'.format(repr(dlst)))
                            fskip.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                            fskip.write('{}\n'.format(en_el.line.rstrip()))
                            fskip.write('---------------\n')
                            fskip.write('{}\n'.format(cspara1))
                            fskip.write('====================================== {}\n'.format(en_el.fname))
                        else:
                            fout.write('{}\n'.format(repr(dlst)))
                            fout.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                            fout.write('{}\n'.format(en_el.line.rstrip()))
                            fout.write('---------------\n')
                            fout.write('{}\n'.format(cspara1))
                            fout.write('====================================== {}\n'.format(en_el.fname))
                            fout.write('{}\n'.format(xx_el.line.rstrip()))

                        # Znovu zjistíme počet obalených podřetězců v českém
                        # odstavci. Znovu vypočítáme rozdílový seznam.
                        cslst2 = self.rexBackticked.findall(xx_el.line)
                        dlst2 = enlst[:]   # kopie
                        for s in cslst2:
                            if s in dlst2:
                                dlst2.remove(s)

                        # Anomálie nastává, pokud nastává alespoň jeden z případů:
                        # - liší se množiny podřetězců v originále a v překladu,
                        # - rozdílový seznam je neprázdný (tj. v překladu nebylo
                        #   něco obaleno),
                        # - liší se délky seznamů v originále a v překladu (tj.
                        #   v překladu bylo obaleno jiné množství podřetězců),
                        # - počet provedených náhrad je větší než délka původního
                        #   rozdílového seznamu (může být redundantní vůči ostatním
                        #   bodům).
                        if set(enlst) != set(cslst2) or len(dlst2) > 0 \
                           or len(enlst) != len(cslst2) or len(dlst) != n:

                            # Za neshodu při synchronizaci považujeme pouze
                            # vznik anomálie -- započítáme další anomálii.
                            if not skipped:
                                anomally_cnt += 1

                            # Zapíšeme do souboru s anomáliemi.
                            fa.write('\ncs {} -- en {}/{}:\n'.format(
                                xx_el.lineno,
                                en_el.fname[1:2],
                                en_el.lineno))

                            # Do souboru f zapisujeme záznam o všech nahrazovaných.
                            # Rozdílový seznam a jeho délka, anglický odstavec,
                            # český odstavec před náhradou a po ní.
                            fa.write('\tenlst  = {} {}\n'.format(len(enlst), repr(enlst)))
                            fa.write('\tcslst  = {} {}\n'.format(len(cslst), repr(cslst)))
                            fa.write('\tdslst  = {} {}\n'.format(len(dlst), repr(dlst)))
                            fa.write('\tcslst2 = {} {}\n'.format(len(cslst2), repr(cslst2)))
                            fa.write('\tdslst2 = {} {}\n'.format(len(dlst2), repr(dlst2)))
                            fa.write('\tsubn   = {}\n'.format(n))
                            fa.write('\t{}\n'.format(en_el.line.rstrip()))
                            fa.write('\t{}\n'.format(cspara1))
                            fa.write('\t{}\n'.format(xx_el.line.rstrip()))

        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        self.info_lines.append(short_name(btfname))
        self.info_lines.append(short_name(btfname_skipped))
        self.info_lines.append(('-'*30) + \
                         ' asynchronous backticks: {}'.format(async_cnt))
        self.info_lines.append(short_name(btfname_anomally))
        self.info_lines.append(('-'*30) + \
                         ' backtick anomalies: {}'.format(anomally_cnt))


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
                rexBadParaQuotes = re.compile(r'["”]')  # Czech ones must be „this way“
            else:
                rexBadParaQuotes = re.compile(r'["”]')  # Czech ones must be „this way“
                
            for en_el, xx_el in zip(self.en_lst, self.xx_lst):

                # Zpracováváme jen odstavce textu.
                if xx_el.type in ('para', 'li', 'uli', 'imgcaption', 'title'):

                    if rexBadParaQuotes.search(xx_el.line) is not None:

                        # Našla se nevhodná uvozovka. Započítáme ji
                        # a zapíšeme do souboru.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
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

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
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
        self.info_lines.append(short_name(fname))
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
                    cslst = rexEmStrong.findall(xx_el.line)

                    # Pokud se něco našlo, zobrazíme originál a český vedle sebe.
                    # Pokud se liší počet označkovaných posloupností, započítáme
                    # to jako další problém k vyřešení a zobrazíme podobu odstavců
                    # do souboru s rozdíly.
                    if enlst or cslst:
                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                xx_el.fname,
                                xx_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(xx_el.type)))

                        # Počty označkovaných posloupností.
                        f.write('\t{} : {}\n'.format(len(enlst), len(cslst)))

                        # Odstavce.
                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(xx_el.line.rstrip()))

                        # Pokud se počet liší, zaznamenáme totéž ještě jednou
                        # do souboru s předpokládanými rozdíly.
                        if len(enlst) != len(cslst):
                            cnt += 1
                            fdiff.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                        xx_el.fname,
                                        xx_el.lineno,
                                        en_el.fname,
                                        en_el.lineno,
                                        repr(xx_el.type)))

                            # Počty označkovaných posloupností.
                            fdiff.write('\t{} : {}\n'.format(len(enlst), len(cslst)))

                            # Odstavce.
                            fdiff.write('\t{}\n'.format(en_el.line.rstrip()))
                            fdiff.write('\t{}\n'.format(xx_el.line.rstrip()))

        # Přidáme informaci o provedení kontroly.
        self.info_lines.append(short_name(fname))
        self.info_lines.append(short_name(fname_diff))
        self.info_lines.append(('-'*30) + \
               ' elements with *em* and **strong**: {}'.format(cnt))


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.checkImages()
        self.fixParaBackticks()
        self.reportBadDoubleQuotes()
        self.reportEmAndStrong()

        return '\n\t'.join(self.info_lines)

