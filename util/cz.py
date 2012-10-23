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
    '''Parser pro druhý průchod, konzumující výstup prvního průchodu.'''

    def __init__(self, fname, toc, aux_dir):
        self.fname_in = fname   # jméno vstupního souboru
        self.toc = toc          # toc = Table Of Content
        self.aux_dir = aux_dir  # adresář pro generovaný výstupní soubor

        self.type = None        # init -- symbolický typ řádku (jeho význam)
        self.parts = []         # init -- seznam částí řádku dle významu
        self.collection = []    # init -- kolekce sesbíraných řádků

        self.fout = None        # souborový objekt otevřený pro výstup.
        self.status = None      # init -- stav konečného automatu

        # Vícekrát použitý vzorek pro číslo s tečkami.
        patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'

        # Řádek obsahující pouze číslo (kapitoly, podkapitoly, ..., bodu seznamu.
        self.rexNum = re.compile(r'^' + patNum + r'\s*$')

        # Číslovaný nadpis.
        self.rexTitle = re.compile(r'^' + patNum + r'\s+(?P<title>.+?)\s*$')

        # Nečíslovaná odrážka korektně explicitně zapsaná (markdown syntaxe).
        self.rexBullet = re.compile(r'^(?P<uli>\*\t.+?)\s*$')

        # Dobře rozpoznaná nečíslovaná odrážka zapsaná Unicode znakem.
        self.rexUBullet = re.compile('^\u2022' + r'\s*(?P<text>.*?)\s*$')

        # Pouze zahajovací znak (dobře rozpoznaný) špatně zalomeného
        # textu nečíslované odrážky. Musí se k němu přidat jeden nebo
        # víc dalších řádků.
        self.rexUXBullet = re.compile('^\u2022' + r'\s*$')

        # Značka přechodu mezi stránkami. Je generovaná v prvním průchodu,
        # takže můžeme volit jednoduchý výraz.
        self.rexPagesep = re.compile(r'^---------- pagesep$')

        # Umístění obrázku s číslem. Může následovat popisný text,
        # ale bývá zalomený za ještě jedním prázdným řádkem.
        patObrazek = r'^Obrázek\s+(?P<num>\d+-\d+).(\s+(?P<text>.+?))?\s*$'
        self.rexObrazek = re.compile(patObrazek)

        # Řádek reprezentující příklad sázený jako kódový řádek
        # neproporcionálním písmem. U této aplikace je uvozen jedním tabulátorem.
        self.rexCode = re.compile(r'^\t(?P<text>.*)$')

        # Řádek, který má být pravděpodobně změněn na příklad textového řádku.
        self.rexXCode = re.compile(r'^(?P<text>[$#].*)$')


    def png_name(self, num):
        '''Pro číslo 'x-y' vrací '18333fig0x0y-tn.png'''

        n1, n2 = num.split('-')
        return '18333fig{:02}{:02}-tn.png'.format(int(n1), int(n2))


    def collect(self, text=None):
        '''Přidá aktuální parts do výstupní kolekce oddělí mezerou.'''

        if len(self.collection) > 0:
            self.collection.append(' ')

        if text is not None:
            self.collection.append(text)
        else:
            self.collection.extend(self.parts)


    def write_collection(self):
        '''Zapíše kolekci na výstup jako jeden řádek a vyprázdní ji.'''

        if len(self.collection) > 0:
            self.fout.write(''.join(self.collection) + '\n')
            self.collection = []


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

            # Pouze číslo s tečkou/tečkami.
            m = self.rexNum.match(self.line)
            if m:
                num = m.group('num')
                self.type = 'num'
                self.parts = [num]
                return

            # Nečíslovaná odrážka (bullet) -- markdown syntaxe.
            m = self.rexBullet.match(self.line)
            if m:
                text = m.group('text')
                self.type = 'uli'        # ListItem nečíslovaného seznamu
                self.parts = ['*\t', text]  # markdown reprezentace...
                return

            # Úvodní unicode znak nečíslované odrážky.
            m = self.rexUXBullet.match(self.line)
            if m:
                self.type = 'xuli'          # jen znak zahajující odrážku
                self.parts = ['*\t']
                return

            # Nečíslovaná odrážka s unicode znakem, asi bez tabulátoru.
            m = self.rexUBullet.match(self.line)
            if m:
                text = m.group('text')
                self.type = 'uli'           # ListItem nečíslovaného seznamu
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
                self.parts = ['Insert {}\n'.format(self.png_name(num)) + \
                              'Obrázek {}. {}'.format(num, text)]
                return

            # Rozhraní mezi stránkami.
            m = self.rexPagesep.match(self.line)
            if m:
                self.type = 'pagesep'
                self.parts = []
                return

            # Řádek s potenciálním příkladem kódu.
            m = self.rexXCode.match(self.line)
            if m:
                self.type = 'xcode'
                self.parts = ['\t', m.group('text')]
                return

            # Řádek se zadaným příkladem kódu.
            m = self.rexCode.match(self.line)
            if m:
                self.type = 'code'
                self.parts = ['\t', m.group('text')]
                return

            # Nerozpoznaný případ.
            self.type = '?'
            self.parts = [ self.line.rstrip() ]


    def run(self):
        self.fout = open(os.path.join(aux_dir, 'pass2.txt'), 'w', encoding='utf-8')

        with open(self.fname_in, encoding='utf-8') as fin:

            self.status = 0
            while self.status != 888:

                self.line = fin.readline()
                self.parse_line()

                if self.type == 'EOF':
                    self.status = 888

                if self.status == 0:            # ------- základní stav
                    if self.type == 'empty':
                        self.collect()
                        self.write_collection() # zapíše prázdný řádek

                    elif self.type == 'pagesep':
                        self.write_collection() # nezapíše nic

                    elif self.type == 'title':
                        # Číslo nadpisu změníme na abstraktní označení
                        # a zapíšeme řádek nadpisu.
                        xxx = abstractNum(self.parts[0])
                        self.collect(xxx)
                        self.collect(self.parts[1])
                        self.collect(xxx)
                        self.write_collection()

                        # Většině nadpisů chybí oddělení prázdným řádkem.
                        # Přidáme jej natvrdo.
                        self.collect('')
                        self.write_collection()

                    elif self.type == 'xcode':
                        self.collect()
                        self.write_collection() # řádky kódu se neslepují
                        self.status = 1         # další řádky až do empty

                    elif self.type == 'code':
                        # Správně a explicitně určený řádek s příkladem kódu
                        # nebo s nějakým textovým výstupem. Provedeme výstup
                        # tohoto řádku a nečiníme žádné speciální předpoklady.
                        self.collect()
                        self.write_collection()

                    elif self.type == 'xuli':
                        # Dobře rozpoznaný zahajovací znak odrážky.
                        self.collect()
                        self.status = 2         # sběr textu odrážky

                    elif self.type == 'uli':
                        # Dobře rozpoznaný zahajovací znak + řádek odrážky.
                        self.collect()
                        self.status = 3         # sběr textu odrážky

                    elif self.type == 'li':
                        # Dobře rozpoznaná položka číslovaného seznamu.
                        self.collect()
                        self.status = 6         # sběr textu položky

                    elif self.type == 'num':
                        # Pravděpodobně špatně zalomený nadpis nebo položka
                        # číslovaného seznamu.
                        self.collect()
                        self.status = 4        # očekává se řádek s textem

                    else:
                        # Diagnostický výstup.
                        self.fout.write('{}|{}\n'.format(self.type,
                                                         ' '.join(self.parts)))

                elif self.status == 1:          # ------- až do empty jako code
                    if self.type == 'empty':
                        self.collect()
                        self.write_collection() # prázdný řádek na výstup
                        self.status = 0
                    else:
                        # Typ a parts položky mohou být odhadnuty chybně. Tento
                        # řádek se nachází v souvislém bloku za 'xcode', takže
                        # jej budeme reinterpretovat jako 'xcode'.
                        self.type = 'xcode'
                        self.parts = ['\t', self.line.rstrip()]
                        self.collect()
                        self.write_collection() # řádky kódu se neslepují

                elif self.status == 2:          # ------- první řádek odrážky
                    self.collect(self.line.strip())
                    self.status = 3

                elif self.status == 3:          # ------- další řádek odrážky
                    if self.type == '?':
                        self.collect()          # pokračovat ve sběru
                    elif self.type == 'empty':
                        self.write_collection()
                        self.collect()          # ukončeno prázdným řádkem
                        self.write_collection()
                        self.status = 0
                    elif self.type == 'uli':
                        self.write_collection() # předchozí odrážka
                        self.collect()          # řádek s další odrážkou
                        self.status = 3         # zůstaneme ve stejném stavu
                    elif self.type == 'xuli':
                        self.write_collection() # předchozí odrážka
                        self.collect()          # jen značka
                        self.status = 2
                    else:
                        self.status = 'unknown after {}'.format(self.status)

                elif self.status == 4:          # ------- očekává text po num
                    if self.type == '?':
                        num = self.collection[0]
                        text = self.parts[0]

                        if num in toc and toc[num] == text:
                            # Je to nadpis. Nahradíme číslo abstraktním označením
                            # úrovně.
                            self.collect()
                            xxx = abstractNum(self.collection[0])
                            self.collection[0] = xxx
                            self.collect(xxx)
                            self.write_collection()

                            # Prázdný řádek po špatně zalomeném nadpisu.
                            self.collect('')
                            self.write_collection()
                            self.status = 0     # do základního stavu
                        else:
                            # Je to číslovaná položka seznamu.
                            self.collection[0] = num + '\t' # přidat tabulátor
                            self.collect()      # zahájit sběr číslované položky
                            self.status = 5
                    else:
                        self.status = 'unknown after {}'.format(self.status)

                elif self.status == 5:          # ------- sběr špatně zalomené 3. item
                    if self.type == '?':
                        self.collect()          # pokračovat ve sběru
                    elif self.type == 'empty':
                        self.write_collection()
                        self.collect()          # ukončeno prázdným řádkem
                        self.write_collection()
                        self.status = 0
                    elif self.type == 'pagesep':
                        self.write_collection()
                        self.collect('')        # ukončeno prázdným řádkem
                        self.write_collection()
                        self.status = 0
                    elif self.type == 'num':
                        self.write_collection() # předchozí bod
                        self.collect()          # jen číslo
                        self.status = 4
                    else:
                        self.status = 'unknown after {}'.format(self.status)

                elif self.status == 6:          # ------- řádek za položkou číslovaného seznamu
                    if self.type == '?':
                        self.collect()          # pokračovat ve sběru
                    elif self.type == 'empty':
                        self.write_collection()
                        self.collect()          # ukončeno prázdným řádkem
                        self.write_collection()
                        self.status = 0
                    elif self.type == 'li':
                        self.write_collection() # vypíšeme předchozí bod
                        self.collect()          # zahájíme sběr dalšího
                        # Zůstaneme ve stejném stavu.
                    else:
                        self.status = 'unknown after {}'.format(self.status)
                elif self.status == 888:        # ------- akce po EOF
                    pass

                else:
                    # Neznámý stav. Indikujeme na výstupu a vypíšeme
                    # sesbíranou kolekci.
                    self.fout.write('!!! Neznámý stav: {}\n'.format(self.status))

        # Uzavřeme výstupní soubor.
        self.fout.close()

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