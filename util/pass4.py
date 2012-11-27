#!python3
# -*- coding: utf-8 -*-

import os
import re

class Parser:
    '''Parser pro čtvrtý průchod -- značkování a kontroly.

       Konzumuje výstup třetího průchodu přímo ve formě objektu pass3.'''

    # Regulární výraz pro rozpoznání znaků uzavřených v opačných apostrofech.
    rexBackticked = re.compile(r'`(?P<txt>\S.*?\S?)`')

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
                    lst = self.rexBackticked.findall(en_el.line)
                    
                    if len(lst) > 0:
                        f.write(repr(lst))

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

        # Přidáme informaci o synchronnosti použití zpětných apostrofů.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass4backticks.txt')
        self.info_files.append(('-'*30) + ' použití zpětných apostrofů se ' +
                               ('shoduje' if sync_flag else 'NESHODUJE'))
        

    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.checkImages()
        self.checkParaBackticks()
        
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
