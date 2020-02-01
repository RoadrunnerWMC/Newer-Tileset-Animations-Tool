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

# (From Puzzle, modified somewhat)

import struct

from PyQt5 import QtCore, QtGui; Qt = QtCore.Qt


RGB4A3LUT = []
RGB4A3LUT_NoAlpha = []
def PrepareRGB4A3LUTs():
    global RGB4A3LUT, RGB4A3LUT_NoAlpha

    RGB4A3LUT = [None] * 0x10000
    RGB4A3LUT_NoAlpha = [None] * 0x10000
    for LUT, hasA in [(RGB4A3LUT, True), (RGB4A3LUT_NoAlpha, False)]:

        # RGB4A3
        for d in range(0x8000):
            if hasA:
                alpha = d >> 12
                alpha = alpha << 5 | alpha << 2 | alpha >> 1
            else:
                alpha = 0xFF
            red = ((d >> 8) & 0xF) * 17
            green = ((d >> 4) & 0xF) * 17
            blue = (d & 0xF) * 17
            LUT[d] = blue | (green << 8) | (red << 16) | (alpha << 24)

        # RGB555
        for d in range(0x8000):
            red = d >> 10
            red = red << 3 | red >> 2
            green = (d >> 5) & 0x1F
            green = green << 3 | green >> 2
            blue = d & 0x1F
            blue = blue << 3 | blue >> 2
            LUT[d + 0x8000] = blue | (green << 8) | (red << 16) | 0xFF000000

PrepareRGB4A3LUTs()


def RGB4A3Decode(tex, w, h, useAlpha=True):
    """
    Decode an RGB4A3 texture to a QImage
    """
    tx = 0; ty = 0
    iter = tex.__iter__()
    dest = [0] * (w * h)

    LUT = RGB4A3LUT if useAlpha else RGB4A3LUT_NoAlpha

    # Loop over all texels
    for i in range(w * h // 16):
        for y in range(ty, ty+4):
            for x in range(tx, tx+4):
                dest[x + y * w] = LUT[next(iter) << 8 | next(iter)]

        # Move on to the next texel
        tx += 4
        if tx >= w: tx = 0; ty += 4

    # Convert the list of ARGB color values into a bytes object, and
    # then convert that into a QImage
    return QtGui.QImage(struct.pack(f'<{w * h}I', *dest), w, h, QtGui.QImage.Format_ARGB32)


def RGB4A3Encode(tex):
    """
    Encode an RGB4A3 texture from a QImage
    """
    w, h = tex.width(), tex.height()

    shorts = []
    colorCache = {}
    for ytile in range(0, h, 4):
        for xtile in range(0, w, 4):
            for ypixel in range(ytile, ytile + 4):
                for xpixel in range(xtile, xtile + 4):

                    if xpixel >= w or ypixel >= h:
                        continue

                    pixel = tex.pixel(xpixel, ypixel)

                    a = pixel >> 24
                    r = (pixel >> 16) & 0xFF
                    g = (pixel >> 8) & 0xFF
                    b = pixel & 0xFF

                    if pixel in colorCache:
                        rgba = colorCache[pixel]

                    else:

                        # See encodingTests.py in Puzzle-Updated for
                        # verification that these channel conversion
                        # formulas are 100% correct

                        # It'd be nice if we could do
                        # if a < 19:
                        #     rgba = 0
                        # for speed, but that defeats the purpose of the
                        # "Toggle Alpha" setting.

                        if a < 238: # RGB4A3
                            alpha = ((a + 18) << 1) // 73
                            red = (r + 8) // 17
                            green = (g + 8) // 17
                            blue = (b + 8) // 17

                            # 0aaarrrrggggbbbb
                            rgba = blue | (green << 4) | (red << 8) | (alpha << 12)

                        else: # RGB555
                            red = ((r + 4) << 2) // 33
                            green = ((g + 4) << 2) // 33
                            blue = ((b + 4) << 2) // 33

                            # 1rrrrrgggggbbbbb
                            rgba = blue | (green << 5) | (red << 10) | (0x8000)

                            colorCache[pixel] = rgba

                    shorts.append(rgba)

    return struct.pack(f'>{w * h}H', *shorts)
