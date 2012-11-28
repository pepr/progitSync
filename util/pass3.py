#!python3
# -*- coding: utf-8 -*-

import docelement
import gen
import os

class Parser:
    '''Parser pro třetí průchod, konzumující (ručně upravený) výstup druhého průchodu.'''

    def __init__(self, cs_name_in, en_name_in, cs_aux_dir, en_aux_dir):
        self.cs_name_in = cs_name_in    # jméno vstupního souboru/adresáře s českou verzí
        self.en_name_in = en_name_in    # jméno vstupního souboru/adresáře s anglickou verzí
        self.cs_aux_dir = cs_aux_dir    # pomocný adresář pro české výstupy
        self.en_aux_dir = en_aux_dir    # pomocný adresář pro anglické výstupy

        self.cs_lst = None              # seznam elementů z českého překladu
        self.en_lst = None              # seznam elementů z anglického originálu

        self.info_files = []

    def writePass3txtFiles(self):
        # Kopie českého vstupu do jednoho souboru. Při tomto průchodu
        # pochází z jednoho souboru, takže jméno souboru vynecháme.
        with open(os.path.join(self.cs_aux_dir, 'pass3.txt'), 'w', encoding='utf-8') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.cs_name_in):
                fout.write('{:4d}:\t{}'.format(lineno, line))

        # Kopie anglického vstupu do jednoho souboru. Pro lepší orientaci
        # v dlouhých řádcích nebudeme vypisovat jméno souboru, ale
        # jen číslo kapitoly (jeden znak relativní cesty).
        with open(os.path.join(self.en_aux_dir, 'pass3.txt'), 'w',
                  encoding='utf-8') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_name_in):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Přidáme informaci o vytvářených souborech.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass3.txt')

        subdir = os.path.basename(self.en_aux_dir)        # anglický výstup
        self.info_files.append(subdir +'/pass3.txt')


    def loadElementLists(self):
        '''Načte elementy dokumentů do členských seznamů.

           Jako vedlejší efekt zachytí reprezentaci seznamů elementů
           do souborů pass3elem.txt v pomocných adresářích.'''

        # Elementy z českého překladu do seznamu a do souboru. Do českého
        # překladu jsou vloženy navíc úseky jako vysvětlivky anglického
        # originálu, který byl ponechán v původním tvaru. Při srovnávání
        # struktury se musí přeskočit. Zapíšeme je ale do zvláštního
        # souboru pass3extra_lines.txt. Natvrdo naplníme množinu čísel
        # přeskakovaných řádků.
        cs_skip = set(range(4137, 4154))
        self.cs_lst = []
        with open(os.path.join(self.cs_aux_dir, 'pass3elem.txt'), 'w',
                  encoding='utf-8') as fout, \
             open(os.path.join(self.cs_aux_dir, 'pass3extra_lines.txt'), 'w',
                  encoding='utf-8') as foutextra:
            for relname, lineno, line in gen.sourceFileLines(self.cs_name_in):
                elem = docelement.Element(relname, lineno, line)
                if lineno in cs_skip:
                    # Přeskočíme elementy, které byly doplněny navíc.
                    # Prostě je nepřidáme do seznamu.
                    foutextra.write('{:4d}:\t{}'.format(lineno, line))
                else:
                    self.cs_lst.append(elem)    # tento do seznamu přidáme
                    fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupních souborech.
        subdir = os.path.basename(self.cs_aux_dir)
        self.info_files.append(subdir +'/pass3extra_lines.txt')
        self.info_files.append(subdir +'/pass3elem.txt')

        # Elementy z anglického originálu do seznamu a do souboru.
        self.en_lst = []
        with open(os.path.join(self.en_aux_dir, 'pass3elem.txt'), 'w',
                  encoding='utf-8') as fout:
            for relname, lineno, line in gen.sourceFileLines(self.en_name_in):
                elem = docelement.Element(relname, lineno, line)
                self.en_lst.append(elem)
                fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupním souboru.
        subdir = os.path.basename(self.en_aux_dir)
        self.info_files.append(subdir +'/pass3elem.txt')


    def checkStructDiffs(self):
        '''Generuje cs/pass3struct_diff.txt s rozdíly ve struktuře zdrojových řádků.'''

        sync_flag = True   # optimistická inicializace

        # Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
        # příklady kódu) porovnáváme za účelem zjištění rozdílů struktury -- zde
        # jen typy elementů.
        struct_diff_fname = os.path.join(self.cs_aux_dir, 'pass3struct_diff.txt')
        with open(struct_diff_fname, 'w', encoding='utf-8') as f:

            # Některé příklady jsou přeložené. V nich rozdíly povolíme.
            cs_line_may_differ = set(range(244, 247))
            cs_line_may_differ.update(range(430, 436))
            cs_line_may_differ.update(range(647, 648))
            cs_line_may_differ.update(range(793, 809))
            cs_line_may_differ.update(range(828, 838))
            cs_line_may_differ.update(range(855, 861))
            cs_line_may_differ.update(range(1032, 1033))
            cs_line_may_differ.update(range(2508, 2511))
            cs_line_may_differ.update(range(2933, 2948))
            cs_line_may_differ.update(range(4925, 4930))
            cs_line_may_differ.update(range(4938, 4943))

            for en_element, cs_element in zip(self.en_lst, self.cs_lst):

                # Pro nejhrubší synchronizaci se budeme řídit pouze typy
                # elementů. (Nejméně přísné pravidlo synchronizace.)
                #
                # Pokud se typy shodují, pak přísnější pravidlo
                # synchronizace vyžaduje, aby se shodovaly řádky
                # s příkladem kódu.
                if en_element.type != cs_element.type \
                   or (en_element.type == 'code'
                       and en_element.line.rstrip() != cs_element.line.rstrip()
                       and cs_element.lineno not in cs_line_may_differ):

                    # Není to synchronní; shodíme příznak.
                    sync_flag = False

                    # U cs jen číslo řádku, u en číslo kapitoly/číslo řádku.
                    f.write('\ncs {} -- en {}/{}:\n'.format(
                            cs_element.lineno,
                            en_element.fname[1:2],
                            en_element.lineno))

                    # Typ a hodnota českého elementu.
                    f.write('\t{}:\t{}\n'.format(cs_element.type,
                                                 cs_element.line.rstrip()))

                    # Typ a hodnota anglického elementu.
                    f.write('\t{}:\t{}\n'.format(en_element.type,
                                                 en_element.line.rstrip()))

        # Přidáme informaci o výstupním souboru.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass3struct_diff.txt')

        # Přidáme informaci o synchronnosti.
        self.info_files.append(('-'*40) + ' struktura se ' +
                               ('shoduje' if sync_flag else 'NESHODUJE'))


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.writePass3txtFiles()
        self.loadElementLists()
        self.checkStructDiffs()

        return '\n\t'.join(self.info_files)
