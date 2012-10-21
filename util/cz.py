#!python3
# -*- coding: utf-8 -*-

'Skript pro zpracování extrahovaného txt z českého překladu v podobě PDF.'

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
    '''

    # Vytvoříme čerstvý pomocný podadresář s extrahovanými informacemi.
    if os.path.isdir(aux_dir):
        shutil.rmtree(aux_dir)
    os.mkdir(aux_dir)

    # TOC line example: "1.1 Správa verzí -- 17"
    # where '--' is the Em-dash.
    patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'
    patTOCitem = patNum + r'\s+(?P<title>.+?)(\s+\u2014)?(\s+(?P<pageno>\d+)\s*)'

    rexTOCline = re.compile(r'^' + patTOCitem + r'$')
    rexObsah = re.compile(r'^\u2014\s+(?P<title>Obsah.*?)(\s+(?P<pageno>\d+)\s*)$')

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

            if status == 0:             # -------
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
                        ftoc.write('{} {}\n'.format(m.group('num'),
                                                    m.group('title')))
                        fignored.write('TOC: ' + line)
                    else:
                        fignored.write(line)    # ignorujeme prázdné...


            elif status == 3:           # ------- záhlaví stránky po Obsahu
                fph.write(line)
                fignored.write('PH: ' + line)
                status = 4

            elif status == 4:           # ------- textové řádky lines
                if line.startswith('\f'):       # FormFeed
                    fignored.write(line)
                    status = 3
                else:
                    fout.write(line)    # běžný platný řádek

            elif status == 888:         # ------- akce po EOF
                pass


def second_pass(fname, aux_dir):
    toc = []
    page_headers = []
    chapters = []
    chapter_content = None

    # TOC line example: "1.1 Správa verzí -- 17"
    # where '--' is the Em-dash.
    patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'
    patTOC = patNum + r'\s+(?P<title>.+?)(\s+\u2014)?(\s+(?P<pageno>\d+)\s*)'

    rexTOC = re.compile(r'^' + patTOC + r'$')
    rexHeadingU = re.compile(r'^\u2014\s+(?P<title>.+?)(\s+(?P<pageno>\d+)\s*)$')
    rexTitle = re.compile(r'^' + patNum + r'\s+(?P<title>.+?)\s*$')

    page_header = None  # init -- the page header string (just below form feed)

    with open(fname, encoding='utf-8') as f:

        status = 0
        while status != 888:

            line = f.readline()
            if line == '':
                status = 888                    # EOF

            if status == 0:             # -------
                if line.startswith('\f'):       # FormFeed
                    status = 1

            elif status == 1:           # ------- the page header lines before TOC
                page_headers.append(line.rstrip())

                m = rexHeadingU.match(line)
                if m and m.group('title') == 'Obsah':
                    status = 2                  # start collecting TOC
                else:
                    status = 0                  # wait for next FF

            elif status == 2:           # ------- collecting TOC
                if line.startswith('\f'):       # FormFeed ends the TOC
                    status = 3
                else:
                    m = rexTOC.match(line)
                    if m:
                        toc.append((m.group('num'), m.group('title')))

            elif status == 3:           # ------- the page header lines after TOC
                page_header = line.rstrip()
                page_headers.append(page_header)
                status = 4                      # wait for next FF

            elif status == 4:           # ------- text lines
                if line.startswith('\f'):       # FormFeed
                    status = 3
                else:
                    m = rexTitle.match(line)    # numbered chapter, sectio... title
                    if m:
                        x = abstractNum(m.group('num'))
                        if len(x) == 1:
                            # Close the previous chapter and start the new one.
                            # Append the chapter title.
                            if chapter_content is not None:
                                chapters.append(chapter_content)
                            s = '{} {} {}\n\n'.format(x, m.group('title'), x)
                            chapter_content = [s]
                        else:
                            # Append the section or subsection title.
                            s = '{} {} {}\n\n'.format(x, m.group('title'), x)
                            chapter_content.append(s)
                    else:
                        # Append normal line. Ignore the lines before
                        # the first chapter.
                        if chapter_content is not None:
                            chapter_content.append(line)

            elif status == 888:         # ------- actions after EOF
                # Append the last chapter.
                chapters.append(chapter_content)

    return toc, page_headers, chapters


if __name__ == '__main__':

    # Auxiliary subdirectory for the extracted information.
    aux_dir = os.path.realpath('../info_aux_cz')

    # Extract the information from the Czech translation text file
    # (captured from CZ.NIC PDF and manually edited ).
    first_pass('../txtFromPDF/scott_chacon_pro_git_CZ.txt', aux_dir)
