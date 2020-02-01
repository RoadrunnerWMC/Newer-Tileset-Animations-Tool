Newer Tileset Animations Tool
=============================

A little tool for importing/exporting animations to/from Newer SMB Wii
tilesets. Not compatible with LH-compressed tilesets, and also doesn't support
retail-style Pa0 animation data.

Requires Python 3.6 or newer.


Format of extracted animations
------------------------------

The extracted animations are saved as a folder containing PNGs of animation
frames, each with a filename in the form `[row]_[column]_[n].png`, where each
of those fields is a 2-digit decimal number. Row/column refer to the tile's
position in the main tileset texture (0-indexed), and "n" is the animation
frame number (also 0-indexed).

In addition to the PNGs, the folder must also contain an "info.txt" file. The
first line of this file specifies the 2- or 3-character prefix to use in all of
the internal animation filenames. The second line must be either "uppercase" or
"lowercase", and controls the casing to use for the hexadecimal values in the
internal animation filenames (the files in Newer Wii itself aren't consistent
in this regard). While info.txt is required to be present in the folder, the
values in it can be overridden via optional command-line arguments when
importing.


Usage -- Exporting
------------------

Exporting is done with the "export" (or "e", for short) command.

    $ python3 main.py export -h
    usage: main.py export [-h] file [output_dir]

    positional arguments:
      file        tileset file to export animations from
      output_dir  directory to store exported animation data in (will be cleared
                  if already exists) (default: input filename plus "_anims")

    optional arguments:
      -h, --help  show this help message and exit


Usage -- Importing
------------------

Importing is done with the "import" (or "i", for short) command.

    $ python3 main.py import -h  
    usage: main.py import [-h] [--add] [--pa {0,1,2,3}] [--prefix PREFIX]
                          [--case {lower,upper}]
                          file dir [output_file]

    positional arguments:
      file                  tileset file to import animations into
      dir                   directory to load animation data from
      output_file           what to save the output file as (default: overwrite
                            the input file)

    optional arguments:
      -h, --help            show this help message and exit
      --add                 don't delete existing animation data for other tiles
                            in the tileset. Warning: this may result in
                            inconsistent tilesets with multiple different
                            animation filename prefixes!
      --pa {0,1,2,3}        tileset number (default: infer from tileset filename)
      --prefix PREFIX       set the prefix string to use for the animation
                            filenames, overriding the one in info.txt (should be
                            2-3 characters long)
      --case {lower,upper}  set the capitalization to use for the animation
                            filenames, overriding the one in info.txt