# Copyright (C) 2019 State Electoral Office
#
# This file is part of ivxv-verificatum.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

table_cla = {0: 'universal',
             1: 'application',
             2: 'context-specific',
             3: 'private'}
table_constructed = {0: 'primitive',
                     1: 'constructed'}
table_tag = {1: 'BOOLEAN',
             2: 'INTEGER',
             3: 'BIT STRING',
             4: 'OCTET STRING',
             5: 'NULL',
             6: 'OBJECT IDENTIFIER',
             16: 'SEQUENCE',
             17: 'SET',
             19: 'PrintableString',
             22: 'IA5String',
             23: 'UTCTime'}


def asn1_len(content):
    r"""
    Usage:
        asn1_len(content), where content is DER encoded bytestring.
    Returns octets string compatible with ASN1 length format.

    Tests from assignment (converted from binary to hex):

    >>> asn1_len("x" * 126)
    '~'
    >>> asn1_len("x" * 127)
    '\x7f'
    >>> asn1_len("x" * 128)
    '\x81\x80'
    >>> asn1_len("x" * 1027)
    '\x82\x04\x03'
    """

    length = len(content)
    if length < 128:
        return chr(length)
    else:
        blocks = (length.bit_length() + 7) / 8
        lengthchars = [chr(0xff & (length >> i*8)) for i in range(blocks)]
        return chr(128 | blocks) + "".join(reversed(lengthchars))


def asn1_boolean(bool):
    """
    Usage:
        asn1_boolean(bool)
    Returns octets string compatible with ASN1 boolean format.
    """

    if bool:
        bool = chr(0xff)
    else:
        bool = chr(0x00)
    return chr(0x01) + asn1_len(bool) + bool


def asn1_integer(i):
    r"""
    Usage:
        asn1_integer(i)
    Returns two's complement octet string for arbitrary long integer.

    Tests are randomly chosen to showcase twos complement for different
    lengths.

    >>> asn1_integer(127)
    '\x02\x01\x7f'
    >>> asn1_integer(-127)
    '\x02\x01\x81'
    >>> asn1_integer(0)
    '\x02\x01\x00'
    >>> asn1_integer(128)
    '\x02\x02\x00\x80'
    >>> asn1_integer(-128)
    '\x02\x01\x80'
    """

    if i > 0:
        blocks = (i.bit_length() + 7) / 8
        if i & (0x80 << (blocks-1) * 8):
            blocks += 1
        return chr(0x02) + asn1_len("x" * blocks) + "".join(reversed(
            [chr(0xff & (i >> 8 * k)) for k in range(blocks)]))
    elif i == 0:
        return chr(0x02) + asn1_len("x") + chr(0)
    else:
        i = -i
        blocks = (i.bit_length() + 7) / 8
        if i & (0x80 << (blocks-1) * 8) and i & (0x7f << (blocks - 1) * 8):
            blocks += 1
        for k in range(blocks):
            i ^= 0xff << k * 8
        i += 1
        return chr(0x02) + asn1_len("x" * blocks) + "".join(reversed(
            [chr(0xff & (i >> 8 * k)) for k in range(blocks)]))


def asn1_enumerated(i):
    k = asn1_integer(i)
    return chr(0x0a) + k[1:]


def asn1_bitstring(bitstr):
    """
    Usage:
        asn1_bitstring(bitstr)
    Returns octet string of bitstring in ASN1 encoding.
    """

    length = (len(bitstr) + 7) / 8
    padding = (8 - (len(bitstr) % 8)) % 8
    return chr(0x03) + asn1_len("x" * (length + 1)) + chr(padding) + \
        "".join(reversed([chr(((int(bitstr, 2) << padding) >> k * 8) & 0xff)
                          for k in range(length)]))


def asn1_bitstring_der(der):
    """
    Usage:
        asn1_bitstring_der(der)
    Returns octet string of byte string in ASN1 encoding.
    """
    bitstr = ""
    for let in der:
        binlet = bin(ord(let))[2:]
        binlet = (8 - len(binlet)) * "0" + binlet
        bitstr += binlet
    return asn1_bitstring(bitstr)


def asn1_octetstring(octets):
    r"""
    Usage:
        asn1_octetstring(octets)
    Returns octets string in ASN1 encoding.

    >>> asn1_octetstring("hello")
    '\x04\x05hello'
    """

    return chr(0x04) + asn1_len(octets) + octets


def asn1_null():
    r"""
    Usage:
        asn1_null():
    Returns NULL tag in ASN1 encoding.

    >>> asn1_null()
    '\x05\x00'
    """
    return chr(0x05) + chr(0x00)


def asn1_objectidentifier(oid):
    r"""
    Usage:
        asn1_objectidentifier(oid), where oid is list of identificator
        elements.
    Returns octet string in ASN1 encoding representing OID.

    >>> asn1_objectidentifier([1, 2, 840])
    '\x06\x03*\x86H'
    >>> asn1_objectidentifier([1, 2, 840, 113549, 1])
    '\x06\x07*\x86H\x86\xf7\r\x01'
    >>> asn1_objectidentifier([1, 2, 840, 5, 127, 128, 129])
    '\x06\t*\x86H\x05\x7f\x81\x00\x81\x01'
    """

    chars = []
    chars.append(chr(40*oid[0]+oid[1]))
    for value in oid[2:]:
        if value < 128:
            chars.append(chr(value))
        else:
            subchars = []
            for i in range(0, (value.bit_length() + 6) / 7):
                subvalue = value % 128
                subchars.insert(0, chr(0x80 | subvalue))
                value -= subvalue
                value >>= 7
            subchars[-1] = chr(0x7f & ord(subchars[-1]))
            chars.extend(subchars)
    return chr(0x06) + asn1_len("x" * len(chars)) + "".join(chars)


def asn1_oid(oid):
    return asn1_objectidentifier(oid)


def asn1_sequence(der):
    """
    Usage:
        asn1_sequence(der), where der is DER encoded bytestring
    Returns ASN1 encoded bytestring for sequence.
    """

    return chr(0x30) + asn1_len(der) + der


def asn1_set(der):
    """
    Usage:
        asn1_set(der), where der is DER encoded bytestring
    Returns ASN1 encoded bytestring for set.
    """

    return chr(0x31) + asn1_len(der) + der


def asn1_printablestring(string):
    """
    Usage:
        asn1_printablestring(string)
    """

    for char in string:
        if ord(char) not in range(32, 127):
            raise ValueError("Input not printable")
    return chr(0x13) + asn1_len(string) + string


def asn1_utctime(time):
    """
    Usage:
        asn1_utctime(time), where time is string format of UTC time.
    Returns ASN1 encoded bytestring for UTC time.
    """

    return chr(0x17) + asn1_len(time) + time


def asn1_gentime(time):
    return chr(0x18) + asn1_len(time) + time


def asn1_tag_explicit_primitive(der, tag):
    """
    Usage:
        asn1_tag_explicit_primitive(der, tag), where der is DER-encoded
        bytestring and tag is required tag to pack with.
    Retruns ASN1 encoded bytestring in DER format explictidly contained in
    primitive tag.
    """

    return chr(0x80 | tag) + asn1_len(der) + der


def asn1_tag_explicit(der, tag):
    """
    Usage:
        asn1_tag_explicit_constructed(der, tag), where der is DER-encoded
        bytestring and tag is required tag to pack with.
    Returns ASN1 encoded bytestring in DER format explictidly contained in
    constructed tag.
    """

    return chr(0xa0 | tag) + asn1_len(der) + der


def asn1_tag_explicit_constructed(der, tag):
    return asn1_tag_explicit(der, tag)


def parse_oid(oid):
    values = []
    f = ord(oid[0])
    values.extend([(f - f % 40) / 40, f % 40])
    oid = oid[1:]
    while oid != "":
        f = ord(oid[0])
        if f < 128:
            values.append(f)
        else:
            i = 0
            while True:
                i <<= 7
                i |= f & 0x7f
                oid = oid[1:]
                f = ord(oid[0])
                if f < 128:
                    i <<= 7
                    i |= f
                    values.append(i)
                    break
        oid = oid[1:]
    return values


class asn_field(object):
    def __init__(self):
        self.cla = ""
        self.constr = ""
        self.tag = ""
        self.length = 0
        self.value = ""
        self.lenblocks = 0
        self.length = 0
        self.rawvalue = ""

    def __str__(self):
        output = ""
        for item in ['cla', 'constr', 'tag', 'length']:
            output += str(getattr(self, item)) + " "
        if self.tag in ['INTEGER']:
            output += str(self.unpacked_value())
        else:
            output += self.value
        return output

    def __repr__(self):
        return "ASN"

    def __getitem__(self, index):
        return self.value[index]

    def unpacked_value(self):
        if self.tag == "INTEGER":
            i = 0
            ii = self.value
            while ii:
                i <<= 8
                i |= ord(ii[0])
                ii = ii[1:]
            return i
        elif self.tag == "OBJECT IDENTIFIER":
            return parse_oid(self.value)


def parse_der(der, depth=0, ret=True):
    """
    Usage:
        parse_der(der, depth=0, ret=True), where der is DER formatted ASN1
        encoded string and depth can be additional initial depth.
    Returns nothing if ret = False, else prints output and returns nothing.
    """
    pointer = 0
    length = 0
    blocks = 0
    fields = []
    while pointer < len(der):
        field = asn_field()
        field.cla = table_cla[(der[pointer] & 0xc0) >> 6]
        field.constr = table_constructed[(der[pointer] & 0x20) >> 5]
        if (der[pointer] & 0xc0) >> 6 == 2:
            field.tag = der[pointer] & 0x1f
        else:
            field.tag = table_tag.get(der[pointer] & 0x1f, "[%d]" %
                                      (der[pointer] & 0x1f))
        blocks = (der[pointer + 1] & 0x7f) if der[pointer + 1] & 0x80 else 0
        field.lenblocks = blocks
        recurse = True if der[pointer] & 0x20 else False
        if blocks == 0:
            length = der[pointer + 1] & 0x7f
        else:
            length = 0
        pointer += 2
        while blocks:
            length <<= 8
            length |= der[pointer]
            pointer += 1
            blocks -= 1
        field.length = length
        field.rawvalue = der[pointer-2-field.lenblocks:pointer+length]
        if recurse:
            field.value = parse_der(der[pointer:pointer+length], depth+1, ret)
        else:
            field.value = der[pointer:pointer+length]
        pointer += length
        fields.append(field)
    return fields


def unpack_ciphertext(der):
    """
    Unpack the DER formatted ASN1 ciphertext.
    """
    return map(lambda x: x.unpacked_value(), parse_der(der)[0])


def pack_ciphertext(c):
    """
    Pack the ciphertext to DER formatted ASN1 ciphertext.
    """
    return asn1_sequence("".join(map(asn1_integer, c)))


def pack_ballot(c):
    """
    Pack the ballot to DER formatted ASN1 ciphertext.
    """
    # TODO: We currently assume that the ElGamal cryptosystem is defined over
    # a multiplicative subgroup of an integer residual ring. This may not be
    # so.
    # However, return to this when this becomes a problem (i.e. we take other
    # underlying groups into use)
    return asn1_sequence(
        asn1_sequence(
            asn1_objectidentifier([1, 3, 6, 1, 4, 1, 3029, 2, 1])
        ) +
        asn1_sequence("".join(map(pack_ciphertext, c)))
    )


def unpack_ballot(der):
    """
    Unpack the DER formatted ASN1 ballot.
    """
    f = lambda v: map(lambda x: x.unpacked_value(), v)
    return map(f, parse_der(der)[0][1])
