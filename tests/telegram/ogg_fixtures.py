"""Contenedores OGG mínimos y ficticios para pruebas estructurales offline."""
from __future__ import annotations


def _crc(data: bytes | bytearray) -> int:
    register = 0
    for value in data:
        register ^= value << 24
        for _ in range(8):
            register = (
                ((register << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
                if register & 0x80000000
                else (register << 1) & 0xFFFFFFFF
            )
    return register


def _page(
    packets: list[bytes],
    *,
    serial: int,
    sequence: int,
    flags: int,
    granule: int,
) -> bytes:
    lacing = bytearray()
    body = bytearray()
    for packet in packets:
        remaining = bytes(packet)
        while len(remaining) >= 255:
            lacing.append(255)
            body.extend(remaining[:255])
            remaining = remaining[255:]
        lacing.append(len(remaining))
        body.extend(remaining)
    header = bytearray(b"OggS")
    header.extend((0, flags))
    header.extend(int(granule).to_bytes(8, "little", signed=False))
    header.extend(int(serial).to_bytes(4, "little"))
    header.extend(int(sequence).to_bytes(4, "little"))
    header.extend(b"\x00\x00\x00\x00")
    header.append(len(lacing))
    header.extend(lacing)
    page = header + body
    page[22:26] = _crc(page).to_bytes(4, "little")
    return bytes(page)


def make_ogg_opus(*, audio_packet: bytes = b"\xf8\xff\xfe", eos: bool = True) -> bytes:
    opus_head = (
        b"OpusHead"
        + bytes((1, 1))
        + (312).to_bytes(2, "little")
        + (48000).to_bytes(4, "little")
        + (0).to_bytes(2, "little", signed=True)
        + bytes((0,))
    )
    opus_tags = b"OpusTags" + (0).to_bytes(4, "little") + (0).to_bytes(4, "little")
    return b"".join((
        _page([opus_head], serial=17, sequence=0, flags=0x02, granule=0),
        _page([opus_tags], serial=17, sequence=1, flags=0, granule=0),
        _page([audio_packet], serial=17, sequence=2, flags=0x04 if eos else 0, granule=960),
    ))


def make_ogg_vorbis() -> bytes:
    identification = (
        b"\x01vorbis"
        + (0).to_bytes(4, "little")
        + bytes((1,))
        + (48000).to_bytes(4, "little")
        + (0).to_bytes(4, "little") * 3
        + bytes((0xB8, 1))
    )
    comment = b"\x03vorbis" + (0).to_bytes(4, "little") + (0).to_bytes(4, "little") + b"\x01"
    setup = b"\x05vorbis" + b"fictitious-setup\x01"
    return b"".join((
        _page([identification], serial=23, sequence=0, flags=0x02, granule=0),
        _page([comment], serial=23, sequence=1, flags=0, granule=0),
        _page([setup], serial=23, sequence=2, flags=0, granule=0),
        _page([b"fictitious-audio"], serial=23, sequence=3, flags=0x04, granule=1024),
    ))


def make_ogg_unknown() -> bytes:
    return _page(
        [b"VideoHeader", b"metadata", b"payload"],
        serial=31,
        sequence=0,
        flags=0x02 | 0x04,
        granule=1,
    )
