import re

class Parser:
    '''Parser pro čtvrtý průchod -- značkování a kontroly.

       Konzumuje výstup třetího průchodu přímo ve formě objektu pass3.'''

    def __init__(self, pass3):
        self.cs_aux_dir = pass3.cs_aux_dir    # pomocný adresář pro české výstupy
        self.en_aux_dir = pass3.en_aux_dir    # pomocný adresář pro anglické výstupy


    def run(self):
        '''Spouštěč jednotlivých fází parseru.'''

        print('\nZatím neimplementován.\a\a\a')
    #
    # Kontrolovat identifikace souborů s obrázky (elementy).
    # Kontrolovat čísla obrázků (elementy).
    #
    # Hledáme značkování uvnitř 'para' elementů. U některých podřetězců můžeme
    # do českého překladu doplnit značkování přímo:
    #  - opačné apostrofy obalují úryvky kódu, který by měl být převzatý 1:1,
    #  - kontrolujeme výskyt podřetězců v opačných apostrofech v cs,
    #  - plníme množinu podřetězců v opačných apostrofech (zapíšeme seřazené
    #    do souboru),
    #  - navrhneme doplnění opačných apostrofů i do míst, kde jsou v originále
    #    zapomenuty (není jasné, co vše se najde; zatím do odděleného souboru),
    #  - obyčejné dvojité uvozovky měníme na české (? -- zatím do odděleného souboru),
    #
    # Další typy značkování jen nahlásíme a budeme asi doplňovat ručně
    # (kurzíva, tučné, ...).
    #
    # V 'para' kontrolovat správnost odkazů na obrázky (vůči originálu).
