#!python3
# -*- coding: utf-8 -*-

'''Skript pro zpracování extrahovaného txt z českého překladu v podobě PDF.'''

import os
import pass1
import pass2
import pass3
import pass4

# Adresář s originálními podadresáři a soubory.
en_src_dir = os.path.abspath('../../progit/en')

# Pomocné podadresáře pro generované informace.
cs_aux_dir = os.path.realpath('../info_aux_cs')
if not os.path.isdir(cs_aux_dir):
    os.makedirs(cs_aux_dir)

en_aux_dir = os.path.realpath('../info_aux_en')
if not os.path.isdir(en_aux_dir):
    os.makedirs(en_aux_dir)

# Textový soubor, který je prvotním vstupem, který byl získán
# uložením PDF jako text a následnou ruční úpravou některých jevů,
# které vznikly ruční sazbou orientovanou na vzhled (tj. nikoliv
# na zachování struktury dokumentu).
csfname_pass1input = '../txtFromPDF/scott_chacon_pro_git_CZ.txt'

# Po manuálních úpravách výše zmíněného souboru dospějeme ke stavu,
# kdy bude vhodné výsledek uložit a poté manuálně upravovat tento.
# Používá už markdown syntaxi.
czfname_pass3input = '../txtCorrected/RucneUpravovanyVysledekPass2.txt'

# Pokud ručně okopírovaný výsledek druhého průchodu (používaný jako
# vstup třetího průchodu) dosud neexistuje, zavoláme první dva průchody.
if not os.path.isfile(czfname_pass3input):

    # Hlavním výsledkem prvního průchodu je soubor pass1.txt a vracený
    # slovník toc.
    print('pass 1:')
    parser1 = pass1.Parser(csfname_pass1input, cs_aux_dir)
    czTOC, msg = parser1.run()
    print('\t' + msg)

    # V druhém průchodu rozpoznáváme pass1.txt a generujeme pass2.txt.
    print('pass 2:')
    parser2 = pass2.Parser(os.path.join(cs_aux_dir, 'pass1.txt'), czTOC, cs_aux_dir)
    msg = parser2.run()
    print('\t' + msg)

    # Po ručních úpravách zdroje pro první průchod (provedena kontrola
    # pass2.txt lidskýma očima) okopírujeme pass2.txt ručně do odděleného
    # souboru, který budeme dále upravovat ručně. (Kdykoliv je možné srovnat
    # jej s nadále generovaným pass2.txt.) V tomto místě kontrolujeme, zda
    # soubor existuje.
    if not os.path.isfile(czfname_pass3input):
        print('\n\n\a\a\aRučně okopírovat pass2.txt do\n\t',
              repr(czfname_pass3input) + ' !!!\n\n')
        sys.exit(1)

# V třetím průchodu sesbíráme informace jednak z originálu a jednak
# z překladu (stejným algoritmem). Vycházíme z čerstvého commitu originálního
# gitovského repozitáře (17bb7f8e z 25.11.2012).
#
# Zjištěné posloupnosti elementů dokumentů (nadpisy, odstavce, obrázky,
# příklady kódu) porovnáváme za účelem zjištění rozdílů struktury. Některé
# informace se porovnávají podrobněji (příklady kódu, identifikace obrázků),
# u některých elementů se porovnává jen druh elementu (existence odstavce,
# existence odrážky, úroveň nadpisu,...).
print('pass 3:')
parser3 = pass3.Parser(czfname_pass3input, en_src_dir, cs_aux_dir, en_aux_dir)
msg = parser3.run()
print('\t' + msg)

# Ve čtvrtém průchodu vycházíme z předpokladu, že se struktura dokumentu
# shoduje. Už generujeme cílovou strukturu cs/, ale pro další strojové
# korekce budeme stále vycházet z informací získaných v předchozím kroku.
print('pass 4:')
parser4 = pass4.Parser(parser3)
msg = parser4.run()
print('\t' + msg)
