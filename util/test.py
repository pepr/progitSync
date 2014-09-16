#!python3

import difflib

en = ['a', 'b', 'bb', 'c', 'x', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p']
xx = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']

diff = difflib.ndiff(xx, en)
print(list(diff))