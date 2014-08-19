#!python3
# -*- coding: utf-8 -*-

import docelement
import gen
import os

def short_name(fname):
    '''Vrací jméno pro log -- jen poslední podadresář s holým jménem.'''
    path, name = os.path.split(fname)
    subdir = os.path.basename(path)
    return '/'.join((subdir, name))


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

        self.info_lines = []            # sběr informačních řádků pro stdout

    def writePass1txtFiles(self):
        # Kopie českého vstupu do jednoho souboru. Při tomto průchodu
        # pochází z jednoho souboru, takže jméno souboru vynecháme.
        cs_single_fname = os.path.join(self.cs_aux_dir, 'pass1.txt')
        with open(cs_single_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.cs_name_in):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Kopie anglického vstupu do jednoho souboru. Pro lepší orientaci
        # v dlouhých řádcích nebudeme vypisovat jméno souboru, ale
        # jen číslo kapitoly (jeden znak relativní cesty).
        en_single_fname = os.path.join(self.en_aux_dir, 'pass1.txt')
        with open(en_single_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_name_in):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Přidáme informaci o vytvářených souborech.
        self.info_lines.append(short_name(cs_single_fname))
        self.info_lines.append(short_name(en_single_fname))


    def loadElementLists(self):
        '''Načte elementy dokumentů do členských seznamů.

           Jako vedlejší efekt zachytí reprezentaci seznamů elementů
           do souborů pass1elem.txt v pomocných adresářích.'''

        # Elementy z českého překladu do seznamu a do souboru. Do českého
        # překladu jsou vloženy navíc úseky jako vysvětlivky anglického
        # originálu, který byl ponechán v původním tvaru. Při srovnávání
        # struktury se musí přeskočit -- nevkládají se do seznamu českých
        # elementů. Pro účely detekce přeskakovaných úseků si vybudujeme
        # slovník seznamů řádků podle obsahu souboru s extra řádky, který
        # je uložen v adresáři s tímto skriptem/modulem. Klíčem slovníku
        # je první řádek z takové posloupnosti.
        path, scriptname = os.path.split(__file__)
        cs_def_extras_fname = os.path.join(path, 'cs_def_extras.txt')
        cs_extras = {}
        status = 0
        lst = None
        with open(cs_def_extras_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # První řádek bude klíčem slovníku, získáme odkaz
                    # na seznam řádků.
                    lst = cs_extras.setdefault(line, [])
                    assert len(lst) == 0

                    lst.append(line)
                    status = 1

                elif status == 1:
                    # Druhý a další řádek nebo konec posloupnosti
                    if line.startswith('====='):    # minimálně 5
                        lst = None
                        status = 0
                    else:
                        lst.append(line)

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Přidáme informaci o souboru s definicemi.
        self.info_lines.append(short_name(cs_def_extras_fname))

        # Procházíme elementy. Pokud narazíme na řádek, který zahajuje
        # vynechávanou posloupnost, začneme porovnávat další řádky.
        # Pokud nejde o vynechávanou posloupnost, zpracováváme řádky
        # normálně, pokud jde, přeskočíme ji, ale zapíšeme vše do
        # pass1extra_lines.txt. Kvůli backtrackingu načteme nejdříve
        # všechny elementy do seznamu.
        self.cs_lst = []
        for relname, lineno, line in gen.sourceFileLines(self.cs_name_in):
            elem = docelement.Element(relname, lineno, line)
            self.cs_lst.append(elem)

        cs_elem_fname = os.path.join(self.cs_aux_dir, 'pass1elem.txt')
        cs_extra_fname = os.path.join(self.cs_aux_dir, 'pass1extra_lines.txt')
        with open(cs_elem_fname, 'w', encoding='utf-8', newline='\n') as fout, \
             open(cs_extra_fname, 'w', encoding='utf-8', newline='\n') as foutextra:

            index = 0       # index zpracovávaného elementu
            while index < len(self.cs_lst):  # pozor, délka se dynamicky mění
                elem = self.cs_lst[index]

                if elem.line in cs_extras:
                    # Mohla by to být vložená (extra) posloupnost.
                    # Porovnáme řádky v délce extra posloupnosti.
                    e_lines = [e.line for e in self.cs_lst[index:index+len(cs_extras[elem.line])]]
                    if e_lines == cs_extras[elem.line]:
                        # Zaznamenáme přeskočené řádky.
                        foutextra.write('{}/{}:\n'.format(elem.fname, elem.lineno))
                        foutextra.write('\n'.join(e_lines))
                        foutextra.write('\n====================\n\n')

                        # Přeskočené řádky vypustíme ze seznamu elementů.
                        del self.cs_lst[index:index+len(cs_extras[elem.line])]

                        # Index posuneme o jeden zpět, protože se posloupnost
                        # vypustila a index se bude zvyšovat o jedničku.
                        index -= 1

                # Posuneme se na další element, který se má zpracovat.
                # Pokud se něco vynechávalo, provedla se korekce, aby
                # to tady fungovalo.
                index += 1

            # Přefiltrované elementy vypíšeme do určeného souboru.
            for elem in self.cs_lst:
                fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupních souborech.
        self.info_lines.append(short_name(cs_extra_fname))
        self.info_lines.append(short_name(cs_elem_fname))

        # Elementy z anglického originálu do seznamu a do souboru.
        self.en_lst = []
        en_elem_fname = os.path.join(self.en_aux_dir, 'pass1elem.txt')
        with open(en_elem_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for relname, lineno, line in gen.sourceFileLines(self.en_name_in):
                elem = docelement.Element(relname, lineno, line)
                self.en_lst.append(elem)
                fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupním souboru.
        self.info_lines.append(short_name(en_elem_fname))


    def checkStructDiffs(self):
        '''Generuje cs/pass1struct_diff.txt s rozdíly ve struktuře zdrojových řádků.'''

        sync_flag = True   # optimistická inicializace

        # Při porovnávání struktury se příklady (příkazy, odsazené zleva)
        # porovnávají a měly by být identické. Výjimku představují
        # případy, kdy se v příkladu uvádí komentář nebo symbolicky popsaný
        # argument, který byl přeložen. Dřívější implementace využívala
        # přeskakování těchto úseků uvedením řádků (odstavců) ve zdrojovém
        # textu. Tímto způsobem se ale neodhalí modifikace obsahu těchto
        # příkladů v originálu. Proto se nově buduje "překladový slovník"
        # těchto úseků z definičního souboru, kde první posloupnost uvádí
        # řádky anglického originálu, oddělovač s nejméně pěti pomlčkami
        # od začátku řádku, řádky jazykově závislého překladu a oddělovač
        # s nejméně pěti rovnítky. Pomocný slovník používá první řádek
        # z originálu jako klíč a dvojici seznamů (en, cz) definujících
        # odpovídající si posloupnosti.
        path, scriptname = os.path.split(__file__)
        cs_translated_snippets_fname = os.path.join(path, 'cs_translated_snippets.txt')
        translated_snippets = {}
        status = 0
        lst = None
        with open(cs_translated_snippets_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # První řádek bude klíčem slovníku, získáme odkaz
                    # na dvojici seznamů řádků.
                    en_lst, cs_lst = translated_snippets.setdefault(line, ([], []))

                    en_lst.append(line)     # první řádek originálu
                    status = 1

                elif status == 1:
                    # Druhý a další řádek originálu nebo konec posloupnosti
                    if line.startswith('-----'):    # minimálně 5
                        en_lst = None               # konec sbírání en
                        status = 2
                    else:
                        en_lst.append(line)

                elif status == 2:
                    # Řádky české posloupnosti.
                    if line.startswith('====='):    # minimálně 5
                        cs_lst = None               # konec sbírání cs
                        status = 0
                    else:
                        cs_lst.append(line)

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Přidáme informaci o souboru s definicemi.
        self.info_lines.append(short_name(cs_translated_snippets_fname))

        # Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
        # příklady kódu) porovnáváme za účelem zjištění rozdílů struktury -- zde
        # jen typy elementů.
        struct_diff_fname = os.path.join(self.cs_aux_dir, 'pass1struct_diff.txt')
        para_len_fname = os.path.join(self.cs_aux_dir, 'pass1paralen.txt')
        translated_snippets_fname = os.path.join(self.cs_aux_dir, 'pass1transl_snippets.txt')
        with open(struct_diff_fname, 'w', encoding='utf-8', newline='\n') as f, \
             open(translated_snippets_fname, 'w', encoding='utf-8', newline='\n') as ftransl, \
             open(para_len_fname, 'w', encoding='utf-8', newline='\n') as flen:

            # Použijeme cyklus while, protože budeme různě přeskakovat a modifikovat
            # seznamy prvků. Musíme manipulovat s indexy i se seznamy.
            en_i = 0       # index zpracovávaného elementu
            cs_i = 0
            while en_i < len(self.en_lst) and cs_i < len(self.cs_lst):

                # Zpřístupníme si elementy na indexech.
                en_elem = self.en_lst[en_i]
                cs_elem = self.cs_lst[cs_i]

                if en_elem.line in translated_snippets:
                    # Mohla by to být vložená přeložená posloupnost.
                    # Odpovídající si definiční seznamy.
                    enlst, cslst = translated_snippets[en_elem.line]

                    # Délky obou definičních seznamů.
                    enlen = len(enlst)
                    cslen = len(cslst)

                    # Příznaky detekce definičních seznamů v en a v cs.
                    is_enseq = [e.line for e in self.en_lst[en_i:en_i+enlen]] == enlst
                    is_csseq = [e.line for e in self.cs_lst[cs_i:cs_i+cslen]] == cslst

                    # Pokud jsou oba příznaky nastaveny, pak jsme nalezli
                    # odpovídající si posloupnosti. Zaznamenáme je do souboru.
                    # Z hlediska dalšího porovnání bude jednodušší obě posloupnosti
                    # vypustit.
                    if is_enseq and is_csseq:
                        # Zaznamenáme přeskočené řádky.
                        ftransl.write('{}/{}:\n'.format(en_elem.fname, en_elem.lineno))
                        ftransl.write('{}/{}:\n'.format(cs_elem.fname, cs_elem.lineno))
                        ftransl.write('~~~~~~~~~~~~~~~\n')
                        ftransl.write(''.join(enlst))
                        ftransl.write('-----\n')
                        ftransl.write(''.join(cslst))
                        ftransl.write('=====\n\n')

                        # Přeskočené řádky vypustíme ze seznamu elementů.
                        del self.en_lst[en_i:en_i+enlen]
                        del self.cs_lst[cs_i:cs_i+cslen]

                        # Indexy posuneme o jeden zpět, protože se posloupnosti
                        # vypustily a indexy se budou zvyšovat o jedničku.
                        en_i -= 1
                        cs_i -= 1

                else:
                    # Jde o jiný případ. Budeme porovnávat strukturu elementů.
                    # Pro nejhrubší synchronizaci se budeme řídit pouze typy
                    # elementů. (Nejméně přísné pravidlo synchronizace.)
                    #
                    # Pokud se typy shodují, pak přísnější pravidlo
                    # synchronizace vyžaduje, aby se shodovaly řádky
                    # s příkladem kódu.
                    if en_elem.type != cs_elem.type \
                       or (en_elem.type == 'code'
                           and en_elem.line.rstrip() != cs_elem.line.rstrip()):
                        # Není to synchronní; shodíme příznak.
                        sync_flag = False

                        # U obou jméno souboru/číslo řádku.
                        f.write('\ncs {}/{} -- en {}/{}:\n'.format(
                                cs_elem.fname,
                                cs_elem.lineno,
                                en_elem.fname,
                                en_elem.lineno))

                        # Typ a hodnota českého elementu.
                        f.write('\t{}:\t{}\n'.format(cs_elem.type,
                                                     cs_elem.line.rstrip()))

                        # Typ a hodnota anglického elementu.
                        f.write('\t{}:\t{}\n'.format(en_elem.type,
                                                     en_elem.line.rstrip()))

                    # V případě shody struktury provedeme heuristickou kontrolu
                    # na délku odstavců. Využívá se skutečnosti, že odstavec
                    # je většinou napsán na jednom dlouhém řádku -- každopádně
                    # stejně v obou jazycích.
                    elif en_elem.type in ('para', 'uli', 'li'):
                        # U obou identifikaci kapitoly, čísla porovnávaných řádků,
                        # délky porovnávaných řádků a poměr délek.
                        flen.write('{} cs/{} -- en/{}:\t{}:{}\t({})\n'.format(
                                   os.path.split(cs_elem.fname)[0],
                                   cs_elem.lineno,
                                   en_elem.lineno,
                                   len(cs_elem.line),
                                   len(en_elem.line),
                                   len(cs_elem.line) / len(en_elem.line)))

                # Posuneme se na další elementy, které se mají zpracovat.
                # Pokud se něco vynechávalo, provedla se korekce, aby
                # to tady fungovalo.
                en_i += 1
                cs_i += 1

        # Přidáme informaci o výstupním souboru.
        self.info_lines.append(short_name(translated_snippets_fname))
        self.info_lines.append(short_name(struct_diff_fname))
        self.info_lines.append(short_name(para_len_fname))

        # Přidáme informaci o synchronnosti.
        self.info_lines.append(('-'*40) + ' struktura se ' +
                               ('shoduje' if sync_flag else 'NESHODUJE'))


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.writePass1txtFiles()
        self.loadElementLists()
        self.checkStructDiffs()

        return '\n\t'.join(self.info_lines)
