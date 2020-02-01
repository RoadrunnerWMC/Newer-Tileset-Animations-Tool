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

import pathlib
import struct


U8_MAGIC = b'\x55\xAA\x38\x2D'


def _loadNullTerminatedStringFrom(
        data, offset, charWidth=1, encoding='latin-1'):
    """
    Load a null-terminated string from data at offset, with the options
    given.
    This is copypasted from ndspy.
    """
    end = data.find(b'\0' * charWidth, offset)
    return data[offset:end].decode(encoding)


def load(data):
    """
    Read a U8 archive and return its contents as a dict.
    """
    if not data.startswith(U8_MAGIC):
        raise ValueError('Incorrect magic for U8 archive')

    # Read header stuff
    rootNodeOffs, headerSize, dataTableOffs = struct.unpack_from('>3I', data, 4)
    assert rootNodeOffs == 0x20

    # "Size" field of the root node tells us the total number of nodes;
    # this is how we calculate the offset of the string table
    rootNodeSize, = struct.unpack_from('>I', data, rootNodeOffs + 8)
    stringTableOffs = rootNodeOffs + 12 * rootNodeSize

    def readNodeAt(idx):
        """
        Read the U8 node at the given index.
        Returns:
        - node's name
        - node's data (bytes if a file, dict if a folder)
        - next node index to read (idx + 1 if a file, idx + [some larger
          number] if a folder)
        """
        offs = rootNodeOffs + 12 * idx

        type = data[offs]
        nameOffs = int.from_bytes(data[offs + 1 : offs + 4], 'big')
        dataOffs, size = struct.unpack_from('>II', data, offs + 4)

        name = _loadNullTerminatedStringFrom(data, stringTableOffs + nameOffs)

        if type == 0:  # File
            fileData = data[dataOffs : dataOffs + size]
            return name, fileData, idx + 1

        elif type == 1:  # Folder
            contents = {}

            # Keep reading nodes until we reach node number 'size'
            # (1-indexed)
            idx += 1
            while idx < size:
                itemName, itemData, idx = readNodeAt(idx)
                contents[itemName] = itemData

            return name, contents, idx

        else:
            raise ValueError(f'Unknown U8 node type: {type}')

    # Read root node and return it
    _, root, _ = readNodeAt(0)
    return root


def save(contents):
    """
    Save a U8 archive file, given its contents as a dictionary
    """
    # Data table offset is aligned to 0x20, as are node data offsets

    # Blank header; actual values will be filled in at the very end
    data = bytearray(b'\0' * 0x20)

    # Tables to populate
    stringsTable = bytearray()
    dataTable = bytearray()

    # Save each node
    valuesToIncreaseByDataTableOffs = {}
    def saveNode(name, contents, myIdx, recursion):
        """
        Save a file or folder node, with a given name and contents
        (bytes or dict), to the given index, and with the given
        recursion value (only used if this is a folder)
        """
        nonlocal data, dataTable, stringsTable

        # Add the name
        nameOffs = len(stringsTable)
        stringsTable += (name + '\0').encode('latin-1')

        # Add dummy data for this node
        nodeOffs = len(data)
        data += b'\0' * 12

        if isinstance(contents, dict):  # Folder
            idx = myIdx + 1
            # The keys MUST be sorted alphabetically and case-insensitively
            for k in sorted(contents, key=lambda s: s.lower()):
                idx = saveNode(k, contents[k], idx, recursion + 1)

            type_ = 1
            dataOffs = max(0, recursion)
            size = nextIdx = idx

        else:  # File
            while len(dataTable) % 0x20:
                dataTable.append(0)
            dataOffs = len(dataTable)
            dataTable += contents

            # This is a bit of a hack: the "data offset" node value is
            # absolute, but at this point we're just putting the file
            # data together into a separate bytearray. So we keep track
            # of all of the offsets that we'll need to fix up once we
            # know exactly where the data table is going to go.
            valuesToIncreaseByDataTableOffs[nodeOffs + 4] = dataOffs

            type_ = 0
            size = len(contents)
            nextIdx = myIdx + 1

        # Save node info
        data[nodeOffs] = type_
        data[nodeOffs + 1 : nodeOffs + 4] = nameOffs.to_bytes(3, 'big')
        struct.pack_into('>II', data, nodeOffs + 4, dataOffs, size)
        
        return nextIdx

    saveNode('', contents, 0, -1)

    # Append the strings table, and make a note of the current length
    # (starting at the root node, at 0x20)
    data += stringsTable
    headerSize = len(data) - 0x20

    # Align to 0x20, make a note of the current length, and append the
    # data table
    while len(data) % 0x20:
        data.append(0)
    dataTableOffs = len(data)
    data += dataTable

    # Fix up data offsets for all of the file nodes
    for offs, relativeValue in valuesToIncreaseByDataTableOffs.items():
        struct.pack_into('>I', data, offs, dataTableOffs + relativeValue)

    # Add the final header values and return
    struct.pack_into('>4s3I', data, 0, U8_MAGIC, 0x20, headerSize, dataTableOffs)
    return bytes(data)
