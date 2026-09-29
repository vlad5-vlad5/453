#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конвертер IPTV плейлистов для OTT-Play FOSS
Добавляет название страны и флаг рядом с названием канала

Форматы вывода:
  - [США] BBC One
  - BBC One [США]
  - BBC One | США
  - 🇺🇸 BBC One [США]  <- по умолчанию для OTT-Play FOSS
"""

import re
import argparse
import sys
import urllib.request
from pathlib import Path
import tempfile

# База стран: код -> информация
COUNTRIES = {
    "AF": {"ru": "Афганистан", "en": "Afghanistan", "flag": "🇦🇫", "aliases": ["AF", "Афганистан", "Afghanistan", "Afghan"]},
    "AL": {"ru": "Албания", "en": "Albania", "flag": "🇦🇱", "aliases": ["AL", "Albania", "Албания"]},
    "DZ": {"ru": "Алжир", "en": "Algeria", "flag": "🇩🇿", "aliases": ["DZ", "Algeria", "Алжир"]},
    "AD": {"ru": "Андорра", "en": "Andorra", "flag": "🇦🇩", "aliases": ["Андорра", "Andorra", "AD"]},
    "AO": {"ru": "Ангола", "en": "Angola", "flag": "🇦🇴", "aliases": ["Angola", "Ангола", "AO"]},
    "AG": {"ru": "Антигуа и Барбуда", "en": "Antigua and Barbuda", "flag": "🇦🇬", "aliases": ["Barbuda", "Антигуа и Барбуда", "AG", "Antigua and Barbuda", "Antigua"]},
    "AR": {"ru": "Аргентина", "en": "Argentina", "flag": "🇦🇷", "aliases": ["Аргентина", "AR", "Argentina", "Corrientes"]},
    "AM": {"ru": "Армения", "en": "Armenia", "flag": "🇦🇲", "aliases": ["Армения", "AM", "Armenia"]},
    "AU": {"ru": "Австралия", "en": "Australia", "flag": "🇦🇺", "aliases": ["Австралия", "AU", "Australia", "Sydney", "Melbourne", "2GB", "3AW"]},
    "AT": {"ru": "Австрия", "en": "Austria", "flag": "🇦🇹", "aliases": ["Австрия", "AT", "Austria"]},
    "AZ": {"ru": "Азербайджан", "en": "Azerbaijan", "flag": "🇦🇿", "aliases": ["Азербайджан", "AZ", "Azerbaijan"]},
    "BS": {"ru": "Багамы", "en": "Bahamas", "flag": "🇧🇸", "aliases": ["BS", "Багамы", "Bahamas"]},
    "BH": {"ru": "Бахрейн", "en": "Bahrain", "flag": "🇧🇭", "aliases": ["Бахрейн", "BH", "Bahrain"]},
    "BD": {"ru": "Бангладеш", "en": "Bangladesh", "flag": "🇧🇩", "aliases": ["BD", "Бангладеш", "Bangladesh"]},
    "BB": {"ru": "Барбадос", "en": "Barbados", "flag": "🇧🇧", "aliases": ["BB", "Barbados", "Барбадос"]},
    "BY": {"ru": "Беларусь", "en": "Belarus", "flag": "🇧🇾", "aliases": ["Belarus", "Белоруссия", "BY", "Беларусь"]},
    "BE": {"ru": "Бельгия", "en": "Belgium", "flag": "🇧🇪", "aliases": ["Belgium", "BE", "Бельгия"]},
    "BZ": {"ru": "Белиз", "en": "Belize", "flag": "🇧🇿", "aliases": ["Белиз", "Belize", "BZ"]},
    "BJ": {"ru": "Бенин", "en": "Benin", "flag": "🇧🇯", "aliases": ["BJ", "Бенин", "Benin"]},
    "BT": {"ru": "Бутан", "en": "Bhutan", "flag": "🇧🇹", "aliases": ["Bhutan", "Бутан", "BT"]},
    "BO": {"ru": "Боливия", "en": "Bolivia", "flag": "🇧🇴", "aliases": ["Bolivia", "Боливия", "BO"]},
    "BA": {"ru": "Босния и Герцеговина", "en": "Bosnia and Herzegovina", "flag": "🇧🇦", "aliases": ["Bosnia", "Босния и Герцеговина", "Herzegovina", "BA", "Bosnia and Herzegovina"]},
    "BW": {"ru": "Ботсвана", "en": "Botswana", "flag": "🇧🇼", "aliases": ["Botswana", "BW", "Ботсвана"]},
    "BR": {"ru": "Бразилия", "en": "Brazil", "flag": "🇧🇷", "aliases": ["Brasil", "BR", "Бразилия", "Brazil"]},
    "BN": {"ru": "Бруней", "en": "Brunei", "flag": "🇧🇳", "aliases": ["Бруней", "BN", "Brunei"]},
    "BG": {"ru": "Болгария", "en": "Bulgaria", "flag": "🇧🇬", "aliases": ["Болгария", "BG", "Bulgaria"]},
    "BF": {"ru": "Буркина-Фасо", "en": "Burkina Faso", "flag": "🇧🇫", "aliases": ["Burkina", "BF", "Burkina Faso", "Буркина-Фасо"]},
    "BI": {"ru": "Бурунди", "en": "Burundi", "flag": "🇧🇮", "aliases": ["Burundi", "Бурунди", "BI"]},
    "CV": {"ru": "Кабо-Верде", "en": "Cape Verde", "flag": "🇨🇻", "aliases": ["Cabo Verde", "CV", "Cape Verde", "Кабо-Верде"]},
    "KH": {"ru": "Камбоджа", "en": "Cambodia", "flag": "🇰🇭", "aliases": ["Камбоджа", "Cambodia", "KH"]},
    "CM": {"ru": "Камерун", "en": "Cameroon", "flag": "🇨🇲", "aliases": ["Cameroon", "Камерун", "CM"]},
    "CA": {"ru": "Канада", "en": "Canada", "flag": "🇨🇦", "aliases": ["Канада", "Canada", "CA"]},
    "CF": {"ru": "ЦАР", "en": "Central African Republic", "flag": "🇨🇫", "aliases": ["Central African Republic", "CF", "ЦАР", "CAR"]},
    "TD": {"ru": "Чад", "en": "Chad", "flag": "🇹🇩", "aliases": ["TD", "Chad", "Чад"]},
    "CL": {"ru": "Чили", "en": "Chile", "flag": "🇨🇱", "aliases": ["Чили", "CL", "Chile"]},
    "CN": {"ru": "Китай", "en": "China", "flag": "🇨🇳", "aliases": ["China", "CN", "Китай"]},
    "CO": {"ru": "Колумбия", "en": "Colombia", "flag": "🇨🇴", "aliases": ["Colombia", "Колумбия", "CO"]},
    "KM": {"ru": "Коморы", "en": "Comoros", "flag": "🇰🇲", "aliases": ["Comoros", "KM", "Коморы"]},
    "CG": {"ru": "Конго", "en": "Congo", "flag": "🇨🇬", "aliases": ["Congo", "Конго", "CG"]},
    "CD": {"ru": "ДР Конго", "en": "DR Congo", "flag": "🇨🇩", "aliases": ["ДР Конго", "Congo Kinshasa", "DR Congo", "CD"]},
    "CR": {"ru": "Коста-Рика", "en": "Costa Rica", "flag": "🇨🇷", "aliases": ["Коста-Рика", "Costa Rica", "CR"]},
    "CI": {"ru": "Кот-д'Ивуар", "en": "Ivory Coast", "flag": "🇨🇮", "aliases": ["CI", "Кот-д'Ивуар", "Cote d'Ivoire", "Ivory Coast"]},
    "HR": {"ru": "Хорватия", "en": "Croatia", "flag": "🇭🇷", "aliases": ["Хорватия", "HR", "Croatia"]},
    "CU": {"ru": "Куба", "en": "Cuba", "flag": "🇨🇺", "aliases": ["Куба", "CU", "Cuba"]},
    "CY": {"ru": "Кипр", "en": "Cyprus", "flag": "🇨🇾", "aliases": ["CY", "Cyprus", "Кипр"]},
    "CZ": {"ru": "Чехия", "en": "Czech", "flag": "🇨🇿", "aliases": ["Czech", "CZ", "Czech Republic", "Чехия"]},
    "DK": {"ru": "Дания", "en": "Denmark", "flag": "🇩🇰", "aliases": ["Дания", "Danmark", "Denmark", "DK"]},
    "DJ": {"ru": "Джибути", "en": "Djibouti", "flag": "🇩🇯", "aliases": ["Djibouti", "DJ", "Джибути"]},
    "DM": {"ru": "Доминика", "en": "Dominica", "flag": "🇩🇲", "aliases": ["Dominica", "Доминика", "DM"]},
    "DO": {"ru": "Доминикана", "en": "Dominican Republic", "flag": "🇩🇴", "aliases": ["DO", "Dominicana", "Доминикана", "Dominican Republic"]},
    "EC": {"ru": "Эквадор", "en": "Ecuador", "flag": "🇪🇨", "aliases": ["Эквадор", "EC", "Ecuador"]},
    "EG": {"ru": "Египет", "en": "Egypt", "flag": "🇪🇬", "aliases": ["EG", "Egypt", "Египет"]},
    "SV": {"ru": "Сальвадор", "en": "El Salvador", "flag": "🇸🇻", "aliases": ["SV", "El Salvador", "Сальвадор", "Salvador"]},
    "GQ": {"ru": "Экваториальная Гвинея", "en": "Equatorial Guinea", "flag": "🇬🇶", "aliases": ["Equatorial Guinea", "Экваториальная Гвинея", "GQ"]},
    "ER": {"ru": "Эритрея", "en": "Eritrea", "flag": "🇪🇷", "aliases": ["ER", "Эритрея", "Eritrea"]},
    "EE": {"ru": "Эстония", "en": "Estonia", "flag": "🇪🇪", "aliases": ["Estonia", "EE", "Эстония"]},
    "SZ": {"ru": "Эсватини", "en": "Eswatini", "flag": "🇸🇿", "aliases": ["Эсватини", "Eswatini", "SZ", "Swaziland"]},
    "ET": {"ru": "Эфиопия", "en": "Ethiopia", "flag": "🇪🇹", "aliases": ["ET", "Эфиопия", "Ethiopia"]},
    "FJ": {"ru": "Фиджи", "en": "Fiji", "flag": "🇫🇯", "aliases": ["Фиджи", "Fiji", "FJ"]},
    "FI": {"ru": "Финляндия", "en": "Finland", "flag": "🇫🇮", "aliases": ["Finland", "Suomi", "Финляндия", "FI"]},
    "FR": {"ru": "Франция", "en": "France", "flag": "🇫🇷", "aliases": ["France", "Франция", "Frankreich", "FR"]},
    "GA": {"ru": "Габон", "en": "Gabon", "flag": "🇬🇦", "aliases": ["Gabon", "Габон", "GA"]},
    "GM": {"ru": "Гамбия", "en": "Gambia", "flag": "🇬🇲", "aliases": ["Gambia", "GM", "Гамбия"]},
    "GE": {"ru": "Грузия", "en": "Georgia", "flag": "🇬🇪", "aliases": ["Georgia", "GE", "Грузия"]},
    "DE": {"ru": "Германия", "en": "Germany", "flag": "🇩🇪", "aliases": ["Германия", "DE", "Germany", "Deutschland", "German", "3sat"]},
    "GH": {"ru": "Гана", "en": "Ghana", "flag": "🇬🇭", "aliases": ["GH", "Ghana", "Гана"]},
    "GR": {"ru": "Греция", "en": "Greece", "flag": "🇬🇷", "aliases": ["Греция", "Greece", "GR"]},
    "GD": {"ru": "Гренада", "en": "Grenada", "flag": "🇬🇩", "aliases": ["GD", "Grenada", "Гренада"]},
    "GT": {"ru": "Гватемала", "en": "Guatemala", "flag": "🇬🇹", "aliases": ["Guatemala", "Гватемала", "GT"]},
    "GN": {"ru": "Гвинея", "en": "Guinea", "flag": "🇬🇳", "aliases": ["Guinea", "Гвинея", "GN"]},
    "GW": {"ru": "Гвинея-Бисау", "en": "Guinea-Bissau", "flag": "🇬🇼", "aliases": ["Гвинея-Бисау", "GW", "Guinea-Bissau"]},
    "GY": {"ru": "Гайана", "en": "Guyana", "flag": "🇬🇾", "aliases": ["Гайана", "GY", "Guyana"]},
    "HT": {"ru": "Гаити", "en": "Haiti", "flag": "🇭🇹", "aliases": ["Haiti", "Гаити", "HT"]},
    "HN": {"ru": "Гондурас", "en": "Honduras", "flag": "🇭🇳", "aliases": ["Honduras", "Гондурас", "HN"]},
    "HU": {"ru": "Венгрия", "en": "Hungary", "flag": "🇭🇺", "aliases": ["Magyar", "Hungary", "Венгрия", "HU"]},
    "IS": {"ru": "Исландия", "en": "Iceland", "flag": "🇮🇸", "aliases": ["Iceland", "Исландия", "IS"]},
    "IN": {"ru": "Индия", "en": "India", "flag": "🇮🇳", "aliases": ["Индия", "IN", "India", "5AAB", "Aastha", "ABP", "Aamar"]},
    "ID": {"ru": "Индонезия", "en": "Indonesia", "flag": "🇮🇩", "aliases": ["ID", "Indonesia", "Индонезия"]},
    "IR": {"ru": "Иран", "en": "Iran", "flag": "🇮🇷", "aliases": ["Иран", "IR", "Persian", "Iran", "Farsi", "4U TV", "4UTV", "4U"]},
    "IQ": {"ru": "Ирак", "en": "Iraq", "flag": "🇮🇶", "aliases": ["Ирак", "Iraq", "IQ"]},
    "IE": {"ru": "Ирландия", "en": "Ireland", "flag": "🇮🇪", "aliases": ["IE", "Ireland", "Ирландия"]},
    "IL": {"ru": "Израиль", "en": "Israel", "flag": "🇮🇱", "aliases": ["IL", "Израиль", "Israel"]},
    "IT": {"ru": "Италия", "en": "Italy", "flag": "🇮🇹", "aliases": ["Италия", "Italia", "Italy", "IT"]},
    "JM": {"ru": "Ямайка", "en": "Jamaica", "flag": "🇯🇲", "aliases": ["Ямайка", "JM", "Jamaica"]},
    "JP": {"ru": "Япония", "en": "Japan", "flag": "🇯🇵", "aliases": ["JP", "Japan", "Япония"]},
    "JO": {"ru": "Иордания", "en": "Jordan", "flag": "🇯🇴", "aliases": ["Иордания", "Jordan", "JO"]},
    "KZ": {"ru": "Казахстан", "en": "Kazakhstan", "flag": "🇰🇿", "aliases": ["Казахстан", "KZ", "Kazakhstan"]},
    "KE": {"ru": "Кения", "en": "Kenya", "flag": "🇰🇪", "aliases": ["Кения", "Kenya", "KE"]},
    "KI": {"ru": "Кирибати", "en": "Kiribati", "flag": "🇰🇮", "aliases": ["Kiribati", "KI", "Кирибати"]},
    "KP": {"ru": "КНДР", "en": "North Korea", "flag": "🇰🇵", "aliases": ["KP", "North Korea", "Северная Корея", "КНДР", "DPRK"]},
    "KR": {"ru": "Корея", "en": "South Korea", "flag": "🇰🇷", "aliases": ["Южная Корея", "Korea", "Корея", "South Korea", "KR"]},
    "KW": {"ru": "Кувейт", "en": "Kuwait", "flag": "🇰🇼", "aliases": ["Кувейт", "Kuwait", "KW"]},
    "KG": {"ru": "Киргизия", "en": "Kyrgyzstan", "flag": "🇰🇬", "aliases": ["Кыргызстан", "KG", "Kyrgyzstan", "Киргизия"]},
    "LA": {"ru": "Лаос", "en": "Laos", "flag": "🇱🇦", "aliases": ["LA", "Laos", "Лаос"]},
    "LV": {"ru": "Латвия", "en": "Latvia", "flag": "🇱🇻", "aliases": ["Latvia", "LV", "Латвия"]},
    "LB": {"ru": "Ливан", "en": "Lebanon", "flag": "🇱🇧", "aliases": ["Lebanon", "LB", "Ливан"]},
    "LS": {"ru": "Лесото", "en": "Lesotho", "flag": "🇱🇸", "aliases": ["Lesotho", "LS", "Лесото"]},
    "LR": {"ru": "Либерия", "en": "Liberia", "flag": "🇱🇷", "aliases": ["Либерия", "Liberia", "LR"]},
    "LY": {"ru": "Ливия", "en": "Libya", "flag": "🇱🇾", "aliases": ["Libya", "Ливия", "LY"]},
    "LI": {"ru": "Лихтенштейн", "en": "Liechtenstein", "flag": "🇱🇮", "aliases": ["Лихтенштейн", "LI", "Liechtenstein"]},
    "LT": {"ru": "Литва", "en": "Lithuania", "flag": "🇱🇹", "aliases": ["Lithuania", "LT", "Литва"]},
    "LU": {"ru": "Люксембург", "en": "Luxembourg", "flag": "🇱🇺", "aliases": ["Люксембург", "Luxembourg", "LU"]},
    "MG": {"ru": "Мадагаскар", "en": "Madagascar", "flag": "🇲🇬", "aliases": ["MG", "Madagascar", "Мадагаскар"]},
    "MW": {"ru": "Малави", "en": "Malawi", "flag": "🇲🇼", "aliases": ["MW", "Малави", "Malawi"]},
    "MY": {"ru": "Малайзия", "en": "Malaysia", "flag": "🇲🇾", "aliases": ["Малайзия", "MY", "Malaysia"]},
    "MV": {"ru": "Мальдивы", "en": "Maldives", "flag": "🇲🇻", "aliases": ["Мальдивы", "Maldives", "MV"]},
    "ML": {"ru": "Мали", "en": "Mali", "flag": "🇲🇱", "aliases": ["Mali", "Мали", "ML"]},
    "MT": {"ru": "Мальта", "en": "Malta", "flag": "🇲🇹", "aliases": ["MT", "Malta", "Мальта"]},
    "MH": {"ru": "Маршалловы Острова", "en": "Marshall Islands", "flag": "🇲🇭", "aliases": ["MH", "Marshall Islands", "Маршалловы Острова"]},
    "MR": {"ru": "Мавритания", "en": "Mauritania", "flag": "🇲🇷", "aliases": ["MR", "Mauritania", "Мавритания"]},
    "MU": {"ru": "Маврикий", "en": "Mauritius", "flag": "🇲🇺", "aliases": ["MU", "Маврикий", "Mauritius"]},
    "MX": {"ru": "Мексика", "en": "Mexico", "flag": "🇲🇽", "aliases": ["Мексика", "MX", "Mexico"]},
    "FM": {"ru": "Микронезия", "en": "Micronesia", "flag": "🇫🇲", "aliases": ["Микронезия", "FM", "Micronesia"]},
    "MD": {"ru": "Молдова", "en": "Moldova", "flag": "🇲🇩", "aliases": ["MD", "Молдова", "Молдавия", "Moldova"]},
    "MC": {"ru": "Монако", "en": "Monaco", "flag": "🇲🇨", "aliases": ["Monaco", "Монако", "MC"]},
    "MN": {"ru": "Монголия", "en": "Mongolia", "flag": "🇲🇳", "aliases": ["Монголия", "MN", "Mongolia"]},
    "ME": {"ru": "Черногория", "en": "Montenegro", "flag": "🇲🇪", "aliases": ["Montenegro", "Черногория", "ME"]},
    "MA": {"ru": "Марокко", "en": "Morocco", "flag": "🇲🇦", "aliases": ["Марокко", "MA", "Morocco", "2M", "2M Monde", "Arryadia"]},
    "MZ": {"ru": "Мозамбик", "en": "Mozambique", "flag": "🇲🇿", "aliases": ["Мозамбик", "Mozambique", "MZ"]},
    "MM": {"ru": "Мьянма", "en": "Myanmar", "flag": "🇲🇲", "aliases": ["Мьянма", "Burma", "MM", "Myanmar"]},
    "NA": {"ru": "Намибия", "en": "Namibia", "flag": "🇳🇦", "aliases": ["NA", "Namibia", "Намибия"]},
    "NR": {"ru": "Науру", "en": "Nauru", "flag": "🇳🇷", "aliases": ["NR", "Nauru", "Науру"]},
    "NP": {"ru": "Непал", "en": "Nepal", "flag": "🇳🇵", "aliases": ["Непал", "Nepal", "NP"]},
    "NL": {"ru": "Нидерланды", "en": "Netherlands", "flag": "🇳🇱", "aliases": ["Нидерланды", "NL", "Netherlands", "Holland", "Nederland", "Almere"]},
    "NZ": {"ru": "Новая Зеландия", "en": "New Zealand", "flag": "🇳🇿", "aliases": ["Новая Зеландия", "NZ", "New Zealand"]},
    "NI": {"ru": "Никарагуа", "en": "Nicaragua", "flag": "🇳🇮", "aliases": ["NI", "Nicaragua", "Никарагуа"]},
    "NE": {"ru": "Нигер", "en": "Niger", "flag": "🇳🇪", "aliases": ["NE", "Нигер", "Niger"]},
    "NG": {"ru": "Нигерия", "en": "Nigeria", "flag": "🇳🇬", "aliases": ["Нигерия", "NG", "Nigeria"]},
    "MK": {"ru": "Северная Македония", "en": "North Macedonia", "flag": "🇲🇰", "aliases": ["Северная Македония", "North Macedonia", "Macedonia", "MK"]},
    "NO": {"ru": "Норвегия", "en": "Norway", "flag": "🇳🇴", "aliases": ["NO", "Норвегия", "Norway", "Norge"]},
    "OM": {"ru": "Оман", "en": "Oman", "flag": "🇴🇲", "aliases": ["Oman", "OM", "Оман"]},
    "PK": {"ru": "Пакистан", "en": "Pakistan", "flag": "🇵🇰", "aliases": ["Pakistan", "PK", "Пакистан"]},
    "PW": {"ru": "Палау", "en": "Palau", "flag": "🇵🇼", "aliases": ["Палау", "Palau", "PW"]},
    "PS": {"ru": "Палестина", "en": "Palestine", "flag": "🇵🇸", "aliases": ["PS", "Palestine", "Палестина"]},
    "PA": {"ru": "Панама", "en": "Panama", "flag": "🇵🇦", "aliases": ["Panama", "Панама", "PA"]},
    "PG": {"ru": "Папуа-Новая Гвинея", "en": "Papua New Guinea", "flag": "🇵🇬", "aliases": ["PG", "Папуа-Новая Гвинея", "Papua New Guinea"]},
    "PY": {"ru": "Парагвай", "en": "Paraguay", "flag": "🇵🇾", "aliases": ["Парагвай", "PY", "Paraguay"]},
    "PE": {"ru": "Перу", "en": "Peru", "flag": "🇵🇪", "aliases": ["Перу", "PE", "Peru"]},
    "PH": {"ru": "Филиппины", "en": "Philippines", "flag": "🇵🇭", "aliases": ["PH", "Philippines", "Филиппины"]},
    "PL": {"ru": "Польша", "en": "Poland", "flag": "🇵🇱", "aliases": ["Польша", "PL", "Poland", "Polska", "4 Fun", "4Fun"]},
    "PT": {"ru": "Португалия", "en": "Portugal", "flag": "🇵🇹", "aliases": ["PT", "Португалия", "Portugal"]},
    "QA": {"ru": "Катар", "en": "Qatar", "flag": "🇶🇦", "aliases": ["Катар", "QA", "Qatar", "Alkass"]},
    "RO": {"ru": "Румыния", "en": "Romania", "flag": "🇷🇴", "aliases": ["Румыния", "Romania", "RO"]},
    "RU": {"ru": "Россия", "en": "Russia", "flag": "🇷🇺", "aliases": ["RU", "Россия", "Russia"]},
    "RW": {"ru": "Руанда", "en": "Rwanda", "flag": "🇷🇼", "aliases": ["RW", "Rwanda", "Руанда"]},
    "KN": {"ru": "Сент-Китс и Невис", "en": "Saint Kitts and Nevis", "flag": "🇰🇳", "aliases": ["KN", "Saint Kitts and Nevis", "Сент-Китс и Невис"]},
    "LC": {"ru": "Сент-Люсия", "en": "Saint Lucia", "flag": "🇱🇨", "aliases": ["LC", "Saint Lucia", "Сент-Люсия"]},
    "VC": {"ru": "Сент-Винсент", "en": "Saint Vincent", "flag": "🇻🇨", "aliases": ["Сент-Винсент", "VC", "Saint Vincent"]},
    "WS": {"ru": "Самоа", "en": "Samoa", "flag": "🇼🇸", "aliases": ["Самоа", "Samoa", "WS"]},
    "SM": {"ru": "Сан-Марино", "en": "San Marino", "flag": "🇸🇲", "aliases": ["San Marino", "Сан-Марино", "SM"]},
    "ST": {"ru": "Сан-Томе и Принсипи", "en": "Sao Tome and Principe", "flag": "🇸🇹", "aliases": ["ST", "Сан-Томе и Принсипи", "Sao Tome and Principe"]},
    "SA": {"ru": "Саудовская Аравия", "en": "Saudi Arabia", "flag": "🇸🇦", "aliases": ["SA", "Саудовская Аравия", "Saudi Arabia", "Saudi"]},
    "SN": {"ru": "Сенегал", "en": "Senegal", "flag": "🇸🇳", "aliases": ["Сенегал", "SN", "Senegal", "2STV"]},
    "RS": {"ru": "Сербия", "en": "Serbia", "flag": "🇷🇸", "aliases": ["RS", "Сербия", "Serbia"]},
    "SC": {"ru": "Сейшелы", "en": "Seychelles", "flag": "🇸🇨", "aliases": ["Сейшелы", "SC", "Seychelles"]},
    "SL": {"ru": "Сьерра-Леоне", "en": "Sierra Leone", "flag": "🇸🇱", "aliases": ["Sierra Leone", "Сьерра-Леоне", "SL"]},
    "SG": {"ru": "Сингапур", "en": "Singapore", "flag": "🇸🇬", "aliases": ["Singapore", "SG", "Сингапур"]},
    "SK": {"ru": "Словакия", "en": "Slovakia", "flag": "🇸🇰", "aliases": ["Словакия", "SK", "Slovakia"]},
    "SI": {"ru": "Словения", "en": "Slovenia", "flag": "🇸🇮", "aliases": ["Словения", "SI", "Slovenia"]},
    "SB": {"ru": "Соломоновы Острова", "en": "Solomon Islands", "flag": "🇸🇧", "aliases": ["SB", "Соломоновы Острова", "Solomon Islands"]},
    "SO": {"ru": "Сомали", "en": "Somalia", "flag": "🇸🇴", "aliases": ["Somalia", "SO", "Сомали"]},
    "ZA": {"ru": "ЮАР", "en": "South Africa", "flag": "🇿🇦", "aliases": ["South Africa", "ЮАР", "ZA", "Южная Африка"]},
    "SS": {"ru": "Южный Судан", "en": "South Sudan", "flag": "🇸🇸", "aliases": ["SS", "Южный Судан", "South Sudan"]},
    "ES": {"ru": "Испания", "en": "Spain", "flag": "🇪🇸", "aliases": ["Spain", "Espana", "Испания", "ES"]},
    "LK": {"ru": "Шри-Ланка", "en": "Sri Lanka", "flag": "🇱🇰", "aliases": ["LK", "Sri Lanka", "Шри-Ланка"]},
    "SD": {"ru": "Судан", "en": "Sudan", "flag": "🇸🇩", "aliases": ["Судан", "SD", "Sudan"]},
    "SR": {"ru": "Суринам", "en": "Suriname", "flag": "🇸🇷", "aliases": ["SR", "Суринам", "Suriname"]},
    "SE": {"ru": "Швеция", "en": "Sweden", "flag": "🇸🇪", "aliases": ["Швеция", "Sweden", "Sverige", "SE"]},
    "CH": {"ru": "Швейцария", "en": "Switzerland", "flag": "🇨🇭", "aliases": ["Switzerland", "Swiss", "CH", "Швейцария"]},
    "SY": {"ru": "Сирия", "en": "Syria", "flag": "🇸🇾", "aliases": ["Syria", "Сирия", "SY"]},
    "TW": {"ru": "Тайвань", "en": "Taiwan", "flag": "🇹🇼", "aliases": ["TW", "Тайвань", "Taiwan"]},
    "TJ": {"ru": "Таджикистан", "en": "Tajikistan", "flag": "🇹🇯", "aliases": ["Tajikistan", "TJ", "Таджикистан"]},
    "TZ": {"ru": "Танзания", "en": "Tanzania", "flag": "🇹🇿", "aliases": ["Танзания", "TZ", "Tanzania"]},
    "TH": {"ru": "Таиланд", "en": "Thailand", "flag": "🇹🇭", "aliases": ["Таиланд", "TH", "Thailand", "Thai", "True4U", "True 4U"]},
    "TL": {"ru": "Восточный Тимор", "en": "Timor-Leste", "flag": "🇹🇱", "aliases": ["Timor-Leste", "East Timor", "Восточный Тимор", "TL"]},
    "TG": {"ru": "Того", "en": "Togo", "flag": "🇹🇬", "aliases": ["Того", "Togo", "TG"]},
    "TO": {"ru": "Тонга", "en": "Tonga", "flag": "🇹🇴", "aliases": ["Тонга", "Tonga", "TO"]},
    "TT": {"ru": "Тринидад и Тобаго", "en": "Trinidad and Tobago", "flag": "🇹🇹", "aliases": ["Тринидад и Тобаго", "TT", "Trinidad and Tobago"]},
    "TN": {"ru": "Тунис", "en": "Tunisia", "flag": "🇹🇳", "aliases": ["TN", "Тунис", "Tunisia"]},
    "TR": {"ru": "Турция", "en": "Turkey", "flag": "🇹🇷", "aliases": ["Турция", "TR", "Turkey", "Turkiye", "A Haber", "A Spor"]},
    "TM": {"ru": "Туркменистан", "en": "Turkmenistan", "flag": "🇹🇲", "aliases": ["Туркменистан", "Turkmenistan", "TM"]},
    "TV": {"ru": "Тувалу", "en": "Tuvalu", "flag": "🇹🇻", "aliases": ["Тувалу", "TV", "Tuvalu"]},
    "UG": {"ru": "Уганда", "en": "Uganda", "flag": "🇺🇬", "aliases": ["UG", "Uganda", "Уганда"]},
    "UA": {"ru": "Украина", "en": "Ukraine", "flag": "🇺🇦", "aliases": ["Украина", "UA", "Ukraine"]},
    "AE": {"ru": "ОАЭ", "en": "UAE", "flag": "🇦🇪", "aliases": ["UAE", "AE", "Emirates", "ОАЭ", "Эмираты"]},
    "GB": {"ru": "Великобритания", "en": "UK", "flag": "🇬🇧", "aliases": ["United Kingdom", "Britain", "Великобритания", "England", "UK", "Great Britain", "GB"]},
    "US": {"ru": "США", "en": "USA", "flag": "🇺🇸", "aliases": ["США", "US", "USA", "United States", "America", "3ABN", "4K Travel"]},
    "UY": {"ru": "Уругвай", "en": "Uruguay", "flag": "🇺🇾", "aliases": ["Уругвай", "UY", "Uruguay"]},
    "UZ": {"ru": "Узбекистан", "en": "Uzbekistan", "flag": "🇺🇿", "aliases": ["UZ", "Узбекистан", "Uzbekistan"]},
    "VU": {"ru": "Вануату", "en": "Vanuatu", "flag": "🇻🇺", "aliases": ["Vanuatu", "VU", "Вануату"]},
    "VA": {"ru": "Ватикан", "en": "Vatican", "flag": "🇻🇦", "aliases": ["VA", "Ватикан", "Vatican"]},
    "VE": {"ru": "Венесуэла", "en": "Venezuela", "flag": "🇻🇪", "aliases": ["Венесуэла", "Venezuela", "VE"]},
    "VN": {"ru": "Вьетнам", "en": "Vietnam", "flag": "🇻🇳", "aliases": ["VN", "Vietnam", "Вьетнам"]},
    "YE": {"ru": "Йемен", "en": "Yemen", "flag": "🇾🇪", "aliases": ["Yemen", "Йемен", "YE"]},
    "ZM": {"ru": "Замбия", "en": "Zambia", "flag": "🇿🇲", "aliases": ["Zambia", "ZM", "Замбия"]},
    "ZW": {"ru": "Зимбабве", "en": "Zimbabwe", "flag": "🇿🇼", "aliases": ["Zimbabwe", "Зимбабве", "ZW"]},
    "KRD": {"ru": "Курдистан", "en": "Kurdistan", "flag": "☀️", "aliases": ["Kurdistan", "Kurd", "Курдистан", "KRD", "KURD", "4KURD", "Курдский", "Kurdish"]},
    "XK": {"ru": "Косово", "en": "Kosovo", "flag": "🇽🇰", "aliases": ["Косово", "Kosovo", "XK"]},
    "PR": {"ru": "Пуэрто-Рико", "en": "Puerto Rico", "flag": "🇵🇷", "aliases": ["Puerto Rico", "PR", "Пуэрто-Рико"]},
    "HK": {"ru": "Гонконг", "en": "Hong Kong", "flag": "🇭🇰", "aliases": ["Гонконг", "Hong Kong", "HK"]},
    "MO": {"ru": "Макао", "en": "Macau", "flag": "🇲🇴", "aliases": ["Macau", "Макао", "MO"]},
}


# База известных каналов -> страна (для случаев когда group-title не страна)
KNOWN_CHANNELS = {
    # UK
    "BBC One": "GB", "BBC Two": "GB", "BBC Three": "GB", "BBC Four": "GB", "BBC News": "GB", "BBC World": "GB",
    "ITV": "GB", "ITV1": "GB", "ITV2": "GB", "ITV3": "GB", "ITV4": "GB", "Channel 4": "GB", "Channel 5": "GB", "Sky News": "GB", "Sky Sports": "GB",
    # USA
    "CNN": "US", "Fox News": "US", "MSNBC": "US", "ABC": "US", "NBC": "US", "CBS": "US", "ESPN": "US", "HBO": "US", "Discovery": "US",
    # Germany
    "ZDF": "DE", "ARD": "DE", "Das Erste": "DE", "RTL": "DE", "Sat.1": "DE", "ProSieben": "DE", "VOX": "DE", "Kabel Eins": "DE",
    # France
    "TF1": "FR", "France 2": "FR", "France 3": "FR", "France 4": "FR", "France 5": "FR", "M6": "FR", "Canal+": "FR",
    # Italy
    "Rai 1": "IT", "Rai 2": "IT", "Rai 3": "IT", "Canale 5": "IT", "Italia 1": "IT", "Rete 4": "IT",
    # Spain
    "La 1": "ES", "La 2": "ES", "Antena 3": "ES", "Telecinco": "ES", "Cuatro": "ES",
    # Turkey
    "TRT 1": "TR", "TRT": "TR", "ATV": "TR", "Kanal D": "TR", "Show TV": "TR", "Star TV": "TR", "Fox Türkiye": "TR",
    # Russia
    "Первый канал": "RU", "Россия 1": "RU", "НТВ": "RU", "ТНТ": "RU", "СТС": "RU", "РЕН ТВ": "RU", "Пятница": "RU", "Матч ТВ": "RU",
    # Ukraine
    "1+1": "UA", "ICTV": "UA", "СТБ": "UA", "Новый канал": "UA", "Украина": "UA",
    # Poland
    "TVP1": "PL", "TVP2": "PL", "Polsat": "PL", "TVN": "PL",
    # etc - will be extended
    "4KURD": "KRD", "Kurdistan TV": "KRD", "Kurd TV": "KRD",
    "4U TV": "IR", "4UTV": "IR",
    "True4U": "TH",
# From undetected list 5003 -> adding
    "1Almere TV": "NL", "Almere TV": "NL",
    "2GB Sydney": "AU", "3AW Melbourne": "AU", "Sydney": "AU", "Melbourne": "AU",
    "2M": "MA", "2M Monde": "MA", "2M Monde +1": "MA",
    "2STV": "SN",
    "3ABN": "US", "3ABN Dare To Dream": "US", "3ABN English": "US", "3ABN French": "US", "3ABN International": "US", "3ABN Kids": "US", "3ABN Latino": "US", "3ABN Praise": "US", "3ABN Proclaim": "US",
    "3sat": "DE", "3sat HD": "DE",
    "4 Fun TV": "PL", "4 Fun Kids": "PL", "4Fun TV": "PL", "4Fun Kids": "PL",
    "4K Travel TV": "US", "4K TRAVEL TV": "US",
    "5AAB TV": "IN",
    "5TV Corrientes": "AR", "Corrientes": "AR",
    "1-2-3 TV": "TH",  # Thai?
    "2M Monde": "MA",
}

# База логотипов для каналов без tvg-logo (используем публичные логотипы)
KNOWN_LOGOS = {
    # UK
    "BBC One": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/bbc-one-uk.png",
    "BBC Two": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/bbc-two-uk.png",
    "BBC News": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/bbc-news-uk.png",
    "ITV": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/itv-uk.png",
    "Channel 4": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/channel-4-uk.png",
    # USA - news / major
    "CNN": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/cnn-us.png",
    "Fox News": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/fox-news-us.png",
    "ABC": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/abc-us.png",
    "NBC": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/nbc-us.png",
    "CBS": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/cbs-us.png",
    "ESPN": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/espn-us.png",
    "HBO": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/hbo-us.png",
    "Discovery": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/discovery-channel-us.png",
    "National Geographic": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/national-geographic-us.png",
    "Cartoon Network": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/cartoon-network-us.png",
    # USA - 4K / Travel / specific from user report
    "4K Travel TV": "https://i.postimg.cc/8P1rXRgm/4K-TRAVEL-2026-728x412p-01.png",
    "4K Travel": "https://i.postimg.cc/8P1rXRgm/4K-TRAVEL-2026-728x412p-01.png",
    "4K TRAVEL": "https://i.postimg.cc/8P1rXRgm/4K-TRAVEL-2026-728x412p-01.png",
    "Travel TV": "https://i.postimg.cc/8P1rXRgm/4K-TRAVEL-2026-728x412p-01.png",
    "Travel Channel": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/travel-channel-us.png",
    "Travel XP": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/india/travel-xp-in.png",
    # USA - other common IPTV
    "Bloomberg": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/bloomberg-us.png",
    "CNBC": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/cnbc-us.png",
    "Fox Sports": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/fox-sports-1-us.png",
    "NFL Network": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/nfl-network-us.png",
    # Germany
    "ZDF": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/zdf-de.png",
    "ARD": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/das-erste-de.png",
    "Das Erste": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/das-erste-de.png",
    "RTL": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/rtl-de.png",
    # France
    "TF1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/france/tf1-fr.png",
    "France 2": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/france/france-2-fr.png",
    # Kurdistan / Iran / etc
    "4KURD": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/kurdistan/4kurd.png",
    "4U TV": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/iran/4u-tv-ir.png",
}

# Загружаем расширенную базу логотипов (3770+ из tv-logo repo) если есть файл tv_logos.json рядом
try:
    import json as _json
    from pathlib import Path as _Path
    _logo_db_path = _Path(__file__).parent / "tv_logos.json"
    if _logo_db_path.exists():
        with open(_logo_db_path, 'r', encoding='utf-8') as _f:
            _extra_logos = _json.load(_f)
            # Добавляем только те, которых нет в KNOWN_LOGOS (приоритет у ручных)
            for _k, _v in _extra_logos.items():
                if _k not in KNOWN_LOGOS:
                    KNOWN_LOGOS[_k] = _v
        # print(f"Loaded {len(_extra_logos)} extra logos from tv_logos.json", file=sys.stderr)
except Exception as _e:
    # Тихо игнорируем если файла нет
    pass

# Построим индекс lower -> logo для быстрого поиска
_LOGO_INDEX_LOWER = {k.lower(): v for k, v in KNOWN_LOGOS.items()}
# Список ключей отсортированный по длине убыванию для поиска по подстроке (сначала длинные)
_LOGO_KEYS_SORTED = sorted(KNOWN_LOGOS.keys(), key=lambda x: len(x), reverse=True)

def get_logo_for_channel(channel_name: str, tvg_id: str = ""):
    """Ищет логотип для канала по имени, с очисткой от флагов и [Страна] и (1080p)"""
    if not channel_name:
        return None
    import re
    # Очистка для поиска: убрать emoji флаги (суррогаты), [Страна], (1080p), (4K) и т.д.
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', channel_name)  # emoji вне BMP
    clean = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]+', '', clean)
    clean = re.sub(r'\s*\[.*?\]\s*', ' ', clean)  # [США]
    clean = re.sub(r'\s*\(.*?\)\s*', ' ', clean)  # (1080p)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Точное совпадение по оригиналу и по очищенному
    if channel_name in KNOWN_LOGOS:
        return KNOWN_LOGOS[channel_name]
    if clean in KNOWN_LOGOS:
        return KNOWN_LOGOS[clean]
    # Быстрый поиск по lower индексу
    lc = clean.lower()
    if lc in _LOGO_INDEX_LOWER:
        return _LOGO_INDEX_LOWER[lc]
    if channel_name.lower() in _LOGO_INDEX_LOWER:
        return _LOGO_INDEX_LOWER[channel_name.lower()]

    # Поиск по подстроке (очищенный) - только для ключей длиной >2, сортируем длинные вперед
    lower_name = lc
    lower_orig = channel_name.lower()
    # Ограничим поиск первыми 500 наиболее релевантными? Но пройдем по всем отсортированным
    for name in _LOGO_KEYS_SORTED:
        if len(name) < 3:
            continue
        nl = name.lower()
        # Пропускаем слишком общие короткие имена
        if len(nl) < 3:
            continue
        if nl in lower_name or nl in lower_orig:
            return KNOWN_LOGOS[name]
    # По tvg-id
    if tvg_id:
        tl = tvg_id.lower()
        if tl in _LOGO_INDEX_LOWER:
            return _LOGO_INDEX_LOWER[tl]
        if tvg_id in KNOWN_LOGOS:
            return KNOWN_LOGOS[tvg_id]
        for name in _LOGO_KEYS_SORTED:
            nl = name.lower()
            if len(nl) < 3:
                continue
            if nl in tl or tl in nl:
                return KNOWN_LOGOS[name]
    return None


# URL TLD to country
TLD_TO_COUNTRY = {
    ".de": "DE", ".fr": "FR", ".it": "IT", ".es": "ES", ".co.uk": "GB", ".uk": "GB", ".us": "US",
    ".ru": "RU", ".ua": "UA", ".by": "BY", ".kz": "KZ", ".tr": "TR", ".pl": "PL", ".nl": "NL",
    ".be": "BE", ".ch": "CH", ".at": "AT", ".cz": "CZ", ".sk": "SK", ".hu": "HU", ".ro": "RO",
    ".bg": "BG", ".gr": "GR", ".pt": "PT", ".se": "SE", ".no": "NO", ".dk": "DK", ".fi": "FI",
    ".ir": "IR", ".iq": "IQ", ".sa": "SA", ".ae": "AE", ".il": "IL", ".in": "IN", ".jp": "JP",
    ".kr": "KR", ".cn": "CN", ".br": "BR", ".ar": "AR", ".mx": "MX", ".ca": "CA", ".au": "AU",
    ".af": "AF", ".al": "AL", ".dz": "DZ", ".am": "AM", ".az": "AZ", ".ge": "GE", ".kg": "KG",
    ".tj": "TJ", ".tm": "TM", ".uz": "UZ", ".md": "MD", ".lv": "LV", ".lt": "LT", ".ee": "EE",
}

# US states and cities -> country (only cities and full names, not 2-letter codes to avoid false positives like tvg-id)
US_STATES = {
    # Cities
    "Albuquerque": "US", "Orlando": "US", "Milwaukee": "US", "Las Vegas": "US", "Tallahassee": "US", "Miami": "US",
    "New York": "US", "Los Angeles": "US", "Chicago": "US", "Houston": "US", "Phoenix": "US", "Philadelphia": "US",
    "San Antonio": "US", "San Diego": "US", "Dallas": "US", "San Jose": "US", "Austin": "US", "Seattle": "US",
    "Perth": "AU", "Sydney": "AU", "Melbourne": "AU", "Brisbane": "AU", "Adelaide": "AU", "Hawaii": "US",
    "Alicante": "ES", "Valencia": "ES", "Madrid": "ES", "Barcelona": "ES",
    "Budapest": "HU", "Bucharest": "RO", "Sofia": "BG", "Warsaw": "PL", "Prague": "CZ",
    "Doha": "QA", "Dubai": "AE", "Istanbul": "TR", "Ankara": "TR",
    # US states full names
    "Texas": "US", "California": "US", "Florida": "US", "New Mexico": "US", "Wisconsin": "US", "Nevada": "US",
}

def detect_country_from_us_states(text: str):
    if not text:
        return None
    t = text.lower()
    for state, code in US_STATES.items():
        # Check as separate word or in parentheses
        if re.search(rf'\b{re.escape(state.lower())}\b', t):
            return code
    return None



# Построение обратного индекса для быстрого поиска
ALIAS_TO_CODE = {}
for code, info in COUNTRIES.items():
    for alias in info["aliases"]:
        ALIAS_TO_CODE[alias.lower()] = code
        # также без пробелов
    ALIAS_TO_CODE[info["ru"].lower()] = code
    ALIAS_TO_CODE[info["en"].lower()] = code
    ALIAS_TO_CODE[code.lower()] = code

# Дополнительные маппинги для OTT плейлистов
EXTRA_GROUP_MAPPINGS = {
    "usa": "US", "united states": "US", "america": "US",
    "uk": "GB", "england": "GB", "britain": "GB", "united kingdom": "GB",
    "deutschland": "DE", "germany": "DE",
    "france": "FR", "frankreich": "FR",
    "italia": "IT", "italy": "IT",
    "espana": "ES", "spain": "ES",
    "nederland": "NL", "holland": "NL",
    "polska": "PL", "poland": "PL",
    "ceska": "CZ", "czech": "CZ",
    "magyar": "HU", "hungary": "HU",
    "turkiye": "TR", "turkey": "TR",
    "rossiya": "RU", "russia": "RU",
    "ukraina": "UA", "ukraine": "UA",
    "belarus": "BY",
    "kazakhstan": "KZ",
    "kurd": "KRD", "kurdish": "KRD", "kurdistan": "KRD", "4kurd": "KRD", "kurd tv": "KRD",
    "iran": "IR", "persian": "IR", "farsi": "IR", "4u tv": "IR", "4utv": "IR", "4u": "IR",
    "true4u": "TH", "true 4u": "TH",
    "afghan": "AF", "afghanistan": "AF",
    "iraq": "IQ",
    "syria": "SY",
    "lebanon": "LB",
    "egypt": "EG",
    "morocco": "MA",
    "algeria": "DZ",
    "moldova": "MD",
    "sverige": "SE", "sweden": "SE",
    "norge": "NO", "norway": "NO",
    "danmark": "DK", "denmark": "DK",
    "suomi": "FI", "finland": "FI",
    "australia": "AU",
    "canada": "CA",
    "brasil": "BR", "brazil": "BR",
}
for k, v in EXTRA_GROUP_MAPPINGS.items():
    ALIAS_TO_CODE[k.lower()] = v

ATTR_RE = re.compile(r'([a-zA-Z0-9_-]+)="([^"]*)"')

def detect_country_from_text(text: str):
    """Пытается определить страну из произвольного текста"""
    if not text:
        return None
    t = text.strip().lower()
    # Прямое совпадение
    if t in ALIAS_TO_CODE:
        return ALIAS_TO_CODE[t]
    # Проверка известных каналов (точное совпадение)
    for ch_name, code in KNOWN_CHANNELS.items():
        if ch_name.lower() == t or ch_name.lower() in t:
            # Проверяем что это не часть другого слова для коротких названий
            if len(ch_name) <= 3:
                if t == ch_name.lower():
                    return code
            else:
                if ch_name.lower() in t:
                    return code
    # Проверка вхождения алиасов (длинные сначала)
    # Сортируем по длине чтобы избежать ложных срабатываний на коротких кодах
    for alias, code in sorted(ALIAS_TO_CODE.items(), key=lambda x: len(x[0]), reverse=True):
        if len(alias) <= 2:  # короткие коды проверяем только как отдельные слова
            continue
        if alias in t:
            return code
    # Проверка коротких кодов как отдельных слов
    words = re.split(r'[\s\|\-\:\[\]\(\)]+', t)
    for w in words:
        if w in ALIAS_TO_CODE and len(w) == 2:
            return ALIAS_TO_CODE[w]
    return None

def detect_country_from_url(url: str):
    """Пытается определить страну из URL по TLD"""
    if not url:
        return None
    url_lower = url.lower()
    # Проверяем TLD (длинные сначала, типа .co.uk)
    for tld, code in sorted(TLD_TO_COUNTRY.items(), key=lambda x: len(x[0]), reverse=True):
        if tld in url_lower:
            return code
    return None

def detect_country(extinf_line: str, display_name: str, url: str = ""):
    """Определяет страну из EXTINF строки"""
    attrs = dict(ATTR_RE.findall(extinf_line))
    
    # 0. Известные каналы по точному имени
    if display_name:
        dn_lower = display_name.lower().strip()
        for ch_name, code in KNOWN_CHANNELS.items():
            if ch_name.lower() == dn_lower:
                return code
        # Проверка что display_name содержит известный канал
        for ch_name, code in KNOWN_CHANNELS.items():
            if len(ch_name) > 3 and ch_name.lower() in dn_lower:
                return code
    
    # 1. tvg-country
    if "tvg-country" in attrs:
        code = detect_country_from_text(attrs["tvg-country"])
        if code:
            return code
    
    # 2. group-title
    if "group-title" in attrs:
        code = detect_country_from_text(attrs["group-title"])
        if code:
            return code
    
    # 3. Префикс в названии канала типа "US: CNN", "DE | ZDF", "[UK] BBC"
    prefix_match = re.match(r'^\s*[\[\(]?([A-Z]{2,3})[\]\)]?[\s\|\-:\]]+', display_name.strip(), re.IGNORECASE)
    if prefix_match:
        possible = prefix_match.group(1).lower()
        if possible in ALIAS_TO_CODE:
            return ALIAS_TO_CODE[possible]
    
    # 4. Название канала содержит страну
    code = detect_country_from_text(display_name)
    if code:
        return code
    
    # 5. tvg-name
    if "tvg-name" in attrs:
        code = detect_country_from_text(attrs["tvg-name"])
        if code:
            return code
    
    # 6. tvg-id содержит страну
    if "tvg-id" in attrs:
        # например "BBC One UK", "Das Erste.de"
        code = detect_country_from_text(attrs["tvg-id"])
        if code:
            return code
    
    # 7. URL содержит TLD страны
    if url:
        code = detect_country_from_url(url)
        if code:
            return code
    
    # 8. US штаты и города (только display_name, не весь extinf чтобы избежать ложных срабатываний на tvg-id)
    code = detect_country_from_us_states(display_name)
    if code:
        return code
    
    return None

def clean_channel_name(name: str, country_code: str = None):
    """Убирает из названия мусорные префиксы с кодами стран чтобы не дублировать"""
    if not name:
        return name
    original = name.strip()
    
    # Убираем префиксы типа "US:", "US |", "US -", "[US]", "(US)", "USA:", "UK -" и т.д.
    # Делаем несколько проходов
    cleaned = original
    
    # Паттерны для удаления в начале
    prefix_patterns = [
        r'^\s*[\[\(][A-Z]{2,3}[\]\)]\s*[\|\-:\s]*',  # [US] | , (GB) -
        r'^\s*[A-Z]{2,3}\s*[\|\-:\]]\s*',  # US | , DE: , UK -
        r'^\s*[A-Z]{2,3}\s+[A-Z]{2,3}\s*[\|\-:\]]\s*',  # US USA |
        r'^\s*(USA|UK|Germany|France|Russia|Italia|Espana|Turkiye|Polska|Ukraine|Belarus)\s*[\|\-:\]]\s*',  # USA | , Germany:
    ]
    for pat in prefix_patterns:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
    
    # Убираем суффиксы типа " [US]", " (US)", " | US" в конце, если они совпадают с detected country
    # или вообще любые коды стран в конце в скобках
    suffix_patterns = [
        r'\s*[\[\(][A-Z]{2,3}[\]\)]\s*$',  # [US] в конце
        r'\s*[\|\-]\s*[A-Z]{2,3}\s*$',  # | US в конце
    ]
    for pat in suffix_patterns:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Убираем лишние пробелы
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    
    return cleaned if cleaned else original

def format_channel_name(clean_name: str, country_code: str, fmt: str, lang: str):
    """Форматирует название канала с добавлением страны"""
    if not country_code or country_code not in COUNTRIES:
        return clean_name
    
    info = COUNTRIES[country_code]
    flag = info["flag"]
    ru = info["ru"]
    en = info["en"]
    
    if lang == "ru":
        country_label = ru
    elif lang == "en":
        country_label = en
    else:  # both
        country_label = f"{en} / {ru}"
    
    # Проверяем не содержит ли уже название страну чтобы не дублировать
    lower_clean = clean_name.lower()
    if ru.lower() in lower_clean or en.lower() in lower_clean:
        # Если уже содержит, возможно только добавить флаг
        if fmt == "flag_prefix" and flag not in clean_name:
            return f"{flag} {clean_name}"
        return clean_name
    
    if fmt == "prefix_bracket":
        return f"[{country_label}] {clean_name}"
    elif fmt == "suffix_bracket":
        return f"{clean_name} [{country_label}]"
    elif fmt == "suffix_paren":
        return f"{clean_name} ({country_label})"
    elif fmt == "pipe":
        return f"{clean_name} | {country_label}"
    elif fmt == "flag_prefix":
        return f"{flag} {clean_name} [{country_label}]"
    elif fmt == "flag_suffix":
        return f"{clean_name} {flag} [{country_label}]"
    elif fmt == "flag_only":
        return f"{flag} {clean_name}"
    elif fmt == "both_bracket":
        return f"[{en} / {ru}] {clean_name}"
    else:
        return f"{flag} {clean_name} [{country_label}]"

def update_extinf_line(line: str, new_display_name: str, country_code: str, lang: str, keep_group: bool = False):
    """Обновляет EXTINF строку: меняет display name, добавляет/обновляет tvg-country и group-title"""
    if not country_code:
        # Только меняем display name если удалось очистить
        parts = line.split(',', 1)
        if len(parts) == 2:
            return parts[0] + ',' + new_display_name
        return line
    
    info = COUNTRIES[country_code]
    ru = info["ru"]
    en = info["en"]
    flag = info["flag"]
    
    # Разбираем атрибуты
    # Формат: #EXTINF:-1 attr="val" attr2="val2",Display Name
    header_match = re.match(r'^(#EXTINF:[^\s]*)\s*(.*?),', line)
    if not header_match:
        # fallback: просто заменить после последней запятой
        if ',' in line:
            idx = line.rfind(',')
            return line[:idx+1] + new_display_name
        return line
    
    duration_part = header_match.group(1)
    attrs_part = header_match.group(2)
    
    attrs = dict(ATTR_RE.findall(attrs_part))
    
    # Обновляем/добавляем tvg-country
    attrs["tvg-country"] = country_code
    
    # Обновляем group-title если нужно
    if not keep_group:
        # Если lang ru -> группа на русском, если en -> на английском, если both -> en / ru
        if lang == "ru":
            attrs["group-title"] = ru
        elif lang == "en":
            attrs["group-title"] = en
        else:
            attrs["group-title"] = f"{en} / {ru}"
        # Добавляем флаг в группу для OTT-Play? Лучше без флага чтобы группировка работала, но можно с флагом
        # Для OTT-Play FOSS группировка по group-title, флаг не мешает
        # Оставим как есть, но если формат flag_prefix - добавим флаг в группу тоже для наглядности
        # attrs["group-title"] = f"{flag} {attrs['group-title']}"
    else:
        # Оставляем оригинальную группу, но если она пустая - ставим страну
        if "group-title" not in attrs or not attrs["group-title"].strip():
            if lang == "ru":
                attrs["group-title"] = ru
            elif lang == "en":
                attrs["group-title"] = en
            else:
                attrs["group-title"] = f"{en} / {ru}"
    
    # Добавляем tvg-id если его нет - для EPG (формат ChannelName.country)
    if "tvg-id" not in attrs or not attrs["tvg-id"].strip():
        # Генерируем tvg-id из очищенного имени + страна
        # Сначала убираем флаги, [Страна], (1080p)
        base_id = re.sub(r'[\U00010000-\U0010ffff]', '', new_display_name)
        base_id = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]+', '', base_id)
        base_id = re.sub(r'\s*\[.*?\]\s*', ' ', base_id)
        base_id = re.sub(r'\s*\(.*?\)\s*', ' ', base_id)
        # Убираем названия стран на русском/английском чтобы не дублировать
        if country_code and country_code in COUNTRIES:
            ru = COUNTRIES[country_code]["ru"]
            en = COUNTRIES[country_code]["en"]
            base_id = base_id.replace(ru, '').replace(en, '')
        base_id = re.sub(r'\s+', ' ', base_id).strip()
        # Оставляем только буквы, цифры, пробелы, дефис
        base_id = re.sub(r'[^\w\s-]', '', base_id, flags=re.UNICODE).strip()
        base_id = re.sub(r'\s+', ' ', base_id).strip()
        if base_id:
            if country_code:
                attrs["tvg-id"] = f"{base_id}.{country_code.lower()}"
            else:
                attrs["tvg-id"] = base_id
            if "tvg-name" not in attrs:
                attrs["tvg-name"] = base_id
    
    # Добавляем логотип если его нет
    if "tvg-logo" not in attrs or not attrs["tvg-logo"].strip():
        # Пытаемся найти логотип по имени канала
        tvg_id = attrs.get("tvg-id", "")
        logo = get_logo_for_channel(new_display_name, tvg_id)
        if not logo:
            # Пробуем по оригинальному имени без флага и страны
            # Убираем эмодзи и [Страна]
            clean_for_logo = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]+', '', new_display_name)
            clean_for_logo = re.sub(r'\s*\[.*?\]\s*', '', clean_for_logo).strip()
            logo = get_logo_for_channel(clean_for_logo, tvg_id)
        if logo:
            attrs["tvg-logo"] = logo
    
    # Пересобираем атрибуты в строку
    # Сохраняем порядок: tvg-id, tvg-name, tvg-logo, group-title, tvg-country, остальные
    ordered_keys = ["tvg-id", "tvg-name", "tvg-logo", "group-title", "tvg-country"]
    # Добавляем остальные ключи
    for k in attrs.keys():
        if k not in ordered_keys:
            ordered_keys.append(k)
    
    attrs_str = ""
    for k in ordered_keys:
        if k in attrs:
            # Экранируем кавычки если есть
            v = attrs[k].replace('"', "'")
            attrs_str += f' {k}="{v}"'
    
    return f"{duration_part}{attrs_str},{new_display_name}"

def load_playlist_lines(input_path_or_url: str):
    """Загружает строки плейлиста из файла или URL"""
    if input_path_or_url.startswith("http://") or input_path_or_url.startswith("https://"):
        print(f"📥 Загружаю плейлист по ссылке: {input_path_or_url}")
        req = urllib.request.Request(input_path_or_url, headers={"User-Agent": "Mozilla/5.0 OTT-Play-FOSS-Converter"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return content.splitlines(keepends=True)
    else:
        p = Path(input_path_or_url)
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            return f.readlines()

def process_playlist(input_path: Path | str, output_path: Path, fmt: str = "flag_prefix", lang: str = "ru", keep_group: bool = False, verbose: bool = False, epg_url: str = None, add_epg: bool = True):
    """Основная функция обработки плейлиста"""
    lines = load_playlist_lines(str(input_path))
    
    output_lines = []
    stats = {"total": 0, "detected": 0, "countries": {}}
    
    # EPG URL по умолчанию - рабочие EPG из iptv-org и epgshare (проверено 2026)
    if add_epg and not epg_url:
        # Используем epgshare + iptv-org рабочие гайды - покрывают 10000+ каналов
        epg_url = "https://epgshare01.online/epgshare01/epg_ripper_US1.xml.gz,https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz,https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz,https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz,https://iptv-org.github.io/epg/guides/us/tvtv.us.epg.xml,https://iptv-org.github.io/epg/guides/uk/sky.com.epg.xml"
    
    # Убедиться что первая строка #EXTM3U с url-tvg для EPG
    if lines and lines[0].strip().startswith("#EXTM3U"):
        first = lines[0].strip()
        if add_epg and 'url-tvg=' not in first:
            # Добавляем url-tvg в первую строку
            if first == "#EXTM3U":
                output_lines.append(f'#EXTM3U url-tvg="{epg_url}"\n')
            else:
                # Уже есть атрибуты, добавляем url-tvg
                output_lines.append(first + f' url-tvg="{epg_url}"\n')
        else:
            output_lines.append(lines[0])
        start_idx = 1
    else:
        if add_epg:
            output_lines.append(f'#EXTM3U url-tvg="{epg_url}"\n')
        else:
            output_lines.append("#EXTM3U\n")
        start_idx = 0
    
    i = start_idx
    undetected = []
    while i < len(lines):
        line = lines[i].rstrip('\n')
        
        if line.strip().startswith("#EXTINF"):
            stats["total"] += 1
            # Достаем display name
            if ',' in line:
                display_name = line.split(',', 1)[1].strip()
            else:
                display_name = ""
            
            # Следующая строка - обычно URL
            next_url = ""
            if i+1 < len(lines):
                nxt = lines[i+1].strip()
                if nxt and not nxt.startswith("#"):
                    next_url = nxt
            
            country_code = detect_country(line, display_name, next_url)
            
            if country_code:
                stats["detected"] += 1
                stats["countries"][country_code] = stats["countries"].get(country_code, 0) + 1
                clean_name = clean_channel_name(display_name, country_code)
                new_display = format_channel_name(clean_name, country_code, fmt, lang)
                new_line = update_extinf_line(line, new_display, country_code, lang, keep_group)
                if verbose:
                    print(f"[{country_code}] {display_name} -> {new_display}")
            else:
                # Не удалось определить страну - оставляем как есть, но очищаем немного
                clean_name = clean_channel_name(display_name)
                new_display = clean_name
                new_line = update_extinf_line(line, new_display, None, lang, keep_group) if clean_name != display_name else line
                if verbose:
                    print(f"[??] {display_name} - страна не определена")
                undetected.append(display_name)
            
            output_lines.append(new_line + "\n")
        else:
            output_lines.append(line + "\n")
        i += 1
    
    with open(output_path, 'w', encoding='utf-8') as out:
        out.writelines(output_lines)
    
    stats["undetected_list"] = undetected
    return stats

def main():
    parser = argparse.ArgumentParser(description="Конвертер плейлистов для OTT-Play FOSS - добавляет страну к названию канала")
    parser.add_argument("input", help="Входной .m3u / .m3u8 файл или URL")
    parser.add_argument("output", nargs="?", help="Выходной файл (по умолчанию input_ott.m3u)")
    parser.add_argument("--format", "-f", dest="fmt", default="flag_prefix",
                        choices=["prefix_bracket", "suffix_bracket", "suffix_paren", "pipe", "flag_prefix", "flag_suffix", "flag_only", "both_bracket"],
                        help="Формат отображения: flag_prefix = 🇺🇸 Название [США] (рекомендуется для OTT-Play FOSS)")
    parser.add_argument("--lang", "-l", default="ru", choices=["ru", "en", "both"], help="Язык названия страны")
    parser.add_argument("--keep-group", action="store_true", help="Не перезаписывать group-title, оставить оригинальные группы")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument("--epg", action="store_true", default=True, help="Добавить EPG url-tvg в заголовок (по умолчанию включено)")
    parser.add_argument("--no-epg", dest="epg", action="store_false", help="Не добавлять EPG")
    parser.add_argument("--epg-url", default=None, help="Кастомный URL EPG (по умолчанию https://iptv-org.github.io/epg/guides/all.xml)")
    
    args = parser.parse_args()
    
    input_str = args.input
    is_url = input_str.startswith("http://") or input_str.startswith("https://")
    
    if not is_url:
        input_path = Path(input_str)
        if not input_path.exists():
            print(f"Ошибка: файл {input_path} не найден", file=sys.stderr)
            sys.exit(1)
    else:
        input_path = input_str
    
    if args.output:
        output_path = Path(args.output)
    else:
        if is_url:
            output_path = Path("playlist_ott.m3u")
        else:
            p = Path(input_str)
            output_path = p.parent / f"{p.stem}_ott{p.suffix}"
    
    stats = process_playlist(input_path, output_path, args.fmt, args.lang, args.keep_group, args.verbose, epg_url=args.epg_url, add_epg=args.epg)
    
    print(f"\n✅ Готово! Обработано {stats['total']} каналов")
    print(f"   Определено стран: {stats['detected']}")
    print(f"   Не определено: {stats['total'] - stats['detected']} ({100 - int(stats['detected']/stats['total']*100) if stats['total']>0 else 0}% )")
    print(f"   Выходной файл: {output_path}")
    if stats["countries"]:
        print("\n📊 По странам:")
        for code, count in sorted(stats["countries"].items(), key=lambda x: x[1], reverse=True):
            info = COUNTRIES.get(code, {"flag":"🏳️","ru":code})
            print(f"   {info['flag']} {info['ru']} ({code}): {count} каналов")
    if stats.get("undetected_list") and len(stats["undetected_list"]) > 0:
        print(f"\n❓ Не определено ({len(stats['undetected_list'])} каналов), первые 20:")
        for name in stats["undetected_list"][:20]:
            print(f"   - {name}")
        if len(stats["undetected_list"]) > 20:
            print(f"   ... и еще {len(stats['undetected_list'])-20} каналов")
        # Сохраняем список неопределенных в файл
        undetected_file = output_path.parent / f"{output_path.stem}_undetected.txt"
        with open(undetected_file, 'w', encoding='utf-8') as f:
            for name in stats["undetected_list"]:
                f.write(name + "\n")
        print(f"\n💾 Список неопределенных сохранен в: {undetected_file}")
        print("   Пришлите этот файл, я добавлю эти каналы в базу!")

if __name__ == "__main__":
    main()
