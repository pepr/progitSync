#!python3
# -*- coding: utf-8 -*-

'''Skript pro srovnávání již dříve synchronizovaného cs překladu a en originálu.'''

import os
import sys

import pass1
import pass2

# Adresáře s originálními podadresáři a soubory.
en_src_dir = os.path.abspath('../../progit/en')
cs_src_dir = os.path.abspath('../../progit/cs')

# Pomocné podadresáře pro generované informace.
cs_aux_dir = os.path.realpath('../info_aux_cs')
if not os.path.isdir(cs_aux_dir):
    os.makedirs(cs_aux_dir)

en_aux_dir = os.path.realpath('../info_aux_en')
if not os.path.isdir(en_aux_dir):
    os.makedirs(en_aux_dir)

# V prvním průchodu sesbíráme informace jednak z originálu a jednak
# z překladu (stejným algoritmem). Vycházíme z čerstvého commitu originálního
# gitovského repozitáře.
#
# Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
# příklady kódu) porovnáváme za účelem zjištění rozdílů struktury. Některé
# informace se porovnávají podrobněji (příklady kódu, identifikace obrázků),
# u některých elementů se porovnává jen druh elementu (existence odstavce,
# existence odrážky, úroveň nadpisu,...).
print('pass 1:')
parser1 = pass1.Parser(cs_src_dir, en_src_dir, cs_aux_dir, en_aux_dir)
msg = parser1.run()
print('\t' + msg)

# V druhém průchodu vycházíme z předpokladu, že se struktura dokumentu
# shoduje. Už generujeme cílovou strukturu cs/, ale pro další strojové
# korekce budeme stále vycházet z informací získaných v předchozím kroku.
print('pass 2:')
parser2 = pass2.Parser(parser1)
msg = parser2.run()
print('\t' + msg)
