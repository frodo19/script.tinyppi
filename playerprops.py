import re
import xbmc


def _cond(condition):
    return xbmc.getCondVisibility(condition)


def _info(label):
    return xbmc.getInfoLabel(label)

    
def _clean(val):
    if val is None:
        return ""
    return str(val).replace(",", "")


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------

_FEL_CACHE = {"ts": 0, "fel": None}

_VIDEO_CODEC_MAP = {
    "av1": "AV1",
    "avc1": "AVC1",
    "div3": "DivX",
    "divx": "DivX",
    "dx50": "DivX",
    "flv": "FLV",
    "h264": "H.264",
    "hev1": "H.265",
    "hevc": "H.265",
    "hvc1": "H.265",
    "mpeg1": "MPEG1",
    "mpeg2": "MPEG2",
    "mpeg2video": "MPEG2",
    "mp4v": "MPEG4",
    "mpeg4": "MPEG4",
    "theora": "Theora",
    "vc1": "VC1",
    "vc-1": "VC1",
    "wvc1": "VC1",
    "vp8": "VP8",
    "vp9": "VP9",
    "wmv": "WMV",
    "wmv3": "WMV",
    "xvid": "XviD",
}

def get_VideoDecoderVar():
    if _cond("Player.Process(videohwdecoder)"):
        return "HW"
    return "SW"


def get_VideoPixelFormatVar():
    val = _info("Player.Process(amlogic.pixformat)")

    if not val:
        return ""

    val = str(val).strip()

    match = re.search(
        r"(\d+)-bit\s*,\s*(RGB|YUV420|YUV422|YUV444)",
        val,
        re.IGNORECASE
    )

    if not match:
        return val

    bits, fmt = match.groups()

    fmt = fmt.upper()

    if fmt == "RGB":
        return f"{bits}-bit, RGB"

    yuv_map = {
        "YUV420": "YUV 4:2:0",
        "YUV422": "YUV 4:2:2",
        "YUV444": "YUV 4:4:4",
    }

    return f"{bits}-bit ({yuv_map.get(fmt, fmt)})"


def _normalize_fps(fps_value):
    try:
        fps = float(fps_value)
    except (TypeError, ValueError):
        return fps_value

    standards = [
        23.976,
        24.0,
        25.0,
        29.97,
        30.0,
        50.0,
        59.94,
        60.0,
        100.0,
        120.0,
    ]

    closest = min(standards, key=lambda x: abs(x - fps))

    if abs(closest - fps) > 0.5:
        return f"{fps:.3f}".rstrip("0").rstrip(".")

    if closest == 23.976:
        return "23.976"
    if closest == 29.97:
        return "29.97"
    if closest == 59.94:
        return "59.94"

    return str(int(closest)) if closest.is_integer() else str(closest)


def get_DisplayModeVar():
    val = _info("Player.Process(amlogic.displaymode)")
    if not val:
        return ""

    val = str(val).strip()

    compact = re.sub(r"\s+", "", val)

    match = re.match(
        r"(\d+(?:x\d+)?)(p|i)(\d+(?:\.\d+)?)[Hh][Zz]",
        compact,
        re.IGNORECASE,
    )
    if not match:
        return val

    res, scan, raw_fps = match.groups()
    norm_fps = _normalize_fps(raw_fps)

    return f"{res}{scan} {norm_fps}Hz"

    
def _format_fps(fps_value):
    try:
        fps = float(fps_value)
    except (TypeError, ValueError):
        return ""

    targets = [
        (23.976, 0.02),
        (29.97,  0.02),
        (59.94,  0.02),
        (60.0,   0.01),
    ]

    for target, tol in targets:
        if abs(fps - target) <= tol:
            fps = target
            break

    if fps.is_integer():
        return str(int(fps))

    return f"{fps:.3f}".rstrip("0").rstrip(".")


def get_VideoResolutionVar():
    width  = _clean(_info("Player.Process(videowidth)"))
    height = _clean(_info("Player.Process(videoheight)"))
    scan   = _clean(_info("Player.Process(videoscantype)"))
    fps    = _clean(_info("Player.Process(videofps)"))

    if not width or not height:
        return ""

    fps = _format_fps(fps)

    return f"{width}x{height}{scan} {fps}FPS"


def get_VideoBitrateMBVar():
    bitrate = _clean(_info("VideoPlayer.VideoBitrate"))

    try:
        kbps = float(bitrate)
    except (TypeError, ValueError):
        return ""

    mbit = kbps / 1000.0

    value = f"{mbit:.2f}".rstrip("0").rstrip(".")

    return f"{value} Mb/s"

    
def get_AudioBitrateMBVar():
    bitrate = _clean(_info("VideoPlayer.AudioBitrate"))

    try:
        kbps = int(float(bitrate))
    except (TypeError, ValueError):
        return ""

    return f"{kbps:,} Kb/s".replace(",", ".")


def get_HdrTypeVar():
    val = _info("VideoPlayer.HdrType")

    if not val:
        return "SDR"

    val = str(val).lower()

    if "hdr10plus" in val:
        return "HDR10+"
    if "hdr10" in val:
        return "HDR10"
    if "dolby" in val or "dv" in val:
        return "Dolby Vision Profile"
    if "hlg" in val:
        return "HLG"

    return val


def _get_fel_from_dmesg():
    import subprocess, time
    now = time.time()
    if now - _FEL_CACHE["ts"] < 5:
        return _FEL_CACHE["fel"]
    try:
        out = subprocess.run(
            ["dmesg"], capture_output=True, text=True, timeout=2
        ).stdout
        fel = mel = None
        for line in reversed(out.splitlines()):
            if "enable_fel " in line and fel is None:
                fel = line.split("enable_fel ")[-1].split()[0] == "1"
            if "enable_mel " in line and mel is None:
                mel = line.split("enable_mel ")[-1].split()[0] == "1"
            if fel is not None and mel is not None:
                break
        confirmed = fel is True and mel is True
        _FEL_CACHE.update({"ts": now, "fel": confirmed})
        return confirmed
    except Exception:
        return None


def get_HdrDetailVar():
    raw = _info("VideoPlayer.HdrDetail")

    if raw:
        lines = str(raw).splitlines()
        out = []

        for line in lines:
            line = line.strip()

            match = re.match(r"(\d+)(FEL|MEL)", line)
            if match:
                num, typ = match.groups()

                if typ == "FEL":
                    color = "palegreen"
                elif typ == "MEL":
                    color = "orange"
                else:
                    color = "white"

                out.append(f"{num} [COLOR {color}]{typ}[/COLOR]")
            else:
                out.append(line)

        return "\n".join(out)

    if "dolby" in str(_info("VideoPlayer.HdrType")).lower():
        if _get_fel_from_dmesg() is True:
            return "7 [COLOR palegreen]FEL[/COLOR]"

    return ""

def get_ModeVar():
    val = _info("Player.Process(amlogic.eoft_gamut)")

    if not val:
        return ""

    parts = str(val).split()

    return parts[0] if len(parts) > 0 else ""


def get_GamutVar():
    val = _info("Player.Process(amlogic.eoft_gamut)")

    if not val:
        return ""

    parts = str(val).split()

    return parts[1] if len(parts) > 1 else ""

def get_VideoCodecVar():
    codec = _info("VideoPlayer.VideoCodec")

    if not codec:
        return ""

    codec = str(codec).lower().strip()

    return _VIDEO_CODEC_MAP.get(codec, codec.upper())


# ---------------------------------------------------------------------------
# Subtitle
# ---------------------------------------------------------------------------

_SUBTITLE_CODEC_MAP = {
    "ass": "ASS",
    "dvb_subtitle": "DVB-SUB",
    "dvb_teletext": "DVB-Text",
    "dvd_subtitle": "VobSub",
    "hdmv_pgs_subtitle": "PGS",
    "microdvd": "MicroDVD",
    "mov_text": "Timed Text",
    "mpl2": "MPL2",
    "realtext": "RealText",
    "sami": "SAMI",
    "srt": "SubRip",
    "ssa": "SSA",
    "subrip": "Subrip",
    "text": "Text",
    "ttml": "TTML",
    "vplayer": "VPlayer",
    "webvtt": "WebVTT",
    "xsub": "XSUB",
}


_LANGUAGE_MAP = {
    "abk": "Apsua",
    "ace": "Baksa Acèh",
    "ach": "Lwo",
    "ada": "Dangme",
    "ady": "Adygebze",
    "aar": "Qafaraf",
    "afh": "Afrihili",
    "afr": "Afrikaans",
    "afa": "Lughat 'afru-aswiatia",
    "ain": "Aynu itak",
    "aka": "Akan",
    "akk": "Akkadû",
    "alb": "Shqip",
    "ale": "Unangam Tunuu",
    "alg": "Algonquin",
    "tut": "Altaic",
    "amh": "Amarinya",
    "anp": "Angika",
    "apa": "Ndee",
    "ara": "Arabiya",
    "arg": "Aragonés",
    "arp": "Hinóno'eitíít",
    "arw": "Arawak",
    "arm": "Hayeren",
    "rup": "Armãneashti",
    "art": "Lingua artificial",
    "asm": "Axomiya",
    "ast": "Asturianu",
    "ath": "Athabaskan",
    "aus": "Australian",
    "map": "Austronesian",
    "ava": "Awar mácʼal",
    "ave": "Avestan",
    "awa": "Awadhi",
    "aym": "Aymar aru",
    "aze": "Azərbaycanca",
    "ban": "Basa Bali",
    "bat": "Baltu",
    "bal": "Balochi",
    "bam": "Bamanankan",
    "bai": "Bamileke",
    "bad": "Banda",
    "bnt": "Bantu",
    "bas": "Mbene",
    "bak": "Bashqortsa",
    "baq": "Euskara",
    "btk": "Batak",
    "bej": "Bedawiyet",
    "bel": "Belaruskaja",
    "bem": "Chibemba",
    "ben": "Bangla",
    "ber": "Tamazight",
    "bho": "Bhojpuri",
    "bih": "Bihari",
    "bik": "Bikol",
    "bin": "Edo",
    "bis": "Bislama",
    "byn": "Blin",
    "zbl": "Blissymbols",
    "nob": "Norsk Bokmål",
    "bos": "Bosanski",
    "bra": "Braj Bhasha",
    "bre": "Brezhoneg",
    "bug": "Basa Ugi",
    "bul": "Bălgarski",
    "bua": "Buryaad xelen",
    "bur": "Myanmara sa",
    "cad": "Caddo",
    "cat": "Català",
    "cau": "Caucasian",
    "ceb": "Sinugboanon",
    "cel": "Celtic",
    "cai": "Central American Indian",
    "khm": "Khmer",
    "chg": "Chagatai",
    "cmc": "Chamic",
    "cha": "Chamoru",
    "che": "Noxchin mott",
    "chr": "Tsalagi",
    "chy": "Tsėhésenėstsestse",
    "chb": "Chibcha",
    "nya": "Chichewa",
    "chi": "Zhongwen",
    "chn": "Chinook Wawa",
    "chp": "Dënesųłıne",
    "cho": "Chahta",
    "chu": "Slověnskyi język",
    "chk": "Foosun Chuuk",
    "chv": "Čăvašla",
    "nwc": "Nepal Bhasa",
    "syc": "Suryaya",
    "cop": "Met Remenkhemi",
    "cor": "Kernowek",
    "cos": "Corsu",
    "cre": "Nēhiyawēwin",
    "mus": "Mvskoke",
    "crp": "Creole",
    "cpe": "English-based creole",
    "cpf": "Créole à base française",
    "cpp": "Crioulo de base portuguesa",
    "crh": "Qırımtatarca",
    "hrv": "Hrvatski",
    "cus": "Cushitic",
    "cze": "Čeština",
    "dak": "Dakȟótiyapi",
    "dan": "Dansk",
    "dar": "Dargwa",
    "del": "Lanape",
    "din": "Thuɔŋjaŋ",
    "div": "Dhivehi",
    "doi": "Dogri",
    "dgr": "Tłı̨chǫ Yatiì",
    "dra": "Dravidian",
    "dua": "Duálá",
    "dum": "Middelnederlands",
    "dut": "Nederlands",
    "dyu": "Julakan",
    "dzo": "Dzongkha",
    "frs": "Seeltersk",
    "efi": "Efik",
    "eka": "Ekajuk",
    "elx": "Elamite",
    "eng": "English",
    "enm": "Middle English",
    "ang": "Englisc",
    "myv": "Erzjan kel'",
    "epo": "Esperanto",
    "est": "Eesti",
    "ewe": "Ewęgbe",
    "ewo": "Ewondo",
    "fan": "Fang",
    "fat": "Fanti",
    "fao": "Føroyskt",
    "fij": "Na Vosa Vakaviti",
    "fil": "Filipino",
    "fin": "Suomi",
    "fiu": "Finno-Ugric",
    "fon": "Fongbe",
    "fre": "Français",
    "frm": "Moyen français",
    "fro": "Ancien français",
    "fur": "Furlan",
    "ful": "Fulfulde",
    "gaa": "Gã",
    "gla": "Gàidhlig",
    "car": "Kari'nja",
    "glg": "Galego",
    "lug": "Luganda",
    "gay": "Gayo",
    "gba": "Gbaya",
    "gez": "Ge'ez",
    "geo": "Kartuli",
    "ger": "Deutsch",
    "gmh": "Diutisk",
    "goh": "Diutisk",
    "gem": "Germanic",
    "gil": "Taetae ni Kiribati",
    "gon": "Gondi",
    "gor": "Bahasa Gorontalo",
    "got": "Gutisko razda",
    "grb": "Grebo",
    "grc": "Ellēnikē",
    "gre": "Elliniká",
    "grn": "Avañe'ẽ",
    "guj": "Gujarati",
    "gwi": "Gwich'in",
    "hai": "Xaat Kíl",
    "hat": "Kreyòl ayisyen",
    "hau": "Hausa",
    "haw": "ʻŌlelo Hawaiʻi",
    "heb": "Ivrit",
    "her": "Oshiherero",
    "hil": "Hiligaynon",
    "him": "Pahari",
    "hin": "Hindi",
    "hmo": "Hiri Motu",
    "hit": "Nesili",
    "hmn": "Hmoob",
    "hun": "Magyar",
    "hup": "Hupa",
    "iba": "Iban",
    "ice": "Íslenska",
    "ido": "Ido",
    "ibo": "Asụsụ Igbo",
    "ijo": "Ijo",
    "ilo": "Ilokano",
    "smn": "Anarâškielâ",
    "inc": "Indo-Aryan",
    "ine": "Indo-European",
    "ind": "Bahasa Indonesia",
    "inh": "Ghalghaj mott",
    "ina": "Interlingua",
    "ile": "Interlingue",
    "iku": "Inuktitut",
    "ipk": "Iñupiatun",
    "ira": "Iranian",
    "gle": "Gaeilge",
    "mga": "Middle Irish",
    "sga": "Old Irish",
    "iro": "Iroquoian",
    "ita": "Italiano",
    "jpn": "Nihongo",
    "jav": "Basa Jawa",
    "jrb": "Al-Yahudiyya al-Arabiya",
    "jpr": "Dzhidi",
    "kbd": "Qabardjébze",
    "kab": "Taqbaylit",
    "kac": "Jingpho",
    "kal": "Kalaallisut",
    "xal": "Halmg keln",
    "kam": "Kikamba",
    "kan": "Kannada",
    "kau": "Kanuri",
    "kaa": "Qaraqalpaq tili",
    "krc": "Qaračaj-malkar til",
    "krl": "Karjalan kieli",
    "kar": "Karen",
    "kas": "Kashmiri",
    "csb": "Kaszëbsczi",
    "kaw": "Kawi",
    "kaz": "Qazaq tili",
    "kha": "Kynshi",
    "khi": "Khoisan",
    "kho": "Sakan",
    "kik": "Gikuyu",
    "kmb": "Kimbundu",
    "kin": "Ikinyarwanda",
    "kir": "Kyrgyzcha",
    "tlh": "tlhIngan Hol",
    "kom": "Komi kyv",
    "kon": "Kikongo",
    "kok": "Konkani",
    "kor": "Hangugo",
    "kos": "Kosrae",
    "kpe": "Kpelle",
    "kro": "Kru",
    "kua": "Oshikwanyama",
    "kum": "Kumuk til",
    "kur": "Kurdî",
    "kru": "Kurukh",
    "kut": "Ktunaxa",
    "lad": "Dzhudeo-Espanyiol",
    "lah": "Lahnda",
    "lam": "Lamba",
    "day": "Land Dayak",
    "lao": "Phasa Lao",
    "lat": "Latina",
    "lav": "Latviešu",
    "lez": "Lezgi č'al",
    "lim": "Limburgs",
    "lin": "Lingála",
    "lit": "Lietuvių",
    "jbo": "Lojban",
    "nds": "Plattdüütsch",
    "dsb": "Dolnoserbski",
    "loz": "Silozi",
    "lub": "Tshiluba",
    "lua": "Luba-Lulua",
    "lui": "Cham'teela",
    "smj": "Julevsámegiella",
    "lun": "Chilunda",
    "luo": "Dholuo",
    "lus": "Mizo ṭawng",
    "ltz": "Lëtzebuergesch",
    "mac": "Makedonski",
    "mad": "Basa Madura",
    "mag": "Magahi",
    "mai": "Maithili",
    "mak": "Basa Mangkasara",
    "mlg": "Malagasy",
    "may": "Bahasa Melayu",
    "mal": "Malayalam",
    "mlt": "Malti",
    "mnc": "Manju gisun",
    "mdr": "Mandar",
    "man": "Mandingo",
    "mni": "Meitei lon",
    "mno": "Manobo",
    "glv": "Gaelg",
    "mao": "Te Reo Māori",
    "arn": "Mapudungun",
    "mar": "Marathi",
    "chm": "Marij jylme",
    "mah": "Kajin M̧ajeļ",
    "mwr": "Marwari",
    "mas": "Maa",
    "myn": "Mayan",
    "men": "Mɛnde yia",
    "mic": "Mìgmawei",
    "min": "Baso Minangkabau",
    "mwl": "Mirandés",
    "moh": "Kanienʼkéha",
    "mdf": "Mokshan kyel'",
    "mkh": "Mon-Khmer",
    "lol": "Lomongo",
    "mon": "Mongol xele",
    "mos": "Mooré",
    "mul": "Multiple languages",
    "mun": "Munda",
    "nqo": "N'Ko",
    "nah": "Nāhuatl",
    "nau": "Dorerin Naoero",
    "nav": "Diné bizaad",
    "nde": "IsiNdebele saseNdoronini",
    "nbl": "IsiNdebele",
    "ndo": "Oshindonga",
    "nap": "Napulitano",
    "new": "Nepal Bhasa",
    "nep": "Nepali",
    "nia": "Li Niha",
    "nic": "Niger-Kordofanian",
    "ssa": "Nilo-Saharan",
    "niu": "Ko e vagahau Niuē",
    "zxx": "No linguistic content",
    "nog": "Nogaj tili",
    "non": "Dönsk tunga",
    "nai": "North American Indian",
    "frr": "Frasch",
    "sme": "Davvisámegiella",
    "nno": "Norsk Nynorsk",
    "nor": "Norsk",
    "nub": "Nubian",
    "nym": "Kinyamwezi",
    "nyn": "Runyankore",
    "nyo": "Runyoro",
    "nzi": "Nzema",
    "oci": "Occitan",
    "arc": "Aramaya",
    "oji": "Anishinaabemowin",
    "ori": "Odia",
    "orm": "Afaan Oromoo",
    "osa": "Wazhazhe ie",
    "oss": "Iron ævzag",
    "oto": "Otomanguean",
    "pal": "Pārsīg",
    "pau": "Tekoi ra Belau",
    "pli": "Pāḷi",
    "pam": "Kapampangan",
    "pag": "Salitan Pangasinan",
    "pan": "Panjabi",
    "pap": "Papiamentu",
    "paa": "Papuan",
    "nso": "Sesotho sa Leboa",
    "per": "Farsi",
    "peo": "Old Persian",
    "phi": "Philippine",
    "phn": "Phoenician",
    "pon": "Mahsen en Pohnpei",
    "pol": "Polski",
    "por": "Português",
    "pra": "Prakrit",
    "pro": "Ancien occitan",
    "pus": "Pashto",
    "que": "Runa Simi",
    "raj": "Rajasthani",
    "rap": "Vananga Rapa Nui",
    "rar": "Māori Kūki 'Āirani",
    "roa": "Romance",
    "rum": "Română",
    "roh": "Rumantsch",
    "rom": "Romani čhib",
    "run": "Ikirundi",
    "rus": "Russkij",
    "sal": "Salishan",
    "sam": "Aramit Šamrayim",
    "smi": "Sami",
    "smo": "Gagana Sāmoa",
    "sad": "Sandawe",
    "sag": "Sängö",
    "san": "Samskrta",
    "sat": "Santali",
    "srd": "Sardu",
    "sas": "Sasak",
    "sco": "Scots",
    "sel": "Seeľkup šənak",
    "sem": "Semitic",
    "srp": "Srpski",
    "srr": "Seereer",
    "shn": "Tai Shan",
    "sna": "chiShona",
    "iii": "Nuosuhxop",
    "scn": "Sicilianu",
    "sid": "Sidaamu Afoo",
    "sgn": "Sign Language",
    "bla": "Siksikáí'powahsin",
    "snd": "Sindhi",
    "sin": "Sinhala",
    "sit": "Sino-Tibetan",
    "sio": "Siouan",
    "sms": "Säämsgjõll",
    "den": "Dene Zhatıé",
    "sla": "Slavic",
    "slo": "Slovenčina",
    "slv": "Slovenščina",
    "sog": "Sogdian",
    "som": "Soomaali",
    "son": "Soŋay",
    "snk": "Soninkanxanne",
    "wen": "Serbšćina",  # Sorbisch
    "sot": "Sesotho",
    "sai": "South American Indian",
    "alt": "Tyva dyl",
    "sma": "Åarjelsaemiegiele",
    "spa": "Español",
    "srn": "Sranantongo",
    "suk": "Kisukuma",
    "sux": "Eme-gir",
    "sun": "Basa Sunda",
    "sus": "Susu",
    "swa": "Kiswahili",
    "ssw": "SiSwati",
    "swe": "Svenska",
    "gsw": "Schwiizerdütsch",
    "syr": "Surayt",
    "tgl": "Tagalog",
    "tah": "Reo Tahiti",
    "tai": "Tai",
    "tgk": "Tojikī",
    "tmh": "Tamasheq",
    "tam": "Tamizh",
    "tat": "Tatarça",
    "tel": "Telugu",
    "ter": "Tereno",
    "tet": "Tetun",
    "tha": "Phasa Thai",
    "tib": "Bodskad",
    "tig": "Tigré",
    "tir": "Tigrinya",
    "tem": "K聲mne",
    "tiv": "Tiv",
    "tli": "Lingít",
    "tpi": "Tok Pisin",
    "tkl": "Tokelau",
    "tog": "Chitonga",
    "ton": "Faka-Tonga",
    "tsi": "Sm'algyax",
    "tso": "Xitsonga",
    "tsn": "Setswana",
    "tum": "Chitumbuka",
    "tup": "Tupí",
    "tur": "Türkçe",
    "ota": "Lisān-ı Osmānī",
    "tuk": "Türkmençe",
    "tvl": "Te Gana Tuvalu",
    "tyv": "Tyva dyl",
    "twi": "Twi",
    "udm": "Udmurt kyl",
    "uga": "Ugaritic",
    "uig": "Uyghurche",
    "ukr": "Ukrajinska",
    "umb": "Úmbúndú",
    "mis": "Uncoded",
    "und": "Undetermined",
    "hsb": "Hornjoserbsce",
    "urd": "Urdu",
    "uzb": "Oʻzbekcha",
    "vai": "Vai",
    "ven": "Tshivenda",
    "vie": "Tiếng Việt",
    "vol": "Volapük",
    "vot": "Vađđa tšeeli",
    "wak": "Wakashan",
    "wal": "Wolaitta",
    "wln": "Walon",
    "war": "Winaray",
    "was": "Wá:šiw ʔítlu",
    "wel": "Cymraeg",
    "fry": "Frysk",
    "wol": "Wolof",
    "xho": "isiXhosa",
    "sah": "Saxa tyla",
    "yao": "Chiyao",
    "yap": "Thin nu Wa'ab",
    "yid": "Yiddish",
    "yor": "Yorùbá",
    "ypk": "Yupik",
    "znd": "Zande",
    "zap": "Diidxazá",
    "zza": "Zazaki",
    "zen": "Zenaga",
    "zha": "Vahcuengh",
    "zul": "isiZulu",
    "zun": "Shiwi'ma",
}


def get_SubtitleNameVar():
    code = _info("VideoPlayer.SubtitlesLanguage")

    if not code:
        return ""

    code = str(code).lower().strip()

    return _LANGUAGE_MAP.get(code, "")


def get_SubtitleCodecVar():
    codec = _info("VideoPlayer.SubtitleCodec")

    if not codec:
        return ""

    codec = str(codec).lower().strip()

    return _SUBTITLE_CODEC_MAP.get(codec, codec.upper())

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

_AUDIO_CODEC_MAP = {
    "aac":              "AAC",
    "aac_latm":         "AAC",
    "aac_lc":           "AAC",
    "he_aac":           "AAC",
    "he_aac_v2":        "AAC",
    "aac_ssr":          "AAC",
    "aac_ltp":          "AAC",
    "ac3":              "Dolby Digital",
    "aif":              "AIFF",
    "aifc":             "AIFF",
    "aiff":             "AIFF",
    "alac":             "ALAC",
    "ape":              "APE",
    "avc":              "AVC",
    "cdda":             "CDDA",
    "dca":              "DTS",
    "dolbydigital":     "Dolby Digital",
    "dtshd":            "DTS-HD",
    "dtshd_ma":         "DTS-HD MA",
    "dtshd_hra":        "DTS-HD HRA",
    "dtshd_ma_x":       "DTS:X MA",
    "dtshd_ma_x_imax":  "DTS:X",
    "eac3":             "Dolby Digital Plus",
    "eac3_ddp_atmos":   "Dolby Digital Plus",
    "flac":             "FLAC",
    "mp1":              "MP1",
    "mp2":              "MP2",
    "mp3":              "MP3",
    "mp3float":         "MP3",
    "ogg":              "OGG",
    "opus":             "OPUS",
    "pcm":              "PCM",
    "pcm_bluray":       "PCM",
    "pcm_s16le":        "PCM",
    "pcm_s24le":        "PCM",
    "truehd":           "Dolby TrueHD",
    "truehd_atmos":     "Dolby TrueHD",
    "vorbis":           "Vorbis",
    "wav":              "WAV",
    "wavpack":          "WAVP",
    "wmapro":           "WMA-PRO",
    "wmav2":            "WMA",
}


_CHANNELS_MAP = {
    1: "1.0", 2: "2.0", 4: "4.0", 5: "5.0",
    6: "5.1", 7: "6.1", 8: "7.1", 10: "9.1",
}


_CHANNELS_INPUT_MAP = {
    1:  "Mono",
    2:  "FL, FR",
    3:  "FL, FR, LFE",
    4:  "FL, FR, BL, BR",
    5:  "FL, FR, LFE, BL, BR",
    6:  "FL, FR, FC, LFE, SL, SR",
    7:  "FL, FR, FC, LFE, BC, SL, SR",
    8:  "FL, FR, FC, LFE, BL, BR, SL, SR",
    9:  "FL, FR, FC, LFE, BL, BR, SL, SR, FWL",
    10: "FL, FR, FC, LFE, BL, BR, SL, SR, FWL, FWR",
}


def get_AudioCodecVar():
    codec = _info("VideoPlayer.AudioCodec")
    if not codec:
        return xbmc.getLocalizedString(13205)
    return _AUDIO_CODEC_MAP.get(codec, codec)


def get_AudioCodecSpatialVar():
    codec = _info("VideoPlayer.AudioCodec")
    if codec == "dtshd_ma_x_imax":
        return "(IMAX)"
    if codec in ("eac3_ddp_atmos", "truehd_atmos"):
        return "(Atmos)"
    return ""


def get_AudioChannelsVar():
    try:
        ch = int(_info("VideoPlayer.AudioChannels"))
        return _CHANNELS_MAP.get(ch, "")
    except (ValueError, TypeError):
        return ""


def get_AudioSampleRateVar():
    samplerate = _clean(_info("Player.Process(audiosamplerate)"))

    try:
        hz = float(samplerate)
    except (TypeError, ValueError):
        return ""

    khz = hz / 1000.0

    if khz.is_integer():
        return f"{int(khz)} kHz"

    return f"{khz:.1f} kHz"


def get_AudioChannelsInputVar():
    try:
        ch = int(_info("VideoPlayer.AudioChannels"))
        return _CHANNELS_INPUT_MAP.get(ch, xbmc.getLocalizedString(13205))
    except (ValueError, TypeError):
        return xbmc.getLocalizedString(13205)


def get_AudioNameVar():
    code = _info("VideoPlayer.AudioLanguage")

    if not code:
        return ""

    code = str(code).lower().strip()

    return _LANGUAGE_MAP.get(code, "")


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

def get_CpuUsageVar():
    raw = _info("System.CpuUsage")

    if not raw:
        return ""

    matches = re.findall(r"#\d+:\s*([\d.]+)%", raw)

    if not matches:
        return raw

    values = []

    for val in matches:
        try:
            num = int(float(val))
            values.append(f"{num:02d}")
        except ValueError:
            continue

    return " | ".join(values)


# ---------------------------------------------------------------------------
# Main update call – use this in your WindowXML class
# ---------------------------------------------------------------------------

def update_properties(window):
    """Call this from onInit() and your update loop."""
    window.setProperty("VideoDecoderVar",       get_VideoDecoderVar())
    window.setProperty("VideoPixelFormatVar",   get_VideoPixelFormatVar())
    window.setProperty("DisplayModeVar",        get_DisplayModeVar())
    window.setProperty("VideoResolutionVar",    get_VideoResolutionVar())
    window.setProperty("VideoBitrateMBVar",     get_VideoBitrateMBVar())
    window.setProperty("AudioBitrateMBVar",     get_AudioBitrateMBVar())
    window.setProperty("HdrTypeVar",            get_HdrTypeVar())
    window.setProperty("HdrDetailVar",          get_HdrDetailVar())
    window.setProperty("ModeVar",               get_ModeVar())
    window.setProperty("GamutVar",              get_GamutVar())
    window.setProperty("VideoCodecVar",         get_VideoCodecVar())
    window.setProperty("AudioCodecVar",         get_AudioCodecVar())
    window.setProperty("AudioCodecSpatialVar",  get_AudioCodecSpatialVar())
    window.setProperty("AudioChannelsVar",      get_AudioChannelsVar())
    window.setProperty("AudioSampleRateVar",    get_AudioSampleRateVar())
    window.setProperty("AudioChannelsInputVar", get_AudioChannelsInputVar())
    window.setProperty("AudioNameVar",          get_AudioNameVar())
    window.setProperty("SubtitleCodecVar",      get_SubtitleCodecVar())
    window.setProperty("SubtitleNameVar",       get_SubtitleNameVar())
    window.setProperty("CpuUsageVar",           get_CpuUsageVar())
