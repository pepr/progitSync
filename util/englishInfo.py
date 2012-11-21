#!python3
'''\
Script for extraction of chapter titles, section titles, subsection
titles, ... from the English original text sources. The text directory
is relative to this one -- see the body of the program.
'''

import gen
import os
import re
import sys



if __name__ == '__main__':

    # Auxiliary subdirectory for the extracted information.
    # Create it if it does not exist.
    aux_dir = os.path.abspath('../info_aux_en')
    if not os.path.isdir(aux_dir):
        os.mkdir(aux_dir)

    # Get the directory with the text sources of the original.
    text_dir = os.path.abspath('../../progit/en')

    # Write the list of source files to the file.
    with open(os.path.join(aux_dir, 'files.txt'), 'w') as f:
        for fname in gen.sourceFiles(text_dir):
            f.write(fname + '\n')

    # Generate a plain text document as concatenation of the source files.
    # The returned fname is filename relative to the text_dir (i.e. in the form
    # of 'subdir/source_file.markdown'.
    with open(os.path.join(aux_dir, 'sourceLines.txt'), 'w', encoding='utf-8') as f:
        last_name = ''
        for fname, line in gen.sourceFileLines(text_dir):
            # The generator also yields items with None instead of filename
            # for separation newlines. Write a header that tells the filename.
            if fname is not None and fname != last_name:
                f.write('\n-----------------------------------------------------\n')
                f.write('{}:\n'.format(fname));
                f.write('-----------------------------------------------------\n')
                last_name = fname

            # The line of the book.
            f.write(line)

    # Write the TOC to the file. First, with generated numbering; then
    # with symbolic TOC levels.
    with open(os.path.join(aux_dir, 'enTOC.txt'), 'w', encoding='utf-8') as f:

        cnt = [0, 0, 0, 0, 0]  # init -- chapter, section, and subsection counters
        for fname, num, title in gen.toc(text_dir):
            # The num is the symbolic numbering level '###', '##' or '#'.
            # Increase the appropriate level counter and zero the next counters.
            level = len(num) - 1  # index of the cnt for the title level
            cnt[level] += 1       # increment the level counter
            for n in range(level+1, len(cnt)):
                cnt[n] = 0        # init the sublevels

            # Build the number from the counters. Join the parts with dot.
            # If it is a single number, the dot will be used at the end.
            lst = [str(n) for n in cnt if n > 0 ]
            if len(lst) == 1:
                lst.append('')
            s = '.'.join(lst)

            f.write('{} {}\n'.format(s, title))
            ##f.write('{}  {} {}\n'.format(fname, s, title))

        f.write('------------------------------------------------------\n')
        for fname, num, title in gen.toc(text_dir):
            f.write('{} {} {}\n'.format(num, title, num))
