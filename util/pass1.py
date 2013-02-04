#!python3
# -*- coding: utf-8 -*-

import docelement
import gen
import os

class Parser:
    '''Parser konzumující již dříve synchronizované české a anglické
       vstupy přímo z adresáře progit/en a progit/cs.'''

    def __init__(self, cs_name_in, en_name_in, cs_aux_dir, en_aux_dir):
        self.cs_name_in = cs_name_in    # jméno vstupního souboru/adresáře s českou verzí
        self.en_name_in = en_name_in    # jméno vstupního souboru/adresáře s anglickou verzí
        self.cs_aux_dir = cs_aux_dir    # pomocný adresář pro české výstupy
        self.en_aux_dir = en_aux_dir    # pomocný adresář pro anglické výstupy

        self.cs_lst = None              # seznam elementů z českého překladu
        self.en_lst = None              # seznam elementů z anglického originálu

        self.info_files = []

    def writePass1txtFiles(self):
        # Kopie českého vstupu do jednoho souboru. Při tomto průchodu
        # pochází z jednoho souboru, takže jméno souboru vynecháme.
        with open(os.path.join(self.cs_aux_dir, 'pass1.txt'), 'w',
                  encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.cs_name_in):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Kopie anglického vstupu do jednoho souboru. Pro lepší orientaci
        # v dlouhých řádcích nebudeme vypisovat jméno souboru, ale
        # jen číslo kapitoly (jeden znak relativní cesty).
        with open(os.path.join(self.en_aux_dir, 'pass1.txt'), 'w',
                  encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_name_in):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Přidáme informaci o vytvářených souborech.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass1.txt')

        subdir = os.path.basename(self.en_aux_dir)        # anglický výstup
        self.info_files.append(subdir +'/pass1.txt')


    def loadElementLists(self):
        '''Načte elementy dokumentů do členských seznamů.

           Jako vedlejší efekt zachytí reprezentaci seznamů elementů
           do souborů pass1elem.txt v pomocných adresářích.'''

        # Elementy z českého překladu do seznamu a do souboru. Do českého
        # překladu jsou vloženy navíc úseky jako vysvětlivky anglického
        # originálu, který byl ponechán v původním tvaru. Při srovnávání
        # struktury se musí přeskočit. Zapíšeme je ale do zvláštního
        # souboru pass1extra_lines.txt. Natvrdo naplníme slovník množin
        # čísel přeskakovaných řádků pro jednotlivé kapitoly.
        cs_skip = {
            '06-git-tools/01-chapter6.markdown':
                set(range(396, 413))
            }
        self.cs_lst = []
        with open(os.path.join(self.cs_aux_dir, 'pass1elem.txt'), 'w',
                  encoding='utf-8', newline='\n') as fout, \
             open(os.path.join(self.cs_aux_dir, 'pass1extra_lines.txt'), 'w',
                  encoding='utf-8', newline='\n') as foutextra:
            for relname, lineno, line in gen.sourceFileLines(self.cs_name_in):
                elem = docelement.Element(relname, lineno, line)
                if lineno in cs_skip.get(relname, {}):
                    # Přeskočíme elementy, které byly doplněny navíc.
                    # Prostě je nepřidáme do seznamu.
                    foutextra.write('{:4d}:\t{}'.format(lineno, line))
                else:
                    self.cs_lst.append(elem)    # tento do seznamu přidáme
                    fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupních souborech.
        subdir = os.path.basename(self.cs_aux_dir)
        self.info_files.append(subdir +'/pass1extra_lines.txt')
        self.info_files.append(subdir +'/pass1elem.txt')

        # Elementy z anglického originálu do seznamu a do souboru.
        self.en_lst = []
        with open(os.path.join(self.en_aux_dir, 'pass1elem.txt'), 'w',
                  encoding='utf-8', newline='\n') as fout:
            for relname, lineno, line in gen.sourceFileLines(self.en_name_in):
                elem = docelement.Element(relname, lineno, line)
                self.en_lst.append(elem)
                fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupním souboru.
        subdir = os.path.basename(self.en_aux_dir)
        self.info_files.append(subdir +'/pass1elem.txt')


    def checkStructDiffs(self):
        '''Generuje cs/pass1struct_diff.txt s rozdíly ve struktuře zdrojových řádků.'''

        sync_flag = True   # optimistická inicializace

        # Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
        # příklady kódu) porovnáváme za účelem zjištění rozdílů struktury -- zde
        # jen typy elementů.
        struct_diff_fname = os.path.join(self.cs_aux_dir, 'pass1struct_diff.txt')
        with open(struct_diff_fname, 'w',
                  encoding='utf-8', newline='\n') as f:

            # Některé příklady jsou přeložené. V nich rozdíly povolíme.
            cs_line_may_differ = {
                '01-introduction/01-chapter1.markdown':
                    set([246, 247, 248]),

                '02-git-basics/01-chapter2.markdown':
                    set([172, 173, 174, 175, 176, 177, 389])
                        .union(range(535, 551))
                        .union(range(570, 580))
                        .union(range(597, 603))
                        .union([774]),

                '04-git-server/01-chapter4.markdown':
                    set([528, 529, 530]),

                '05-distributed-git/01-chapter5.markdown':
                    set([90, 92, 93, 94, 95, 96, 97, 99, 101, 103, 104]),

                '07-customizing-git/01-chapter7.markdown':
                    set([40, 42, 44, 53, 55, 57]),

              }

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
                       and cs_element.lineno not in cs_line_may_differ.get(cs_element.fname, {})):

                    # Není to synchronní; shodíme příznak.
                    sync_flag = False

                    # U obou jméno souboru/číslo řádku.
                    f.write('\ncs {}/{} -- en {}/{}:\n'.format(
                            cs_element.fname,
                            cs_element.lineno,
                            en_element.fname,
                            en_element.lineno))

                    # Typ a hodnota českého elementu.
                    f.write('\t{}:\t{}\n'.format(cs_element.type,
                                                 cs_element.line.rstrip()))

                    # Typ a hodnota anglického elementu.
                    f.write('\t{}:\t{}\n'.format(en_element.type,
                                                 en_element.line.rstrip()))

        # Přidáme informaci o výstupním souboru.
        subdir = os.path.basename(self.cs_aux_dir)        # český výstup
        self.info_files.append(subdir +'/pass1struct_diff.txt')

        # Přidáme informaci o synchronnosti.
        self.info_files.append(('-'*40) + ' struktura se ' +
                               ('shoduje' if sync_flag else 'NESHODUJE'))


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.writePass1txtFiles()
        self.loadElementLists()
        self.checkStructDiffs()

        return '\n\t'.join(self.info_files)
