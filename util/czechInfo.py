#!python3
'''\
Skript pro zjištění všech nadpisů kapitol, podkapitol, ... z extrahovaného
českého překladu knihy.
'''

import collections
import os
import re

def extractCZ(fname):
    toc = []
    page_headers = []
    headings = []

    # TOC line example: "1.1 Správa verzí -- 17"
    # where '--' is the Em-dash.
    patNum = r'(?P<num>(?P<num1>\d+)\.(?P<num2>\d+)?(\.(?P<num3>\d+))?)'
    patTOC = patNum + r'\s+(?P<title>.+?)(\s+\u2014)?(\s+(?P<pageno>\d+)\s*)'

    rexTOC = re.compile(r'^' + patTOC + r'$')
    rexHeadingU = re.compile(r'^\u2014\s+(?P<title>.+?)(\s+(?P<pageno>\d+)\s*)$')

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
                        toc.append((m.group('num'),
                                    m.group('title'),
                                    ))

            elif status == 3:           # ------- the page header lines after TOC
                page_header = line.rstrip()
                page_headers.append(page_header)
                status = 4                      # wait for next FF

            elif status == 4:           # ------- text lines
                if line.startswith('\f'):       # FormFeed
                    status = 3
                else:
                    m = rexTOC.match(line)      # TOC-like line in the text
                    if m:
                        headings.append(line.rstrip())


    return toc, page_headers, headings



if __name__ == '__main__':

    # Auxiliary subdirectory for the extracted information.
    # Create it if it does not exist.
    aux_dir = os.path.abspath('../info_aux_cz')
    if not os.path.isdir(aux_dir):
        os.mkdir(aux_dir)

    # Extract the information from the Czech translation text file (captured
    # and manually edited PDF with the CZ.NIC translation).
    toc, page_headers, headings = extractCZ('../txtFromPDF/scott_chacon_pro_git_CZ.txt')

    # TOC
    with open(os.path.join(aux_dir, 'czTOC.txt'), 'w', encoding='utf-8') as f:
        for num, title in toc:
            f.write('{} {}\n'.format(num, title))

        # TOC formatted the src-input way.
        f.write('------------------------------------------------------\n')
        for num, title in toc:
            # Get the level of the title and construct the '#', '##', or '###'.
            lst = num.split('.')
            if lst[-1] == '':    # chapter numbering ends with dot
                del lst[-1]
            x = '#' * len(lst)

            # The TOC with symbolic levels of titles (no explicit numbering).
            f.write('{} {} {}\n'.format(x, title, x))

    # Page headers
    with open(os.path.join(aux_dir, 'PageHeaders.txt'), 'w', encoding='utf-8') as f:
        for line in page_headers:
            f.write(line + '\n')

    # Headings
    with open(os.path.join(aux_dir, 'Headings.txt'), 'w', encoding='utf-8') as f:
        for line in headings:
            f.write(line + '\n')

