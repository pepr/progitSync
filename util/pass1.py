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

    def __init__(self, lang, root_src_dir, root_aux_dir):
        self.lang = lang    # the language abbrev. like 'cs', 'fr', 'ru', etc.
        self.root_src_dir = os.path.realpath(root_src_dir)
        self.root_aux_dir = os.path.realpath(root_aux_dir)

        # Location of the root directory with the English original.
        self.en_src_dir = os.path.join(self.root_src_dir, 'en')

        # Derive the location of the directory for the target language.
        self.xx_src_dir = os.path.join(self.root_src_dir, lang)

        # Location of the root for the generated files for English.
        self.en_aux_dir = os.path.join(self.root_aux_dir, 'en_aux')
        print(self.en_aux_dir)

        # Derive the auxiliary directory for the target language.
        self.xx_aux_dir = os.path.join(self.root_aux_dir, lang + '_aux')
        print(self.xx_aux_dir)

        # Create the auxiliary directories if they does not exist.
        if not os.path.isdir(self.en_aux_dir):
            os.makedirs(self.en_aux_dir)

        if not os.path.isdir(self.xx_aux_dir):
            os.makedirs(self.xx_aux_dir)


        self.en_lst = None  # elements from the English original
        self.xx_lst = None  # elements from the target language

        self.info_lines = []    # lines for displaying through the stdout

    def writePass1txtFiles(self):
        # Kopie českého vstupu do jednoho souboru. Při tomto průchodu
        # pochází z jednoho souboru, takže jméno souboru vynecháme.
        xx_single_fname = os.path.join(self.xx_aux_dir, 'pass1.txt')
        with open(xx_single_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Kopie anglického vstupu do jednoho souboru. Pro lepší orientaci
        # v dlouhých řádcích nebudeme vypisovat jméno souboru, ale
        # jen číslo kapitoly (jeden znak relativní cesty).
        en_single_fname = os.path.join(self.en_aux_dir, 'pass1.txt')
        with open(en_single_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for fname, lineno, line in gen.sourceFileLines(self.en_src_dir):
                fout.write('{}/{}:\t{}'.format(fname[1:2], lineno, line))

        # Přidáme informaci o vytvářených souborech.
        self.info_lines.append(short_name(xx_single_fname))
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
        xx_def_extras_fname = os.path.join(path, '{}_def_extras.txt'.format(self.lang))
        xx_extras = {}
        status = 0
        lst = None
        with open(xx_def_extras_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # První řádek bude klíčem slovníku, získáme odkaz
                    # na seznam řádků.
                    lst = xx_extras.setdefault(line, [])
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
        self.info_lines.append(short_name(xx_def_extras_fname))

        # Procházíme elementy. Pokud narazíme na řádek, který zahajuje
        # vynechávanou posloupnost, začneme porovnávat další řádky.
        # Pokud nejde o vynechávanou posloupnost, zpracováváme řádky
        # normálně, pokud jde, přeskočíme ji, ale zapíšeme vše do
        # pass1extra_lines.txt. Kvůli backtrackingu načteme nejdříve
        # všechny elementy do seznamu.
        self.xx_lst = []
        for relname, lineno, line in gen.sourceFileLines(self.xx_src_dir):
            elem = docelement.Element(relname, lineno, line)
            self.xx_lst.append(elem)

        xx_elem_fname = os.path.join(self.xx_aux_dir, 'pass1elem.txt')
        xx_extra_fname = os.path.join(self.xx_aux_dir, 'pass1extra_lines.txt')
        with open(xx_elem_fname, 'w', encoding='utf-8', newline='\n') as fout, \
             open(xx_extra_fname, 'w', encoding='utf-8', newline='\n') as foutextra:

            index = 0       # index zpracovávaného elementu
            while index < len(self.xx_lst):  # pozor, délka se dynamicky mění
                elem = self.xx_lst[index]

                if elem.line in xx_extras:
                    # Mohla by to být vložená (extra) posloupnost.
                    # Porovnáme řádky v délce extra posloupnosti.
                    e_lines = [e.line for e in self.xx_lst[index:index+len(xx_extras[elem.line])]]
                    if e_lines == xx_extras[elem.line]:
                        # Zaznamenáme přeskočené řádky.
                        foutextra.write('{}/{}:\n'.format(elem.fname, elem.lineno))
                        foutextra.write(''.join(e_lines))
                        foutextra.write('====================\n\n')

                        # Přeskočené řádky vypustíme ze seznamu elementů.
                        del self.xx_lst[index:index+len(xx_extras[elem.line])]

                        # Index posuneme o jeden zpět, protože se posloupnost
                        # vypustila a index se bude zvyšovat o jedničku.
                        index -= 1

                # Posuneme se na další element, který se má zpracovat.
                # Pokud se něco vynechávalo, provedla se korekce, aby
                # to tady fungovalo.
                index += 1

            # Přefiltrované elementy vypíšeme do určeného souboru.
            for elem in self.xx_lst:
                fout.write(repr(elem) + '\n')

        # Přidáme informaci o výstupních souborech.
        self.info_lines.append(short_name(xx_extra_fname))
        self.info_lines.append(short_name(xx_elem_fname))

        # Elementy z anglického originálu do seznamu a do souboru.
        self.en_lst = []
        en_elem_fname = os.path.join(self.en_aux_dir, 'pass1elem.txt')
        with open(en_elem_fname, 'w', encoding='utf-8', newline='\n') as fout:
            for relname, lineno, line in gen.sourceFileLines(self.en_src_dir):
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
        xx_translated_snippets_fname = os.path.join(path, '{}_translated_snippets.txt'.format(self.lang))
        translated_snippets = {}
        status = 0
        lst = None
        with open(xx_translated_snippets_fname, encoding='utf-8') as f:
            for line in f:
                if status == 0:
                    # První řádek bude klíčem slovníku, získáme odkaz
                    # na dvojici seznamů řádků.
                    en_lst, xx_lst = translated_snippets.setdefault(line, ([], []))
                    assert len(en_lst) == 0
                    assert len(xx_lst) == 0

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
                        xx_lst = None               # konec sbírání cs
                        status = 0
                    else:
                        xx_lst.append(line)

                else:
                    raise NotImplementedError('status = {}\n'.format(status))

        # Přidáme informaci o souboru s definicemi.
        self.info_lines.append(short_name(xx_translated_snippets_fname))

        # Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
        # příklady kódu) porovnáváme za účelem zjištění rozdílů struktury -- zde
        # jen typy elementů.
        struct_diff_fname = os.path.join(self.xx_aux_dir, 'pass1struct_diff.txt')
        para_len_fname = os.path.join(self.xx_aux_dir, 'pass1paralen.txt')
        translated_snippets_fname = os.path.join(self.xx_aux_dir, 'pass1transl_snippets.txt')
        with open(struct_diff_fname, 'w', encoding='utf-8', newline='\n') as f, \
             open(translated_snippets_fname, 'w', encoding='utf-8', newline='\n') as ftransl, \
             open(para_len_fname, 'w', encoding='utf-8', newline='\n') as flen:

            # Použijeme cyklus while, protože budeme různě přeskakovat a modifikovat
            # seznamy prvků. Musíme manipulovat s indexy i se seznamy.
            en_i = 0       # index zpracovávaného elementu
            xx_i = 0
            while en_i < len(self.en_lst) and xx_i < len(self.xx_lst):

                # Zpřístupníme si elementy na indexech.
                en_elem = self.en_lst[en_i]
                xx_elem = self.xx_lst[xx_i]

                if en_elem.line in translated_snippets:
                    # Mohla by to být vložená přeložená posloupnost.
                    # Odpovídající si definiční seznamy.
                    enlst, cslst = translated_snippets[en_elem.line]

                    # Délky obou definičních seznamů.
                    enlen = len(enlst)
                    cslen = len(cslst)

                    # Příznaky detekce definičních seznamů v en a v cs.
                    is_enseq = [e.line for e in self.en_lst[en_i:en_i+enlen]] == enlst
                    is_csseq = [e.line for e in self.xx_lst[xx_i:xx_i+cslen]] == cslst

                    # Pokud jsou oba příznaky nastaveny, pak jsme nalezli
                    # odpovídající si posloupnosti. Zaznamenáme je do souboru.
                    # Z hlediska dalšího porovnání bude jednodušší obě posloupnosti
                    # vypustit.
                    if is_enseq and is_csseq:
                        # Zaznamenáme přeskočené řádky.
                        ftransl.write('{}/{}:\n'.format(en_elem.fname, en_elem.lineno))
                        ftransl.write('{}/{}:\n'.format(xx_elem.fname, xx_elem.lineno))
                        ftransl.write('~~~~~~~~~~~~~~~\n')
                        ftransl.write(''.join(enlst))
                        ftransl.write('-----\n')
                        ftransl.write(''.join(cslst))
                        ftransl.write('========================== {}\n\n'.format(en_elem.fname))

                        # Přeskočené řádky vypustíme ze seznamu elementů.
                        del self.en_lst[en_i:en_i+enlen]
                        del self.xx_lst[xx_i:xx_i+cslen]

                        # Indexy posuneme o jeden zpět, protože se posloupnosti
                        # vypustily a indexy se budou zvyšovat o jedničku.
                        en_i -= 1
                        xx_i -= 1

                else:
                    # Jde o jiný případ. Budeme porovnávat strukturu elementů.
                    # Pro nejhrubší synchronizaci se budeme řídit pouze typy
                    # elementů. (Nejméně přísné pravidlo synchronizace.)
                    #
                    # Pokud se typy shodují, pak přísnější pravidlo
                    # synchronizace vyžaduje, aby se shodovaly řádky
                    # s příkladem kódu.
                    if en_elem.type != xx_elem.type \
                       or (en_elem.type == 'code'
                           and en_elem.line.rstrip() != xx_elem.line.rstrip()):
                        # Není to synchronní; shodíme příznak.
                        sync_flag = False

                        # U obou jméno souboru/číslo řádku.
                        f.write('\ncs {}/{} -- en {}/{}:\n'.format(
                                xx_elem.fname,
                                xx_elem.lineno,
                                en_elem.fname,
                                en_elem.lineno))

                        # Typ a hodnota českého elementu.
                        f.write('\t{}:\t{}\n'.format(xx_elem.type,
                                                     xx_elem.line.rstrip()))

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
                                   os.path.split(xx_elem.fname)[0],
                                   xx_elem.lineno,
                                   en_elem.lineno,
                                   len(xx_elem.line),
                                   len(en_elem.line),
                                   len(xx_elem.line) / len(en_elem.line)))

                # Posuneme se na další elementy, které se mají zpracovat.
                # Pokud se něco vynechávalo, provedla se korekce, aby
                # to tady fungovalo.
                en_i += 1
                xx_i += 1

        # Přidáme informaci o výstupním souboru.
        self.info_lines.append(short_name(translated_snippets_fname))
        self.info_lines.append(short_name(struct_diff_fname))
        self.info_lines.append(short_name(para_len_fname))

        # Přidáme informaci o synchronnosti.
        self.info_lines.append(('-'*30) + ' structure of the doc is ' +
                               ('the same' if sync_flag else '  DIFFERENT'))


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        self.writePass1txtFiles()
        self.loadElementLists()
        self.checkStructDiffs()

        return '\n\t'.join(self.info_lines)
