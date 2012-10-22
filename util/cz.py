#!python3
# -*- coding: utf-8 -*-

'''Skript pro zpracování extrahovaného txt z českého překladu v podobě PDF.'''

import collections
import os
import re
import shutil


def abstractNum(num):
    '''Get the number of the title and construct the '#', '##', or '###'.'''
    lst = num.split('.')
    if lst[-1] == '':    # chapter numbering ends with dot
        del lst[-1]
    return '#' * len(lst)


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

    with open(os.path.join(aux_dir, 'czTOC.txt'), 'w', encoding='utf-8') as ftoc,       \
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

#-----------------------------------------------------------------
class Pass2Parser:
    '''Parser konzumující výstup prvního průchodu.'''

    def __init__(self, fname, toc, aux_dir):
        self.fname_in = fname
        self.toc = toc    # toc = Table Of Content
        self.aux_dir = aux_dir

        self.type = None  # init -- symbolický typ řádku (jeho význam)
        self.parts = None # init -- seznam částí řádku dle významu

        patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'
        self.rexTitle = re.compile(r'^' + patNum + r'\s+(?P<title>.+?)\s*$')

        # Bullet.
        self.rexBullet = re.compile('^[*\u2022]' + r'\s*(?P<text>.*?)\s*$')

        # Značka přechodu mezi stránkami. Je generovaná v prvním průchodu,
        # takže můžeme volit jednoduchý výraz.
        self.rexPagesep = re.compile(r'^---------- pagesep$')

        # Umístění obrázku s číslem. Může následovat popisný text,
        # ale bývá zalomený za ještě jedním prázdným řádkem.
        patObrazek = r'^Obrázek\s+(?P<num>\d+-\d+).(\s+(?P<text>.+?))?\s*$'
        self.rexObrazek = re.compile(patObrazek)


    def png_name(self, num):
        '''Pro číslo 'x-y' vrací '18333fig0x0y-tn.png'''

        n1, n2 = num.split('-')
        return '18333fig{:02}{:02}-tn.png'.format(int(n1), int(n2))


    def parse_line(self):
        '''Rozloží self.line na self.type a self.parts.'''

        if self.line == '':
            # Prázdný řádek indikuje konec načítaného souboru. Python
            # platný řádek souboru nikdy nevrátí jako zcela prázdný.
            # Z pohledu řešeného problému to tedy není prázdný řádek
            # ve významu oddělovače.
            self.type = 'EOF'
            self.parts = None

        elif self.line.isspace():
            # Řádek obsahující jen whitespace považujeme za prázdný
            # řádek ve významu oddělovače.
            self.type = 'empty'
            self.parts = ['']   # reprezentací bude prázdný řetězec

        else:
            # Budeme testovat přes regulární výrazy a v případě
            # rozpoznání určíme typ, rozložíme na části a ukončíme
            # běh metody. (Dalo by se to zoptimalizovat, ale nestojí
            # to za námahu).
            m = self.rexTitle.match(self.line)
            if m:
                num = m.group('num')
                title = m.group('title')

                # Pokud je číslo a hodnota nadpisu zachycena v toc, jde
                # skutečně o nadpis. Pokud ne, budeme to pokládat za položku
                # číslovaného seznamu.
                if num in toc and title == toc[num]:
                    self.type = 'title'
                    self.parts = [num, title]
                else:
                    self.type = 'li'
                    self.parts = [num + '\t', title]

                return

            # Nečíslovaná odrážka (bullet).
            m = self.rexBullet.match(self.line)
            if m:
                text = m.group('text')
                self.type = 'li'        # ListItem nečíslovaného seznamu
                self.parts = ['*\t', text]  # markdown reprezentace...
                return

            # Obrázek s popisem.
            m = self.rexObrazek.match(self.line)
            if m:
                text = m.group('text')
                if text is None:
                    text = ''           # korekce
                num = m.group('num')
                self.type = 'obrazek'
                self.parts = ['Insert {}\n'.format(self.png_name(num)),
                              'Obrázek {}. {}'.format(num, text)]
                return

            # Rozhraní mezi stránkami.
            m = self.rexPagesep.match(self.line)
            if m:
                self.type = 'pagesep'
                self.parts = []
                return

            # Nerozpoznaný případ.
            self.type = '???'
            self.parts = [ self.line.rstrip() ]


    def run(self):
        with open(self.fname_in, encoding='utf-8') as fin, \
             open(os.path.join(aux_dir, 'pass2.txt'), 'w', encoding='utf-8') as fout:

            status = 0
            while status != 888:

                self.line = fin.readline()
                self.parse_line()

                if self.type == 'EOF':
                    status = 888

                if status == 0:             # -------
                    fout.write('{}|{}\n'.format(self.type,
                                                ' '.join(self.parts)))

                elif status == 888:         # ------- akce po EOF
                    pass


if __name__ == '__main__':

    # Pomocný podadresář pro generované informace.
    aux_dir = os.path.realpath('../info_aux_cz')

    # Zpracujeme český překlad z textového souboru, který byl získán
    # uložením PDF jako text a následnou ruční úpravou některých jevů,
    # které vznikly ruční sazbou orientovanou na vzhled (tj. nikoliv
    # na zachování struktury dokumentu). Hlavním výsledkem je soubor
    # pass1.txt a vracený slovník toc.
    toc = first_pass('../txtFromPDF/scott_chacon_pro_git_CZ.txt', aux_dir)

    # V druhém průchodu rozpoznáváme pass1.txt a generujeme pass2.txt.
    parser = Pass2Parser(os.path.join(aux_dir, 'pass1.txt'), toc, aux_dir)
    parser.run()