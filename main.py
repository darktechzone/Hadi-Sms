import os
import re
import time
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Lock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)

# ---------- CONFIG ----------
BASE_URL = os.environ.get("PANEL_BASE_URL", "http://smshadi.net")
USERNAME = os.environ.get("PANEL_USER", "Ahmad05")
PASSWORD = os.environ.get("PANEL_PASS", "Ahmad05")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*"
}

# ---------- STATE ----------
session = None
sesskey = None
last_login = 0
login_lock = Lock()
otp_cache = {"data": [], "timestamp": 0}
cache_lock = Lock()

consecutive_failures = 0
FAILURE_THRESHOLD = 5
BREAKER_TIMEOUT = 30

# ---------- FULL COUNTRY MAP ----------
COUNTRY_MAP = {
    '1': {'code': '+1', 'name': 'USA/Canada'},
    '7': {'code': '+7', 'name': 'Russia'},
    '20': {'code': '+20', 'name': 'Egypt'},
    '27': {'code': '+27', 'name': 'South Africa'},
    '30': {'code': '+30', 'name': 'Greece'},
    '31': {'code': '+31', 'name': 'Netherlands'},
    '32': {'code': '+32', 'name': 'Belgium'},
    '33': {'code': '+33', 'name': 'France'},
    '34': {'code': '+34', 'name': 'Spain'},
    '36': {'code': '+36', 'name': 'Hungary'},
    '39': {'code': '+39', 'name': 'Italy'},
    '40': {'code': '+40', 'name': 'Romania'},
    '41': {'code': '+41', 'name': 'Switzerland'},
    '43': {'code': '+43', 'name': 'Austria'},
    '44': {'code': '+44', 'name': 'United Kingdom'},
    '45': {'code': '+45', 'name': 'Denmark'},
    '46': {'code': '+46', 'name': 'Sweden'},
    '47': {'code': '+47', 'name': 'Norway'},
    '48': {'code': '+48', 'name': 'Poland'},
    '49': {'code': '+49', 'name': 'Germany'},
    '51': {'code': '+51', 'name': 'Peru'},
    '52': {'code': '+52', 'name': 'Mexico'},
    '53': {'code': '+53', 'name': 'Cuba'},
    '54': {'code': '+54', 'name': 'Argentina'},
    '55': {'code': '+55', 'name': 'Brazil'},
    '56': {'code': '+56', 'name': 'Chile'},
    '57': {'code': '+57', 'name': 'Colombia'},
    '58': {'code': '+58', 'name': 'Venezuela'},
    '60': {'code': '+60', 'name': 'Malaysia'},
    '61': {'code': '+61', 'name': 'Australia'},
    '62': {'code': '+62', 'name': 'Indonesia'},
    '63': {'code': '+63', 'name': 'Philippines'},
    '64': {'code': '+64', 'name': 'New Zealand'},
    '65': {'code': '+65', 'name': 'Singapore'},
    '66': {'code': '+66', 'name': 'Thailand'},
    '81': {'code': '+81', 'name': 'Japan'},
    '82': {'code': '+82', 'name': 'South Korea'},
    '84': {'code': '+84', 'name': 'Vietnam'},
    '86': {'code': '+86', 'name': 'China'},
    '90': {'code': '+90', 'name': 'Turkey'},
    '91': {'code': '+91', 'name': 'India'},
    '92': {'code': '+92', 'name': 'Pakistan'},
    '93': {'code': '+93', 'name': 'Afghanistan'},
    '94': {'code': '+94', 'name': 'Sri Lanka'},
    '95': {'code': '+95', 'name': 'Myanmar'},
    '98': {'code': '+98', 'name': 'Iran'},
    '211': {'code': '+211', 'name': 'South Sudan'},
    '212': {'code': '+212', 'name': 'Morocco'},
    '213': {'code': '+213', 'name': 'Algeria'},
    '216': {'code': '+216', 'name': 'Tunisia'},
    '218': {'code': '+218', 'name': 'Libya'},
    '220': {'code': '+220', 'name': 'Gambia'},
    '221': {'code': '+221', 'name': 'Senegal'},
    '222': {'code': '+222', 'name': 'Mauritania'},
    '223': {'code': '+223', 'name': 'Mali'},
    '224': {'code': '+224', 'name': 'Guinea'},
    '225': {'code': '+225', 'name': 'Ivory Coast'},
    '226': {'code': '+226', 'name': 'Burkina Faso'},
    '227': {'code': '+227', 'name': 'Niger'},
    '228': {'code': '+228', 'name': 'Togo'},
    '229': {'code': '+229', 'name': 'Benin'},
    '230': {'code': '+230', 'name': 'Mauritius'},
    '231': {'code': '+231', 'name': 'Liberia'},
    '232': {'code': '+232', 'name': 'Sierra Leone'},
    '233': {'code': '+233', 'name': 'Ghana'},
    '234': {'code': '+234', 'name': 'Nigeria'},
    '235': {'code': '+235', 'name': 'Chad'},
    '236': {'code': '+236', 'name': 'Central African Republic'},
    '237': {'code': '+237', 'name': 'Cameroon'},
    '238': {'code': '+238', 'name': 'Cape Verde'},
    '239': {'code': '+239', 'name': 'Sao Tome and Principe'},
    '240': {'code': '+240', 'name': 'Equatorial Guinea'},
    '241': {'code': '+241', 'name': 'Gabon'},
    '242': {'code': '+242', 'name': 'Congo'},
    '243': {'code': '+243', 'name': 'DRC'},
    '244': {'code': '+244', 'name': 'Angola'},
    '245': {'code': '+245', 'name': 'Guinea-Bissau'},
    '246': {'code': '+246', 'name': 'Diego Garcia'},
    '248': {'code': '+248', 'name': 'Seychelles'},
    '249': {'code': '+249', 'name': 'Sudan'},
    '250': {'code': '+250', 'name': 'Rwanda'},
    '251': {'code': '+251', 'name': 'Ethiopia'},
    '252': {'code': '+252', 'name': 'Somalia'},
    '253': {'code': '+253', 'name': 'Djibouti'},
    '254': {'code': '+254', 'name': 'Kenya'},
    '255': {'code': '+255', 'name': 'Tanzania'},
    '256': {'code': '+256', 'name': 'Uganda'},
    '257': {'code': '+257', 'name': 'Burundi'},
    '258': {'code': '+258', 'name': 'Mozambique'},
    '260': {'code': '+260', 'name': 'Zambia'},
    '261': {'code': '+261', 'name': 'Madagascar'},
    '262': {'code': '+262', 'name': 'Reunion'},
    '263': {'code': '+263', 'name': 'Zimbabwe'},
    '264': {'code': '+264', 'name': 'Namibia'},
    '265': {'code': '+265', 'name': 'Malawi'},
    '266': {'code': '+266', 'name': 'Lesotho'},
    '267': {'code': '+267', 'name': 'Botswana'},
    '268': {'code': '+268', 'name': 'Swaziland'},
    '269': {'code': '+269', 'name': 'Comoros'},
    '290': {'code': '+290', 'name': 'St. Helena'},
    '291': {'code': '+291', 'name': 'Eritrea'},
    '297': {'code': '+297', 'name': 'Aruba'},
    '298': {'code': '+298', 'name': 'Faroe Islands'},
    '299': {'code': '+299', 'name': 'Greenland'},
    '350': {'code': '+350', 'name': 'Gibraltar'},
    '351': {'code': '+351', 'name': 'Portugal'},
    '352': {'code': '+352', 'name': 'Luxembourg'},
    '353': {'code': '+353', 'name': 'Ireland'},
    '354': {'code': '+354', 'name': 'Iceland'},
    '355': {'code': '+355', 'name': 'Albania'},
    '356': {'code': '+356', 'name': 'Malta'},
    '357': {'code': '+357', 'name': 'Cyprus'},
    '358': {'code': '+358', 'name': 'Finland'},
    '359': {'code': '+359', 'name': 'Bulgaria'},
    '370': {'code': '+370', 'name': 'Lithuania'},
    '371': {'code': '+371', 'name': 'Latvia'},
    '372': {'code': '+372', 'name': 'Estonia'},
    '373': {'code': '+373', 'name': 'Moldova'},
    '374': {'code': '+374', 'name': 'Armenia'},
    '375': {'code': '+375', 'name': 'Belarus'},
    '376': {'code': '+376', 'name': 'Andorra'},
    '377': {'code': '+377', 'name': 'Monaco'},
    '378': {'code': '+378', 'name': 'San Marino'},
    '379': {'code': '+379', 'name': 'Vatican City'},
    '380': {'code': '+380', 'name': 'Ukraine'},
    '381': {'code': '+381', 'name': 'Serbia'},
    '382': {'code': '+382', 'name': 'Montenegro'},
    '383': {'code': '+383', 'name': 'Kosovo'},
    '385': {'code': '+385', 'name': 'Croatia'},
    '386': {'code': '+386', 'name': 'Slovenia'},
    '387': {'code': '+387', 'name': 'Bosnia and Herzegovina'},
    '389': {'code': '+389', 'name': 'North Macedonia'},
    '420': {'code': '+420', 'name': 'Czech Republic'},
    '421': {'code': '+421', 'name': 'Slovakia'},
    '423': {'code': '+423', 'name': 'Liechtenstein'},
    '500': {'code': '+500', 'name': 'Falkland Islands'},
    '501': {'code': '+501', 'name': 'Belize'},
    '502': {'code': '+502', 'name': 'Guatemala'},
    '503': {'code': '+503', 'name': 'El Salvador'},
    '504': {'code': '+504', 'name': 'Honduras'},
    '505': {'code': '+505', 'name': 'Nicaragua'},
    '506': {'code': '+506', 'name': 'Costa Rica'},
    '507': {'code': '+507', 'name': 'Panama'},
    '508': {'code': '+508', 'name': 'St. Pierre and Miquelon'},
    '509': {'code': '+509', 'name': 'Haiti'},
    '590': {'code': '+590', 'name': 'Guadeloupe'},
    '591': {'code': '+591', 'name': 'Bolivia'},
    '592': {'code': '+592', 'name': 'Guyana'},
    '593': {'code': '+593', 'name': 'Ecuador'},
    '594': {'code': '+594', 'name': 'French Guiana'},
    '595': {'code': '+595', 'name': 'Paraguay'},
    '596': {'code': '+596', 'name': 'Martinique'},
    '597': {'code': '+597', 'name': 'Suriname'},
    '598': {'code': '+598', 'name': 'Uruguay'},
    '599': {'code': '+599', 'name': 'Caribbean Netherlands'},
    '670': {'code': '+670', 'name': 'East Timor'},
    '672': {'code': '+672', 'name': 'Australian External Territories'},
    '673': {'code': '+673', 'name': 'Brunei'},
    '674': {'code': '+674', 'name': 'Nauru'},
    '675': {'code': '+675', 'name': 'Papua New Guinea'},
    '676': {'code': '+676', 'name': 'Tonga'},
    '677': {'code': '+677', 'name': 'Solomon Islands'},
    '678': {'code': '+678', 'name': 'Vanuatu'},
    '679': {'code': '+679', 'name': 'Fiji'},
    '680': {'code': '+680', 'name': 'Palau'},
    '681': {'code': '+681', 'name': 'Wallis and Futuna'},
    '682': {'code': '+682', 'name': 'Cook Islands'},
    '683': {'code': '+683', 'name': 'Niue'},
    '685': {'code': '+685', 'name': 'Samoa'},
    '686': {'code': '+686', 'name': 'Kiribati'},
    '687': {'code': '+687', 'name': 'New Caledonia'},
    '688': {'code': '+688', 'name': 'Tuvalu'},
    '689': {'code': '+689', 'name': 'French Polynesia'},
    '690': {'code': '+690', 'name': 'Tokelau'},
    '691': {'code': '+691', 'name': 'Micronesia'},
    '692': {'code': '+692', 'name': 'Marshall Islands'},
    '850': {'code': '+850', 'name': 'North Korea'},
    '852': {'code': '+852', 'name': 'Hong Kong'},
    '853': {'code': '+853', 'name': 'Macau'},
    '855': {'code': '+855', 'name': 'Cambodia'},
    '856': {'code': '+856', 'name': 'Laos'},
    '880': {'code': '+880', 'name': 'Bangladesh'},
    '886': {'code': '+886', 'name': 'Taiwan'},
    '960': {'code': '+960', 'name': 'Maldives'},
    '961': {'code': '+961', 'name': 'Lebanon'},
    '962': {'code': '+962', 'name': 'Jordan'},
    '963': {'code': '+963', 'name': 'Syria'},
    '964': {'code': '+964', 'name': 'Iraq'},
    '965': {'code': '+965', 'name': 'Kuwait'},
    '966': {'code': '+966', 'name': 'Saudi Arabia'},
    '967': {'code': '+967', 'name': 'Yemen'},
    '968': {'code': '+968', 'name': 'Oman'},
    '970': {'code': '+970', 'name': 'Palestine'},
    '971': {'code': '+971', 'name': 'UAE'},
    '972': {'code': '+972', 'name': 'Israel'},
    '973': {'code': '+973', 'name': 'Bahrain'},
    '974': {'code': '+974', 'name': 'Qatar'},
    '975': {'code': '+975', 'name': 'Bhutan'},
    '976': {'code': '+976', 'name': 'Mongolia'},
    '977': {'code': '+977', 'name': 'Nepal'},
    '992': {'code': '+992', 'name': 'Tajikistan'},
    '993': {'code': '+993', 'name': 'Turkmenistan'},
    '994': {'code': '+994', 'name': 'Azerbaijan'},
    '995': {'code': '+995', 'name': 'Georgia'},
    '996': {'code': '+996', 'name': 'Kyrgyzstan'},
    '998': {'code': '+998', 'name': 'Uzbekistan'}
}

FLAG_MAP = {
    'USA/Canada': '🇺🇸', 'Russia': '🇷🇺', 'Egypt': '🇪🇬', 'South Africa': '🇿🇦',
    'Greece': '🇬🇷', 'Netherlands': '🇳🇱', 'Belgium': '🇧🇪', 'France': '🇫🇷',
    'Spain': '🇪🇸', 'Hungary': '🇭🇺', 'Italy': '🇮🇹', 'Romania': '🇷🇴',
    'Switzerland': '🇨🇭', 'Austria': '🇦🇹', 'United Kingdom': '🇬🇧',
    'Denmark': '🇩🇰', 'Sweden': '🇸🇪', 'Norway': '🇳🇴', 'Poland': '🇵🇱',
    'Germany': '🇩🇪', 'Peru': '🇵🇪', 'Mexico': '🇲🇽', 'Cuba': '🇨🇺',
    'Argentina': '🇦🇷', 'Brazil': '🇧🇷', 'Chile': '🇨🇱', 'Colombia': '🇨🇴',
    'Venezuela': '🇻🇪', 'Malaysia': '🇲🇾', 'Australia': '🇦🇺', 'Indonesia': '🇮🇩',
    'Philippines': '🇵🇭', 'New Zealand': '🇳🇿', 'Singapore': '🇸🇬', 'Thailand': '🇹🇭',
    'Japan': '🇯🇵', 'South Korea': '🇰🇷', 'Vietnam': '🇻🇳', 'China': '🇨🇳',
    'Turkey': '🇹🇷', 'India': '🇮🇳', 'Pakistan': '🇵🇰', 'Afghanistan': '🇦🇫',
    'Sri Lanka': '🇱🇰', 'Myanmar': '🇲🇲', 'Iran': '🇮🇷', 'South Sudan': '🇸🇸',
    'Morocco': '🇲🇦', 'Algeria': '🇩🇿', 'Tunisia': '🇹🇳', 'Libya': '🇱🇾',
    'Gambia': '🇬🇲', 'Senegal': '🇸🇳', 'Mauritania': '🇲🇷', 'Mali': '🇲🇱',
    'Guinea': '🇬🇳', 'Ivory Coast': '🇨🇮', 'Burkina Faso': '🇧🇫', 'Niger': '🇳🇪',
    'Togo': '🇹🇬', 'Benin': '🇧🇯', 'Mauritius': '🇲🇺', 'Liberia': '🇱🇷',
    'Sierra Leone': '🇸🇱', 'Ghana': '🇬🇭', 'Nigeria': '🇳🇬', 'Chad': '🇹🇩',
    'Central African Republic': '🇨🇫', 'Cameroon': '🇨🇲', 'Cape Verde': '🇨🇻',
    'Sao Tome and Principe': '🇸🇹', 'Equatorial Guinea': '🇬🇶', 'Gabon': '🇬🇦',
    'Congo': '🇨🇬', 'DRC': '🇨🇩', 'Angola': '🇦🇴', 'Guinea-Bissau': '🇬🇼',
    'Seychelles': '🇸🇨', 'Sudan': '🇸🇩', 'Rwanda': '🇷🇼', 'Ethiopia': '🇪🇹',
    'Somalia': '🇸🇴', 'Djibouti': '🇩🇯', 'Kenya': '🇰🇪', 'Tanzania': '🇹🇿',
    'Uganda': '🇺🇬', 'Burundi': '🇧🇮', 'Mozambique': '🇲🇿', 'Zambia': '🇿🇲',
    'Madagascar': '🇲🇬', 'Reunion': '🇷🇪', 'Zimbabwe': '🇿🇼', 'Namibia': '🇳🇦',
    'Malawi': '🇲🇼', 'Lesotho': '🇱🇸', 'Botswana': '🇧🇼', 'Swaziland': '🇸🇿',
    'Comoros': '🇰🇲', 'St. Helena': '🇸🇭', 'Eritrea': '🇪🇷', 'Aruba': '🇦🇼',
    'Faroe Islands': '🇫🇴', 'Greenland': '🇬🇱', 'Gibraltar': '🇬🇮',
    'Portugal': '🇵🇹', 'Luxembourg': '🇱🇺', 'Ireland': '🇮🇪', 'Iceland': '🇮🇸',
    'Albania': '🇦🇱', 'Malta': '🇲🇹', 'Cyprus': '🇨🇾', 'Finland': '🇫🇮',
    'Bulgaria': '🇧🇬', 'Lithuania': '🇱🇹', 'Latvia': '🇱🇻', 'Estonia': '🇪🇪',
    'Moldova': '🇲🇩', 'Armenia': '🇦🇲', 'Belarus': '🇧🇾', 'Andorra': '🇦🇩',
    'Monaco': '🇲🇨', 'San Marino': '🇸🇲', 'Vatican City': '🇻🇦', 'Ukraine': '🇺🇦',
    'Serbia': '🇷🇸', 'Montenegro': '🇲🇪', 'Kosovo': '🇽🇰', 'Croatia': '🇭🇷',
    'Slovenia': '🇸🇮', 'Bosnia and Herzegovina': '🇧🇦', 'North Macedonia': '🇲🇰',
    'Czech Republic': '🇨🇿', 'Slovakia': '🇸🇰', 'Liechtenstein': '🇱🇮',
    'Belize': '🇧🇿', 'Guatemala': '🇬🇹', 'El Salvador': '🇸🇻', 'Honduras': '🇭🇳',
    'Nicaragua': '🇳🇮', 'Costa Rica': '🇨🇷', 'Panama': '🇵🇦', 'St. Pierre and Miquelon': '🇵🇲',
    'Haiti': '🇭🇹', 'Guadeloupe': '🇬🇵', 'Bolivia': '🇧🇴', 'Guyana': '🇬🇾',
    'Ecuador': '🇪🇨', 'French Guiana': '🇬🇫', 'Paraguay': '🇵🇾', 'Martinique': '🇲🇶',
    'Suriname': '🇸🇷', 'Uruguay': '🇺🇾', 'Caribbean Netherlands': '🇧🇶',
    'East Timor': '🇹🇱', 'Brunei': '🇧🇳', 'Nauru': '🇳🇷', 'Papua New Guinea': '🇵🇬',
    'Tonga': '🇹🇴', 'Solomon Islands': '🇸🇧', 'Vanuatu': '🇻🇺', 'Fiji': '🇫🇯',
    'Palau': '🇵🇼', 'Cook Islands': '🇨🇰', 'Samoa': '🇼🇸', 'Kiribati': '🇰🇮',
    'New Caledonia': '🇳🇨', 'Tuvalu': '🇹🇻', 'French Polynesia': '🇵🇫',
    'Micronesia': '🇫🇲', 'Marshall Islands': '🇲🇭', 'North Korea': '🇰🇵',
    'Hong Kong': '🇭🇰', 'Macau': '🇲🇴', 'Cambodia': '🇰🇭', 'Laos': '🇱🇦',
    'Bangladesh': '🇧🇩', 'Taiwan': '🇹🇼', 'Maldives': '🇲🇻', 'Lebanon': '🇱🇧',
    'Jordan': '🇯🇴', 'Syria': '🇸🇾', 'Iraq': '🇮🇶', 'Kuwait': '🇰🇼',
    'Saudi Arabia': '🇸🇦', 'Yemen': '🇾🇪', 'Oman': '🇴🇲', 'Palestine': '🇵🇸',
    'UAE': '🇦🇪', 'Israel': '🇮🇱', 'Bahrain': '🇧🇭', 'Qatar': '🇶🇦',
    'Bhutan': '🇧🇹', 'Mongolia': '🇲🇳', 'Nepal': '🇳🇵', 'Tajikistan': '🇹🇯',
    'Turkmenistan': '🇹🇲', 'Azerbaijan': '🇦🇿', 'Georgia': '🇬🇪', 'Kyrgyzstan': '🇰🇬',
    'Uzbekistan': '🇺🇿'
}

# ---------- HELPERS ----------
def get_country(phone_digits):
    for length in range(4, 0, -1):
        prefix = phone_digits[:length]
        if prefix in COUNTRY_MAP:
            return COUNTRY_MAP[prefix]
    return None

def clean_number(raw):
    digits = re.sub(r'\D', '', raw)
    if not digits or len(digits) < 7:
        return None
    info = get_country(digits)
    if info:
        cc = info['code'].replace('+', '')
        rest = digits[len(cc):] if digits.startswith(cc) else digits
        if len(rest) < 7:
            return None
        phone = info['code'] + rest
        country = info['name']
    else:
        phone = '+' + digits
        country = 'Unknown'
    flag = FLAG_MAP.get(country, '🌍')
    return {'phone': phone, 'country': country, 'flag': flag}

def extract_otp(text):
    if not text:
        return None
    clean = re.sub(r'\n', ' ', text).strip()
    patterns = [
        r'#\s*(\d{4,8})',
        r'(?:code|otp|verification\s*code|confirm\s*code|auth\s*code)\s*(?:is|:)?\s*(\d{4,8})',
        r'your\s+whatsapp\s+code\s*:\s*(\d{4,8})',
        r'(?<![0-9+])(\d{4,8})(?![0-9])',
        r'(\d{3,4})[\- ](\d{3,4})'
    ]
    for pat in patterns:
        m = re.search(pat, clean, re.I)
        if m:
            if pat == patterns[-1] and len(m.groups()) == 2:
                combined = m.group(1) + m.group(2)
                if 4 <= len(combined) <= 8:
                    return combined
            else:
                if pat == patterns[3]:
                    val = m.group(1)
                    if re.match(r'^(584|1|7|8|9)', val) and len(val) >= 10:
                        continue
                return m.group(1)
    return None

# ---------- SESSION MANAGEMENT ----------
def create_session_with_retries():
    sess = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)
    return sess

def extract_sesskey_from_page(html):
    """Extract sesskey from client stats page HTML using patterns."""
    patterns = [
        r'data_smscdr\.php[^"]*sesskey=([^&"\s]+)',
        r'sesskey=([^&\s"\']+)',
        r'var\s+sesskey\s*=\s*["\']([^"\']+)["\'];',
        r'SESSKEY\s*[:=]\s*["\']?([a-zA-Z0-9+/=]+)["\']?'
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None

def fetch_sesskey():
    global sesskey
    try:
        url = f"{BASE_URL}/client/SMSCDRStats"
        headers = {**HEADERS, "Referer": url}
        if session and session.cookies:
            headers["Cookie"] = '; '.join([f"{k}={v}" for k, v in session.cookies.items()])
        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            extracted = extract_sesskey_from_page(resp.text)
            if extracted:
                sesskey = extracted
                print(f"[SESSKEY] Found: {sesskey}")
                return True
            else:
                print("[SESSKEY] Not found in page")
        else:
            print(f"[SESSKEY] Fetch failed: {resp.status_code}")
    except Exception as e:
        print(f"[SESSKEY] Error: {e}")
    return False

def login():
    global session, sesskey, last_login
    with login_lock:
        if session and (time.time() - last_login) < 3600:
            return True
        try:
            print("[LOGIN] Starting...")
            session = create_session_with_retries()
            login_paths = ["/login", "/sign-in"]
            success = False

            for login_path in login_paths:
                try:
                    login_url = f"{BASE_URL}{login_path}"
                    r1 = session.get(login_url, headers=HEADERS, timeout=10)
                    if r1.status_code in (503, 403):
                        print(f"[LOGIN] {r1.status_code} on login page, waiting 3s...")
                        time.sleep(3)
                        continue
                    if r1.status_code != 200:
                        continue

                    html = r1.text
                    captcha_match = re.search(r'What is (\d+) \+ (\d+) = \?', html)
                    if not captcha_match:
                        continue
                    ans = int(captcha_match[1]) + int(captcha_match[2])
                    print(f"[LOGIN] Captcha answer: {ans}")

                    signin_url = f"{BASE_URL}/signin"
                    data = {"username": USERNAME, "password": PASSWORD, "capt": str(ans)}
                    headers_post = {**HEADERS, "Content-Type": "application/x-www-form-urlencoded"}

                    r2 = session.post(
                        signin_url,
                        data=data,
                        headers=headers_post,
                        allow_redirects=False,
                        timeout=10
                    )
                    print(f"[LOGIN] POST status: {r2.status_code}")

                    if r2.status_code in (503, 403):
                        print(f"[LOGIN] {r2.status_code} on signin, waiting 3s...")
                        time.sleep(3)
                        continue

                    if r2.status_code in (302, 301):
                        last_login = time.time()
                        print(f"[LOGIN] Success ({r2.status_code})")
                        success = True
                        break
                    elif r2.status_code == 200:
                        html2 = r2.text.lower()
                        if "logout" in html2 or "dashboard" in html2:
                            last_login = time.time()
                            print("[LOGIN] Success (200)")
                            success = True
                            break
                except Exception as e:
                    print(f"[LOGIN] Error with {login_path}: {e}")

            if not success:
                raise Exception("All login paths failed")

            # Fetch sesskey from client stats page
            if not fetch_sesskey():
                print("[LOGIN] Could not retrieve sesskey, but continuing (may affect data fetch)")

            return True
        except Exception as e:
            print(f"[LOGIN] Failed: {e}")
            session = None
            sesskey = None
            return False

def ensure_session():
    if not session or (time.time() - last_login) > 3600:
        print("[SESSION] Expired, re-logging...")
        return login()
    if sesskey is None:
        if fetch_sesskey():
            return True
        else:
            return login()
    return True

# ---------- FETCH NUMBERS ----------
def fetch_numbers():
    if not ensure_session():
        return []
    params = {
        "frange": "",
        "fclient": "",
        "sEcho": "1",
        "iDisplayStart": "0",
        "iDisplayLength": "-1",
        "_": int(time.time() * 1000)
    }
    if sesskey:
        params["sesskey"] = sesskey
    try:
        url = f"{BASE_URL}/client/res/data_smsnumbers.php"
        headers = {**HEADERS, "Referer": f"{BASE_URL}/client/MySMSNumbers"}
        if session and session.cookies:
            headers["Cookie"] = '; '.join([f"{k}={v}" for k, v in session.cookies.items()])
        resp = session.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"[NUMBERS] HTTP {resp.status_code}")
            return []
        data = resp.json()
        result = []
        for row in data.get("aaData", []):
            if len(row) < 4:
                continue
            raw = row[2].strip()  # The number is at index 2, not 3
            if not raw:
                continue
            cleaned = clean_number(raw)
            if cleaned:
                result.append({
                    "raw": raw,
                    "e164": cleaned['phone'],
                    "country": cleaned['country'],
                    "flag": cleaned['flag']
                })
            else:
                result.append({"raw": raw, "e164": None, "country": "Unknown", "flag": "🌍"})
        return result
    except Exception as e:
        print(f"[NUMBERS] Error: {e}")
        return []

# ---------- FETCH OTPs ----------
def fetch_otps(limit=100):
    if not ensure_session():
        return []
    today = time.strftime("%Y-%m-%d")
    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "",
        "fnum": "",
        "fcli": "",
        "fgdate": "",
        "fgmonth": "",
        "fgrange": "",
        "fgnumber": "",
        "fgcli": "",
        "fg": "0",
        "sEcho": "1",
        "iDisplayStart": "0",
        "iDisplayLength": str(limit),
        "_": int(time.time() * 1000)
    }
    if sesskey:
        params["sesskey"] = sesskey
    try:
        url = f"{BASE_URL}/client/res/data_smscdr.php"
        headers = {**HEADERS, "Referer": f"{BASE_URL}/client/SMSCDRStats"}
        if session and session.cookies:
            headers["Cookie"] = '; '.join([f"{k}={v}" for k, v in session.cookies.items()])
        resp = session.get(url, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            print(f"[OTP] HTTP {resp.status_code}")
            return []
        data = resp.json()
        if not data.get("aaData"):
            return []
        rows = data["aaData"]
        rows.sort(key=lambda x: x[0] if x and len(x) > 0 else '', reverse=True)
        result = []
        for row in rows:
            if len(row) < 6:
                continue
            number = row[2].strip() if row[2] else ''
            message = row[5].strip() if row[5] else ''
            if not number or not message:
                continue
            otp = extract_otp(message)
            if not otp:
                continue
            service = row[3].strip() if len(row) > 3 and row[3] else 'Unknown'
            timestamp = row[0] if row[0] else ''
            cleaned = clean_number(number)
            country = cleaned['country'] if cleaned else 'Unknown'
            flag = cleaned['flag'] if cleaned else '🌍'
            result.append({
                "number": number,
                "otp": otp,
                "service": service,
                "message": message[:300],
                "timestamp": timestamp,
                "country": country,
                "flag": flag
            })
            if len(result) >= 10:
                break
        return result
    except Exception as e:
        print(f"[OTP] Error: {e}")
        return []

# ---------- CACHED OTPs ----------
def get_cached_otps():
    with cache_lock:
        now = time.time()
        if otp_cache["data"] and (now - otp_cache["timestamp"]) < 10:
            return otp_cache["data"]
        fresh = fetch_otps(100)
        if fresh:
            otp_cache["data"] = fresh
            otp_cache["timestamp"] = now
            return fresh
        return otp_cache["data"]

# ---------- ROUTES ----------
@app.route("/")
def root():
    return jsonify({
        "message": "NumberPanel API (Client endpoints)",
        "endpoints": ["/numbers", "/sms"],
        "status": "online"
    })

@app.route("/numbers")
def numbers():
    try:
        data = fetch_numbers()
        return jsonify({"success": True, "count": len(data), "numbers": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/sms")
def sms():
    try:
        data = get_cached_otps()
        return jsonify({"success": True, "count": len(data), "otps": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)
