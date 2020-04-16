# Copyright 2020 RoadrunnerWMC
#
# This file is part of Newer Tileset Animations Tool.
#
# Newer Tileset Animations Tool is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Newer Tileset Animations Tool is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Newer Tileset Animations Tool.  If not, see
# <https://www.gnu.org/licenses/>.

import argparse
import pathlib
import shutil

from PyQt5 import QtCore, QtGui; Qt = QtCore.Qt

import rgb4a3
import u8


def isAnimFilename(fn):
    """
    Check if the provided filename matches the tile animation filename
    convention:
        xxxxx_nnn.bin
    where "x" is any character (and there are any amount of them), and
    "nnn" is a 3-digit hex number between 000 and 3FF inclusive (either
    upper- or lowercase)
    """
    if not fn.lower().endswith('.bin'): return False
    if len(fn) < 9: return False # "x_nnn.bin" -- must have at least 1 x

    if fn[-8] != '_': return False
    if fn[-7] not in '0123': return False
    if fn[-6].lower() not in '0123456789abcdef': return False
    if fn[-5].lower() not in '0123456789abcdef': return False

    return True


def findAnimationFilenames(tset):
    """
    Given a tileset dictionary (in the form returned by u8.py), return
    a dictionary mapping animation data filenames (without "BG_tex/") to
    their file data.
    """
    BG_tex = tset.get('BG_tex', {})

    animFiles = {}
    for fn, data in BG_tex.items():
        if not isinstance(data, bytes):
            continue

        if isAnimFilename(fn):
            animFiles[fn] = data

    return animFiles


def analyzeAnimFilenames(fns):
    """
    Given a set of animation filenames, return their prefix string and
    whether the tile ID hex values are upper- or lowercase.
    (If the casing is impossible to determine, default to uppercase
    because that's what the majority of tilesets use.)
    """
    # The prefix strings *should* all be the same, and it's unclear what
    # to do if they're not the same, so let's just take the first one
    # and assume it applies to all of them
    first = next(iter(fns))
    prefix = first[:first.index('_')]

    # Assume the tile ID is uppercase unless we can prove it's lowercase
    isUpper = True
    for fn in fns:
        if fn[-6] in 'abcdef' or fn[-5] in 'abcdef':
            isUpper = False
            break

    return prefix, isUpper


def clamp(tile):
    """
    Given a 24x24 QImage, return a clamped 32x32 one.
    (From Puzzle)
    """
    minitex = QtGui.QImage(32, 32, QtGui.QImage.Format_ARGB32)
    minitex.fill(Qt.transparent)

    minipainter = QtGui.QPainter(minitex)
    minipainter.drawImage(4, 4, tile)
    minipainter.end()

    for i in range(4,28):

        # Top Clamp
        color = minitex.pixel(i, 4)
        for p in range(0,4):
            minitex.setPixel(i, p, color)

        # Left Clamp
        color = minitex.pixel(4, i)
        for p in range(0,4):
            minitex.setPixel(p, i, color)

        # Right Clamp
        color = minitex.pixel(i, 27)
        for p in range(27,31):
            minitex.setPixel(i, p, color)

        # Bottom Clamp
        color = minitex.pixel(27, i)
        for p in range(27,31):
            minitex.setPixel(p, i, color)

    # UpperLeft Corner Clamp
    color = minitex.pixel(4, 4)
    for x in range(0,4):
        for y in range(0,4):
            minitex.setPixel(x, y, color)

    # UpperRight Corner Clamp
    color = minitex.pixel(27, 4)
    for x in range(27,31):
        for y in range(0,4):
            minitex.setPixel(x, y, color)

    # LowerLeft Corner Clamp
    color = minitex.pixel(4, 27)
    for x in range(0,4):
        for y in range(27,31):
            minitex.setPixel(x, y, color)

    # LowerRight Corner Clamp
    color = minitex.pixel(27, 27)
    for x in range(27,31):
        for y in range(27,31):
            minitex.setPixel(x, y, color)

    return minitex


def handleExport(args):
    """
    Export tileset animations
    """
    # Load tileset
    with open(args.file, 'rb') as f:
        tset = u8.load(f.read())

    # Find animation files
    animFiles = findAnimationFilenames(tset)

    if not animFiles:
        print('Error: no animations found in this tileset. Aborting.')
        return

    # Get some info regarding their filenames
    prefix, isUpper = analyzeAnimFilenames(animFiles)

    # Prepare output directory
    if args.output_dir is None:
        args.output_dir = pathlib.Path(str(args.file) + '_anims')
    if args.output_dir.is_dir():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True)

    # Save config file
    upperStr = 'uppercase' if isUpper else 'lowercase'
    (args.output_dir / 'info.txt').write_text(f'{prefix}\n{upperStr}', encoding='utf-8')

    # Save all frames
    for fn, animData in animFiles.items():
        tileNum = int(fn[-7:-4], 16)
        x = tileNum & 0xF
        y = (tileNum >> 4) & 0xF

        numFrames = len(animData) // 2048
        for n in range(numFrames):
            frameData = animData[2048 * n : 2048 * (n + 1)]
            frame = rgb4a3.RGB4A3Decode(frameData, 32, 32).copy(4, 4, 24, 24)
            frame.save(str(args.output_dir / f'{y:02d}_{x:02d}_{n:02d}.png'))


def handleImport(args):
    """
    Import tileset animations
    """
    # Load info.txt, and also guess Pa number
    info = (args.dir / 'info.txt').read_text(encoding='utf-8')
    prefix, case = info.split('\n')[:2]
    isUpper = (case.lower() != 'lowercase')
    pa = {'0': 0, '1': 1, '2': 2, '3': 3}.get(args.file.name[2], 1)

    # Apply any CLI overrides for those values
    if args.prefix is not None:
        prefix = args.prefix

    if args.case == 'lower':
        isUpper = False
    elif args.case == 'upper':
        isUpper = True

    if args.pa is not None:
        pa = args.pa

    # Load all animation data filenames
    frames = {}
    for fn in args.dir.glob('*.png'):
        if len(fn.name) != 12: continue
        if fn.name[0] not in '0123456789': continue
        if fn.name[1] not in '0123456789': continue
        if fn.name[2] != '_': continue
        if fn.name[3] not in '0123456789': continue
        if fn.name[4] not in '0123456789': continue
        if fn.name[5] != '_': continue
        if fn.name[6] not in '0123456789': continue
        if fn.name[7] not in '0123456789': continue

        row = int(fn.name[:2])
        col = int(fn.name[3:5])
        n = int(fn.name[6:8])
        assert row < 16
        assert col < 16

        tileNum = (pa << 8) | (row << 4) | col

        if tileNum not in frames:
            frames[tileNum] = {}
        frames[tileNum][n] = fn

    # Create animation data files
    animationFiles = {}
    for tileNum, frameFilenames in frames.items():
        animData = bytearray()

        n = 0
        while n in frameFilenames:
            frame = clamp(QtGui.QImage(str(frameFilenames[n])))
            animData += rgb4a3.RGB4A3Encode(frame)
            n += 1

        tileNumStr = f'{tileNum:03x}'
        if isUpper: tileNumStr = tileNumStr.upper()
        animationFiles[f'{prefix}_{tileNumStr}.bin'] = animData

    # Load tileset file
    with open(args.file, 'rb') as f:
        tset = u8.load(f.read())

    # Find existing animation files
    animFiles = findAnimationFilenames(tset)

    # Remove them all, unless --add was specified
    if not args.add:
        for fn in animFiles:
            tset['BG_tex'].pop(fn)

    # Add the new ones
    tset['BG_tex'].update(animationFiles)

    # And save it
    if args.output_file is None:
        args.output_file = args.file
    args.output_file.write_bytes(u8.save(tset))



def main(args=None):
    """
    Main function for the CLI
    """
    app = QtGui.QGuiApplication([])

    # Main argument parser
    parser = argparse.ArgumentParser(
        description='Newer Wii Tileset Animations Tool: import or export tileset animations')
    subparsers = parser.add_subparsers(title='commands',
        description='(run a command with -h for additional help)')

    # Export
    parser_export = subparsers.add_parser('export', aliases=['e'],
                                          help='export animations')
    parser_export.add_argument('file', type=pathlib.Path,
        help='tileset file to export animations from')
    parser_export.add_argument('output_dir', nargs='?', type=pathlib.Path,
        help='directory to store exported animation data in (will be cleared if already exists) (default: input filename plus "_anims")')
    parser_export.set_defaults(func=handleExport)

    # Import
    parser_import = subparsers.add_parser('import', aliases=['i'],
                                          help='import animations (replacing all existing ones, unless --add is specified)')
    parser_import.add_argument('file', type=pathlib.Path,
        help='tileset file to import animations into')
    parser_import.add_argument('dir', type=pathlib.Path,
        help='directory to load animation data from')
    parser_import.add_argument('output_file', nargs='?', type=pathlib.Path,
        help='what to save the output file as (default: overwrite the input file)')
    parser_import.add_argument('--add', action='store_true',
        help="don't delete existing animation data for other tiles in the tileset. Warning: this may result in inconsistent tilesets with multiple different animation filename prefixes!")
    parser_import.add_argument('--pa', choices=[0, 1, 2, 3], type=int,
        help='tileset number (default: infer from tileset filename)')
    parser_import.add_argument('--prefix',
        help='set the prefix string to use for the animation filenames, overriding the one in info.txt (normally 2-3 characters long)')
    parser_import.add_argument('--case', choices=['lower', 'upper'],
        help='set the capitalization to use for the animation filenames, overriding the one in info.txt')
    parser_import.set_defaults(func=handleImport)

    # Parse args and run appropriate function
    pArgs = parser.parse_args(args)
    if hasattr(pArgs, 'func'):
        pArgs.func(pArgs)
    else:  # this happens if no arguments were specified at all
        parser.print_usage()


if __name__ == '__main__':
    main()
