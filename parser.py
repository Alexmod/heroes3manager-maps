# -*- coding: utf-8 -*-
# Парсер карт Heroes3. Принимает путь к файлу. Отдает информацию о карте
import gzip
import struct
import chardet
import os
import humanize
import hashlib


h3m_versions = {0x0E: "RoE", 0x15: "AB", 0x1C: "SoD", 0x33: "WoG"}
h3m_diffictulties = {0: "Easy", 1: "Normal", 2: "Hard", 3: "Expert",
                     4: "Impossible"}
h3m_mapsize = {32: "Small", 72: 'Medium', 108: 'Large', 144: 'Extra Large',
               252: 'XXL'}


def get_utf8_str(string, column_name, column_encode):
    err_dict = {column_name: 'unknown', column_encode: 'unknown'}
    if string:
        encode = chardet.detect(string).get('encoding')
        encode = 'windows-1251' if encode == 'MacCyrillic' else encode
        try:
            utf8_str = \
                string.decode(encode).encode('utf8').decode('utf8').strip()
        except:
            return err_dict

        return {column_name: utf8_str, 'encode': encode}

    return err_dict


def mapsize(size):
    if size <= 36:
        return 'Small'
    if size <= 72:
        return 'Medium'
    if size <= 108:
        return 'Large'
    if size <= 144:
        return 'Extra Large'
    return 'XXL'


def ParserMap(fn):
    h3m_data = gzip.open(fn)

    def r(s):
        return struct.unpack(s,
                             h3m_data.read(
                                 struct.calcsize(s)))

    res = {}
    # Версия игры
    try:
        res['Version'] = h3m_versions[r("<I")[0]]
    except (KeyError, OSError, EOFError, struct.error):
        res['error'] = 'This is not heroes map!'
        return res

    # Размер карты и наличие подземелья
    (_, size, underground) = r("<BIB")
    res['underground'] = 'Есть' if underground else 'Нет'
    res['mapsize'] = mapsize(int(size))

    # Название карты
    (vlength, ) = r("<I")
    name = h3m_data.read(vlength)
    res.update(get_utf8_str(name, 'name', 'name_enc'))

    # Описание карты
    (vlength, ) = r("<I")
    descr = h3m_data.read(vlength)
    res.update(get_utf8_str(descr, 'descr', 'descr_enc'))

    # Уровень сложности
    res['difficulty'] = h3m_diffictulties[r("<B")[0]]

    # Размер файла в кб
    res['file_size'] = humanize.naturalsize(os.path.getsize(fn), gnu=True)

    # Считаем md5. Засовываем туда все данные, кроме descr. В descr бывает
    # добавляют название сайта, откуда скачали карту и будет дубль.
    tmp = res['Version'] + res['underground'] + res['mapsize'] + \
        res['name'].lower() + res['difficulty']
    res['_id'] = hashlib.md5(str(tmp).encode('utf-8')).hexdigest()
    res['status'] = 'Не играл'
    res['comment'] = None
    res['last_game'] = None
    return res
