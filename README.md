# progitSync -- Synchronizing the translation with the original

Project for synchronizing and for improvement of the translations
of Scott Chacon's "Pro Git". The Git repository with the sources
of the book is available at https://github.com/progit/progit.

The implementation language of the scripts is Python 3.

## Goal

The main goal is to help human translators to keep their translation
in sync with the changes of the English original.

This is rather new project. Contact me if you have any suggestions.

## Notes

The project is actually a by-product of the older one (progitCZ; still present
in the earlier commits of the Git repository). Originally, it was the tool to convert
the Czech translation was published in CZ.NIC Edition
of the CZ.NIC association (see http://knihy.nic.cz/page/351/ -- switch
to English/Czech at the top of the page). The book is available both as printed
book and the free PDF document at http://knihy.nic.cz/
(http://knihy.nic.cz/files/nic/edice/scott_chacon_pro_git.pdf).

## The original goals of the `progitCZ` were:

1. The first goal was to convert the translation in the PDF form back to the markdown syntax used by
   Scott Chacon. This goal should enable the synchronization of the newer parts
   of original with the translation. The first conversion were finished 3rd November 2012.

2. The second goal was to replace the partial Czech translation
   at http://git-scm.com/book/cs at the time. The idea was to make
   the translation widely available on-line at the very prominent and
   well known site -- the source of Git. The repository is available
   as multilingual project at https://github.com/progit/progit.
   The Czech update was published here in 12th November 2012.

3. The third (long term) project was to make the translation easily
   synchronized and updated--based on the changes in the original--alive and
   widely available to the Czech users. The GitHub Issues tool can be
   used for collecting suggestions.
