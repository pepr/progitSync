#!python3
# -*- coding: utf-8 -*-

'''Skript pro zpracování extrahovaného txt z českého překladu v podobě PDF.'''

import os
import pass1
import pass2
import pass3
import pass4


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
    parser1 = pass1.Parser('../txtFromPDF/scott_chacon_pro_git_CZ.txt',
                           cs_aux_dir)
    czTOC = parser1.run()
    print('done')

    # V druhém průchodu rozpoznáváme pass1.txt a generujeme pass2.txt.
    print('pass 2 ... ', end='')
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
