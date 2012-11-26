#!python3
# -*- coding: utf-8 -*-

import os
import re
import shutil

class Parser:
    '''Parser pro první průchod ručně získaným textovým souborem (z českého PDF).

       Generuje pass1.txt, který obsahuje zredukovaný obsah souboru fname.
       Pro účely srovnávání s originálem generuje czTOC.txt z řádků
       velkého obsahu na začátku dokumentu. Záhlaví stránek zachycuje
       do PageHeaders.txt. Zmíněné prvky při prvním průchodu do pass1.txt
       nezapisuje. Ostatní vypuštěné prvky (nepatřící ani do obsahu, ani
       k hlavičkám stránek) zapisuje do ignored.txt. Vše se generuje
       do adresáře self.cs_aux_dir, který se nejdříve úplně promaže (vytvoří znovu).

       Pro potřeby další fáze generuje slovník obsahu, kde klíčem je
       číslo kapitoly/podkapitoly/... a hodnotou je text jejího názvu.
       Tento slovník se později používá pro rozpoznání řádků, které
       sice mohou vypadat jako nadpis, ale nejsou jím (například seznam
       číslovaných položek).
    '''

    # Regulární výrazy pro rozpoznání částí dokumentu jsou stejné
    # pro všechny případné instance (ale bude jedna).
    #    
    # Řádek obsahu má tvar: "1.1 Správa verzí -- 17"
    # kde '--' je čtverčíková pomlčka.
    patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'
    patTOCitem = patNum + r'\s+(?P<title>.+?)(\s+\u2014)?(\s+(?P<pageno>\d+)\s*)'

    rexTOCline = re.compile(r'^' + patTOCitem + r'$')
    rexObsah = re.compile(r'^\u2014\s+(?P<title>Obsah.*?)(\s+(?P<pageno>\d+)\s*)$')
    rexKapitola = re.compile(r'^\d+\.\s+Kapitola\s+\d+\s*$')


    def __init__(self, fname, cs_aux_dir):
        self.fname = fname
        self.cs_aux_dir = cs_aux_dir


    def run(self):
        # Vytvoříme čerstvý pomocný podadresář s extrahovanými informacemi.
        if os.path.isdir(self.cs_aux_dir):
            shutil.rmtree(self.cs_aux_dir)
        os.mkdir(self.cs_aux_dir)

        # Slovník naplněný položkami obsahu, který funkce vrací.
        toc = {}

        with open(os.path.join(self.cs_aux_dir, 'czTOC1.txt'), 'w', 
                  encoding='utf-8') as ftoc,                            \
             open(os.path.join(self.cs_aux_dir, 'PageHeaders.txt'), 'w',
                  encoding='utf-8') as fph,                             \
             open(os.path.join(self.cs_aux_dir, 'ignored.txt'), 'w', 
                  encoding='utf-8') as fignored,                        \
             open(os.path.join(self.cs_aux_dir, 'pass1.txt'), 'w', 
                  encoding='utf-8') as fout,                            \
             open(self.fname, encoding='utf-8') as fin:

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
                    m = self.rexObsah.match(line)
                    if m:
                        status = 2                  # začneme sbírat řádky obsahu
                    else:
                        status = 0                  # ignorujeme do dalšího FF

                elif status == 2:           # ------- sbíráme řádky obsahu
                    if line.startswith('\f'):       # FormFeed ukončuje Obsah
                        fignored.write(line)
                        status = 3
                    else:
                        m = self.rexTOCline.match(line)  # je to řádek s položkou obsahu?
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

                    mKap = self.rexKapitola.match(line)  # stránka s velkým názvem kapitoly
                    mObsah = self.rexObsah.match(line)   # stránka s obsahem kapitoly
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
