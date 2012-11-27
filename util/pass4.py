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
        # The order is not important.
        lst2 = [re.escape(s) for s in set(lst)]
        
        # Join the escaped substrings to form the regular expression 
        # pattern, build the regular expression, and return it.
        pat = '|'.join(lst2)
        rex = re.compile(pat)
        return rex
        

    def checkParaBackticks(self):
        '''Kontroluje synchronnost použití zpětných apostrofů v 'para' elementech.

           Výsledky zapisuje do pass4backticks.txt.'''

        sync_flag = True  # optimistická inicializace
        images_fname = os.path.join(self.cs_aux_dir, 'pass4backticks.txt')
        with open(images_fname, 'w', encoding='utf-8') as f:
            for en_el, cs_el in zip(self.en_lst, self.cs_lst):

                # Zpracováváme jen odstavce textu.
                if en_el.type == 'para':

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

                        # Není shoda. Shodíme příznak...
                        sync_flag = False

                        # ... a zapíšeme do souboru.
                        f.write('\ncs {} -- en {}/{}:\n'.format(
                                cs_el.lineno,
                                en_el.fname[1:2],
                                en_el.lineno))

                        # Nalezené posloupnosti symbolů.
                        #f.write('\t' + repr(cslst) + '\n')
                        #f.write('\t' + repr(enlst) + '\n')
                        f.write('\t' + repr(dlst) + '\n')

                        # Anglický odstavec.
                        f.write('\t{}\n'.format(en_el.line.rstrip()))

                        # Český odstavec před úpravou.
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))

                        rex = self.buildRex(dlst)
                        cs_el.line, n = rex.subn(r'`\g<0>`', cs_el.line)

                        # Projdeme rozdílový seznam dosud neoznačkovaných řetězců
                        # a jeden po druhém je v řádku obalíme.
                        if False:
                            line = cs_el.line
                            for s in set(dlst):
                                replacement = '`' + s + '`'
                                line = line.replace(s, replacement)
                            cs_el.line = line

                        # Český odstavec po úpravě.
                        f.write('\t{}\n'.format(cs_el.line.rstrip()))


        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass4backticks.txt')
        self.info_files.append(('-'*30) + ' použití zpětných apostrofů se ' +
                               ('shoduje' if sync_flag else 'NESHODUJE'))


    def writePass4txtFile(self):
        ''' Zapíše strojově modifikovaný soubor do pass4.txt.'''

        with open(os.path.join(self.cs_aux_dir, 'pass4.txt'), 'w',
                  encoding='utf-8') as fout:
            for cs_element in self.cs_lst:
                fout.write(cs_element.line)

        # Přidáme informaci o vytvářeném souboru.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass4.txt')



    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.checkImages()
        self.checkParaBackticks()
        self.writePass4txtFile()

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
