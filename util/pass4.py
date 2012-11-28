#!python3
# -*- coding: utf-8 -*-

import os
import re

class Parser:
    '''Parser pro čtvrtý průchod -- značkování a kontroly.

       Konzumuje výstup třetího průchodu přímo ve formě objektu pass3.'''

    # Regulární výraz pro rozpoznání znaků uzavřených v opačných apostrofech.
    rexBackticked = re.compile(r'`(\S.*?\S?)`')

    def __init__(self, pass3):
        self.cs_aux_dir = pass3.cs_aux_dir    # pomocný adresář pro české výstupy
        self.en_aux_dir = pass3.en_aux_dir    # pomocný adresář pro anglické výstupy

        self.en_lst = pass3.en_lst
        self.cs_lst = pass3.cs_lst

        self.info_files = []
        self.backticked_set = set()


    def checkImages(self):
        sync_flag = True  # optimistická inicializace
        images_fname = os.path.join(self.cs_aux_dir, 'pass4img_diff.txt')
        with open(images_fname, 'w', encoding='utf-8') as f:
            for en_el, cs_el in zip(self.en_lst, self.cs_lst):
                if    en_el.type == 'img' and en_el.attrib != cs_el.attrib \
                   or en_el.type == 'imgcaption' \
                      and en_el.attrib[0] != cs_el.attrib[0]:

                    # Není shoda. Shodíme příznak...
                    sync_flag = False

                    # ... a zapíšeme do souboru.
                    f.write('\ncs {} -- en {}/{}:\n'.format(
                            cs_el.lineno,
                            en_el.fname[1:2],
                            en_el.lineno))

                    # Typ a hodnota českého elementu.
                    f.write('\t{}:\t{}\n'.format(cs_el.type,
                                                 cs_el.line.rstrip()))

                    # Typ a hodnota anglického elementu.
                    f.write('\t{}:\t{}\n'.format(en_el.type,
                                                 en_el.line.rstrip()))

        # Přidáme informaci o synchronnosti obrázků.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass4img_diff.txt')
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

           Výsledky zapisuje do pass4backticks.txt.'''

        anomally_cnt = 0  # init -- počet odhalených anomálií
        btfname = os.path.join(self.cs_aux_dir, 'pass4backticks.txt')
        btfname_anomally = os.path.join(self.cs_aux_dir, 'pass4backticks_anomally.txt')

        # Při řešení anomálií byly některé případy vyřešeny ručně, ale test
        # náhrad by odstavec považoval stále za nevyřešený. Proto číslo řádku
        # s odstavcem musíme přidat mezi přeskakované.
        cs_skip = set([349, 668, 920, 1006, 1015, 1042, 1050, 1218, 1285, 1449,
                       1458, 1728, 
                      ])

        with open(btfname, 'w', encoding='utf-8') as f, \
             open(btfname_anomally, 'w', encoding='utf-8') as fa:
            for en_el, cs_el in zip(self.en_lst, self.cs_lst):

                # Zpracováváme jen odstavce textu. Odstavce vykazující známou
                # anomálii ale přeskakujeme.
                if en_el.type == 'para' and cs_el.lineno not in cs_skip:

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

                        # ... a zapíšeme do souboru.
                        f.write('\ncs {} -- en {}/{}:\n'.format(
                                cs_el.lineno,
                                en_el.fname[1:2],
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
        self.info_files.append(subdir +'/pass4backticks.txt')
        self.info_files.append(subdir +'/pass4backticks_anomally.txt')
        self.info_files.append(('-'*30) + \
                         ' anomálie u zpětných apostrofů: {}'.format(anomally_cnt))


    def writePass4txtFile(self):
        ''' Zapíše strojově modifikovaný soubor do pass4.txt.'''

        with open(os.path.join(self.cs_aux_dir, 'pass4.txt'), 'w',
                  encoding='utf-8') as fout:
            for cs_element in self.cs_lst:
                fout.write(cs_element.line)

        # Přidáme informaci o vytvářeném souboru.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass4.txt')


    def splitToFiles(self):
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
                # takže je přímo připlácneme k "pass3cs/". Dodatečně
                # oddělíme adresář a zajistíme jeho existenci.
                en_fname = en_element.fname
                cs_fname = os.path.join(self.cs_aux_dir, 'pass4cs', en_fname)
                cs_fname = os.path.abspath(cs_fname)

                cs_chapter_dir = os.path.dirname(cs_fname)
                if not os.path.isdir(cs_chapter_dir):
                    os.makedirs(cs_chapter_dir)

                # Otevřeme nový výstupní soubor.
                f = open(cs_fname, 'w', encoding='utf-8')

                # Pro informaci vypíšeme relativní jméno originálu (je stejné
                # jako jméno výstupního souboru, přidáme natvrdo cs/).
                self.info_files.append('.../pass4cs/' + en_fname)

            # Zapíšeme řádek českého elementu.
            f.write(cs_element.line)

        # Uzavřeme soubor s poslední částí knihy.
        f.close()



    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.checkImages()
        self.fixParaBackticks()
        self.writePass4txtFile()
        self.splitToFiles()

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
