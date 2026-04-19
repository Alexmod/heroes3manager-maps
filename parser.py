# -*- coding: utf-8 -*-
"""Парсер карт Heroes of Might and Magic III / HotA.

Модуль читает заголовок `.h3m`-карты и возвращает основную информацию
о карте в виде словаря.
"""

import gzip
import hashlib
import os
import struct

try:
    import chardet
except ImportError:
    chardet = None

try:
    import humanize
except ImportError:
    humanize = None


H3M_VERSIONS = {
    0x0E: "RoE",
    0x15: "AB",
    0x1C: "SoD",
    0x20: "HotA",
    0x33: "WoG",
}
HOTA_VERSION = 0x20
HOTA_HEADER_OFFSET = 14
HOTA_HEADER_SCAN_LIMIT = 256

H3M_DIFFICULTIES = {
    0: "Easy",
    1: "Normal",
    2: "Hard",
    3: "Expert",
    4: "Impossible",
}


def get_utf8_str(raw_bytes, column_name, column_encode):
    """Преобразовать байтовую строку карты в обычную Python-строку.

    Сначала пытается определить кодировку через `chardet`, если он
    установлен. Если не получилось, использует несколько запасных
    кодировок.
    """
    err_dict = {column_name: "unknown", column_encode: "unknown"}
    if not raw_bytes:
        return err_dict

    encodings = []
    if chardet is not None:
        detected = chardet.detect(raw_bytes).get("encoding")
        if detected:
            encodings.append(_normalize_encoding(detected))

    encodings.extend(["utf-8", "cp1251", "latin-1"])

    seen = set()
    for encoding in encodings:
        if not encoding or encoding in seen:
            continue
        seen.add(encoding)
        try:
            value = raw_bytes.decode(encoding).strip()
        except (LookupError, UnicodeDecodeError):
            continue
        return {column_name: value, column_encode: encoding}

    return err_dict


def mapsize(size):
    """Вернуть человекочитаемое название размера карты."""
    if size <= 36:
        return "Small"
    if size <= 72:
        return "Medium"
    if size <= 108:
        return "Large"
    if size <= 144:
        return "Extra Large"
    return "XXL"


class BufferReader:
    """Небольшой helper для последовательного чтения бинарного буфера."""

    def __init__(self, data, offset=0):
        """Создать читатель поверх `bytes` с заданным смещением."""
        self.data = data
        self.offset = offset

    def read(self, fmt):
        """Прочитать значение по формату `struct` и сдвинуть курсор."""
        size = struct.calcsize(fmt)
        end = self.offset + size
        if end > len(self.data):
            raise EOFError("Unexpected end of H3M header")
        value = struct.unpack_from(fmt, self.data, self.offset)
        self.offset = end
        return value

    def read_bytes(self, size):
        """Прочитать фиксированное количество байт и сдвинуть курсор."""
        end = self.offset + size
        if end > len(self.data):
            raise EOFError("Unexpected end of H3M header")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def read_h3_string(self):
        """Прочитать строку Heroes 3: длина `uint32` + данные."""
        (length,) = self.read("<I")
        return length, self.read_bytes(length)


def _normalize_encoding(encoding):
    """Нормализовать имя кодировки к значениям, понятным Python."""
    encoding = encoding.lower()
    if encoding == "maccyrillic":
        return "cp1251"
    return encoding


def _format_size(size_bytes):
    """Вернуть размер файла в компактном человекочитаемом виде."""
    if humanize is not None:
        return humanize.naturalsize(size_bytes, gnu=True)

    value = float(size_bytes)
    for suffix in ("B", "K", "M", "G", "T"):
        if value < 1024 or suffix == "T":
            if suffix == "B":
                return "{0}{1}".format(int(value), suffix)
            if value.is_integer():
                return "{0}{1}".format(int(value), suffix)
            return "{0:.1f}{1}".format(value, suffix)
        value /= 1024


def _read_map_bytes(filename):
    """Распаковать `.h3m` и вернуть его содержимое целиком."""
    with gzip.open(filename, "rb") as h3m_data:
        return h3m_data.read()


def _parse_common_header(data, offset):
    """Прочитать общий заголовок карты, начиная с указанного смещения."""
    reader = BufferReader(data, offset)
    (_, size, underground) = reader.read("<BIB")
    name_len, name = reader.read_h3_string()
    descr_len, descr = reader.read_h3_string()
    (difficulty,) = reader.read("<B")
    return {
        "size": size,
        "underground": underground,
        "name_len": name_len,
        "name": name,
        "descr_len": descr_len,
        "descr": descr,
        "difficulty": difficulty,
    }


def _looks_like_text(raw_bytes):
    """Проверить, что байты похожи на текст, а не на случайный мусор."""
    if not raw_bytes or b"\x00" in raw_bytes:
        return False

    bad_chars = 0
    for value in bytearray(raw_bytes):
        if value < 32 and value not in (9, 10, 13):
            bad_chars += 1

    return bad_chars == 0


def _is_plausible_header(header):
    """Проверить, что заголовок похож на валидную карту."""
    return (
        0 < header["size"] <= 512
        and header["underground"] in (0, 1)
        and 1 <= header["name_len"] <= 128
        and 0 <= header["descr_len"] <= 65535
        and header["difficulty"] in H3M_DIFFICULTIES
        and _looks_like_text(header["name"])
    )


def _read_header(data, version_code):
    """Найти и прочитать заголовок карты с учетом версии формата.

    У HotA перед обычным блоком заголовка есть дополнительный префикс,
    поэтому сначала пробуем HOTA-смещение, а затем обычное.
    """
    candidate_offsets = [4]
    if version_code == HOTA_VERSION:
        candidate_offsets = [HOTA_HEADER_OFFSET, 4]

    for offset in candidate_offsets:
        try:
            header = _parse_common_header(data, offset)
        except (EOFError, struct.error):
            continue
        if _is_plausible_header(header):
            return header

    if version_code == HOTA_VERSION:
        scan_limit = min(HOTA_HEADER_SCAN_LIMIT, len(data))
        for offset in range(4, scan_limit):
            if offset in candidate_offsets:
                continue
            try:
                header = _parse_common_header(data, offset)
            except (EOFError, struct.error):
                continue
            if _is_plausible_header(header):
                return header

    raise ValueError("Unsupported or damaged map header")


def ParserMap(fn):
    """Прочитать `.h3m` и вернуть словарь с информацией о карте."""
    res = {}

    try:
        data = _read_map_bytes(fn)
        (version_code,) = struct.unpack_from("<I", data, 0)

        # Версия игры / формата карты.
        res["Version"] = H3M_VERSIONS[version_code]
        header = _read_header(data, version_code)
    except (KeyError, OSError, EOFError, struct.error, ValueError):
        res["error"] = "This is not heroes map!"
        return res

    # Размер карты и наличие подземелья.
    res["underground"] = "Есть" if header["underground"] else "Нет"
    res["mapsize"] = mapsize(header["size"])

    # Название и описание карты.
    res.update(get_utf8_str(header["name"], "name", "name_enc"))
    res.update(get_utf8_str(header["descr"], "descr", "descr_enc"))

    # Уровень сложности.
    res["difficulty"] = H3M_DIFFICULTIES[header["difficulty"]]

    # Размер файла на диске.
    res["file_size"] = _format_size(os.path.getsize(fn))

    # Считаем md5 по основным данным карты без описания.
    # Описание часто меняют при перезаливке на сайты, из-за чего
    # одинаковые карты могли бы считаться разными.
    tmp = (
        res["Version"]
        + res["underground"]
        + res["mapsize"]
        + res["name"].lower()
        + res["difficulty"]
    )
    res["_id"] = hashlib.md5(tmp.encode("utf-8")).hexdigest()
    res["status"] = "Не играл"
    res["comment"] = None
    res["last_game"] = None
    return res
