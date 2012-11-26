#!python3
# -*- coding: utf-8 -*-

import re
'''Capturing one line of a document and converting it to an object.'''


class Element:
    '''Rozpoznané Elementy dokumentu odpovídající řádkům zdrojového textu.'''

    # Řádek se symbolicky uvedeným nadpisem (#### Nadpis ####).
    rexTitle = re.compile(r'^(?P<level>#+)\s+(?P<title>.+?)\s+\1\s*$')

    # Nečíslovaná odrážka korektně explicitně zapsaná (markdown syntaxe).
    rexBullet = re.compile(r'^\*\s+(?P<uli>.+?)\s*$')

    # Příkaz pro vložení obrázku.
    rexInsImg = re.compile(r'^Insert\s+(?P<img>\d+fig\d+\.png)\s*$')

    # Popis obrázku.
    rexImgCaption = re.compile(r'^(Fig(ure)?|Obrázek)\.\s+(?P<num>\d+.+\d+).?\s+(?P<text>.+?)\s*$')

    # Příklad kódu.
    rexCode = re.compile(r'^( {4}|\t)(?P<code>.+?)\s*$')

    # Položka číslovaného seznamu.
    rexLi = re.compile(r'^(?P<num>\d+\.)\t(?P<text>.+?)\s*$')

    def __init__(self, fname, lineno, line):
        self.fname = fname      # původní zdrojový soubor
        self.lineno = lineno    # číslo řádku ve zdrojovém souboru
        self.line = line        # původní řádek

        self.type = None        # typ elementu
        self.attrib = None      # init -- atributy elementu (význam dle typu)

        # Řádek obsahující jen whitespace považujeme za prázdný
        # řádek ve významu oddělovače.
        if self.line.isspace():
            self.type = 'empty'
            self.attrib = ''   # reprezentací bude prázdný řetězec
            return

        # Řádek s nadpisem.
        m = self.rexTitle.match(line)
        if m:
            self.type = 'title'
            self.attrib = (len(m.group('level')), m.group('title'))
            return

        # Odrážka.
        m = self.rexBullet.match(line)
        if m:
            self.type = 'uli'
            self.attrib = m.group('uli')
            return

        # Položka číslovaného seznamu.
        m = self.rexLi.match(line)
        if m:
            self.type = 'li'
            self.attrib = (m.group('num'), m.group('text'))
            return

        # Řádek pro vložení souboru obrázku.
        m = self.rexInsImg.match(line)
        if m:
            self.type = 'img'
            self.attrib = m.group('img')
            return

        # Řádek s popisem obrázku.
        m = self.rexImgCaption.match(line)
        if m:
            self.type = 'imgcaption'
            self.attrib = (m.group('num'), m.group('text'))
            return

        # Řádek s kódem.
        m = self.rexCode.match(line)
        if m:
            self.type = 'code'
            self.attrib = m.group('code')
            return

        # Prázdný řádek odpovídá situaci, kdy skončil soubor a další řádek
        # nebylo možno načíst. Neměl by nastávat, ale pro jistotu.
        if self.line == '':
            # Z pohledu řešeného problému to tedy není prázdný řádek
            # ve významu oddělovače.
            self.type = 'EOF'
            self.attrib = None
            return

        # Ostatní případy budeme považovat za odstavec.
        self.type = 'para'
        self.attrib = line.rstrip()


    def __repr__(self):
        return repr((self.fname, self.lineno, self.type, self.attrib))


    def __str__(self):
        return self.line
