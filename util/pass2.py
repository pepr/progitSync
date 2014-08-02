#!python3
# -*- coding: utf-8 -*-

import os
import re

class Parser:
    '''Parser pro značkování a kontroly.

       Konzumuje výstup prvního průchodu přímo ve formě objektu pass1.'''

    # Regulární výraz pro rozpoznání znaků uzavřených v opačných apostrofech.
    rexBackticked = re.compile(r'`(\S.*?\S?)`')

    def __init__(self, pass1):
        self.cs_aux_dir = pass1.cs_aux_dir    # pomocný adresář pro české výstupy
        self.en_aux_dir = pass1.en_aux_dir    # pomocný adresář pro anglické výstupy

        self.en_lst = pass1.en_lst
        self.cs_lst = pass1.cs_lst

        self.info_files = []
        self.backticked_set = set()


    def checkImages(self):
        sync_flag = True  # optimistická inicializace
        images_fname = os.path.join(self.cs_aux_dir, 'pass2img_diff.txt')
        with open(images_fname, 'w', encoding='utf-8', newline='\n') as f:
            for en_el, cs_el in zip(self.en_lst, self.cs_lst):
                if    en_el.type == 'img' and en_el.attrib != cs_el.attrib \
                   or en_el.type == 'imgcaption' \
                      and en_el.attrib[0] != cs_el.attrib[0]:

                    # Není shoda. Shodíme příznak...
                    sync_flag = False

                    # ... a zapíšeme do souboru.
                    f.write('\ncs {}/{} -- en {}/{}:\n'.format(
                            cs_el.fname,
                            cs_el.lineno,
                            en_el.fname,
                            en_el.lineno))

                    # Typ a hodnota českého elementu.
                    f.write('\t{}:\t{}\n'.format(cs_el.type,
                                                 cs_el.line.rstrip()))

                    # Typ a hodnota anglického elementu.
                    f.write('\t{}:\t{}\n'.format(en_el.type,
                                                 en_el.line.rstrip()))

        # Přidáme informaci o synchronnosti obrázků.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass2img_diff.txt')
        self.info_files.append(('-'*30) + ' informace o obrázcích se ' +
                               ('shodují' if sync_flag else 'NESHODUJÍ'))


    def buildRex(self, lst):
        '''Build a regular expression mathing substrings from the lst.'''

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
        btfname = os.path.join(self.cs_aux_dir, 'pass2backticks.txt')
        btfname_skipped = os.path.join(self.cs_aux_dir, 'pass2backticks_skiped.txt')
        btfname_anomally = os.path.join(self.cs_aux_dir, 'pass2backticks_anomally.txt')

        # Při řešení anomálií byly některé případy vyřešeny ručně, ale test
        # náhrad by odstavec považoval stále za nevyřešený. Proto číslo řádku
        # s odstavcem musíme přidat mezi přeskakované.
        cs_skip = {
            '01-introduction/01-chapter1.markdown':
                set([193, 197, 237, 250]),

            '02-git-basics/01-chapter2.markdown':
                set([92, 424, 763, 850, 886, 894, 1063, 1130]),

            '03-git-branching/01-chapter3.markdown':
                set([18, 68, 77, 355, 392, 394, 423, 433, 459, 475, 481,
                     526, 535, 548]),

            '04-git-server/01-chapter4.markdown':
                set([179, 330, 530]),

            '05-distributed-git/01-chapter5.markdown':
                set([115]),

            '07-customizing-git/01-chapter7.markdown':
                set([463]),

            '08-git-and-other-scms/01-chapter8.markdown':
                set([90, 238, 291, 395]),

            '09-git-internals/01-chapter9.markdown':
                set([30, 332, 336]),

            }

        with open(btfname, 'w', encoding='utf-8', newline='\n') as fout, \
             open(btfname_skipped, 'w', encoding='utf-8', newline='\n') as fskip, \
             open(btfname_anomally, 'w', encoding='utf-8', newline='\n') as fa:

            # Hlavička souboru s problémy. Upozorníme na ignorované odstavce.
            fout.write('Přeskakované odstavce -- viz fixParaBackticks() v pass2.py:\n')
            for k in sorted(cs_skip):
                chapter = k.split('/')[1][3:11]
                fout.write('  {}: {!r}\n'.format(chapter, sorted(cs_skip[k])))
            fout.write('=' * 78 + '\n')

            # Hlavička souboru s odstavci, jejichž porovnávání bylo potlačeno.
            # Někdy bychom ale mohli chtít prohlédnout, jestli je to potlačeno
            # správně.
            fskip.write('Přeskakované odstavce -- viz fixParaBackticks() v pass2.py:\n')
            for k in sorted(cs_skip):
                chapter = k.split('/')[1][3:11]
                fskip.write('  {}: {!r}\n'.format(chapter, sorted(cs_skip[k])))
            fskip.write('=' * 78 + '\n')

            fa.write('Anomálie')
            fa.write('=' * 78 + '\n')

            # V cyklu porovnáme a zpracujeme prvky z obou dokumentů.
            for en_el, cs_el in zip(self.en_lst, self.cs_lst):

                # Zpracováváme jen odstavce textu a testy z odrážek a číslovaných
                # seznamů. Odstavce vykazující známou anomálii ale přeskakujeme.
                if en_el.type in ['para', 'uli', 'li']:

                    if cs_el.lineno not in cs_skip.get(cs_el.fname, {}):
                        f = fout
                        skipped = False
                    else:
                        f = fskip
                        skipped = True

                    # Najdeme všechny symboly uzavřené ve zpětných apostrofech
                    # v originálním odstavci.
                    enlst = self.rexBackticked.findall(en_el.line)
                    cslst = self.rexBackticked.findall(cs_el.line)

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

                        # Započítáme a zapíšeme do souboru.
                        if not skipped:
                            async_cnt += 1
                        f.write('\ncs {}/{} -- en {}/{}:\n'.format(
                                cs_el.fname,
                                cs_el.lineno,
                                en_el.fname,
                                en_el.lineno))

                        # Český odstavec před úpravou.
                        cspara1 = cs_el.line.rstrip()

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
                            cs_el.line, n = rex.subn(r'`\g<0>`', cs_el.line)

                        # Do souboru f zapisujeme záznam o všech nahrazovaných.
                        # Rozdílový seznam a jeho délka, anglický odstavec,
                        # český odstavec před náhradou a po ní.
                        f.write('\t{}\n'.format(repr(dlst)))
                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(cspara1))
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))

                        # Znovu zjistíme počet obalených podřetězců v českém
                        # odstavci. Znovu vypočítáme rozdílový seznam.
                        cslst2 = self.rexBackticked.findall(cs_el.line)
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
                                cs_el.lineno,
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
                            fa.write('\t{}\n'.format(cs_el.line.rstrip()))

        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass2backticks.txt')
        self.info_files.append(subdir +'/pass2backticks_skiped')
        self.info_files.append(('-'*30) + \
                         ' nesynchronnost zpětných apostrofů: {}'.format(async_cnt))
        self.info_files.append(subdir +'/pass2backticks_anomally.txt')
        self.info_files.append(('-'*30) + \
                         ' anomálie u zpětných apostrofů: {}'.format(anomally_cnt))


    def reportBadDoubleQuotes(self):
        '''Kontroluje použití zprávných uvozovek v českých elementech.

           V 'para' elementech musí být „takové“, v 'code' elementech
           zase "takové" a v ostatních elementech uvidíme.

           Výsledky zapisuje do pass2dquotes.txt.'''

        cnt = 0         # init -- počet odhalených chyb
        fname = os.path.join(self.cs_aux_dir, 'pass2dquotes.txt')

        with open(fname, 'w', encoding='utf-8', newline='\n') as f:

            # Regulární výraz pro nevhodné uvozovky v odstavcích.
            rexBadParaQuotes = re.compile(r'["”]')  # české musí být „takhle“
            rexBadCodeQuotes = re.compile(r'[„“”]')

            for en_el, cs_el in zip(self.en_lst, self.cs_lst):

                # Zpracováváme jen odstavce textu.
                if cs_el.type in ('para', 'li', 'uli', 'imgcaption', 'title'):

                    if rexBadParaQuotes.search(cs_el.line) is not None:

                        # Našla se nevhodná uvozovka. Započítáme ji
                        # a zapíšeme do souboru.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                cs_el.fname,
                                cs_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(cs_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))

                elif cs_el.type == 'code':

                    if rexBadCodeQuotes.search(cs_el.line) is not None:

                        # Našla se nevhodná uvozovka. Započítáme ji
                        # a zapíšeme do souboru.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                cs_el.fname,
                                cs_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(cs_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))

                elif cs_el.type not in ('empty', 'img'):
                        # Neznámý typ elementu.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                cs_el.fname,
                                cs_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(cs_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))


        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass2dquotes.txt')
        self.info_files.append(('-'*30) + \
               ' elementy s chybnými uvozovkami: {}'.format(cnt))


    def reportEmAndStrong(self):
        '''Sbírá odstavce s *emphasize* a **strong** vyznačením.

           Výsledky zapisuje do pass2em_strong.txt.'''

        cnt = 0         # init -- počet odhalených chyb
        fname = os.path.join(self.cs_aux_dir, 'pass2em_strong.txt')

        with open(fname, 'w', encoding='utf-8', newline='\n') as f:

            # Regulární výraz pro jednoduché nebo dvojité hvězdičky.
            rexEmStrong = re.compile(r'(\*{1,2})(\S.*?\S?)\1')

            for en_el, cs_el in zip(self.en_lst, self.cs_lst):

                # Zpracováváme jen odstavce textu.
                if cs_el.type in ('para', 'li', 'uli', 'imgcaption', 'title'):

                    if rexEmStrong.search(cs_el.line) is not None:

                        # Našlo se vyznačení.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, {}:\n'.format(
                                cs_el.fname,
                                cs_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(cs_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))

                elif cs_el.type not in ('empty', 'img', 'code'):
                        # Neznámý typ elementu.
                        cnt += 1

                        f.write('\ncs {}/{} -- en {}/{}, neznámý element {}:\n'.format(
                                cs_el.fname,
                                cs_el.lineno,
                                en_el.fname,
                                en_el.lineno,
                                repr(cs_el.type)))

                        f.write('\t{}\n'.format(en_el.line.rstrip()))
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))


        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass2em_strong.txt')
        self.info_files.append(('-'*30) + \
               ' elementy s *em* a **strong**: {}'.format(cnt))


    def writePass2txtFile(self):
        ''' Zapíše strojově modifikovaný soubor do pass2.txt.'''

        with open(os.path.join(self.cs_aux_dir, 'pass2.txt'), 'w',
                  encoding='utf-8', newline='\n') as fout:
            for cs_element in self.cs_lst:
                fout.write(cs_element.line)

        # Přidáme informaci o vytvářeném souboru.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass2.txt')


    def splitToChapterFiles(self):
        '''Jediný vstupní cs soubor do více souborů s cílovou strukturou.

           Využívá se informací z načtených seznamů elementů.
           '''

        assert len(self.cs_lst) > 0
        assert len(self.en_lst) > 0

        en_fname = None
        cs_fname = None
        f = None
        for en_element, cs_element in zip(self.en_lst, self.cs_lst):
            # Při změně souboru originálu uzavřeme původní, zajistíme
            # existenci cílového adresáře a otevřeme nový výstupní soubor.
            if en_element.fname != en_fname:
                # Pokud byl otevřen výstupní soubor, uzavřeme jej.
                if f is not None:
                    f.close()

                # Zachytíme jméno anglického originálu a trochu je zneužijeme.
                # Obsahuje relativní cestu vůči podadresáři "en/" originálu,
                # takže je přímo připlácneme k "pass2cs/". Dodatečně
                # oddělíme adresář a zajistíme jeho existenci.
                en_fname = en_element.fname
                cs_fname = os.path.join(self.cs_aux_dir, 'pass2cs', en_fname)
                cs_fname = os.path.abspath(cs_fname)

                cs_chapter_dir = os.path.dirname(cs_fname)
                if not os.path.isdir(cs_chapter_dir):
                    os.makedirs(cs_chapter_dir)

                # Otevřeme nový výstupní soubor.
                f = open(cs_fname, 'w', encoding='utf-8', newline='\n')

                # Pro informaci vypíšeme relativní jméno originálu (je stejné
                # jako jméno výstupního souboru, ale v jiném adresáři).
                self.info_files.append('.../pass2cs/' + en_fname)

            # Zapíšeme řádek českého elementu.
            f.write(cs_element.line)

        # Uzavřeme soubor s poslední částí knihy.
        f.close()



    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.checkImages()
        self.fixParaBackticks()
        self.reportBadDoubleQuotes()
        self.reportEmAndStrong()
        self.writePass2txtFile()
        self.splitToChapterFiles()

        return '\n\t'.join(self.info_files)

    #
    # Hledáme značkování uvnitř 'para' elementů. U některých podřetězců můžeme
    # do českého překladu doplnit značkování přímo:
    #  - opačné apostrofy obalují úryvky kódu, který by měl být převzatý 1:1,
    #  - kontrolujeme výskyt podřetězců v opačných apostrofech v cs,
    #  - plníme množinu podřetězců v opačných apostrofech (zapíšeme seřazené
    #    do souboru),
    #  - navrhneme doplnění opačných apostrofů i do míst, kde jsou v originále
    #    zapomenuty (není jasné, co vše se najde; zatím do odděleného souboru),
    #  - obyčejné dvojité uvozovky měníme na české (? -- zatím do odděleného souboru),
    #
    # Další typy značkování jen nahlásíme a budeme asi doplňovat ručně
    # (kurzíva, tučné, ...).
    #
    # V 'para' kontrolovat správnost odkazů na obrázky (vůči originálu).
