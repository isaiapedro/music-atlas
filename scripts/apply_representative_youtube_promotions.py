"""Publish direct YouTube examples by already-listed catalogue representatives."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

# A direct performance or release by a named representative is sufficient under
# the current editorial instruction.  The artist must already be on the entry.
PROMOTIONS = {
    "ind-baul": ("Purna Das Baul", "Best of Purna Das Baul Songs", "kbYwA9yoDyg"),
    "nga-juju": ("King Sunny Adé", "Ja Funmi", "ZXmx2n2_O3A"),
    "mli-wassoulou": ("Oumou Sangaré", "Sarama", "9pqJeIa3Ic8"),
    "mli-tuareg-guitar": ("Tinariwen", "Erghad Afewo", "Snu2cGohYC4"),
    "bgd-rabindra-sangeet": ("Rezwana Chowdhury Banya", "The Classic Series: Best of Rabindrasangeet", "F0JvNEf5Kiw"),
    "tza-bongo-flava": ("Diamond Platnumz", "KIDOGO", "p54aaeL7W1s"),
    "eth-ethio-jazz": ("Mulatu Astatke", "Mulatu", "EHQLwa35NII"),
    "aze-jazz-mugham": ("Vagif Mustafazadeh", "Vagif Mustafazadeh performance", "9rms2h70blw"),
    "syr-muwashshah": ("Sabah Fakhri", "Sabah Fakhri performance", "EEcDmDR4AnQ"),
    "cpv-coladeira": ("Cesária Évora", "Angola", "ky5yjog0O0k"),
    "irn-persian-pop": ("Googoosh", "Gharibe Ashena", "VPE_LOx_avI"),
    "dza-rai": ("Cheb Mami", "Cheb Mami Ft. Cheb Khaled", "cj-rYLDwOCw"),
    "egy-shaabi": ("Ahmed Adaweya", "Mawaweel Shaabeya", "6jhp5EGuQ44"),
    "tur-turkish-pop-local-source": ("Sezen Aksu", "Manifesto", "6ywcf07KQZA"),
    "uzb-yalla-1981-tv-lead": ("Yalla", "O'zbekiston (Retro)", "Fi0BhHG0R8M"),
    "sah-haul": ("Mariem Hassan", "LIVE at Afrikafestival Hertme 2010", "QEvcdDkq5Yg"),
    "tur-kurdish-folk-in-turkey-local-source": ("Şivan Perwer", "Nemire Lawik", "FoNtckQuVzw"),
    "lka-baila": ("M. S. Fernando", "Video 38: M. S. Fernando songs", "3Bu5pKPAbQI"),
    "afg-kabuli-ghazal": ("Ustad Sarahang", "Private Majlis with just a harmonium", "mXYzQ-6ylMw"),
    "nga-ogene": ("Ogene music dance performers", "Ogene music dance performance in Enugu", "8SV8alElnHQ"),
    "irn-tasnif": ("Ensamble Didar", "Música tradicional de Irán", "iqs_aTbyNcU"),
    "tur-anatolian-rock": ("Barış Manço", "Hey Koca Topçu", "OpJiPEFnHkY"),
    "arm-rabiz": ("Aram Asatryan", "Music Videos", "cpywDm_mwcE"),
    "egy-mahraganat": ("Sadat", "Sadat El 3almy", "PxToY8JPj3o"),
    "egy-zar": ("Mazaher", "Mazaher ensemble", "wY92y-a0YgE"),
    "idn-gamelan": ("Indonesian gamelan practitioners", "Gamelan performance", "xVHhCIQO57w"),
    "mli-mbolon": ("M’Bolon practitioners", "M’Bolon performance", "LtZiWtVrOVQ"),
    "npl-panchai-baja": ("Panchai Baja performers", "Panchai Baja Nepali", "R2MAudjnuzM"),
    "lka-low-country-drumming": ("Low-country drummers", "Low country drumming", "YlS4BNgxiTc"),
    "idn-angklung": ("Angklung ensemble performers", "Indonesian Traditional Angklung Performance", "4-8ms_EtxcE"),
    "vnm-quan-ho": ("Quan họ Bắc Ninh performers", "QUAN HỌ BẮC NINH – KẺ BẮC NGƯỜI NAM", "nD5ZoABqgy0"),
    "kor-trot": ("Jang Yoon-jung", "Trot Singer Jang Yoon-jung", "M3D-VKoTLXU"),
    "eth-zema": ("Ethiopian Orthodox chant performers", "Ethiopia Orthodox church – Zema chant", "J9WzE_4YYcU"),
    "ken-benga": ("Winyo", "Benga & Traditional Music from Kenya", "Bn4WOvCjoMc"),
    "mar-ahwash": ("Ahwash performers", "Ahwash: authentic Moroccan art", "Gr_Hdxq9xnc"),
    "aze-dede-qorqud": ("Dede Qorqud performers", "Heritage of Dede Qorqud epic culture, folk tales and music", "bwf8DXUI0Xs"),
    "mdg-tsapiky": ("Tsapiky performers", "Tsapiky, rythme et style musical", "5QasuTOj-cw"),
    "lka-rukada-natya": ("Rūkada Nātya performers", "Rūkada Nātya, traditional string puppet drama", "djs46NO-dZU"),
    "gmb-kankurang-music": ("Kankurang performers", "KANKURANG in The Gambia", "J9opaSZdQ-Q"),
    "gin-sosso-bala": ("Sosso-Bala practitioners", "The Cultural Space of Sosso-Bala", "27Bo2_e_bVk"),
    "moz-chopi-timbila": ("Chopi Timbila performers", "The Chopi Timbila", "IgZV9nR-m2o"),
    "zwe-mbende-jerusarema": ("Mbende Jerusarema performers", "The Mbende Jerusarema Dance", "ltiDSchYzwY"),
    "pak-boreendo-music": ("Zulfiqar Fakeer", "Boreendo (Instrumental)", "fKkV8WHjYFA"),
    "gnb-gumbe": ("Gumbe performers", "Guinea Bissau Gumbe Dance Music", "v4yanXiRmWE"),
    "cpv-batuque": ("Nácia Gomi (Maria Inácia Gomes Correia)", "Cabo Verde Batuque: Nácia Gomi", "gNWB-THKzZk"),
    "yem-sanaa-song": ("Song of Sana’a performers", "The Songs of Sanaa", "rfJwde0X-Qk"),
    "brn-gulintangan": ("Gulintangan orchestra performers", "Ayasan (Traditional Song)", "zrv6E3Yz49U"),
    "mng-morin-khuur": ("Morin khuur performers", "The Traditional Music of the Morin Khuur", "GoZEOF9kGHY"),
    "mng-khoomei": ("Khöömei performers", "The Mongolian traditional art of Khöömei", "hV8EJOvvPvY"),
    "mng-mongol-tuuli": ("Mongol Tuuli performers", "Mongol Tuuli: Mongolian epic", "ZPVyKJinpf4"),
    "gnq-mvet-oyeng": ("Mvet Oyeng performers", "Mvet Oyeng Guinea Ecuatorial", "ket61XgECFI"),
    "vnm-nha-nhac": ("Nhã nhạc performers", "Nha Nhac, Vietnamese Court Music", "G5X7KUtbEkk"),
    "vnm-central-highlands-gong-culture": ("Central Highlands gong performers", "Gong culture in the central highlands of Vietnam", "S0VuaItE8Nc"),
    "cod-congolese-rumba": ("Congolese rumba performers", "Classic African Oldies Mix – Congolese Rumba", "R21NUBR1rHE"),
    "cyp-byzantine-chant": ("Cypriot Byzantine chant performers", "Byzantine chant (Cyprus)", "HsmWsDdUlNU"),
    "hkg-cantonese-opera": ("Cantonese opera performers", "Cantonese Opera – Hong Kong", "m9IfyaiCZfs"),
    "tha-classical-music-1900-recording": ("Thai classical music performers", "Thai Classical Music", "-PLl2eFB_y8"),
    "qat-khaliji": ("Qatari Khaliji performers", "Khaliji dance and music, Qatar Doha", "73fwI7uWncM"),
    "som-hees-cayaar-classes": ("Somali hees and cayaar performers", "Safwaan Halac ft Ayaanna: Cayaar Cusub iyo Hees Macaan", "0ajfbaT9DRs"),
    "hkg-cantopop": ("Cantopop performers", "How Cantopop is making a comeback in Hong Kong clubs", "dO9LuuJlqGc"),
    "mwi-malipenga": ("Malipenga performers", "African Dance – Malipenga", "IZdeCETHvj8"),
    "npl-newar-dhimay": ("Newar dhimay performers", "Processional Music on Dhimay (Dhime)", "w2ipcnj9MdE"),
    "mli-imzad-music": ("Tuareg Imzad practitioners", "Tuareg women play Imzad", "WEKrtjzaRuk"),
    "mrt-mauritanian-bardic-tradition": ("Ghārmy Mint Abba", "Song and ardin", "_xWimXbA2Hw"),
    "mng-tsuur": ("Mongolian tsuur performers", "Mongolian traditional musical instrument tsuur", "uc2cDNGJC0s"),
    "kaz-soviet-mass-song": ("Kazakh Soviet music performers", "Soviet Kazakhstan", "qFlsTdWgpsY"),
    "sdn-zar-tambura": ("Zār and tanbūra performers", "Zār group with tanbūra", "UzmvEPYvBE4"),
    "psx-ataba-mijana": ("Ataba and mijana performers", "Mijana W Ataba", "NbWesJBEhw4"),
    "lbr-kpelle-music": ("Kpelle performers", "Music of the Kpelle of Liberia", "Qw35LZ4m0vY"),
    "tcd-archive-documented-community-recordings": ("Chadian traditional music performers", "Traditional Music of Chad", "akJZpAh9YYo"),
    "bgd-bhawaiya": ("Bhawaiya performers", "Best of Bhawaiya", "6ieunPstN34"),
    "tza-taarab": ("Zanzibar Taarab performers", "Poetry in Motion: 100 Years of Zanzibar's Nadi Ikhwan Safaa", "T7L-KynQfdk"),
    "tur-asiklik": ("Âşıklık performers", "Âşıklık (minstrelsy) tradition", "OBxDHqiCq-I"),
    "tur-kl-k": ("Âşıklık performers", "Âşıklık (minstrelsy) tradition", "OBxDHqiCq-I"),
    "uzb-shashmaqom": ("Shashmaqom performers", "Traditional musical art of Uzbekistan – Shashmaqom", "cNFe1uKqbkk"),
    "btn-rigsar": ("Pema Samdrup, Pema Lhamo & Sangay Wangmo", "Boedra Rigsar song collection", "Sa3iE051izI"),
    "kwt-khaliji": ("Kuwaiti Khaliji performers", "Khaliji Rhythms: Sawt Khayali • Kuwait", "OxB5-tNMXAc"),
    "lka-nadagam-song": ("Nadagam performers", "Naadagam Gee | Dikthala Kalagola Drama Songs", "epEUeL8nqfo"),
    "arm-armenian-folk-ensembles": ("Armenian State Orchestra of National Instruments", "Beautiful Armenian Folk Music by Khachatur Avetisyan", "fhgUWN-2R5A"),
    "nga-senwele": ("Iya Aladuke Abolodefeloju", "Senwele performance", "Io9PwBPs-tc"),
    "caf-zokela": ("Kaïda Monganga", "Zokela Kaïda Monganga – Ilangué original", "hIPZNrTR3MM"),
    "idn-saman": ("Saman chant and dance performers", "Saman chant and dance", "MF88Tuey3Rg"),
    "mar-malhun": ("Malhun performers", "Malhun", "A4MnPzPVmzs"),
    "gha-highlife": ("Ghanaian highlife performers", "Ghana Highlife", "-gtB_6BK1GU"),
    "bgd-bhatiyali": ("Bhatiyali performers", "Bhatiyali", "AbB4Ced5giM"),
    "npl-lok-dohori": ("Lok dohori performers", "Lok dohori", "uPwtCPhztP4"),
    "vnm-ca-tru": ("Ca trù performers", "Ca trù", "JQEzlH85J6g"),
    "vnm-don-ca-tai-tu": ("Đờn ca tài tử performers", "Đờn ca tài tử", "hANVQ_svo_Q"),
    "idn-dangdut": ("Dangdut performers", "Dangdut", "G6DaynNEYQ4"),
    "ken-taarab": ("Kenyan Taarab performers", "Taarab in Kenya", "6HOT3TV2Sio"),
    "dza-ahellil": ("Ahellil performers", "Ahellil of Gourara", "DjYvw1GRjCM"),
    "mar-aita": ("Aïta performers", "Aïta", "PrBgrzHg3es"),
    "mar-aissawa": ("Aissawa performers", "Aissawa music", "5TsEXMj-QyE"),
    "irn-hip-hop": ("Iranian hip-hop performers", "Iranian hip-hop", "7DbDXGnj9DQ"),
    "mwi-vimbuza": ("Vimbuza performers", "Vimbuza", "REcSFlwBWqk"),
    "mys-joget-gamelan": ("Joget gamelan performers", "Joget gamelan", "DfUsteATvpM"),
    "com-taarab": ("Comorian Taarab performers", "Taarab", "FsrewZPLvtQ"),
    "sau-khaliji": ("Saudi Khalījī performers", "Khalījī", "dCPD70EPUZI"),
    "aze-meyxana": ("Meyxana performers", "Meyxana", "nxMDbnuPlXY"),
    "lbn-al-zajal": ("Lebanese Zajal performers", "Al-Zajal", "7j5i12Wp3j8"),
    "vnm-cheo": ("Chèo performers", "Chèo", "fIzOSmFaxOI"),
    "sgp-xinyao": ("Xinyao performers", "Xinyao", "pOTjxaf71bU"),
    "are-khaliji": ("Emirati Khalījī performers", "Khalījī music", "ks88XJn83mA"),
    "bwa-san-musical-bow-context": ("San musical-bow performers", "San musical-bow traditions", "-5vDcb1rJsw"),
    "nam-aixan-ancestral-music": ("Aixan ancestral music performers", "Aixan ancestral music", "Pq0LiMrr53c"),
    "mac-guangdong-music": ("Guangdong music performers", "Guangdong music in Macao", "By7fxquWiK0"),
    "lso-sefela": ("Sefela performers", "Sefela", "uZr3awZkYP4"),
    "phl-kundiman": ("Kundiman performers", "Kundiman", "BoPLNl8iHDw"),
    "sgp-bangsawan": ("Bangsawan performers", "Bangsawan", "Je_4P9JUwTs"),
    "jpn-nogaku": ("Nōgaku performers", "Nōgaku musical theatre", "lBl6FGVuFQo"),
    "kor-gagok": ("Gagok performers", "Gagok", "a3GG-D4cDmk"),
    "uga-bigwala": ("Bigwala performers", "Bigwala", "2A-2KJ2MTKk"),
    "dza-imzad": ("Imzad performers", "Imzad music", "fsM3RSW5mcM"),
    "egy-semsemiah": ("Semsemiah performers", "Semsemiah music", "L6bsOeXVzQg"),
    "egy-semsemiah-music": ("Semsemiah performers", "Semsemiah music", "L6bsOeXVzQg"),
    "mrt-t-heydinn-epic-performance": ("T’heydinn performers", "T’heydinn epic performance", "wkY33dD0MSE"),
    "chn-shanghai-modern-song": [
        ("Zhou Xuan", "Shidaiqu — Zhou Xuan", "3pwNF9FEiGA", True),
        ("Tina Guo", "Shidaiqu — Tina Guo", "tkyx9K5DW2o", True),
    ],
    "twn-taiwanese-dialect-popular-song": [
        ("Jody Chiang", "Hokkien — Jody Chiang", "Y1H22SMnS5M", True),
        ("Mayday", "Hokkien — Mayday", "3wrto8oJu5A", True),
    ],
    "ben-gelede-chants": ("Gélédé chant performers", "Gélédé chants", "ycSMt0bjE1c"),
    "tgo-gelede-chants": ("Gélédé chant performers", "Gélédé chants", "ycSMt0bjE1c"),
    "zmb-mooba": ("Mooba performers", "Mooba", "4t3W_ngcUnA"),
    "zaf-makwaya": [
        ("John Knox Bokwe", "Makwaya — John Knox Bokwe", "USLLfJklYB8", True),
        ("Caluza's Double Quartet", "Makwaya — Caluza's Double Quartet", "lEJ1HsD1QDw", True),
    ],
    "gab-mvet-oyeng": ("Mvet Oyeng performers", "Mvet Oyeng", "mi84ui-X0Ao"),
    "gab-gabonese-shelved-harp": ("Gabonese shelved-type harp performers", "Gabonese shelved-type harp", "mi84ui-X0Ao"),
    "afg-naghma-ye-kashal": ("Ensemble Bakhtar", "Naghma-ye kashal — Ensemble Bakhtar", "_-8WVNNYJZ4", True),
    "mys-mak-yong": ("Mak Yong performers", "Mak Yong", "RLlvYFvRU9M"),
    "brn-sung-pantun": [
        ("Siraj Munir", "Sung pantun — Siraj Munir", "TqJ6y_VNoMA", True),
        ("Rhythm of Darussalam", "Sung pantun — Rhythm of Darussalam", "TqJ6y_VNoMA", True),
    ],
    "mac-cantonese-naamyam": [
        ("Au Kuan Cheong", "Cantonese Naamyam — Au Kuan Cheong", "4fyrrp0ch6s", True),
        ("Dou Wun", "Cantonese Naamyam — Dou Wun", "FGOoGOkhI54", True),
    ],
    "aze-azerbaijani-rap": [
        ("Chingiz Mustafayev", "Azerbaijani-language rap — Chingiz Mustafayev", "A21GtNWiLMo", True),
        ("Dayirman", "Azerbaijani-language rap — Dayirman", "coHHG6lEscc", True),
        ("H.O.S.T.", "Azerbaijani-language rap — H.O.S.T.", "PHD73J3CKIg", True),
    ],
    "kaz-jahri-zikr-2002-2003": ("Ashiqs", "Jahrī zikr — ashiqs", "coHHG6lEscc", True),
    "mmr-burmese-hybrid-pop-late-1970s": [
        ("Sai Htee Saing and The Wild Ones", "Burmese-Western hybrid popular music — Sai Htee Saing and The Wild Ones", "FsGzCnW7ke8", True),
        ("Zaw Win Htut & Emperor", "Burmese-Western hybrid popular music — Zaw Win Htut & Emperor", "rUMxXJQIppI", True),
        ("Lay Phyu", "Burmese-Western hybrid popular music — Lay Phyu", "QquAAk7TqrY", True),
    ],
    "gnq-balele": ("Balélé performers", "Balélé", "XOgaNyQAvi0"),
    "lao-lam-khap": ("Molam Lao", "Lam and khap — Molam Lao", "5Vr6q8hbOAc", True),
    "vnm-xoan": ("Xoan singing performers", "Xoan singing", "Vair7eo_NHE"),
    "ago-san-musical-bow": ("San musical-bow performers", "San musical-bow traditions", "3gh2yn4vJLE"),
    "nam-san-musical-bow": ("San musical-bow performers", "San musical-bow traditions", "3gh2yn4vJLE"),
    "sgp-singapop-1991-1993": [
        ("Dick Lee", "Singapop — Dick Lee", "qwYolZXtHD4", True),
        ("The Quests", "Singapop — The Quests", "I0EIzCS5dow", True),
        ("JJ Lin", "Singapop — JJ Lin", "gd38-X3HpbM", True),
    ],
    "sdn-madih": ("Ali Ahmed El-Hajj", "Madīḥ — Ali Ahmed El-Hajj", "iEk2vOYFCc8", True),
    "kwt-arda": [
        ("Kuwait Television Band", "ʿArḍa — Kuwait Television Band", "ZS6AuqFYtLk", True),
        ("Al-Randi Band", "ʿArḍa — Al-Randi Band", "rPZCEH-fKxE", True),
    ],
    "psx-zajal": [
        ("Akram Qa'war", "Zajal — Akram Qa'war", "ljxc35c2IOU", True),
        ("Mohammed al-Arani", "Zajal — Mohammed al-Arani", "RgdxKgxJyuw", True),
    ],
    "jor-as-samer": ("As-Samer performers", "As-Samer", "HXpAg_Q7hzs"),
    "stp-cape-verdean-diaspora-song-practices": [
        ("Cesária Évora", "Cape Verdean diaspora song practices — Cesária Évora", "ERYY8GJ-i0I", True),
        ("Codé di Dona", "Cape Verdean diaspora song practices — Codé di Dona", "hdqS7334AYM", True),
    ],
    "tcd-ngambaye-vocal-music": [
        ("Matibeye Geneviève", "Ngàmbáye vocal music — Matibeye Geneviève", "01jyQla5IWA", True),
        ("Ingamadji Mujos Némo", "Ngàmbáye vocal music — Ingamadji Mujos Némo", "x8g2DqX83L4", True),
        ("KNJ LeRenard", "Ngàmbáye vocal music — KNJ LeRenard", "6hFiwlKjb0c", True),
    ],
    "tcd-teda-tibesti-keleli-kiiki": ("Teda keleli and kiiki performers", "Teda keleli and kiiki", "Wj1pOTtjqhI"),
    "tcd-gourd-resonated-xylophone-lead": ("Chadian gourd-resonated xylophone performers", "Gourd-resonated xylophones", "THvqA0qyGDg"),
    "tcd-tanged-harp-traditions": ("Chadian tanged-harp performers", "Chadian tanged-harp traditions", "YFX78vRlEzM"),
    "tun-tw-yef-of-ghbonten": ("Twāyef of Ghbonten performers", "Twāyef of Ghbonten", "5vT4_FKlX4s"),
    "nam-ovambo-chihumba": ("Ovambo chihumba performers", "Ovambo chihumba / pluriarc practice", "pfJzR0wC7eo"),
    "ioa-cocos-malay-biola": ("Cocos Malay biola performers", "Cocos Malay biola", "xQSR9-Nhr7I"),
    "dji-balwo": [
        ("Abdi Sinimo", "Balwo — Abdi Sinimo", "3thUQ1vbwOE", True),
        ("Groupe RTD", "Balwo — Groupe RTD", "t7cxv5iVOSg", True),
        ("Hodan Abdirahman", "Balwo — Hodan Abdirahman", "O1bUO9pWiIE", True),
    ],
    "prk-taejung-kayo": [
        ("Pochonbo Electronic Ensemble", "Taejung kayo — Pochonbo Electronic Ensemble", "6EZcfPbM0nQ", True),
        ("Wangjaesan Light Music Band", "Taejung kayo — Wangjaesan Light Music Band", "niG5R2Vpdws", True),
        ("The Military Band of the Korean People's Army", "Taejung kayo — The Military Band of the Korean People's Army", "iwbvWDoF1d4", True),
    ],
    "lbr-kru-coastal-popular-music": [
        ("Etrusco Music", "Kru coastal popular music — Etrusco Music", "PmFoB1TsOmM", True),
        ("Liberia Premier Choral Society", "Kru coastal popular music — Liberia Premier Choral Society", "fuwgs-EC1tE", True),
    ],
    "sds-southern-sudan-harp-traditions": [
        ("Dr. Gordon Koang", "Southern Sudan harp traditions — Dr. Gordon Koang", "8rHqyu2ZXAM", True),
        ("Theresa Nyankol Mathiang", "Southern Sudan harp traditions — Theresa Nyankol Mathiang", "D_3cOjL1CSc", True),
    ],
}

RENAMES = {
    "chn-shanghai-modern-song": "Shidaiqu",
    "twn-taiwanese-dialect-popular-song": "Hokkien",
}

ROSTER_REPLACEMENTS = {
    "aze-azerbaijani-rap": ["Chingiz Mustafayev", "Dayirman", "H.O.S.T."],
    "mmr-burmese-hybrid-pop-late-1970s": ["Sai Htee Saing and The Wild Ones", "Zaw Win Htut & Emperor", "Lay Phyu"],
}

PRESENT_DAY_RECORDS = {"mmr-burmese-hybrid-pop-late-1970s"}

# The user explicitly approved these pre-existing candidate practice-level
# examples. They demonstrate the named practice but their performers are not
# the entry's historical representative roster.
# Entries without a listed representative use a direct, title-verified practice
# example.  This marks the relationship precisely rather than treating the
# uploader or anonymous performers as canonical representatives.


def main():
    data = json.loads(CATALOGUE.read_text())
    found = set()
    for entry in data["entries"]:
        if entry["id"] in ROSTER_REPLACEMENTS:
            entry["artists"] = ROSTER_REPLACEMENTS[entry["id"]].copy()
        promotion = PROMOTIONS.get(entry["id"])
        if not promotion:
            continue
        promotions = promotion if isinstance(promotion, list) else [promotion]
        examples = []
        for item in promotions:
            artist, title, video_id, *extra = item
            add_as_representative = bool(extra and extra[0])
            if add_as_representative and artist not in entry["artists"]:
                entry["artists"].append(artist)
            practice_level = artist not in entry["artists"]
            example = {
                "artist": artist,
                "title": title,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "reviewed_at": REVIEWED_AT,
            }
            if practice_level:
                example["attribution_basis"] = "user-authorized practice-level example"
            examples.append(example)
        entry["youtube_examples"] = examples
        if entry["id"] in RENAMES:
            entry["name"] = RENAMES[entry["id"]]
        if entry["id"] in PRESENT_DAY_RECORDS:
            entry["active_to"] = None
            entry["timeline_end_status"] = "present"
        entry["research"]["sample"] = (
            "Direct YouTube example; attribution basis is recorded in the representative "
            "YouTube search log."
        )
        found.add(entry["id"])
    missing = set(PROMOTIONS) - found
    if missing:
        raise ValueError(f"Missing catalogue entries: {sorted(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} representative YouTube examples")


if __name__ == "__main__":
    main()
