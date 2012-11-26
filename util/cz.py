#!python3
# -*- coding: utf-8 -*-

'''Skript pro zpracování extrahovaného txt z českého překladu v podobě PDF.'''

import collections
import gen
import os
import pass2
import pass3
import pass4
import re
import shutil
import sys


def first_pass(fname, aux_dir):
    '''První průchod ručně získaným textovým souborem (z českého PDF).

       Generuje pass1.txt, který obsahuje zredukovaný obsah souboru fname.
       Pro účely srovnávání s originálem generuje czTOC.txt z řádků
       velkého obsahu na začátku dokumentu. Záhlaví stránek zachycuje
       do PageHeaders.txt. Zmíněné prvky při prvním průchodu do pass1.txt
       nezapisuje. Ostatní vypuštěné prvky (nepatřící ani do obsahu, ani
       k hlavičkám stránek) zapisuje do ignored.txt. Vše se generuje
       do adresáře aux_dir, který se nejdříve úplně promaže (vytvoří znovu).

       Pro potřeby další fáze generuje slovník obsahu, kde klíčem je
       číslo kapitoly/podkapitoly/... a hodnotou je text jejího názvu.
       Tento slovník se později používá pro rozpoznání řádků, které
       sice mohou vypadat jako nadpis, ale nejsou jím (například seznam
       číslovaných položek).
    '''

    # Vytvoříme čerstvý pomocný podadresář s extrahovanými informacemi.
    if os.path.isdir(aux_dir):
        shutil.rmtree(aux_dir)
    os.mkdir(aux_dir)

    # Slovník naplněný položkami obsahu, který funkce vrací.
    toc = {}

    # Řádek obsahu má tvar: "1.1 Správa verzí -- 17"
    # kde '--' je čtverčíková pomlčka.
    patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'
    patTOCitem = patNum + r'\s+(?P<title>.+?)(\s+\u2014)?(\s+(?P<pageno>\d+)\s*)'

    rexTOCline = re.compile(r'^' + patTOCitem + r'$')
    rexObsah = re.compile(r'^\u2014\s+(?P<title>Obsah.*?)(\s+(?P<pageno>\d+)\s*)$')
    rexKapitola = re.compile(r'^\d+\.\s+Kapitola\s+\d+\s*$')

    with open(os.path.join(aux_dir, 'czTOC1.txt'), 'w', encoding='utf-8') as ftoc,       \
         open(os.path.join(aux_dir, 'PageHeaders.txt'), 'w', encoding='utf-8') as fph,  \
         open(os.path.join(aux_dir, 'ignored.txt'), 'w', encoding='utf-8') as fignored, \
         open(os.path.join(aux_dir, 'pass1.txt'), 'w', encoding='utf-8') as fout,       \
         open(fname, encoding='utf-8') as fin:

        status = 0
        while status != 888:

            line = fin.readline()
            if line == '':
                status = 888                    # EOF

            if status == 0:             # ------- ignorujeme do FF (před Obsahem)
                fignored.write(line)            # všechny řádky do prvního FormFeed
                if line.startswith('\f'):       # ... se ignorují
                    status = 1

            elif status == 1:           # ------- záhlaví stránek před Obsahem
                fph.write(line)
                fignored.write('PH: ' + line)
                m = rexObsah.match(line)
                if m:
                    status = 2                  # začneme sbírat řádky obsahu
                else:
                    status = 0                  # ignorujeme do dalšího FF

            elif status == 2:           # ------- sbíráme řádky obsahu
                if line.startswith('\f'):       # FormFeed ukončuje Obsah
                    fignored.write(line)
                    status = 3
                else:
                    m = rexTOCline.match(line)  # je to řádek s položkou obsahu?
                    if m:
                        # Zapíšeme v očištěné podobě, bez čísla stránky.
                        num = m.group('num')
                        title = m.group('title')
                        ftoc.write('{} {}\n'.format(num, title))

                        # Řádek obsahu zachytíme do slovníku pro potřeby
                        # druhého průchodu.
                        toc[num] = title

                        # Řádek obsahu ale nezapisujeme do výstupního
                        # filtrovaného souboru.
                        fignored.write('TOC: ' + line)
                    else:
                        fignored.write(line)    # ignorujeme prázdné...


            elif status == 3:           # ------- záhlaví stránky po Obsahu
                fph.write(line)
                fignored.write('PH: ' + line)

                # Na výstupu nahradíme FormFee + page heading značkou,
                # která by mohla ulehčit řešení speciálních případů
                # při dalším průchodu.
                fout.write('---------- pagesep\n')

                mKap = rexKapitola.match(line)  # stránka s velkým názvem kapitoly
                mObsah = rexObsah.match(line)   # stránka s obsahem kapitoly
                if mKap or mObsah:
                    status = 5          # ignorovat celou stránku (po Obsahu)
                else:
                    status = 4          # sbírat následující řádky


            elif status == 4:           # ------- textové řádky lines
                if line.startswith('\f'):       # FormFeed
                    fignored.write(line)
                    status = 3
                else:
                    fout.write(line)    # běžný platný řádek

            elif status == 5:           # ------- ignorujeme stránku (po Obsahu)
                fignored.write(line)            # všechny řádky do prvního FormFeed
                if line.startswith('\f'):       # ... se ignorují
                    status = 3

            elif status == 888:         # ------- akce po EOF
                pass

    # Pro potřeby druhého průchodu vrátíme slovník s položkami obsahu.
    return toc


if __name__ == '__main__':

    # Pomocné podadresáře pro generované informace.
    cs_aux_dir = os.path.realpath('../info_aux_cs')
    if not os.path.isdir(cs_aux_dir):
        os.makedirs(cs_aux_dir)

    en_aux_dir = os.path.realpath('../info_aux_en')
    if not os.path.isdir(en_aux_dir):
        os.makedirs(en_aux_dir)

    # Zpracujeme český překlad z textového souboru, který byl získán
    # uložením PDF jako text a následnou ruční úpravou některých jevů,
    # které vznikly ruční sazbou orientovanou na vzhled (tj. nikoliv
    # na zachování struktury dokumentu). Hlavním výsledkem je soubor
    # pass1.txt a vracený slovník toc.
    print('pass 1 ... ', end='')
    czTOC = first_pass('../txtFromPDF/scott_chacon_pro_git_CZ.txt', cs_aux_dir)

    # V druhém průchodu rozpoznáváme pass1.txt a generujeme pass2.txt.
    print('done\npass 2 ... ', end='')
    parser2 = pass2.Parser(os.path.join(cs_aux_dir, 'pass1.txt'), czTOC, cs_aux_dir)
    parser2.run()
    print('done')

    # Po ručních úpravách zdroje pro první průchod (provedena kontrola
    # pass2.txt lidskýma očima) okopírujeme pass2.txt ručně do odděleného
    # souboru, který budeme dále upravovat ručně. (Kdykoliv je možné srovnat
    # jej s nadále generovaným pass2.txt.) V tomto místě kontrolujeme, zda
    # soubor existuje.
    czfname_pass2man = '../txtCorrected/RucneUpravovanyVysledekPass2.txt'
    if not os.path.isfile(czfname_pass2man):
        print('\n\n\a\a\aRučně okopírovat pass2.txt do\n\t',
              repr(czfname_pass2man) + ' !!!\n\n')
        sys.exit(1)

    # Adresář s originálními podadresáři a soubory.
    en_src_dir = os.path.abspath('../../progit/en')

    # V třetím průchodu sesbíráme informace jednak z originálu a jednak
    # z překladu (stejným algoritmem). Vycházíme z druhého commitu originálního
    # gitovského repozitáře (dfaab52e5a438d7fcd0d9c9af63289e5e3985fba), ve kterém
    # byly originální zdrojové soubory přemístěny do podadresáře en. V prvním
    # commitu podadresář en neexistoval a byl zjevně zaveden až v okamžiku
    # prvních kroků překladatelů knihy.
    #
    # Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
    # příklady kódu) porovnáváme za účelem zjištění rozdílů struktury. Některé
    # informace se porovnávají podrobněji (příklady kódu, identifikace obrázků),
    # u některých elementů se porovnává jen druh elementu (existence odstavce,
    # existence odrážky, úroveň nadpisu,...).
    print('pass 3 ... ')
    parser3 = pass3.Parser(czfname_pass2man, en_src_dir, cs_aux_dir, en_aux_dir)
    parser3.run()
    print('\tdone')

    # Ve čtvrtém průchodu vycházíme z předpokladu, že se struktura dokumentu
    # shoduje. Už generujeme cílovou strukturu cs/, ale pro další strojové
    # korekce budeme stále vycházet z informací získaných v předchozím kroku.
    print('pass 4 ... ')
    parser4 = pass4.Parser(parser3)
    parser4.run()
    print('\tdone')
