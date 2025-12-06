# Standard library imports
from datetime import datetime, timedelta
import html
from zoneinfo import ZoneInfo
import asyncio
import random
import sys
import time
import io
import json
import os

# تنظیم encoding برای Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Third-party imports
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    AIORateLimiter,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Local imports
from loadConfig import configBot
from curds import curdCommands, CreateDB
from dapi import api, nardeban

# منطقه زمانی مرجع برای تمام محاسبات زمان‌بندی
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def now_tehran():
    """datetime aware با منطقه زمانی تهران"""
    return datetime.now(TEHRAN_TZ)


# توابع مدیریت ساعت و دقیقه توقف و شروع در configs.json
def get_stop_time_from_config():
    """خواندن ساعت و دقیقه توقف خودکار از configs.json - برمی‌گرداند (hour, minute) یا None"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            # پشتیبانی از فرمت قدیمی (فقط hour)
            if 'stop_hour' in config and 'stop_minute' not in config:
                return (config.get('stop_hour'), 0)
            # فرمت جدید (hour و minute)
            stop_hour = config.get('stop_hour')
            stop_minute = config.get('stop_minute', 0)
            if stop_hour is not None:
                return (stop_hour, stop_minute)
            return None
    except Exception as e:
        print(f"❌ خطا در خواندن stop_time از configs.json: {e}")
        return None

def set_stop_time_in_config(hour, minute=0):
    """ذخیره ساعت و دقیقه توقف خودکار در configs.json"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['stop_hour'] = hour
        config['stop_minute'] = minute
        with open('configs.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✅ ساعت توقف خودکار ({hour:02d}:{minute:02d}) در configs.json ذخیره شد.")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره stop_time در configs.json: {e}")
        return False

def get_start_time_from_config():
    """خواندن ساعت و دقیقه شروع خودکار از configs.json - برمی‌گرداند (hour, minute) یا None"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            # پشتیبانی از فرمت قدیمی (فقط hour)
            if 'start_hour' in config and 'start_minute' not in config:
                return (config.get('start_hour'), 0)
            # فرمت جدید (hour و minute)
            start_hour = config.get('start_hour')
            start_minute = config.get('start_minute', 0)
            if start_hour is not None:
                return (start_hour, start_minute)
            return None
    except Exception as e:
        print(f"❌ خطا در خواندن start_time از configs.json: {e}")
        return None

def set_start_time_in_config(hour, minute=0):
    """ذخیره ساعت و دقیقه شروع خودکار در configs.json"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['start_hour'] = hour
        config['start_minute'] = minute
        with open('configs.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✅ ساعت شروع خودکار ({hour:02d}:{minute:02d}) در configs.json ذخیره شد.")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره start_time در configs.json: {e}")
        return False

# توابع سازگاری با کد قدیمی
def get_stop_hour_from_config():
    """خواندن فقط ساعت توقف (برای سازگاری)"""
    result = get_stop_time_from_config()
    return result[0] if result else None

def set_stop_hour_in_config(hour):
    """ذخیره فقط ساعت توقف (برای سازگاری)"""
    return set_stop_time_in_config(hour, 0)

def get_start_hour_from_config():
    """خواندن فقط ساعت شروع (برای سازگاری)"""
    result = get_start_time_from_config()
    return result[0] if result else None

def set_start_hour_in_config(hour):
    """ذخیره فقط ساعت شروع (برای سازگاری)"""
    return set_start_time_in_config(hour, 0)

def get_repeat_days_from_config():
    """خواندن تعداد روزهای تکرار از configs.json"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('repeat_days', 365)  # پیش‌فرض 365 روز
    except Exception as e:
        print(f"❌ خطا در خواندن repeat_days از configs.json: {e}")
        return 365

def set_repeat_days_in_config(days, reset_start_date=False):
    """ذخیره تعداد روزهای تکرار در configs.json
    
    Args:
        days: تعداد روزهای تکرار
        reset_start_date: اگر True باشد، تاریخ شروع را به امروز تنظیم می‌کند
    """
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['repeat_days'] = days
        # ذخیره یا به‌روزرسانی تاریخ شروع تکرار
        if reset_start_date or 'repeat_start_date' not in config:
            config['repeat_start_date'] = now_tehran().strftime('%Y-%m-%d')
        with open('configs.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✅ تعداد روزهای تکرار ({days}) در configs.json ذخیره شد.")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره repeat_days در configs.json: {e}")
        return False

def get_repeat_start_date_from_config():
    """خواندن تاریخ شروع تکرار از configs.json"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            date_str = config.get('repeat_start_date')
            if date_str:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            return now_tehran().date()
    except Exception as e:
        print(f"❌ خطا در خواندن repeat_start_date از configs.json: {e}")
        return now_tehran().date()

def is_repeat_period_active():
    """بررسی اینکه آیا دوره تکرار هنوز فعال است یا نه"""
    try:
        repeat_days = get_repeat_days_from_config()
        start_date = get_repeat_start_date_from_config()
        current_date = now_tehran().date()
        days_passed = (current_date - start_date).days
        return days_passed < repeat_days
    except Exception as e:
        print(f"❌ خطا در بررسی دوره تکرار: {e}")
        return True  # در صورت خطا، فعال در نظر بگیر

def get_active_weekdays_from_config():
    """خواندن روزهای فعال هفته از configs.json - برمی‌گرداند لیست اعداد (0=شنبه تا 6=جمعه)"""
    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            weekdays = config.get('active_weekdays', [0, 1, 2, 3, 4, 5, 6])  # پیش‌فرض همه روزها
            # اطمینان از اینکه لیست است
            if isinstance(weekdays, list):
                return weekdays
            return [0, 1, 2, 3, 4, 5, 6]  # در صورت خطا، همه روزها
    except Exception as e:
        print(f"❌ خطا در خواندن active_weekdays از configs.json: {e}")
        return [0, 1, 2, 3, 4, 5, 6]  # در صورت خطا، همه روزها

def set_active_weekdays_in_config(weekdays):
    """ذخیره روزهای فعال هفته در configs.json
    
    Args:
        weekdays: لیست اعداد (0=شنبه تا 6=جمعه)
    """
    try:
        # اعتبارسنجی
        valid_weekdays = [d for d in weekdays if 0 <= d <= 6]
        if not valid_weekdays:
            print("⚠️ هیچ روز معتبری انتخاب نشده - همه روزها فعال می‌شوند")
            valid_weekdays = [0, 1, 2, 3, 4, 5, 6]
        
        with open('configs.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['active_weekdays'] = sorted(list(set(valid_weekdays)))  # حذف تکراری‌ها و مرتب‌سازی
        with open('configs.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
        active_names = [weekday_names[d] for d in sorted(valid_weekdays)]
        print(f"✅ روزهای فعال هفته ({', '.join(active_names)}) در configs.json ذخیره شد.")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره active_weekdays در configs.json: {e}")
        return False

def format_weekdays_display(weekdays):
    """فرمت کردن نمایش روزهای هفته برای نمایش در منو"""
    weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
    weekday_short = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']
    
    if len(weekdays) == 7:
        return "همه روزها"
    elif len(weekdays) == 0:
        return "هیچ روزی"
    elif len(weekdays) <= 3:
        # نمایش نام کامل
        return ', '.join([weekday_names[d] for d in sorted(weekdays)])
    else:
        # نمایش کوتاه
        return ', '.join([weekday_short[d] for d in sorted(weekdays)])

def is_today_active_weekday():
    """بررسی اینکه آیا امروز یکی از روزهای فعال هفته است یا نه"""
    try:
        # در Python، weekday() برمی‌گرداند: 0=Monday, 6=Sunday
        # در ایران: 0=شنبه, 1=یکشنبه, ..., 6=جمعه
        # پس باید تبدیل کنیم: python_weekday = (iran_weekday + 2) % 7
        current_weekday_python = now_tehran().weekday()  # 0=Monday, 6=Sunday
        # تبدیل به فرمت ایرانی: 0=شنبه, 6=جمعه
        iran_weekday = (current_weekday_python + 2) % 7
        
        active_weekdays = get_active_weekdays_from_config()
        return iran_weekday in active_weekdays
    except Exception as e:
        print(f"❌ خطا در بررسی روز هفته: {e}")
        return True  # در صورت خطا، فعال در نظر بگیر

def is_stop_time_in_past():
    """بررسی اینکه آیا ساعت توقف خودکار در گذشته است یا نه"""
    try:
        stop_time_config = get_stop_time_from_config()
        if stop_time_config is None:
            return False  # اگر تنظیم نشده باشد، در گذشته نیست
        
        stop_hour, stop_minute = stop_time_config
        now = now_tehran()
        stop_time_today = now.replace(hour=stop_hour, minute=stop_minute, second=0, microsecond=0)
        
        # اگر ساعت توقف امروز از ساعت فعلی گذشته باشد، در گذشته است
        return stop_time_today < now
    except Exception as e:
        print(f"❌ خطا در بررسی ساعت توقف: {e}")
        return False  # در صورت خطا، در گذشته در نظر نگیر

# ==================== مدیریت توکن‌ها در فایل JSON ====================
from tokens_manager import (
    add_tokens_to_json,
    remove_token_from_json,
    get_tokens_from_json,
    get_all_pending_tokens_from_json,
    has_pending_tokens_in_json,
    load_tokens_json,
    update_token_status,
    get_token_stats,
    reset_tokens_for_chat
)

# ایجاد فایل JSON در صورت عدم وجود
try:
    load_tokens_json()  # این تابع خودش فایل را ایجاد می‌کند اگر وجود نداشته باشد
    print("✅ فایل tokens.json آماده است.")
except Exception as e:
    print(f"⚠️ خطا در ایجاد فایل tokens.json: {e}")
# ==================== پایان مدیریت توکن‌ها در فایل JSON ====================

# Initialize configuration and database
try:
    Datas = configBot()
    print(f"🔍 [Startup] Datas.admin = {Datas.admin} (type: {type(Datas.admin)})")
    
    # بررسی اینکه admin تعریف شده است
    if Datas.admin is None:
        print("❌ خطا: admin در فایل configs.json تعریف نشده است!")
        print("لطفاً فایل configs.json را بررسی کنید و مقدار 'admin' را تنظیم کنید.")
        sys.exit(1)
    
    print(f"✅ Admin پیش‌فرض: {Datas.admin} (type: {type(Datas.admin)})")
    
    curd = curdCommands(Datas)
    db = CreateDB(Datas)
    divarApi = api()
except FileNotFoundError as e:
    print(f"❌ خطا: فایل پیکربندی یافت نشد: {e}")
    print("لطفاً فایل configs.json را بررسی کنید.")
    sys.exit(1)
except KeyError as e:
    print(f"❌ خطا: کلید مورد نیاز در فایل پیکربندی یافت نشد: {e}")
    print("لطفاً فایل configs.json را بررسی کنید.")
    sys.exit(1)
except Exception as e:
    print(f"❌ خطا در مقداردهی اولیه: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

application_instance: Application | None = None
scheduler = AsyncIOScheduler(timezone="Asia/Tehran")


def get_bot():
    if application_instance is None:
        return None
    return application_instance.bot


async def bot_send_message(chat_id, text, **kwargs):
    """ارسال پیام با retry mechanism برای مدیریت خطاهای timeout"""
    bot = get_bot()
    if bot is None:
        print("⚠️ Bot instance not available yet for sending messages.")
        return
    
    max_retries = 3
    retry_delay = 2  # ثانیه
    
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return  # اگر موفق بود، از تابع خارج شو
        except (TimedOut, NetworkError) as e:
            # خطاهای timeout یا network - retry کن
            if attempt < max_retries - 1:
                print(f"⚠️ خطا در ارسال پیام (تلاش {attempt + 1}/{max_retries}): {type(e).__name__} - صبر {retry_delay} ثانیه...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # exponential backoff
                continue
            else:
                # آخرین تلاش هم ناموفق بود
                print(f"❌ خطا در ارسال پیام بعد از {max_retries} تلاش: {type(e).__name__} - {str(e)}")
                # خطا را log کن اما crash نکن
                import traceback
                traceback.print_exc()
                return
        except Exception as e:
            # سایر خطاها - retry نکن، فقط log کن
            error_name = type(e).__name__
            print(f"❌ خطا در ارسال پیام: {error_name} - {str(e)}")
            # برای خطاهای غیر timeout، خطا را log کن اما crash نکن
            import traceback
            traceback.print_exc()
            return

try:
    db.create()
except Exception as e:
    print(e)
try:
    curd.cTable_manage()
except Exception as e:
    print(e)
try:
    curd.cTable_adminp()
except Exception as e:
    print(e)
try:
    curd.cTable_logins()
except Exception as e:
    print(e)
try:
    curd.cTable_sents()
except Exception as e:
    print(e)
try:
    curd.cTable_admins()
except Exception as e:
    print(e)
try:
    curd.cTable_jobs()
except Exception as e:
    print(e)
try:
    curd.cTable_tokens()
except Exception as e:
    print(e)

# اضافه کردن ادمین پیش‌فرض به دیتابیس
try:
    admin_int = int(Datas.admin) if Datas.admin is not None else None
    admins_list = curd.getAdmins()
    admins_list_int = [int(admin_id) for admin_id in admins_list] if admins_list else []
    
    if admin_int not in admins_list_int:
        curd.setAdmin(chatid=admin_int)
        print(f"✅ Admin پیش‌فرض ({admin_int}) به دیتابیس اضافه شد.")
    else:
        print(f"ℹ️ Admin پیش‌فرض ({admin_int}) قبلاً در دیتابیس موجود است.")
except Exception as e:
    print(f"❌ خطا در اضافه کردن ادمین پیش‌فرض: {e}")
    import traceback
    traceback.print_exc()

# تابع helper برای چک کردن ادمین بودن (شامل ادمین پیش‌فرض)
def isAdmin(chatid):
    """بررسی می‌کند که آیا کاربر ادمین است (شامل ادمین پیش‌فرض)"""
    try:
        # بررسی اولیه
        if chatid is None:
            print(f"❌ [isAdmin] chatid None است")
            return False
        
        # تبدیل chatid به int (ممکن است string یا int باشد)
        try:
            if isinstance(chatid, str):
                chatid_int = int(chatid.strip())
            else:
                chatid_int = int(chatid)
        except (ValueError, TypeError) as e:
            print(f"❌ [isAdmin] خطا در تبدیل chatid به int: {e} (chatid: {chatid}, type: {type(chatid)})")
            return False
        
        # بررسی ادمین پیش‌فرض
        if Datas.admin is not None:
            try:
                # Datas.admin ممکن است int یا string باشد
                if isinstance(Datas.admin, str):
                    admin_int = int(Datas.admin.strip())
                else:
                    admin_int = int(Datas.admin)
                
                # بررسی ادمین پیش‌فرض
                if chatid_int == admin_int:
                    print(f"✅ [isAdmin] کاربر {chatid_int} ادمین پیش‌فرض است - بازگشت True")
                    return True
                else:
                    print(f"⚠️ [isAdmin] کاربر {chatid_int} ادمین پیش‌فرض نیست (admin: {admin_int})")
            except (ValueError, TypeError) as e:
                print(f"⚠️ [isAdmin] خطا در تبدیل Datas.admin: {e} (Datas.admin: {Datas.admin}, type: {type(Datas.admin)})")
        else:
            print(f"⚠️ [isAdmin] Datas.admin None است!")
        
        # بررسی ادمین‌های دیتابیس
        try:
            admins_list = curd.getAdmins()
            if admins_list:
                admins_list_int = []
                for admin_id in admins_list:
                    try:
                        if isinstance(admin_id, str):
                            admins_list_int.append(int(admin_id.strip()))
                        else:
                            admins_list_int.append(int(admin_id))
                    except (ValueError, TypeError):
                        continue  # نادیده گرفتن مقادیر نامعتبر
                
                if chatid_int in admins_list_int:
                    print(f"✅ [isAdmin] کاربر {chatid_int} در لیست ادمین‌ها است - بازگشت True")
                    return True
        except Exception as e:
            print(f"⚠️ [isAdmin] خطا در بررسی ادمین‌های دیتابیس: {e}")
        
        print(f"❌ [isAdmin] کاربر {chatid_int} ادمین نیست - بازگشت False")
        return False
        
    except Exception as e:
        print(f"❌ [isAdmin] خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()
        return False

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """افزودن ادمین جدید - فقط ادمین پیش‌فرض می‌تواند استفاده کند"""
    try:
        user = update.message
        chatid = user.chat.id
        
        # بررسی اینکه آیا کاربر ادمین پیش‌فرض است
        admin_int = int(Datas.admin) if Datas.admin is not None else None
        if chatid != admin_int:
            await context.bot.send_message(chat_id=chatid, text="❌ شما مجاز به استفاده از این دستور نیستید.")
            return
        
        # بررسی صحت ورودی
        parts = user.text.split(" ")
        if len(parts) < 2:
            await context.bot.send_message(chat_id=chatid, text="❌ لطفاً چت آیدی ادمین را وارد کنید.\nمثال: /add 123456789")
            return
        
        try:
            adminChatid = int(parts[1])
        except ValueError:
            await context.bot.send_message(chat_id=chatid, text="❌ چت آیدی باید یک عدد باشد.\nمثال: /add 123456789")
            return
        
        # بررسی اینکه آیا این ادمین قبلاً اضافه شده یا نه
        if adminChatid == admin_int:
            await context.bot.send_message(chat_id=chatid, text="❌ این ادمین پیش‌فرض است و قبلاً در سیستم موجود است.")
            return
        
        # اضافه کردن ادمین
        if curd.setAdmin(chatid=adminChatid) == 1:
            await context.bot.send_message(chat_id=chatid, text="✅ ادمین جدید با موفقیت به لیست ادمین ها افزوده شد.")
            try:
                await context.bot.send_message(chat_id=adminChatid, text="تبریک ، شما به ادمین های ربات اضافه شدید ، برای تایید فعال سازی لطفا /start را ارسال کنید")
            except:
                pass
        else:
                await context.bot.send_message(chat_id=chatid, text="❌ مشکلی در اضافه کردن ادمین وجود دارد.")
    except Exception as e:
        print(f"❌ خطا در تابع addadmin: {e}")
        import traceback
        traceback.print_exc()
        try:
            await context.bot.send_message(chat_id=chatid, text="❌ خطایی در پردازش درخواست شما رخ داد.")
        except:
            pass

def format_admin_menu(chat_id):
    """
    ساخت متن و دکمه‌های منوی اصلی ادمین.
    این تابع برای جلوگیری از تکرار کد در بخش‌های مختلف استفاده می‌شود.
    """
    curd.addAdmin(chatid=chat_id)
    curd.addManage(chatid=chat_id)
    mngDetail = curd.getManage(chatid=chat_id)
    stats = curd.getStats(chatid=chat_id)

    # وضعیت کلی
    is_active = mngDetail[0] == 1
    status_emoji = "🟢" if is_active else "🔴"
    status_text = "فعال" if is_active else "غیرفعال"

    # نوع نردبان
    nardeban_type = mngDetail[3] if len(mngDetail) > 3 else 1
    type_names = {1: "ترتیبی کامل", 2: "تصادفی", 3: "ترتیبی نوبتی", 4: "جریان طبیعی"}
    type_name = type_names.get(nardeban_type, "ترتیبی کامل")
    
    # فاصله بین نردبان‌ها
    interval_minutes = mngDetail[5] if len(mngDetail) > 5 else 5
    
    # ساعت و دقیقه توقف و شروع خودکار - از configs.json خوانده می‌شود
    stop_time = get_stop_time_from_config()
    start_time = get_start_time_from_config()
    
    # تعداد روزهای تکرار - از configs.json خوانده می‌شود
    repeat_days = get_repeat_days_from_config()
    
    # روزهای فعال هفته - از configs.json خوانده می‌شود
    active_weekdays = get_active_weekdays_from_config()
    weekdays_text = format_weekdays_display(active_weekdays)

    # وضعیت job و فاصله نردبان
    job_id = curd.getJob(chatid=chat_id)
    has_job = job_id is not None
    job_status = "🔄 در حال اجرا" if has_job else "⏸️ متوقف"

    interval_text = "در انتظار شروع"
    if nardeban_type == 4:
        interval_text = "نامنظم (۳ تا ۱۵ دقیقه)"
    elif has_job:
        job = scheduler.get_job(job_id) if scheduler else None
        if job and isinstance(job.trigger, IntervalTrigger):
            seconds = job.trigger.interval.total_seconds()
            if seconds >= 60:
                minutes = max(1, round(seconds / 60))
                interval_text = f"هر {minutes} دقیقه"
            else:
                interval_text = f"هر {int(seconds)} ثانیه"
        elif job:
            interval_text = "ثبت شده (Trigger نامشخص)"
        else:
            interval_text = "job در scheduler یافت نشد"
    
    # نمایش ساعت و دقیقه توقف و شروع خودکار
    stop_time_text = "تنظیم نشده"
    if stop_time is not None:
        stop_hour, stop_minute = stop_time
        stop_time_text = f"{stop_hour:02d}:{stop_minute:02d}"
    
    start_time_text = "تنظیم نشده"
    if start_time is not None:
        start_hour, start_minute = start_time
        start_time_text = f"{start_hour:02d}:{start_minute:02d}"

    welcome_text = f"""🤖 <b>منوی مدیریت ربات نردبان</b>

{status_emoji} <b>وضعیت ربات:</b> {status_text}
📊 <b>آمار کلی:</b>
   ✅ نردبان شده: <b>{stats['total_nardeban']}</b>
   📦 کل استخراج: <b>{stats['total_tokens']}</b>
   ⏳ در انتظار: <b>{stats['total_pending']}</b>
   ❌ ناموفق: <b>{stats.get('total_failed', 0)}</b>

⚙️ <b>تنظیمات جاری:</b>
   ⏱️ فاصله بین نردبان‌ها: <b>{interval_minutes} دقیقه</b>
   🎯 نوع نردبان: <b>{type_name}</b>
   {job_status}
   ⏱️ فاصله فعلی: <b>{interval_text}</b>
   ▶️ شروع خودکار: <b>{start_time_text}</b>
   🕐 توقف خودکار: <b>{stop_time_text}</b>
   🔁 تکرار: <b>{repeat_days} روز</b>
   📅 روزهای هفته: <b>{weekdays_text}</b>

👇 <i>یکی از گزینه‌های زیر را انتخاب کنید:</i>"""

    # منوی اصلی مینیمال
    btns = [
        # وضعیت ربات و کنترل اصلی
        [
            InlineKeyboardButton(
                f"{'🟢' if is_active else '🔴'} {'خاموش کردن' if is_active else 'روشن کردن'} ربات",
                callback_data="setactive:0" if is_active else "setactive:1"
            )
        ],
        [
            InlineKeyboardButton(
                '⏹️ توقف نردبان' if has_job else '▶️ شروع نردبان',
                callback_data='remJob' if has_job else 'startJob'
            )
        ],
        
        # منوهای اصلی
        [
            InlineKeyboardButton('📊 آمار و گزارشات', callback_data='stats_menu'),
            InlineKeyboardButton('📱 مدیریت لاگین‌ها', callback_data='managelogin')
        ],
        [
            InlineKeyboardButton('⚙️ تنظیمات ربات', callback_data='settings_menu'),
            InlineKeyboardButton('🔧 عملیات پیشرفته', callback_data='advanced_menu')
        ]
    ]

    # منوی ادمین اصلی (فقط برای ادمین اصلی)
    if int(chat_id) == int(Datas.admin):
        btns.append([InlineKeyboardButton('👥 مدیریت ادمین‌ها', callback_data='manageAdmins')])

    # دکمه‌های کمکی
    btns.append([
        InlineKeyboardButton('❓ راهنما', callback_data='help_menu'),
        InlineKeyboardButton('🔁 بروزرسانی', callback_data='refreshMenu')
    ])

    return welcome_text, InlineKeyboardMarkup(btns)


def format_login_management_menu(chat_id):
    """
    ساخت متن و دکمه‌های مدیریت لاگین‌ها برای یک کاربر خاص.
    """
    logins = curd.getLogins(chatid=chat_id)
    text = "📱 <b>مدیریت لاگین‌های دیوار</b>\n\n"
    buttons = []

    if not logins or logins == 0:
        text += "⚠️ شما هیچ شماره‌ای تا به حال اضافه نکرده‌اید!"
        buttons.append([InlineKeyboardButton('➕ اضافه کردن لاگین جدید', callback_data='addlogin')])
    else:
        text += "📋 <b>لیست لاگین‌های شما:</b>\n\n"
        for phone, _, active in logins:
            phone_str = str(phone)
            status_text = "✅ فعال" if active else "❌ غیرفعال"
            next_state = 0 if active else 1
            buttons.append([
                InlineKeyboardButton(status_text, callback_data=f"status:{next_state}:{phone_str}"),
                InlineKeyboardButton(f"📱 {phone_str}", callback_data=f"del:{phone_str}"),
                InlineKeyboardButton("🔄 به‌روزرسانی", callback_data=f"update:{phone_str}"),
            ])
        buttons.append([InlineKeyboardButton('➕ اضافه کردن لاگین جدید', callback_data='addlogin')])

    buttons.append([InlineKeyboardButton('🔙 بازگشت به منو اصلی', callback_data='backToMenu')])
    return text, InlineKeyboardMarkup(buttons)


def _chunk_lines_for_message(lines, limit=3500):
    """تقسیم خطوط متن به چند پیام برای جلوگیری از تجاوز از محدودیت تلگرام."""
    chunks = []
    current = ""
    for raw_line in lines:
        line = raw_line or ""
        addition = line if not current else f"\n{line}"
        if len(current) + len(addition) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current += addition
    if current:
        chunks.append(current)
    return chunks


async def report_ads_by_status(chatid, heading, empty_text, fetch_func):
    """گزارش وضعیت آگهی‌ها بر اساس تابع fetch_func (مثل تمدید یا منقضی)."""
    logins = curd.getLogins(chatid=chatid)
    if not logins or logins == 0:
        await bot_send_message(chat_id=chatid, text="⚠️ هیچ لاگین فعالی برای بررسی وجود ندارد.")
        return

    active_logins = [login for login in logins if login[2] == 1]
    if not active_logins:
        await bot_send_message(chat_id=chatid, text="⚠️ همه لاگین‌ها غیرفعال هستند. ابتدا یک شماره را فعال کنید.")
        return

    lines = [heading, ""]
    total_found = 0

    for phone, cookie, _ in active_logins:
        nardeban_api = nardeban(apiKey=cookie)

        try:
            tokens_info = await asyncio.to_thread(fetch_func, nardeban_api)
        except Exception as e:
            err_text = str(e).strip() or "خطای نامشخص"
            err_text = html.escape(err_text[:120])
            lines.append(f"📱 <b>{phone}</b>: ❌ خطا در دریافت اطلاعات ({err_text})")
            lines.append("")
            continue

        if not tokens_info:
            lines.append(f"📱 <b>{phone}</b>: {empty_text}")
            lines.append("")
            continue

        total_found += len(tokens_info)
        lines.append(f"📱 <b>{phone}</b> - {len(tokens_info)} آگهی یافت شد:")
        for idx, info in enumerate(tokens_info[:5], 1):
            token = info.get('token')
            label = html.escape((info.get('label') or 'نیاز به تمدید').strip())
            title = html.escape((info.get('title') or '').strip())
            extra = f" – {title}" if title else ""
            if token:
                short_token = html.escape(token[:8] + "...")
                ad_link = f"https://divar.ir/v/{token}"
                lines.append(f"   {idx}. <a href='{ad_link}'>🔗 {short_token}</a> ({label}{extra})")
            else:
                lines.append(f"   {idx}. {label}{extra}")
        if len(tokens_info) > 5:
            lines.append(f"   • ... {len(tokens_info) - 5} آگهی دیگر")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(f"📊 جمع کل: {total_found} آگهی")

    for chunk in _chunk_lines_for_message(lines):
        await bot_send_message(
            chat_id=chatid,
            text=chunk,
            parse_mode='HTML',
            disable_web_page_preview=False
        )


async def report_ads_needing_renewal(chatid):
    await report_ads_by_status(
        chatid=chatid,
        heading="🧭 <b>گزارش آگهی‌های نیازمند تمدید (قبل از انقضا)</b>",
        empty_text="هیچ آگهی نزدیک به انقضا نیست.",
        fetch_func=lambda api: api.get_tokens_needing_renewal()
    )


async def report_expired_ads(chatid):
    await report_ads_by_status(
        chatid=chatid,
        heading="📛 <b>گزارش آگهی‌های منقضی شده</b>",
        empty_text="هیچ آگهی منقضی نشده‌ای وجود ندارد.",
        fetch_func=lambda api: api.get_expired_tokens()
    )


async def renew_ads_by_status(chatid, heading, fetch_func):
    """تمدید گروهی آگهی‌ها بر اساس وضعیت (نزدیک انقضا یا منقضی)."""
    logins = curd.getLogins(chatid=chatid)
    if not logins or logins == 0:
        await bot_send_message(chat_id=chatid, text="⚠️ هیچ لاگین فعالی برای تمدید وجود ندارد.")
        return

    active_logins = [login for login in logins if login[2] == 1]
    if not active_logins:
        await bot_send_message(chat_id=chatid, text="⚠️ همه لاگین‌ها غیرفعال هستند. ابتدا یک شماره را فعال کنید.")
        return

    lines = [heading, ""]
    total_attempted = 0
    total_success = 0
    total_failed = 0

    for phone, cookie, _ in active_logins:
        nardeban_api = nardeban(apiKey=cookie)

        try:
            tokens_info = await asyncio.to_thread(fetch_func, nardeban_api)
        except Exception as e:
            err_text = html.escape((str(e).strip() or "خطای نامشخص")[:120])
            lines.append(f"📱 <b>{phone}</b>: ❌ خطا در دریافت لیست ({err_text})")
            lines.append("")
            continue

        if not tokens_info:
            lines.append(f"📱 <b>{phone}</b>: هیچ آگهی مطابق معیار یافت نشد.")
            lines.append("")
            continue

        phone_success = 0
        phone_failed = 0

        for info in tokens_info:
            token = info.get('token')
            if not token:
                continue

            total_attempted += 1
            try:
                result = await asyncio.to_thread(
                    nardeban_api.sendNardebanWithToken,
                    int(phone),
                    chatid,
                    token,
                    False
                )
            except Exception as e:
                phone_failed += 1
                total_failed += 1
                err_text = html.escape((str(e).strip() or "خطای نامشخص")[:80])
                lines.append(f"   • {token[:8]}...: ❌ خطا ({err_text})")
                continue

            if result and result[0] == 1:
                phone_success += 1
                total_success += 1
            else:
                phone_failed += 1
                total_failed += 1
                err_msg = result[2] if result and len(result) > 2 else "نامشخص"
                lines.append(f"   • {token[:8]}...: ❌ {html.escape(err_msg[:100])}")

        lines.append(f"📱 <b>{phone}</b>: ✅ {phone_success} | ❌ {phone_failed}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(f"🔁 کل تلاش‌ها: {total_attempted}")
    lines.append(f"✅ موفق: {total_success}")
    lines.append(f"❌ ناموفق: {total_failed}")

    for chunk in _chunk_lines_for_message(lines):
        await bot_send_message(
            chat_id=chatid,
            text=chunk,
            parse_mode='HTML',
            disable_web_page_preview=True
        )


async def renew_need_ads(chatid):
    await renew_ads_by_status(
        chatid=chatid,
        heading="♻️ <b>تمدید همه آگهی‌های نیازمند تمدید</b>",
        fetch_func=lambda api: api.get_tokens_needing_renewal()
    )


async def renew_expired_ads(chatid):
    await renew_ads_by_status(
        chatid=chatid,
        heading="♻️ <b>تمدید همه آگهی‌های منقضی شده</b>",
        fetch_func=lambda api: api.get_expired_tokens()
    )


async def send_admin_menu(chat_id, message_id=None):
    """ارسال یا بروزرسانی منوی اصلی ادمین با مدیریت خطا."""
    bot = get_bot()
    if bot is None:
        print("⚠️ Bot instance not available for send_admin_menu.")
        return

    try:
        welcome_text, keyboard = format_admin_menu(chat_id)
        if message_id:
            max_retries = 3
            retry_delay = 2
            for attempt in range(max_retries):
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=welcome_text,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    return
                except (TimedOut, NetworkError) as e:
                    # خطاهای timeout یا network - retry کن
                    if attempt < max_retries - 1:
                        print(f"⚠️ خطا در ویرایش پیام (تلاش {attempt + 1}/{max_retries}): {type(e).__name__} - صبر {retry_delay} ثانیه...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        print(f"❌ خطا در ویرایش پیام بعد از {max_retries} تلاش: {type(e).__name__}")
                        # اگر retry ناموفق بود، سعی کن پیام جدید بفرستی
                        break
                except Exception as e:
                    # سایر خطاها (مثلاً message not modified) - سعی کن پیام جدید بفرستی
                    error_name = type(e).__name__
                    print(f"⚠️ خطا در ویرایش پیام: {error_name} - تلاش برای ارسال پیام جدید...")
                    break
            
            # اگر ویرایش موفق نبود، پیام جدید ارسال کن
            await bot_send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await bot_send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        print(f"❌ خطا در send_admin_menu: {e}")
        import traceback
        traceback.print_exc()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # پشتیبانی از هم message و هم callback_query
        if update.message:
            user = update.message
            chat_id = user.chat.id
        elif update.callback_query:
            chat_id = update.callback_query.from_user.id
        else:
            return
        
        print(f"📥 دستور /start دریافت شد از کاربر: {chat_id} (type: {type(chat_id)})")
        print(f"🔍 بررسی ادمین بودن برای chat_id: {chat_id}, Datas.admin: {Datas.admin} (type: {type(Datas.admin)})")
        
        is_admin_result = isAdmin(chat_id)
        print(f"🔍 نتیجه isAdmin: {is_admin_result}")
        
        if is_admin_result:
            try:
                await send_admin_menu(chat_id=chat_id)
                print(f"✅ منو برای کاربر {chat_id} ارسال شد")
            except Exception as e:
                print(f"⚠️ خطا در ارسال منو برای کاربر {chat_id}: {e}")
                # سعی کن یک پیام ساده بفرستی
                try:
                    await bot_send_message(chat_id=chat_id, text="🤖 ربات آماده است. لطفاً دوباره /start را ارسال کنید.")
                except:
                    pass
        else:
            # اگر کاربر ادمین نبود → یک پیام و کیبورد بفرستد
            # بررسی مجدد برای اطمینان از اینکه کاربر واقعاً ادمین نیست
            final_check = isAdmin(chat_id)
            if final_check:
                print(f"⚠️ [start] کاربر {chat_id} در بررسی مجدد ادمین تشخیص داده شد - پیام خطا ارسال نمی‌شود")
                return
            
            keyRequest = [[InlineKeyboardButton('درخواست ادمین شدن', callback_data='reqAdmin')]]
            await context.bot.send_message(
                chat_id=chat_id,
                text="شما مجاز به استفاده از ربات نمیباشید .",
                reply_markup=InlineKeyboardMarkup(keyRequest)
            )
            print(f"⚠️ کاربر {chat_id} مجاز نیست")
    except Exception as e:
        print(f"❌ خطا در تابع start: {e}")
        import traceback
        traceback.print_exc()
        try:
            if update.message:
                await context.bot.send_message(
                    chat_id=update.message.chat.id,
                    text="❌ خطایی در پردازش درخواست شما رخ داد. لطفاً دوباره تلاش کنید."
                )
        except:
            pass

async def shoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message
    print(f"📨 [shoro] دستور /end دریافت شد از کاربر: {user.chat.id}")
    is_admin_result = isAdmin(user.chat.id)
    print(f"🔍 [shoro] نتیجه isAdmin: {is_admin_result}")
    if is_admin_result:
        if curd.getJob(chatid=user.chat.id):
            await context.bot.send_message(chat_id=user.chat.id, text="شما یک عملیات نردبان فعال دارید ، از غیرفعال سازی آن اطمینان یابید سپس اقدام کنید !", reply_to_message_id=user.message_id)
        else:
            await asyncio.to_thread(refreshUsed, chatid=user.chat.id)
            user = update.message
            endTime = int(user.text.split("=")[1])
            if endTime in range(0, 24):
                await startNardebanDasti(end=endTime, chatid=user.chat.id)
                await context.bot.send_message(chat_id=user.chat.id, text="عملیات نردبان دستی شکل گرفت.", reply_to_message_id=user.message_id)
            else:
                await context.bot.send_message(chat_id=user.chat.id,
                                 text="مقدار ساعت پایانی عددی باید بین 0 تا 23 باشد !",
                                 reply_to_message_id=user.message_id)
    else:
        # بررسی مجدد برای اطمینان از اینکه کاربر واقعاً ادمین نیست
        final_check = isAdmin(user.chat.id)
        if final_check:
            print(f"⚠️ [shoro] کاربر {user.chat.id} در بررسی مجدد ادمین تشخیص داده شد - پیام خطا ارسال نمی‌شود")
            return
        
        print(f"❌ [shoro] کاربر {user.chat.id} ادمین نیست - ارسال پیام خطا")
        await context.bot.send_message(chat_id=user.chat.id, text="شما مجاز به استفاده از ربات نمیباشید .")

async def auto_start_nardeban(chatid):
    """تابع برای شروع خودکار نردبان در ساعت مشخص شده"""
    try:
        # بررسی اینکه آیا دوره تکرار هنوز فعال است
        if not is_repeat_period_active():
            print(f"⚠️ [auto_start] دوره تکرار برای کاربر {chatid} به پایان رسیده - شروع خودکار انجام نمی‌شود")
            # حذف job شروع خودکار
            try:
                job_id = f"auto_start_{chatid}"
                if scheduler:
                    scheduler.remove_job(job_id)
                print(f"✅ Job شروع خودکار برای کاربر {chatid} حذف شد (پایان دوره تکرار)")
            except:
                pass
            return
        
        # بررسی اینکه آیا job فعالی وجود دارد
        job_id = curd.getJob(chatid=chatid)
        if job_id:
            print(f"⚠️ [auto_start] کاربر {chatid} قبلاً job فعال دارد - شروع خودکار انجام نمی‌شود")
            return
        
        # بررسی اینکه آیا امروز یکی از روزهای فعال هفته است
        if not is_today_active_weekday():
            print(f"⚠️ [auto_start] امروز یکی از روزهای فعال هفته نیست - شروع خودکار انجام نمی‌شود")
            return
        
        # بررسی اینکه آیا ربات فعال است
        manageDetails = curd.getManage(chatid=chatid)
        if manageDetails[0] != 1:
            print(f"⚠️ [auto_start] ربات کاربر {chatid} غیرفعال است - شروع خودکار انجام نمی‌شود")
            return
        
        # بررسی اینکه آیا ساعت توقف خودکار در گذشته است
        if is_stop_time_in_past():
            stop_time_config = get_stop_time_from_config()
            if stop_time_config:
                stop_hour, stop_minute = stop_time_config
                print(f"⚠️ [auto_start] ساعت توقف خودکار ({stop_hour:02d}:{stop_minute:02d}) در گذشته است - شروع خودکار انجام نمی‌شود")
                await bot_send_message(
                    chat_id=chatid,
                    text=f"⚠️ ساعت توقف خودکار ({stop_hour:02d}:{stop_minute:02d}) در گذشته است.\n\nلطفاً ساعت توقف را به آینده تنظیم کنید یا منتظر فردا بمانید."
                )
            return
        
        # دریافت ساعت و دقیقه توقف از configs.json
        stop_time_config = get_stop_time_from_config()
        if stop_time_config is not None:
            end_hour, end_minute = stop_time_config
            # برای سازگاری با startNardebanDasti که فقط hour می‌گیرد، از hour استفاده می‌کنیم
            end_hour = end_hour
        else:
            # اگر تنظیم نشده باشد، از ساعت فعلی + 12 ساعت استفاده می‌کنیم
            current_hour = now_tehran().hour
            end_hour = (current_hour + 12) % 24
        
        now_local = now_tehran()
        print(f"🚀 [auto_start] شروع خودکار نردبان برای کاربر {chatid} در ساعت {now_local.hour:02d}:{now_local.minute:02d}")
        await startNardebanDasti(chatid=chatid, end=end_hour)
    except Exception as e:
        print(f"❌ [auto_start] خطا در شروع خودکار نردبان: {e}")
        import traceback
        traceback.print_exc()

async def setup_auto_start_job(chatid, start_hour, start_minute=0):
    """تنظیم job برای شروع خودکار در ساعت و دقیقه مشخص شده با در نظر گیری روزهای هفته"""
    try:
        # حذف job قبلی شروع خودکار (اگر وجود داشته باشد)
        all_jobs = scheduler.get_jobs() if scheduler else []
        for job in all_jobs:
            if job.id and f"auto_start_{chatid}" in str(job.id):
                try:
                    scheduler.remove_job(job.id)
                except:
                    pass
        
        # دریافت روزهای فعال هفته
        active_weekdays_iran = get_active_weekdays_from_config()
        
        # تبدیل از فرمت ایرانی به APScheduler
        # APScheduler: 0=Monday, 1=Tuesday, ..., 6=Sunday
        # ایران: 0=شنبه, 1=یکشنبه, ..., 6=جمعه
        # تبدیل: apscheduler_day = (iran_day + 2) % 7
        active_weekdays_apscheduler = [(day + 2) % 7 for day in active_weekdays_iran]
        
        # اضافه کردن job جدید برای شروع خودکار
        job_id = f"auto_start_{chatid}"
        
        # اگر همه روزها فعال هستند، day_of_week را تنظیم نکنیم (همه روزها)
        if len(active_weekdays_apscheduler) == 7:
            scheduler.add_job(
                auto_start_nardeban,
                trigger="cron",
                args=[chatid],
                hour=start_hour,
                minute=start_minute,
                id=job_id,
                replace_existing=True
            )
        else:
            scheduler.add_job(
                auto_start_nardeban,
                trigger="cron",
                args=[chatid],
                hour=start_hour,
                minute=start_minute,
                day_of_week=active_weekdays_apscheduler,
                id=job_id,
                replace_existing=True
            )
        
        weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
        active_names = [weekday_names[d] for d in sorted(active_weekdays_iran)]
        print(f"✅ Job شروع خودکار برای کاربر {chatid} در ساعت {start_hour:02d}:{start_minute:02d} در روزهای {', '.join(active_names)} تنظیم شد")
    except Exception as e:
        print(f"❌ خطا در تنظیم job شروع خودکار: {e}")
        import traceback
        traceback.print_exc()

async def setup_auto_stop_job(chatid, stop_hour, stop_minute=0):
    """تنظیم job برای توقف خودکار در ساعت و دقیقه مشخص شده"""
    # این تابع در startNardebanDasti استفاده می‌شود
    # job توقف در startNardebanDasti تنظیم می‌شود
    pass

async def mainMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.message
        chatid = user.chat.id
        print(f"📨 [mainMenu] پیام متنی دریافت شد از کاربر: {chatid}, متن: {user.text[:50]}")
        
        is_admin_result = isAdmin(chatid)
        print(f"🔍 [mainMenu] نتیجه isAdmin: {is_admin_result}")
        
        if is_admin_result:
            status = curd.getStatus(chatid=chatid) #0:slogin , 1:slimit, 2:scode
            print(f"🔍 [mainMenu] status: slogin={status[0]}, slimit={status[1]}, scode={status[2]}")
            
            # بررسی اینکه آیا باید فاصله بین نردبان‌ها را تنظیم کنیم
            # استفاده از یک flag جدید در adminp برای sinterval
            # برای سازگاری، از scode به عنوان flag استفاده می‌کنیم (اگر scode == 2 باشد، یعنی در حال تنظیم interval هستیم)
            if status[2] == 2:  # scode == 2 به معنای تنظیم interval است
                try:
                    interval_value = int(user.text)
                    if interval_value < 1:
                        await context.bot.send_message(chat_id=chatid, text="❌ فاصله باید حداقل 1 دقیقه باشد.", reply_to_message_id=user.message_id)
                        return
                    curd.setStatusManage(q="interval_minutes", v=interval_value, chatid=chatid)
                    curd.setStatus(q="scode", v=0, chatid=chatid)
                    txt = f"🔎 فاصله بین نردبان‌ها به <code>{str(interval_value)}</code> دقیقه تنظیم گردید. ✅"
                    await context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                     parse_mode='HTML')
                except ValueError:
                    await context.bot.send_message(chat_id=chatid, text="❌ لطفاً یک عدد معتبر وارد کنید.", reply_to_message_id=user.message_id)
            elif status[2] == 3:  # scode == 3 به معنای تنظیم stop_time است
                try:
                    # پارس کردن ورودی: می‌تواند "8:30" یا "8" باشد
                    user_input = user.text.strip()
                    if ':' in user_input:
                        parts = user_input.split(':')
                        if len(parts) != 2:
                            raise ValueError("فرمت نامعتبر")
                        stop_hour_value = int(parts[0].strip())
                        stop_minute_value = int(parts[1].strip())
                    else:
                        stop_hour_value = int(user_input)
                        stop_minute_value = 0
                    
                    if stop_hour_value < 0 or stop_hour_value > 23:
                        await context.bot.send_message(chat_id=chatid, text="❌ ساعت باید بین 0 تا 23 باشد.", reply_to_message_id=user.message_id)
                        return
                    if stop_minute_value < 0 or stop_minute_value > 59:
                        await context.bot.send_message(chat_id=chatid, text="❌ دقیقه باید بین 0 تا 59 باشد.", reply_to_message_id=user.message_id)
                        return
                    
                    if set_stop_time_in_config(stop_hour_value, stop_minute_value):
                        curd.setStatus(q="scode", v=0, chatid=chatid)
                        txt = f"🔎 ساعت توقف خودکار به <code>{stop_hour_value:02d}:{stop_minute_value:02d}</code> تنظیم گردید. ✅"
                        await context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                         parse_mode='HTML')
                        # بروزرسانی job توقف خودکار
                        await setup_auto_stop_job(chatid, stop_hour_value, stop_minute_value)
                    else:
                        await context.bot.send_message(chat_id=chatid, text="❌ خطا در ذخیره ساعت توقف.", reply_to_message_id=user.message_id)
                except ValueError as e:
                    await context.bot.send_message(chat_id=chatid, text="❌ لطفاً فرمت صحیح وارد کنید:\n<code>ساعت:دقیقه</code> یا <code>ساعت</code>\nمثال: <code>22:30</code> یا <code>22</code>", reply_to_message_id=user.message_id, parse_mode='HTML')
            elif status[2] == 4:  # scode == 4 به معنای تنظیم start_time است
                try:
                    # پارس کردن ورودی: می‌تواند "8:30" یا "8" باشد
                    user_input = user.text.strip()
                    if ':' in user_input:
                        parts = user_input.split(':')
                        if len(parts) != 2:
                            raise ValueError("فرمت نامعتبر")
                        start_hour_value = int(parts[0].strip())
                        start_minute_value = int(parts[1].strip())
                    else:
                        start_hour_value = int(user_input)
                        start_minute_value = 0
                    
                    if start_hour_value < 0 or start_hour_value > 23:
                        await context.bot.send_message(chat_id=chatid, text="❌ ساعت باید بین 0 تا 23 باشد.", reply_to_message_id=user.message_id)
                        return
                    if start_minute_value < 0 or start_minute_value > 59:
                        await context.bot.send_message(chat_id=chatid, text="❌ دقیقه باید بین 0 تا 59 باشد.", reply_to_message_id=user.message_id)
                        return
                    
                    if set_start_time_in_config(start_hour_value, start_minute_value):
                        curd.setStatus(q="scode", v=0, chatid=chatid)
                        txt = f"🔎 ساعت شروع خودکار به <code>{start_hour_value:02d}:{start_minute_value:02d}</code> تنظیم گردید. ✅"
                        await context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                         parse_mode='HTML')
                        # بروزرسانی job شروع خودکار
                        await setup_auto_start_job(chatid, start_hour_value, start_minute_value)
                    else:
                        await context.bot.send_message(chat_id=chatid, text="❌ خطا در ذخیره ساعت شروع.", reply_to_message_id=user.message_id)
                except ValueError as e:
                    await context.bot.send_message(chat_id=chatid, text="❌ لطفاً فرمت صحیح وارد کنید:\n<code>ساعت:دقیقه</code> یا <code>ساعت</code>\nمثال: <code>8:30</code> یا <code>8</code>", reply_to_message_id=user.message_id, parse_mode='HTML')
            elif status[2] == 5:  # scode == 5 به معنای تنظیم repeat_days است
                try:
                    repeat_days_value = int(user.text.strip())
                    if repeat_days_value < 1:
                        await context.bot.send_message(chat_id=chatid, text="❌ تعداد روزها باید حداقل 1 باشد.", reply_to_message_id=user.message_id)
                        return
                    if repeat_days_value > 3650:  # حداکثر 10 سال
                        await context.bot.send_message(chat_id=chatid, text="❌ تعداد روزها نمی‌تواند بیشتر از 3650 (10 سال) باشد.", reply_to_message_id=user.message_id)
                        return
                    
                    if set_repeat_days_in_config(repeat_days_value, reset_start_date=True):
                        curd.setStatus(q="scode", v=0, chatid=chatid)
                        start_date = get_repeat_start_date_from_config()
                        end_date = start_date + timedelta(days=repeat_days_value)
                        txt = f"🔎 تعداد روزهای تکرار به <code>{repeat_days_value}</code> روز تنظیم گردید. ✅\n\n📅 دوره تکرار از <code>{start_date.strftime('%Y-%m-%d')}</code> تا <code>{end_date.strftime('%Y-%m-%d')}</code> فعال است."
                        await context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                         parse_mode='HTML')
                        # بروزرسانی jobهای شروع خودکار برای همه ادمین‌ها
                        start_time = get_start_time_from_config()
                        if start_time is not None:
                            start_hour, start_minute = start_time
                            admins = curd.getAdmins()
                            for admin_id in admins:
                                try:
                                    await setup_auto_start_job(int(admin_id), start_hour, start_minute)
                                except Exception as e:
                                    print(f"⚠️ خطا در بروزرسانی job شروع خودکار برای ادمین {admin_id}: {e}")
                            if Datas.admin:
                                await setup_auto_start_job(int(Datas.admin), start_hour, start_minute)
                    else:
                        await context.bot.send_message(chat_id=chatid, text="❌ خطا در ذخیره تعداد روزهای تکرار.", reply_to_message_id=user.message_id)
                except ValueError:
                    await context.bot.send_message(chat_id=chatid, text="❌ لطفاً یک عدد معتبر وارد کنید.\nمثال: <code>365</code>", reply_to_message_id=user.message_id, parse_mode='HTML')
            elif status[1] == 1:
                print(f"✅ [mainMenu] پردازش slimit برای کاربر {chatid}")
                curd.editLimit(newLimit=user.text, chatid=chatid)
                curd.setStatus(q="slimit", v=0, chatid=chatid)
                txt = f"🔎 سقف تعداد اگهی برای نردبان روزانه به  <code>{str(user.text)}</code> تنظیم گردید. ✅"
                await context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                 parse_mode='HTML')
            elif status[0] == 1:
                print(f"✅ [mainMenu] پردازش slogin برای کاربر {chatid}")
                curd.setStatus(q="slogin", v=user.text, chatid=chatid)
                divarApi.login(phone=user.text)
                curd.setStatus(q="scode", v=1, chatid=chatid)
                txt = f"🔎 کد با موفقیت به شماره <code>{str(user.text)}</code>ارسال شد ، لطفا کد را ارسال کنید :  ✅"
                await context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                 parse_mode='HTML')
            elif status[2] == 1:
                print(f"✅ [mainMenu] پردازش scode برای کاربر {chatid}")
                cookie = divarApi.verifyOtp(phone=status[0], code=user.text)
                if cookie['token']:
                    if curd.addLogin(phone=status[0], cookie=cookie['token'], chatid=chatid) == 0:
                        curd.updateLogin(phone=status[0], cookie=cookie['token'])
                    curd.setStatus(q="scode", v=0, chatid=chatid)
                    curd.setStatus(q="slogin", v=0, chatid=chatid)
                    txtr = f"✅ ورود به شماره {str(status[0])} موفقیت آمیز بود ."
                else:
                    txtr = str(cookie)
                await context.bot.send_message(chat_id=chatid, text=txtr, reply_to_message_id=user.message_id,
                                 parse_mode='HTML')
            else:
                print(f"⚠️ [mainMenu] کاربر {chatid} ادمین است اما هیچ status فعالی ندارد - پیام ارسال نمی‌شود")
        else:
            # بررسی مجدد برای اطمینان از اینکه کاربر واقعاً ادمین نیست
            final_check = isAdmin(chatid)
            if final_check:
                print(f"⚠️ [mainMenu] کاربر {chatid} در بررسی مجدد ادمین تشخیص داده شد - پیام خطا ارسال نمی‌شود")
                return
            
            print(f"❌ [mainMenu] کاربر {chatid} ادمین نیست - ارسال پیام خطا")
            await context.bot.send_message(chat_id=chatid, text="شما مجاز به استفاده از ربات نمیباشید .")
    except Exception as e:
        print(f"❌ خطا در تابع mainMenu: {e}")
        import traceback
        traceback.print_exc()
        try:
            await context.bot.send_message(chat_id=chatid, 
                                   text="❌ خطایی در پردازش پیام شما رخ داد.")
        except:
            pass

async def qrycall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔍 [qrycall] تابع qrycall فراخوانی شد")
    try:
        qry: CallbackQuery = update.callback_query
        if not qry:
            print("⚠️ [qrycall] callback_query None است")
            return
        
        chatid = qry.from_user.id
        data = qry.data
        
        print(f"🔍 [qrycall] دریافت callback query: chatid={chatid}, data={data}")
        
        if data == "reqAdmin":
            dataReq = qry.from_user
            txtReq = f"🗣 کاربری با چت آیدی {str(dataReq.id)} و نام {dataReq.full_name}  برای ربات شما درخواست ادمینی دارد ، آیا تایید میکنید ؟"
            btnadmin = [[InlineKeyboardButton('تایید', callback_data=f'admin:{str(dataReq.id)}')]]
            try:
                await context.bot.send_message(chat_id=Datas.admin, text=txtReq, reply_markup=InlineKeyboardMarkup(btnadmin))
            except:
                txtResult = "مشکلی در ارسال درخواست وجود دارد ."
            else:
                txtResult = "درخواست شما برای ادمین ارسال شد ، منتظر تایید آن باشید !"
            await qry.answer(text=txtResult, show_alert=True)
            return  # خروج از تابع بعد از پردازش reqAdmin
        
        # بررسی ادمین بودن برای سایر callback ها
        print(f"🔍 [qrycall] بررسی ادمین بودن برای chatid={chatid}, data={data}")
        is_admin = isAdmin(chatid)
        print(f"🔍 [qrycall] نتیجه isAdmin: {is_admin}")
        if not is_admin:
            print(f"❌ [qrycall] کاربر {chatid} ادمین نیست - فقط پاسخ callback (بدون پیام خطا)")
            # فقط پاسخ callback بده، بدون نمایش alert
            try:
                await qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            return
        print(f"✅ [qrycall] کاربر {chatid} ادمین است - ادامه پردازش")
        
        # اگر ادمین است، پردازش callback ها
        if data == "stats_info":
            # دریافت آمار به‌روز شده از دیتابیس (همیشه به‌روز است)
            print(f"📊 [stats_info] دریافت آمار به‌روز برای کاربر {chatid}")
            stats = curd.getStats(chatid=chatid)
            print(f"📊 [stats_info] آمار دریافت شده: نردبان={stats['total_nardeban']}, کل={stats['total_tokens']}, انتظار={stats['total_pending']}")
            
            # ساخت پیام با آمار هر لاگین
            stats_msg = "📊 <b>آمار کامل اگهی‌های شما</b>\n\n"
            
            # آمار هر لاگین
            if stats['login_stats']:
                for login_stat in stats['login_stats']:
                    stats_msg += f"📱 <b>شماره {login_stat['phone']}:</b>\n"
                    stats_msg += f"   ✅ نردبان شده: <b>{login_stat['nardeban_count']}</b>\n"
                    stats_msg += f"   📦 کل استخراج: <b>{login_stat['total_tokens']}</b>\n"
                    stats_msg += f"   ⏳ در انتظار: <b>{login_stat['pending_count']}</b>\n"
                    if login_stat.get('failed_count', 0) > 0:
                        stats_msg += f"   ❌ ناموفق: <b>{login_stat['failed_count']}</b>\n"
                    stats_msg += "\n"
            else:
                stats_msg += "⚠️ هیچ لاگینی ثبت نشده است.\n\n"
            
            # جمع کل
            stats_msg += "━━━━━━━━━━━━━━━━\n"
            stats_msg += f"📊 <b>جمع کل:</b>\n"
            stats_msg += f"   ✅ نردبان شده: <b>{stats['total_nardeban']}</b>\n"
            stats_msg += f"   📦 کل استخراج: <b>{stats['total_tokens']}</b>\n"
            stats_msg += f"   ⏳ در انتظار: <b>{stats['total_pending']}</b>\n"
            if stats.get('total_failed', 0) > 0:
                stats_msg += f"   ❌ ناموفق: <b>{stats['total_failed']}</b>"
            
            # ساخت منوی فرعی برای آمار
            stats_menu_buttons = [
                [InlineKeyboardButton('📋 لیست اگهی‌ها', callback_data='listAds')],
                [InlineKeyboardButton('🔙 بازگشت به آمار', callback_data='stats_menu')]
            ]
            
            # ساخت InlineKeyboardMarkup
            keyboard_markup = InlineKeyboardMarkup(stats_menu_buttons)
            print(f"🔍 [stats_info] InlineKeyboardMarkup ساخته شد با {len(stats_menu_buttons)} ردیف دکمه")
            print(f"🔍 [stats_info] دکمه 1: {stats_menu_buttons[0][0].text} - callback_data: {stats_menu_buttons[0][0].callback_data}")
            print(f"🔍 [stats_info] دکمه 2: {stats_menu_buttons[1][0].text} - callback_data: {stats_menu_buttons[1][0].callback_data}")
            print(f"🔍 [stats_info] keyboard_markup type: {type(keyboard_markup)}")
            print(f"🔍 [stats_info] keyboard_markup.inline_keyboard: {keyboard_markup.inline_keyboard}")
            print(f"🔍 [stats_info] طول پیام آمار: {len(stats_msg)} کاراکتر")
            
            # پاسخ به callback (فقط یک بار)
            try:
                await qry.answer()  # پاسخ به callback
                print(f"✅ [stats_info] پاسخ callback با موفقیت ارسال شد")
            except Exception as e:
                print(f"⚠️ [stats_info] خطا در پاسخ به callback: {e}")
            
            # ویرایش پیام منو به پیام آمار با دکمه‌ها
            try:
                print(f"🔍 [stats_info] در حال ویرایش پیام با reply_markup...")
                print(f"🔍 [stats_info] qry.message موجود است: {qry.message is not None}")
                if qry.message:
                    print(f"🔍 [stats_info] qry.message.message_id: {qry.message.message_id}")
                    print(f"🔍 [stats_info] qry.message.chat.id: {qry.message.chat.id}")
                
                # استفاده از context.bot.edit_message_text برای اطمینان از کارکرد صحیح
                edited_message = await context.bot.edit_message_text(
                    chat_id=chatid,
                    message_id=qry.message.message_id,
                    text=stats_msg,
                    parse_mode='HTML',
                    reply_markup=keyboard_markup
                )
                print(f"✅ [stats_info] پیام آمار با دکمه‌ها برای کاربر {chatid} ویرایش شد")
                print(f"🔍 [stats_info] edited_message.reply_markup موجود است: {edited_message.reply_markup is not None if edited_message else False}")
                if edited_message and edited_message.reply_markup:
                    print(f"🔍 [stats_info] تعداد دکمه‌ها در reply_markup: {len(edited_message.reply_markup.inline_keyboard)}")
                    for i, row in enumerate(edited_message.reply_markup.inline_keyboard):
                        print(f"🔍 [stats_info] ردیف {i+1}: {len(row)} دکمه")
                        for j, btn in enumerate(row):
                            print(f"🔍 [stats_info]   دکمه {j+1}: {btn.text} - {btn.callback_data}")
            except Exception as e:
                print(f"⚠️ [stats_info] خطا در ویرایش پیام: {e}")
                import traceback
                traceback.print_exc()
                # اگر ویرایش موفق نبود، پیام جدید ارسال کن
                try:
                    print(f"🔍 [stats_info] تلاش برای ارسال پیام جدید...")
                    result = await context.bot.send_message(
                        chat_id=chatid,
                        text=stats_msg,
                        parse_mode='HTML',
                        reply_markup=keyboard_markup
                    )
                    print(f"✅ [stats_info] پیام آمار جدید با دکمه‌ها برای کاربر {chatid} ارسال شد. Message ID: {result.message_id}")
                    print(f"🔍 [stats_info] result.reply_markup موجود است: {result.reply_markup is not None}")
                    if result.reply_markup:
                        print(f"🔍 [stats_info] تعداد دکمه‌ها در reply_markup: {len(result.reply_markup.inline_keyboard)}")
                        for i, row in enumerate(result.reply_markup.inline_keyboard):
                            print(f"🔍 [stats_info] ردیف {i+1}: {len(row)} دکمه")
                            for j, btn in enumerate(row):
                                print(f"🔍 [stats_info]   دکمه {j+1}: {btn.text} - {btn.callback_data}")
                except Exception as e2:
                    print(f"❌ [stats_info] خطا در ارسال پیام جدید: {e2}")
                    import traceback
                    traceback.print_exc()
        elif data == "listAds":
            # نمایش لیست اگهی‌ها با لینک کامل
            try:
                try:
                    await qry.answer()
                except Exception as e:
                    print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
                
                # دریافت تمام توکن‌های pending از JSON
                all_pending = get_all_pending_tokens_from_json(chatid=chatid)
                
                if not all_pending:
                    await context.bot.send_message(
                        chat_id=chatid,
                        text="⚠️ هیچ اگهی pending برای نمایش وجود ندارد."
                    )
                    return
                
                # دریافت شماره‌های تلفن برای نمایش
                phone_numbers = curd.get_phone_numbers_by_chatid(chatid=chatid)
                # تبدیل به int برای تطابق
                phone_dict = {int(phone): [] for phone in phone_numbers}
                
                # گروه‌بندی توکن‌ها بر اساس شماره تلفن
                for phone, token in all_pending:
                    phone_int = int(phone) if not isinstance(phone, int) else phone
                    if phone_int in phone_dict:
                        phone_dict[phone_int].append(token)
                
                # ساخت پیام با لینک کامل هر اگهی
                message = "📋 <b>لیست اگهی‌های شما:</b>\n\n"
                
                total_count = 0
                for phone, tokens in phone_dict.items():
                    if tokens:
                        message += f"📱 <b>شماره {phone}:</b>\n"
                        for idx, token in enumerate(tokens, 1):
                            ad_link = f"https://divar.ir/v/{token}"
                            message += f"   {idx}. <a href='{ad_link}'>🔗 اگهی {token[:8]}...</a>\n"
                        message += f"   <b>تعداد: {len(tokens)} اگهی</b>\n\n"
                        total_count += len(tokens)
                
                message += f"━━━━━━━━━━━━━━━━\n"
                message += f"📊 <b>جمع کل: {total_count} اگهی</b>"
                
                # اگر پیام خیلی طولانی است، آن را تقسیم کن
                if len(message) > 4096:
                    # تقسیم پیام به چند بخش
                    parts = []
                    current_part = "📋 <b>لیست اگهی‌های شما:</b>\n\n"
                    
                    for phone, tokens in phone_dict.items():
                        if tokens:
                            phone_section = f"📱 <b>شماره {phone}:</b>\n"
                            for idx, token in enumerate(tokens, 1):
                                ad_link = f"https://divar.ir/v/{token}"
                                phone_section += f"   {idx}. <a href='{ad_link}'>🔗 اگهی {token[:8]}...</a>\n"
                            phone_section += f"   <b>تعداد: {len(tokens)} اگهی</b>\n\n"
                            
                            if len(current_part) + len(phone_section) > 4000:
                                parts.append(current_part)
                                current_part = phone_section
                            else:
                                current_part += phone_section
                    
                    if current_part:
                        current_part += f"━━━━━━━━━━━━━━━━\n"
                        current_part += f"📊 <b>جمع کل: {total_count} اگهی</b>"
                        parts.append(current_part)
                    
                    # ارسال هر بخش
                    for part in parts:
                        await context.bot.send_message(
                            chat_id=chatid,
                            text=part,
                            parse_mode='HTML',
                            disable_web_page_preview=False
                        )
                else:
                    await context.bot.send_message(
                        chat_id=chatid,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                
                print(f"✅ [listAds] لیست اگهی‌ها برای کاربر {chatid} ارسال شد ({total_count} اگهی)")
            except Exception as e:
                print(f"❌ [listAds] خطا در نمایش لیست اگهی‌ها: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await context.bot.send_message(
                        chat_id=chatid,
                        text="❌ خطا در نمایش لیست اگهی‌ها."
                    )
                except:
                    pass
        elif data == "checkRenewal":
            await qry.answer(text="در حال بررسی آگهی‌های نیازمند تمدید...", show_alert=False)
            await report_ads_needing_renewal(chatid=chatid)
        elif data == "renewNeedAds":
            await qry.answer(text="در حال تمدید آگهی‌های نزدیک به انقضا...", show_alert=False)
            await renew_need_ads(chatid=chatid)
        elif data == "reExtract":
            # استخراج مجدد اگهی‌ها برای تمام لاگین‌های فعال
            await qry.answer(text="در حال استخراج مجدد اگهی‌ها...", show_alert=False)
            await reExtractTokens(chatid=chatid)
        elif data == "resetTokens":
            await qry.answer(text="ریست همه استخراج‌ها...", show_alert=False)
            await resetAllExtractions(chatid=chatid)
            await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
        elif data == "setNardebanType":
            # نمایش منوی انتخاب نوع نردبان
            mngDetail = curd.getManage(chatid=chatid)
            current_type = mngDetail[3] if len(mngDetail) > 3 else 1
            
            type_buttons = [
                [InlineKeyboardButton(f"{'✅' if current_type == 1 else '⚪'} 1️⃣ ترتیبی کامل هر لاگین", callback_data='nardebanType:1')],
                [InlineKeyboardButton(f"{'✅' if current_type == 2 else '⚪'} 2️⃣ تصادفی", callback_data='nardebanType:2')],
                [InlineKeyboardButton(f"{'✅' if current_type == 3 else '⚪'} 3️⃣ ترتیبی نوبتی", callback_data='nardebanType:3')],
                [InlineKeyboardButton(f"{'✅' if current_type == 4 else '⚪'} 🎢 4️⃣ جریان طبیعی", callback_data='nardebanType:4')],
                [InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')]
            ]
            
            try:
                await qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            
            type_info_text = """⚙️ <b>انتخاب نوع نردبان</b>

<b>1️⃣ ترتیبی کامل هر لاگین:</b>
   هر لاگین → همه آگهی‌هاش کامل نردبان می‌شود → بعد لاگین بعدی

<b>2️⃣ تصادفی:</b>
   در هر بار اجرای ربات، یک آگهی کاملاً تصادفی از بین همه لاگین‌ها انتخاب و نردبان می‌شود

<b>3️⃣ ترتیبی نوبتی:</b>
   از هر لاگین فقط یک آگهی → می‌ره سراغ لاگین بعدی → دوباره برمی‌گرده تا همه آگهی‌ها تمام شوند

<b>🎢 4️⃣ جریان طبیعی:</b>
   آگهی‌های قدیمی‌تر اولویت می‌گیرند
   آگهی‌هایی که بازدید کمتر دارند زودتر نردبان می‌شوند
   فاصله زمانی بین نردبان‌ها کاملاً نامنظم است"""
            
            await context.bot.send_message(
                chat_id=chatid,
                text=type_info_text,
                reply_markup=InlineKeyboardMarkup(type_buttons),
                parse_mode='HTML'
            )
        elif data.startswith("nardebanType:"):
            # تنظیم نوع نردبان
            nardeban_type = int(data.split(":")[1])
            curd.setStatusManage(q="nardeban_type", v=nardeban_type, chatid=chatid)
            
            type_names = {1: "ترتیبی کامل", 2: "تصادفی", 3: "ترتیبی نوبتی", 4: "جریان طبیعی"}
            await qry.answer(text=f"نوع نردبان به {type_names[nardeban_type]} تغییر یافت", show_alert=True)
            if qry.message:
                await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
            else:
                await send_admin_menu(chat_id=chatid)
        elif data == "backToMenu":
            try:
                await qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            if qry.message:
                await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
            else:
                await send_admin_menu(chat_id=chatid)
        elif data == "refreshMenu":
            try:
                await qry.answer(text="منو بروزرسانی شد ✅", show_alert=False)
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            if qry.message:
                await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
            else:
                await send_admin_menu(chat_id=chatid)
        
        # زیرمنوهای جدید
        elif data == "stats_menu":
            await qry.answer()
            stats_buttons = [
                [InlineKeyboardButton('📊 مشاهده آمار کامل', callback_data='stats_info')],
                [InlineKeyboardButton('📋 لیست اگهی‌ها', callback_data='listAds')],
                [InlineKeyboardButton('🧭 آگهی‌های نیاز به تمدید', callback_data='checkRenewal')],
                [InlineKeyboardButton('🔙 بازگشت به منو اصلی', callback_data='backToMenu')]
            ]
            await context.bot.edit_message_text(
                chat_id=chatid,
                message_id=qry.message.message_id,
                text="📊 <b>آمار و گزارشات</b>\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(stats_buttons),
                parse_mode='HTML'
            )
        
        elif data == "settings_menu":
            await qry.answer()
            mngDetail = curd.getManage(chatid=chatid)
            interval_minutes = mngDetail[1] if len(mngDetail) > 1 and mngDetail[1] is not None else 30
            
            # نوع نردبان
            nardeban_type = mngDetail[3] if len(mngDetail) > 3 else 1
            type_names = {1: "ترتیبی", 2: "تصادفی", 3: "نوبتی", 4: "طبیعی"}
            type_name = type_names.get(nardeban_type, "نامشخص")
            
            # زمان شروع و توقف
            start_time = get_start_time_from_config()
            stop_time = get_stop_time_from_config()
            start_time_text = f"{start_time[0]:02d}:{start_time[1]:02d}" if start_time else "تنظیم نشده"
            stop_time_text = f"{stop_time[0]:02d}:{stop_time[1]:02d}" if stop_time else "تنظیم نشده"
            
            settings_buttons = [
                [
                    InlineKeyboardButton(f'⏱️ فاصله: {interval_minutes} دقیقه', callback_data='setInterval'),
                    InlineKeyboardButton(f'⚙️ نوع: {type_name}', callback_data='setNardebanType')
                ],
                [
                    InlineKeyboardButton(f'▶️ شروع: {start_time_text}', callback_data='setStartHour'),
                    InlineKeyboardButton(f'🕐 توقف: {stop_time_text}', callback_data='setStopHour')
                ],
                [InlineKeyboardButton('📅 تنظیم روزهای فعال', callback_data='setWeekdays')],
                [InlineKeyboardButton('🔙 بازگشت به منو اصلی', callback_data='backToMenu')]
            ]
            await context.bot.edit_message_text(
                chat_id=chatid,
                message_id=qry.message.message_id,
                text="⚙️ <b>تنظیمات ربات</b>\n\nتنظیمات مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(settings_buttons),
                parse_mode='HTML'
            )
        
        elif data == "advanced_menu":
            await qry.answer()
            advanced_buttons = [
                [InlineKeyboardButton('🔄 استخراج مجدد', callback_data='reExtract')],
                [InlineKeyboardButton('♻️ تمدید آگهی‌های نیازمند', callback_data='renewNeedAds')],
                [InlineKeyboardButton('♻️ ریست کامل استخراج‌ها', callback_data='resetTokens')],
                [InlineKeyboardButton('🔙 بازگشت به منو اصلی', callback_data='backToMenu')]
            ]
            await context.bot.edit_message_text(
                chat_id=chatid,
                message_id=qry.message.message_id,
                text="🔧 <b>عملیات پیشرفته</b>\n\n⚠️ این عملیات با احتیاط انجام دهید:",
                reply_markup=InlineKeyboardMarkup(advanced_buttons),
                parse_mode='HTML'
            )
        elif data == "help_menu":
            try:
                await qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            help_text = (
                "📘 <b>راهنمای سریع مدیریت ربات</b>\n\n"
                "🔹 <b>روشن/خاموش</b>: فعال یا غیرفعال کردن تمام عملیات نردبان.\n"
                "🔹 <b>آمار کامل</b>: مشاهده وضعیت هر لاگین و اگهی‌ها.\n"
                "🔹 <b>مدیریت لاگین‌ها</b>: افزودن، حذف یا بروزرسانی کوکی‌ها.\n"
                "🔹 <b>سقف نردبان</b>: تعیین تعداد نردبان روزانه برای هر لاگین.\n"
                "🔹 <b>نوع نردبان</b>: انتخاب استراتژی اجرای نردبان.\n"
                "🔹 <b>استخراج مجدد</b>: دریافت لیست جدید اگهی‌ها از دیوار.\n"
                "🔹 <b>توقف نردبان</b>: لغو job فعال و ریست شمارنده‌ها.\n\n"
                "برای بازگشت به منوی اصلی، گزینه زیر را انتخاب کنید."
            )
            help_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')]
            ])
            if qry.message:
                await context.bot.edit_message_text(
                    chat_id=chatid,
                    message_id=qry.message.message_id,
                    text=help_text,
                    reply_markup=help_keyboard,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(chat_id=chatid, text=help_text, reply_markup=help_keyboard, parse_mode='HTML')
        elif data == "manageAdmins":
            # فقط ادمین پیش‌فرض می‌تواند ادمین‌ها را مدیریت کند
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            if chatid != admin_int:
                await qry.answer(text="❌ فقط ادمین پیش‌فرض می‌تواند ادمین‌ها را مدیریت کند!", show_alert=True)
                return
            
            adminsChatids = curd.getAdmins()
            newKeyAdmins = []
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            
            # اضافه کردن ادمین پیش‌فرض به لیست (با علامت ⭐ و غیرقابل حذف)
            if admin_int:
                newKeyAdmins.append(
                    [
                        InlineKeyboardButton(f'⭐ {str(admin_int)} (پیش‌فرض)', callback_data='none'),
                        InlineKeyboardButton('🔒', callback_data='none')
                    ]
                )
            
            # اضافه کردن سایر ادمین‌ها
            if adminsChatids:
                for admin in adminsChatids:
                    admin_id_int = int(admin)
                    # اگر ادمین پیش‌فرض نبود، به لیست اضافه کن
                    if admin_id_int != admin_int:
                        newKeyAdmins.append(
                            [
                                InlineKeyboardButton(f'🗣 {str(admin)}', callback_data='none'),
                                InlineKeyboardButton('❌', callback_data=f'delAdmin:{str(admin)}')
                            ]
                        )
            
            if newKeyAdmins:
                try:
                    qry.answer()  # پاسخ به callback
                except Exception as e:
                    print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
                
                # اضافه کردن دکمه بازگشت
                newKeyAdmins.append([InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')])
                
                admin_text = "👥 <b>مدیریت ادمین‌ها</b>\n\n"
                admin_text += "⭐ = ادمین پیش‌فرض (غیرقابل حذف)\n"
                admin_text += "🗣 = ادمین عادی\n"
                admin_text += "❌ = حذف ادمین"
                
                await context.bot.send_message(
                    chat_id=chatid,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup(newKeyAdmins),
                    parse_mode='HTML'
                )
            else:
                await qry.answer(text="هیچ ادمینی وجود ندارد.", show_alert=True)
        elif data.startswith("setactive"):
            value = data.split(":")[1]
            if value == "1":
                curd.setStatusManage(q="active", v=1, chatid=chatid)
                status_msg = "✅ ربات روشن شد"
            else:
                curd.setStatusManage(q="active", v=0, chatid=chatid)
                status_msg = "❌ ربات خاموش شد"
            
            try:
                await qry.answer(text=status_msg, show_alert=False)
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            
            if qry.message:
                await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
            else:
                await send_admin_menu(chat_id=chatid)
        elif data.startswith("delAdmin"):
            # فقط ادمین پیش‌فرض می‌تواند ادمین حذف کند
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            if chatid != admin_int:
                await qry.answer(text="❌ فقط ادمین پیش‌فرض می‌تواند ادمین حذف کند!", show_alert=True)
                return
            
            adminID = int(data.split(":")[1])
            # بررسی اینکه آیا این ادمین پیش‌فرض است یا نه
            if adminID == admin_int:
                txtResult = "❌ نمی‌توانید ادمین پیش‌فرض را حذف کنید!"
                await qry.answer(text=txtResult, show_alert=True)
            else:
                if curd.remAdmin(chatid=adminID) == 1:
                    txtResult = "کاربر مورد نظر با موفقیت از لیست ادمین ها حذف شد ."
                    try:
                        await context.bot.send_message(chat_id=adminID,
                                         text="متاسفانه شما از لیست ادمین های ربات خارج شدید !")
                    except:
                        pass
                else:
                    txtResult = "مشکلی در حذف کردن کاربر وجود دارد ."
                await qry.answer(text=txtResult, show_alert=True)
        elif data.startswith("admin"):
            # فقط ادمین پیش‌فرض می‌تواند ادمین اضافه کند
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            if chatid != admin_int:
                await qry.answer(text="❌ فقط ادمین پیش‌فرض می‌تواند ادمین اضافه کند!", show_alert=True)
                return
            
            newAdminChatID = int(data.split(":")[1])
            if curd.setAdmin(chatid=newAdminChatID) == 1:
                txtResult = "کاربر مورد نظر با موفقیت به لیست ادمین ها اضافه شد ."
                try:
                    await context.bot.send_message(chat_id=newAdminChatID, text="شما با موفقیت به لیست ادمین های ربات اضافه شدید برای فعال سازی لطفا /start را بزنید.")
                except:
                    pass
            else:
                txtResult = "مشکلی در اضافه کردن کاربر وجود دارد ."
            await qry.answer(text=txtResult, show_alert=True)
        elif data.startswith("del"):
            if curd.delLogin(phone=data.split(":")[1]) == 1:
                await qry.answer(text="با موفقیت حذف شد")
            else:
                await qry.answer(text="مشکلی در حذف شدن وحود دارد")
        elif data.startswith("update"):
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            phoneL = data.split(":")[1]
            curd.setStatus(q="slogin", v=phoneL, chatid=chatid)
            divarApi.login(phone=phoneL)
            curd.setStatus(q="scode", v=1, chatid=chatid)
            txt = f"🔎 کد با موفقیت به شماره <code>{str(phoneL)}</code>ارسال شد ، لطفا کد را ارسال کنید :  ✅"
            await context.bot.send_message(chat_id=qry.message.chat.id, text=txt, parse_mode='HTML')
        elif data == "setInterval":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            # استفاده از scode=2 به عنوان flag برای تنظیم interval
            curd.setStatus(q="scode", v=2, chatid=chatid)
            await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً یک عدد برای تعیین فاصله بین نردبان‌ها (به دقیقه) ارسال کنید : ")
        elif data == "setStartHour":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            # استفاده از scode=4 به عنوان flag برای تنظیم start_time
            curd.setStatus(q="scode", v=4, chatid=chatid)
            await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً ساعت شروع خودکار را وارد کنید:\n\n📌 فرمت: <code>ساعت:دقیقه</code>\nمثال: <code>8:30</code> یا <code>14:15</code>\n\nیا فقط ساعت: <code>8</code>")
        elif data == "setStopHour":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            # استفاده از scode=3 به عنوان flag برای تنظیم stop_time
            curd.setStatus(q="scode", v=3, chatid=chatid)
            await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً ساعت توقف خودکار را وارد کنید:\n\n📌 فرمت: <code>ساعت:دقیقه</code>\nمثال: <code>22:30</code> یا <code>14:15</code>\n\nیا فقط ساعت: <code>22</code>", parse_mode='HTML')
        elif data == "setRepeatDays":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            # استفاده از scode=5 به عنوان flag برای تنظیم repeat_days
            curd.setStatus(q="scode", v=5, chatid=chatid)
            await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً تعداد روزهای تکرار را وارد کنید:\n\n📌 مثال: <code>365</code> (برای یک سال)\nیا <code>30</code> (برای یک ماه)")
        elif data == "setWeekdays":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            
            # نمایش منوی انتخاب روزهای هفته
            active_weekdays = get_active_weekdays_from_config()
            weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
            weekday_short = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']
            
            buttons = []
            for i, (name, short) in enumerate(zip(weekday_names, weekday_short)):
                is_active = i in active_weekdays
                emoji = "✅" if is_active else "⚪"
                buttons.append([
                    InlineKeyboardButton(
                        f"{emoji} {name} ({short})",
                        callback_data=f"toggleWeekday:{i}"
                    )
                ])
            
            buttons.append([InlineKeyboardButton('✅ تایید', callback_data='confirmWeekdays')])
            buttons.append([InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')])
            
            text = "📅 <b>انتخاب روزهای فعال هفته</b>\n\n"
            text += "روزهایی که می‌خواهید jobهای خودکار فعال باشند را انتخاب کنید:\n\n"
            text += "✅ = فعال\n⚪ = غیرفعال"
            
            await context.bot.send_message(
                chat_id=chatid,
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='HTML'
            )
        elif data.startswith("toggleWeekday:"):
            # تغییر وضعیت یک روز هفته
            try:
                weekday_index = int(data.split(":")[1])
                active_weekdays = get_active_weekdays_from_config()
                
                if weekday_index in active_weekdays:
                    # حذف از لیست
                    active_weekdays = [d for d in active_weekdays if d != weekday_index]
                else:
                    # اضافه به لیست
                    active_weekdays.append(weekday_index)
                
                # بررسی اینکه حداقل یک روز فعال باشد
                if not active_weekdays:
                    try:
                        await qry.answer(text="❌ حداقل یک روز باید فعال باشد!", show_alert=True)
                    except:
                        pass
                    return
                
                # ذخیره موقت (برای نمایش در منو)
                set_active_weekdays_in_config(active_weekdays)
                
                # نمایش مجدد منو با وضعیت جدید
                weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
                weekday_short = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']
                
                buttons = []
                for i, (name, short) in enumerate(zip(weekday_names, weekday_short)):
                    is_active = i in active_weekdays
                    emoji = "✅" if is_active else "⚪"
                    buttons.append([
                        InlineKeyboardButton(
                            f"{emoji} {name} ({short})",
                            callback_data=f"toggleWeekday:{i}"
                        )
                    ])
                
                buttons.append([InlineKeyboardButton('✅ تایید', callback_data='confirmWeekdays')])
                buttons.append([InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')])
                
                text = "📅 <b>انتخاب روزهای فعال هفته</b>\n\n"
                text += "روزهایی که می‌خواهید jobهای خودکار فعال باشند را انتخاب کنید:\n\n"
                text += "✅ = فعال\n⚪ = غیرفعال"
                
                try:
                    await qry.answer()  # پاسخ به callback
                except:
                    pass
                
                await context.bot.edit_message_text(
                    chat_id=chatid,
                    message_id=qry.message.message_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"❌ خطا در toggleWeekday: {e}")
                try:
                    await qry.answer(text="❌ خطا در تغییر وضعیت روز", show_alert=True)
                except:
                    pass
        elif data == "confirmWeekdays":
            # تایید و بروزرسانی jobهای خودکار
            try:
                await qry.answer(text="✅ روزهای هفته تنظیم شد", show_alert=False)
            except:
                pass
            
            # بروزرسانی jobهای شروع خودکار
            start_time = get_start_time_from_config()
            if start_time is not None:
                start_hour, start_minute = start_time
                admins = curd.getAdmins()
                for admin_id in admins:
                    try:
                        await setup_auto_start_job(int(admin_id), start_hour, start_minute)
                    except Exception as e:
                        print(f"⚠️ خطا در بروزرسانی job شروع خودکار برای ادمین {admin_id}: {e}")
                if Datas.admin:
                    await setup_auto_start_job(int(Datas.admin), start_hour, start_minute)
            
            # بازگشت به منو
            if qry.message:
                await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
            else:
                await send_admin_menu(chat_id=chatid)
        elif data == "managelogin":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            
            txt, keyboard = format_login_management_menu(chat_id=chatid)
            try:
                await context.bot.send_message(chat_id=chatid, text=txt, reply_markup=keyboard, parse_mode='HTML')
            except Exception as e:
                print(f"❌ خطا در ارسال منوی مدیریت لاگین: {e}")
                import traceback
                traceback.print_exc()
                # سعی کن با bot_send_message ارسال کن
                await bot_send_message(chat_id=chatid, text=txt, reply_markup=keyboard, parse_mode='HTML')
        elif data == "addlogin":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            curd.setStatus(q="slogin", v=1, chatid=chatid)
            await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً شماره لاگین را وارد نمایید : ")
        elif data == "remJob":
            job_id = curd.getJob(chatid=chatid)
            if job_id:
                try:
                    # حذف job نردبان
                    scheduler.remove_job(job_id=job_id)
                    
                    # حذف job توقف خودکار مربوطه (اگر وجود داشته باشد)
                    try:
                        stop_job_id = f"auto_stop_{chatid}_{job_id}"
                        scheduler.remove_job(stop_job_id)
                    except:
                        pass  # اگر job توقف وجود نداشت، مشکلی نیست
                    
                    curd.removeJob(chatid=chatid)
                    refreshUsed(chatid=chatid)
                    txtResult = f"✅ عملیات نردبان با موفقیت متوقف شد."
                except Exception as e:
                    txtResult = f"❌ در غیرفعال‌سازی عملیات نردبان مشکلی وجود دارد:\n{str(e)}"
                    curd.removeJob(chatid=chatid)
                    print(f"❌ خطا در حذف job: {e}")
                    import traceback
                    traceback.print_exc()
                
                try:
                    await qry.answer()  # پاسخ به callback
                except Exception as e:
                    print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
                await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                                 text=txtResult)
                # بروزرسانی منو
                if qry.message:
                    await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
            else:
                await qry.answer(text="شما هیچ نردبان فعالی ندارید!", show_alert=True)
        elif data == "startJob":
            # بررسی اینکه آیا job فعالی وجود دارد
            job_id = curd.getJob(chatid=chatid)
            if job_id:
                await qry.answer(text="⚠️ شما یک نردبان فعال دارید!", show_alert=True)
                return
            
            # بررسی اینکه آیا دوره تکرار هنوز فعال است (هماهنگ با auto_start_nardeban)
            if not is_repeat_period_active():
                repeat_days = get_repeat_days_from_config()
                start_date = get_repeat_start_date_from_config()
                end_date = start_date + timedelta(days=repeat_days)
                await qry.answer(
                    text=f"❌ دوره تکرار به پایان رسیده است!\n\n📅 دوره: {start_date.strftime('%Y-%m-%d')} تا {end_date.strftime('%Y-%m-%d')}\n\nلطفاً تعداد روزهای تکرار را افزایش دهید.",
                    show_alert=True
                )
                return
            
            # بررسی اینکه آیا امروز یکی از روزهای فعال هفته است (هماهنگ با auto_start_nardeban)
            if not is_today_active_weekday():
                active_weekdays = get_active_weekdays_from_config()
                weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
                active_names = [weekday_names[d] for d in sorted(active_weekdays)]
                current_weekday_python = now_tehran().weekday()
                iran_weekday = (current_weekday_python + 2) % 7
                today_name = weekday_names[iran_weekday]
                await qry.answer(
                    text=f"❌ امروز ({today_name}) یکی از روزهای فعال هفته نیست!\n\n📅 روزهای فعال: {', '.join(active_names)}\n\nلطفاً روزهای هفته را تنظیم کنید یا منتظر یکی از روزهای فعال بمانید.",
                    show_alert=True
                )
                return
            
            # بررسی اینکه آیا ربات فعال است
            manageDetails = curd.getManage(chatid=chatid)
            if manageDetails[0] != 1:
                await qry.answer(text="❌ ابتدا ربات را فعال کنید!", show_alert=True)
                return
            
            # بررسی اینکه آیا لاگین فعالی وجود دارد
            logins = curd.getCookies(chatid=chatid)
            if not logins:
                await qry.answer(text="❌ هیچ لاگین فعالی وجود ندارد!", show_alert=True)
                return
            
            # بررسی اینکه آیا ساعت توقف خودکار در گذشته است (هماهنگ با auto_start_nardeban)
            if is_stop_time_in_past():
                stop_time_config = get_stop_time_from_config()
                if stop_time_config:
                    stop_hour, stop_minute = stop_time_config
                    await qry.answer(
                        text=f"❌ ساعت توقف خودکار ({stop_hour:02d}:{stop_minute:02d}) در گذشته است!\n\nلطفاً ساعت توقف را به آینده تنظیم کنید یا منتظر فردا بمانید.",
                        show_alert=True
                    )
                else:
                    await qry.answer(
                        text="❌ ساعت توقف خودکار تنظیم نشده است!",
                        show_alert=True
                    )
                return
            
            try:
                await qry.answer(text="در حال شروع نردبان...", show_alert=False)
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query: {e}")
            
            # دریافت ساعت و دقیقه توقف از configs.json یا استفاده از ساعت پیش‌فرض (هماهنگ با auto_start_nardeban)
            stop_time_config = get_stop_time_from_config()
            if stop_time_config is not None:
                end_hour, end_minute = stop_time_config
            else:
                # اگر تنظیم نشده باشد، از ساعت فعلی + 12 ساعت استفاده می‌کنیم
                current_hour = now_tehran().hour
                end_hour = (current_hour + 12) % 24
                end_minute = 0
            
            # شروع نردبان (همان منطق auto_start_nardeban)
            now_local = now_tehran()
            print(f"🚀 [startJob] شروع دستی نردبان برای کاربر {chatid} در ساعت {now_local.hour:02d}:{now_local.minute:02d}")
            await startNardebanDasti(chatid=chatid, end=end_hour)
            
            # بروزرسانی منو
            if qry.message:
                await send_admin_menu(chat_id=chatid, message_id=qry.message.message_id)
        elif data.startswith("status"):
            details = data.split(":")
            success, message = curd.activeLogin(phone=details[2], status=int(details[1]), chatid=chatid)

            txt, keyboard = format_login_management_menu(chat_id=chatid)
            bot = get_bot()
            if bot:
                try:
                    await bot.edit_message_text(
                        chat_id=chatid,
                        message_id=qry.message.message_id,
                        text=txt,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"⚠️ [status] خطا در ویرایش پیام مدیریت لاگین: {e}")
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=chatid,
                            message_id=qry.message.message_id,
                            reply_markup=keyboard
                        )
                    except Exception as inner_e:
                        print(f"⚠️ [status] خطا در به‌روزرسانی keyboard: {inner_e}")
            await qry.answer(text=message, show_alert=not success)
        else:
            # اگر هیچ callback match نکرد، فقط پاسخ بده (بدون پیام خطا)
            print(f"⚠️ [qrycall] هیچ handler برای data={data} پیدا نشد")
            try:
                await qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
    except Exception as e:
        print(f"❌ [qrycall] خطا در پردازش callback query: {e}")
        import traceback
        traceback.print_exc()
        # سعی نکن callback query قدیمی را answer کنی
        try:
            if update.callback_query:
                # فقط اگر خطا BadRequest نبود، answer کن
                if "too old" not in str(e).lower() and "timeout" not in str(e).lower():
                    update.callback_query.answer()
        except:
            pass

async def startNardebanDasti(chatid, end: int):
    await bot_send_message(chat_id=chatid, text="عملیات شروع شد")

    manageDetails = curd.getManage(chatid=chatid)  # 0 = Active , 1 = Limite Global
    logins = curd.getCookies(chatid=chatid)

    if not logins:
        await bot_send_message(chat_id=chatid, text="تمامی لاگین‌های شما غیرفعال است و نمی‌توانم نردبانی انجام دهم!")
        return

    has_pending = has_pending_tokens_in_json(chatid=chatid)
    
    if has_pending:
        all_pending = get_all_pending_tokens_from_json(chatid=chatid)
        pending_by_phone = {}
        for phone, token in all_pending:
            pending_by_phone.setdefault(phone, []).append(token)
        
        pending_info = "📋 استخراج‌های فرایند قبلی یافت شد:\n\n"
        for phone, tokens in pending_by_phone.items():
            pending_info += f"📱 شماره {phone}: {len(tokens)} اگهی pending\n"
        pending_info += "\n✅ نردبان از ادامه اگهی‌های قبلی شروع می‌شود."
        await bot_send_message(chat_id=chatid, text=pending_info)
    else:
        await bot_send_message(chat_id=chatid, text="🔄 هیچ اگهی pending از فرایند قبلی یافت نشد. در حال استخراج اولیه...")
        active_logins = [l for l in logins if l[2] == 0]
        if active_logins:
            for l in active_logins:
                try:
                    nardebanAPI = nardeban(apiKey=l[1])
                    brandToken = nardebanAPI.getBranToken()
                    
                    if not brandToken:
                        await bot_send_message(chat_id=chatid, text=f"❌ خطا در دریافت brand token برای شماره {l[0]}")
                        continue
                    
                    tokens = nardebanAPI.get_all_tokens(brand_token=brandToken)
                    
                    if tokens:
                        new_count = add_tokens_to_json(chatid=chatid, phone=int(l[0]), tokens=tokens)
                        
                        if new_count > 0:
                            existing_tokens = curd.get_tokens_by_phone(phone=int(l[0]))
                            new_tokens = [t for t in tokens if t not in existing_tokens]
                            if new_tokens:
                                curd.insert_tokens_by_phone(phone=int(l[0]), tokens=new_tokens)
                            
                            await bot_send_message(chat_id=chatid, text=f"✅ از شماره {l[0]}: {new_count} اگهی استخراج شد.")
                        else:
                            await bot_send_message(chat_id=chatid, text=f"ℹ️ از شماره {l[0]}: همه اگهی‌ها قبلاً استخراج شده بودند.")
                    else:
                        await bot_send_message(chat_id=chatid, text=f"⚠️ از شماره {l[0]}: هیچ اگهی‌ای یافت نشد.")
                        
                except Exception as e:
                    print(f"Error extracting tokens for phone {l[0]}: {e}")
                    await bot_send_message(chat_id=chatid, text=f"❌ خطا در استخراج برای شماره {l[0]}: {str(e)}")
            
            await bot_send_message(chat_id=chatid, text="✅ استخراج اولیه به پایان رسید.")
    
    # استفاده از فاصله تنظیم شده توسط کاربر
    interval_minutes = manageDetails[5] if len(manageDetails) > 5 else 5
    nardeban_type = manageDetails[3] if len(manageDetails) > 3 else 1
    
    # حذف job توقف خودکار قبلی (اگر وجود داشته باشد) - برای همه انواع
    try:
        all_jobs = scheduler.get_jobs() if scheduler else []
        for existing_job in all_jobs:
            if existing_job.id and f"auto_stop_{chatid}" in str(existing_job.id):
                try:
                    scheduler.remove_job(existing_job.id)
                except:
                    pass
    except Exception as e:
        print(f"⚠️ خطا در حذف job توقف قبلی: {e}")
    
    # استفاده از ساعت و دقیقه توقف از configs.json یا استفاده از end که از دستور /end آمده
    stop_time_config = get_stop_time_from_config()
    if stop_time_config is not None:
        final_stop_hour, final_stop_minute = stop_time_config
    else:
        final_stop_hour = end
        final_stop_minute = 0
    
    if nardeban_type == 4:
        await bot_send_message(chat_id=chatid, text="🎢 نوع نردبان: جریان طبیعی - زمان‌بندی نامنظم فعال است.")
        
        # برای نوع 4، یک job توقف خودکار تنظیم می‌کنیم (بدون job interval)
        # اما باید job_id را از دیتابیس بگیریم یا یک ID موقت بسازیم
        # در واقع برای نوع 4، job توقف باید job نردبان را متوقف کند
        # اما چون job interval نداریم، باید یک flag در دیتابیس ذخیره کنیم
        
        # ایجاد یک job توقف که فقط یک بار اجرا می‌شود (در ساعت توقف)
        # این job باید یک flag را تنظیم کند که sendNardeban آن را بررسی کند
        # یا می‌توانیم job توقف را به گونه‌ای تنظیم کنیم که فقط یک پیام بفرستد
        
        # برای سادگی، job توقف را تنظیم می‌کنیم که در ساعت مشخص شده یک پیام بفرستد
        # و کاربر می‌تواند دستی توقف کند
        stop_job_id = f"auto_stop_{chatid}_natural"
        
        # دریافت روزهای فعال هفته
        active_weekdays_iran = get_active_weekdays_from_config()
        active_weekdays_apscheduler = [(day + 2) % 7 for day in active_weekdays_iran]
        
        async def stop_natural_flow(chatid):
            """تابع برای توقف جریان طبیعی"""
            await bot_send_message(chat_id=chatid, text="🕐 ساعت توقف خودکار رسیده است. لطفاً در صورت نیاز دستی توقف کنید.")
        
        if len(active_weekdays_apscheduler) == 7:
            scheduler.add_job(
                stop_natural_flow,
                trigger="cron",
                args=[chatid],
                hour=final_stop_hour,
                minute=final_stop_minute,
                id=stop_job_id,
                replace_existing=True
            )
        else:
            scheduler.add_job(
                stop_natural_flow,
                trigger="cron",
                args=[chatid],
                hour=final_stop_hour,
                minute=final_stop_minute,
                day_of_week=active_weekdays_apscheduler,
                id=stop_job_id,
                replace_existing=True
            )
        
        await bot_send_message(chat_id=chatid, text=f"🕐 توقف خودکار در ساعت {final_stop_hour:02d}:{final_stop_minute:02d} تنظیم شد.")
        await sendNardeban(chatid)
    else:
        await bot_send_message(chat_id=chatid, text=f"⏱️ فاصله بین نردبان‌ها: {str(interval_minutes)} دقیقه")
        
        # ایجاد job نردبان
        job = scheduler.add_job(sendNardeban, "interval", args=[chatid], minutes=interval_minutes)
        curd.addJob(chatid=chatid, job=job.id)
        
        # ایجاد job توقف خودکار با ID منحصر به فرد
        stop_job_id = f"auto_stop_{chatid}_{job.id}"
        
        # دریافت روزهای فعال هفته برای job توقف (باید در همان روزهایی که شروع فعال است، توقف هم فعال باشد)
        active_weekdays_iran = get_active_weekdays_from_config()
        active_weekdays_apscheduler = [(day + 2) % 7 for day in active_weekdays_iran]
        
        # اگر همه روزها فعال هستند، day_of_week را تنظیم نکنیم
        if len(active_weekdays_apscheduler) == 7:
            scheduler.add_job(
                remJob,
                trigger="cron",
                args=[scheduler, job.id, chatid],
                hour=final_stop_hour,
                minute=final_stop_minute,
                id=stop_job_id,
                replace_existing=True
            )
        else:
            # توقف فقط در روزهایی که شروع فعال است
            scheduler.add_job(
                remJob,
                trigger="cron",
                args=[scheduler, job.id, chatid],
                hour=final_stop_hour,
                minute=final_stop_minute,
                day_of_week=active_weekdays_apscheduler,
                id=stop_job_id,
                replace_existing=True
            )
        
        await bot_send_message(chat_id=chatid, text=f"🕐 توقف خودکار در ساعت {final_stop_hour:02d}:{final_stop_minute:02d} تنظیم شد.")
        
        # اجرای اولین نردبان دقیقاً در زمان شروع برای جلوگیری از تاخیر یک دور کامل
        await sendNardeban(chatid)

def shouldExtractTokens(chatid, available_logins):
    """بررسی می‌کند که آیا باید استخراج انجام شود یا نه
    استخراج در موارد زیر انجام می‌شود:
    1. هیچ توکن pending وجود نداشته باشد
    2. هیچ توکن در JSON وجود نداشته باشد (اولین بار)
    3. یا اینکه همه توکن‌ها پردازش شده باشند (success/failed)
    """
    try:
        # چک کردن اینکه آیا توکن pending در JSON وجود دارد
        has_pending = has_pending_tokens_in_json(chatid=chatid)
        
        # اگر توکن pending وجود دارد، نیازی به استخراج نیست
        if has_pending:
            return False
        
        # بررسی وجود توکن‌ها در JSON
        tokens_data = load_tokens_json()
        if chatid not in tokens_data:
            # اولین بار - هیچ توکنی وجود ندارد
            print(f"ℹ️ [shouldExtractTokens] اولین استخراج برای chatid={chatid}")
            return True
        
        # شمارش توکن‌های موجود
        total_tokens = 0
        for phone_data in tokens_data[chatid].values():
            if isinstance(phone_data, dict):
                total_tokens += len(phone_data.get("pending", []))
                total_tokens += len(phone_data.get("success", []))
                total_tokens += len(phone_data.get("failed", []))
        
        # اگر هیچ توکنی وجود ندارد، استخراج کن
        if total_tokens == 0:
            print(f"ℹ️ [shouldExtractTokens] هیچ توکنی در JSON وجود ندارد، استخراج انجام می‌شود")
            return True
        
        # اگر توکن وجود دارد اما pending نیست، یعنی همه پردازش شده‌اند
        # در این حالت، تابع auto_reset_and_extract_if_all_done باید فراخوانی شود
        print(f"ℹ️ [shouldExtractTokens] توکن‌ها موجود اما pending نیست - نیاز به بررسی ریست")
        return False
        
    except Exception as e:
        print(f"Error in shouldExtractTokens: {e}")
        return False

async def extractTokensIfNeeded(chatid, available_logins):
    """استخراج توکن‌ها فقط در صورتی که همه اگهی‌ها نردبان شده باشند - بهینه‌سازی شده"""
    try:
        # بررسی اینکه آیا باید استخراج انجام شود
        if not shouldExtractTokens(chatid, available_logins):
            return
        
        # همه اگهی‌ها نردبان شده‌اند، حالا استخراج کن
        await bot_send_message(chat_id=chatid, text="✅ همه اگهی‌ها نردبان شدند. در حال استخراج مجدد...")
        
        # بهینه‌سازی: یک بار بارگذاری همه توکن‌های موجود از JSON
        tokens_data = load_tokens_json()
        all_existing_tokens = set()
        if chatid in tokens_data:
            for phone_data in tokens_data[chatid].values():
                if isinstance(phone_data, dict):
                    all_existing_tokens.update(phone_data.get("pending", []))
                    all_existing_tokens.update(phone_data.get("success", []))
                    all_existing_tokens.update(phone_data.get("failed", []))
        
        # جمع‌آوری پیام‌ها برای ارسال یکجا
        messages = []
        total_extracted = 0
        
        for l in available_logins:
            try:
                nardebanAPI = nardeban(apiKey=l[1])
                brandToken = nardebanAPI.getBranToken()
                
                if not brandToken:
                    messages.append(f"❌ شماره {l[0]}: خطا در دریافت brand token")
                    continue
                
                # استخراج توکن‌های جدید
                tokens = nardebanAPI.get_all_tokens(brand_token=brandToken)
                
                if tokens:
                    # فیلتر کردن توکن‌های جدید (بهینه‌سازی: استفاده از set)
                    new_tokens = [t for t in tokens if t not in all_existing_tokens]
                    
                    if new_tokens:
                        # ذخیره توکن‌ها در JSON
                        new_count = add_tokens_to_json(chatid=chatid, phone=int(l[0]), tokens=new_tokens)
                        
                        if new_count > 0:
                            # به‌روزرسانی set برای بررسی سریع‌تر در آینده
                            all_existing_tokens.update(new_tokens)
                            
                            # همچنین در دیتابیس هم ذخیره کن (برای سازگاری)
                            curd.insert_tokens_by_phone(phone=int(l[0]), tokens=new_tokens)
                            
                            total_extracted += new_count
                            messages.append(f"✅ شماره {l[0]}: {new_count} اگهی جدید")
                        else:
                            messages.append(f"ℹ️ شماره {l[0]}: همه اگهی‌ها قبلاً استخراج شده بودند")
                    else:
                        messages.append(f"ℹ️ شماره {l[0]}: همه اگهی‌ها قبلاً استخراج شده بودند")
                else:
                    messages.append(f"⚠️ شماره {l[0]}: هیچ اگهی‌ای یافت نشد")
                    
            except Exception as e:
                print(f"Error extracting tokens for phone {l[0]}: {e}")
                messages.append(f"❌ شماره {l[0]}: خطا - {str(e)[:50]}")
        
        # ارسال پیام‌های جمع‌آوری شده
        if messages:
            summary = "📊 <b>خلاصه استخراج:</b>\n\n" + "\n".join(messages)
            if total_extracted > 0:
                summary += f"\n\n✅ <b>جمع کل: {total_extracted} اگهی جدید استخراج شد</b>"
            await bot_send_message(chat_id=chatid, text=summary, parse_mode='HTML')
        else:
            await bot_send_message(chat_id=chatid, text="✅ استخراج اگهی‌ها به پایان رسید.")
    except Exception as e:
        print(f"Error in extractTokensIfNeeded: {e}")

async def trigger_extract_if_done(chatid):
    """اگر هیچ اگهی pending باقی نمانده باشد، بلافاصله استخراج مجدد را اجرا می‌کند"""
    try:
        if has_pending_tokens_in_json(chatid=chatid):
            return

        logins = curd.getCookies(chatid=chatid)
        if not logins:
            return

        await extractTokensIfNeeded(chatid, logins)
    except Exception as e:
        print(f"Error in trigger_extract_if_done: {e}")

def are_all_ads_processed(chatid):
    """
    بررسی می‌کند که آیا همه اگهی‌ها پردازش شده‌اند (نردبان شده یا failed)
    """
    try:
        # بررسی اینکه آیا هیچ اگهی pending وجود دارد
        has_pending = has_pending_tokens_in_json(chatid=chatid)
        if has_pending:
            return False
        
        # بررسی وجود اگهی‌های پردازش شده
        tokens_data = load_tokens_json()
        if chatid not in tokens_data:
            return False
        
        # شمارش اگهی‌های پردازش شده
        total_processed = 0
        for phone_data in tokens_data[chatid].values():
            if isinstance(phone_data, dict):
                total_processed += len(phone_data.get("success", []))
                total_processed += len(phone_data.get("failed", []))
        
        # اگر حداقل یک اگهی پردازش شده باشد و هیچ pending نباشد
        return total_processed > 0
        
    except Exception as e:
        print(f"Error in are_all_ads_processed: {e}")
        return False

async def auto_reset_and_extract_if_all_done(chatid):
    """
    بررسی می‌کند که آیا همه اگهی‌ها نردبان شده‌اند یا نه
    اگر همه نردبان شده باشند، فایل اگهی‌ها را ریست کرده و استخراج مجدد انجام می‌دهد
    """
    try:
        print(f"🔍 [auto_reset] بررسی وضعیت اگهی‌ها برای chatid={chatid}")
        
        # بررسی اینکه آیا همه اگهی‌ها پردازش شده‌اند
        if not are_all_ads_processed(chatid):
            print(f"ℹ️ [auto_reset] همه اگهی‌ها هنوز پردازش نشده‌اند، ریست انجام نمی‌شود")
            return False
        
        # شمارش اگهی‌های پردازش شده برای نمایش
        tokens_data = load_tokens_json()
        total_processed = 0
        if chatid in tokens_data:
            for phone_data in tokens_data[chatid].values():
                if isinstance(phone_data, dict):
                    total_processed += len(phone_data.get("success", []))
                    total_processed += len(phone_data.get("failed", []))
        
        print(f"✅ [auto_reset] همه اگهی‌ها ({total_processed}) پردازش شده‌اند. شروع ریست و استخراج مجدد...")
        
        # ارسال پیام اطلاع‌رسانی
        await bot_send_message(
            chat_id=chatid, 
            text=f"🔄 <b>ریست خودکار اگهی‌ها</b>\n\n"
                 f"✅ همه اگهی‌ها ({total_processed}) پردازش شدند\n"
                 f"🔄 در حال ریست فایل اگهی‌ها و استخراج مجدد...",
            parse_mode='HTML'
        )
        
        # ریست کامل توکن‌های این chatid از JSON
        reset_success = reset_tokens_for_chat(chatid)
        if not reset_success:
            print(f"❌ [auto_reset] خطا در ریست توکن‌ها از JSON")
            await bot_send_message(chat_id=chatid, text="❌ خطا در ریست فایل اگهی‌ها")
            return False
        
        # حذف توکن‌ها از دیتابیس نیز
        logins = curd.getCookies(chatid=chatid)
        if logins:
            for login in logins:
                phone = login[0]
                curd.delete_tokens_by_phone(phone=int(phone))
        
        # ریست شمارنده‌های استفاده
        curd.refreshUsed(chatid)
        
        print(f"✅ [auto_reset] ریست کامل انجام شد، شروع استخراج مجدد...")
        
        # استخراج مجدد اگهی‌ها
        if logins:
            await extractTokensIfNeeded(chatid, logins)
            
            # پس از استخراج مجدد، تمامی نردبان شده‌ها نیز ریست شود
            # ریست شمارنده‌های نردبان برای همه لاگین‌ها
            for login in logins:
                phone = login[0]
                curd.reset_nardeban_count(phone=int(phone))
            
            await bot_send_message(
                chat_id=chatid, 
                text="✅ <b>ریست و استخراج مجدد با موفقیت انجام شد</b>\n\n"
                     "🎯 اگهی‌های جدید آماده نردبان هستند\n"
                     "♻️ شمارنده‌های نردبان همه لاگین‌ها ریست شد",
                parse_mode='HTML'
            )
            return True
        else:
            await bot_send_message(chat_id=chatid, text="⚠️ هیچ لاگین فعالی برای استخراج مجدد یافت نشد")
            return False
            
    except Exception as e:
        print(f"❌ [auto_reset] خطا در auto_reset_and_extract_if_all_done: {e}")
        import traceback
        traceback.print_exc()
        await bot_send_message(chat_id=chatid, text=f"❌ خطا در ریست خودکار: {str(e)}")
        return False

async def sendNardeban(chatid):
    try:
        logins = curd.getCookies(chatid=chatid)  # 0 : Phone , 1:Cookie , 2 : used
        manageDetails = curd.getManage(chatid=chatid)
        if not manageDetails or manageDetails[0] != 1:
            return
        
        climit = manageDetails[2] if manageDetails[2] is not None else 0
        nardeban_type = manageDetails[3] if len(manageDetails) > 3 else 1  # نوع نردبان
        
        # فیلتر کردن لاگین‌هایی که:
        # 1. به سقف نرسیده‌اند (l[2] < climit)، یا
        # 2. اگهی pending دارند (حتی اگر به سقف رسیده باشند)
        available_logins = []
        for l in logins:
            # بررسی اینکه آیا به سقف نرسیده است
            under_limit = climit == 0 or l[2] < int(climit)
            
            # بررسی اینکه آیا اگهی pending دارد
            has_pending = False
            try:
                pending_tokens = get_tokens_from_json(chatid=chatid, phone=int(l[0]), status="pending")
                has_pending = len(pending_tokens) > 0
            except:
                pass
            
            # اگر به سقف نرسیده یا اگهی pending دارد، در دسترس است
            if under_limit or has_pending:
                available_logins.append(l)
        
        if not available_logins:
            # بررسی دقیق‌تر: آیا واقعاً همه لاگین‌ها به سقف رسیده‌اند و اگهی pending ندارند؟
            all_at_limit = all(l[2] >= int(climit) for l in logins) if climit > 0 else False
            has_any_pending = has_pending_tokens_in_json(chatid=chatid)
            
            if all_at_limit and not has_any_pending:
                await bot_send_message(chat_id=chatid, text="تمام لاگین‌ها به سقف نردبان رسیده‌اند و هیچ اگهی pending وجود ندارد.")
            else:
                # این حالت نباید اتفاق بیفتد، اما برای اطمینان
                await bot_send_message(chat_id=chatid, text="⚠️ هیچ لاگین در دسترسی یافت نشد. لطفاً بررسی کنید.")
            return
        
        # بررسی و استخراج توکن‌ها فقط در صورتی که همه اگهی‌ها نردبان شده باشند
        await extractTokensIfNeeded(chatid, available_logins)
        
        # بررسی اضافی: اگر همه اگهی‌ها پردازش شده‌اند، ریست و استخراج مجدد انجام بده
        print(f"🔍 [sendNardeban] بررسی نهایی برای ریست خودکار...")
        await auto_reset_and_extract_if_all_done(chatid)
        
        # نوع 1: ترتیبی کامل هر لاگین
        # رفتار: هر لاگین → همه آگهی‌هاش کامل نردبان می‌شود → بعد لاگین بعدی
        # در هر اجرا فقط یک نردبان انجام می‌شود (از آخرین توکن pending)
        if nardeban_type == 1:
            for l in available_logins:
                try:
                    nardebanAPI = nardeban(apiKey=l[1])
                    # sendNardeban از آخر لیست توکن‌ها شروع می‌کند و اولین توکن pending را پیدا می‌کند
                    # استخراج خودکار در ابتدای فرایند حذف شد - فقط زمانی استخراج می‌شود که همه اگهی‌ها نردبان شده باشند
                    result = nardebanAPI.sendNardeban(number=int(l[0]), chatid=chatid)
                    success = await handleNardebanResult(result, l, chatid, nardebanAPI)
                    
                    # در هر اجرا فقط یک نردبان انجام می‌شود
                    if success:
                        break
                    
                except Exception as e:
                    print(f"Error in nardeban process for phone {l[0]}: {e}")
                    await bot_send_message(chat_id=chatid, text=f"خطا در فرآیند نردبان برای شماره {l[0]}: {str(e)}")
        
        # نوع 2: تصادفی
        # رفتار: در هر بار اجرای ربات، یک آگهی کاملاً تصادفی از بین همه لاگین‌ها انتخاب و نردبان می‌شود
        elif nardeban_type == 2:
            # دریافت تمام توکن‌های pending از JSON
            all_pending = get_all_pending_tokens_from_json(chatid=chatid)
            
            if not all_pending:
                # اگر توکن pending وجود نداشت
                await bot_send_message(chat_id=chatid, text="⚠️ هیچ اگهی pending برای نردبان وجود ندارد.")
                return
            
            # انتخاب تصادفی یک توکن از بین همه توکن‌های pending
            selected_phone, selected_token = random.choice(all_pending)
            
            # پیدا کردن لاگین مربوطه
            selected_login = next((l for l in available_logins if str(l[0]) == str(selected_phone)), None)
            if not selected_login:
                await bot_send_message(chat_id=chatid, text=f"لاگین برای شماره {selected_phone} یافت نشد.")
                return
            
            try:
                nardebanAPI = nardeban(apiKey=selected_login[1])
                result = nardebanAPI.sendNardebanWithToken(number=int(selected_phone), chatid=chatid, token=selected_token)
                await handleNardebanResult(result, selected_login, chatid, nardebanAPI)
            except Exception as e:
                print(f"Error in random nardeban: {e}")
                await bot_send_message(chat_id=chatid, text=f"خطا در نردبان تصادفی: {str(e)}")
        
        # نوع 3: ترتیبی نوبتی
        # رفتار: از هر لاگین فقط یک آگهی → می‌ره سراغ لاگین بعدی → دوباره برمی‌گرده تا همه آگهی‌ها تمام شوند
        elif nardeban_type == 3:
            # دریافت آخرین لاگین استفاده شده از دیتابیس (برای نوبتی بودن)
            last_used_phone = None
            if len(manageDetails) > 4 and manageDetails[4] is not None:
                last_used_phone = manageDetails[4]
            
            # پیدا کردن لاگین بعدی که توکن pending دارد (نوبتی)
            selected_login = None
            selected_token = None
            start_index = 0
            
            # اگر آخرین لاگین استفاده شده را می‌دانیم، از لاگین بعدی شروع می‌کنیم
            if last_used_phone:
                for i, l in enumerate(available_logins):
                    if str(l[0]) == str(last_used_phone):
                        start_index = (i + 1) % len(available_logins)  # از لاگین بعدی شروع می‌کنیم
                        break
            
            # جستجوی نوبتی: از start_index شروع می‌کنیم و دور می‌زنیم
            found = False
            for i in range(len(available_logins)):
                index = (start_index + i) % len(available_logins)
                l = available_logins[index]
                
                # دریافت اولین توکن pending برای این لاگین از JSON
                tokens_from_json = get_tokens_from_json(chatid=chatid, phone=int(l[0]), status="pending")
                token = tokens_from_json[0] if tokens_from_json else None
                if token:
                    selected_login = l
                    selected_token = token
                    found = True
                    break  # اولین لاگینی که توکن pending دارد را انتخاب می‌کنیم
            
            if not found or not selected_login or not selected_token:
                # اگر توکن pending وجود نداشت
                await bot_send_message(chat_id=chatid, text="⚠️ هیچ اگهی pending برای نردبان وجود ندارد.")
                return
            
            try:
                nardebanAPI = nardeban(apiKey=selected_login[1])
                result = nardebanAPI.sendNardebanWithToken(number=int(selected_login[0]), chatid=chatid, token=selected_token)
                success = await handleNardebanResult(result, selected_login, chatid, nardebanAPI)
                
                # ذخیره آخرین لاگین استفاده شده برای نوبت بعدی
                if success:
                    # ذخیره شماره تلفن آخرین لاگین استفاده شده در دیتابیس
                    curd.setStatusManage(q="last_round_robin_phone", v=int(selected_login[0]), chatid=chatid)
            except Exception as e:
                print(f"Error in round-robin nardeban: {e}")
                await bot_send_message(chat_id=chatid, text=f"خطا در نردبان نوبتی: {str(e)}")
        
        # نوع 4: جریان طبیعی (Natural Flow)
        # رفتار: آگهی‌های قدیمی‌تر اولویت می‌گیرند، آگهی‌هایی که بازدید کمتر دارند زودتر نردبان می‌شوند
        # فاصله زمانی بین نردبان‌ها کاملاً نامنظم است (3 تا 15 دقیقه)
        elif nardeban_type == 4:
            # دریافت تمام توکن‌های pending از JSON
            all_pending = get_all_pending_tokens_from_json(chatid=chatid)
            
            if not all_pending:
                # اگر توکن pending وجود نداشت
                await bot_send_message(chat_id=chatid, text="⚠️ هیچ اگهی pending برای نردبان وجود ندارد.")
                return
            
            # انتخاب آگهی بر اساس اولویت:
            # 1. آگهی‌های قدیمی‌تر (اولین توکن‌های pending = قدیمی‌تر)
            # 2. آگهی‌هایی که بازدید کمتر دارند (فرض: توکن‌های قدیمی‌تر = بازدید کمتر)
            
            # گروه‌بندی بر اساس شماره تلفن
            tokens_by_phone = {}
            for phone, token in all_pending:
                if phone not in tokens_by_phone:
                    tokens_by_phone[phone] = []
                tokens_by_phone[phone].append(token)
            
            # انتخاب قدیمی‌ترین توکن از هر لاگین (اولین توکن در لیست = قدیمی‌ترین)
            # توجه: get_pending_tokens_by_phone توکن‌ها را به ترتیب ذخیره‌سازی برمی‌گرداند
            # که معمولاً قدیمی‌ترین توکن‌ها اول هستند
            selected_candidates = []
            for phone, tokens in tokens_by_phone.items():
                if tokens:
                    # اولین توکن = قدیمی‌ترین (فرض: ترتیب ذخیره‌سازی حفظ شده)
                    selected_candidates.append((phone, tokens[0]))
            
            if not selected_candidates:
                await bot_send_message(chat_id=chatid, text="⚠️ هیچ آگهی مناسب برای نردبان یافت نشد.")
                return
            
            # انتخاب قدیمی‌ترین آگهی از بین همه لاگین‌ها
            # از اولین کاندیدا استفاده می‌کنیم (قدیمی‌ترین توکن از اولین لاگین)
            # برای طبیعی‌تر شدن، می‌توان از بین چند کاندیدای اول انتخاب تصادفی کرد
            selected_phone, selected_token = selected_candidates[0]
            
            # پیدا کردن لاگین مربوطه
            selected_login = next((l for l in available_logins if str(l[0]) == str(selected_phone)), None)
            if not selected_login:
                await bot_send_message(chat_id=chatid, text=f"لاگین برای شماره {selected_phone} یافت نشد.")
                return
            
            try:
                nardebanAPI = nardeban(apiKey=selected_login[1])
                result = nardebanAPI.sendNardebanWithToken(number=int(selected_phone), chatid=chatid, token=selected_token)
                success = await handleNardebanResult(result, selected_login, chatid, nardebanAPI)
                
                # اگر موفق بود، زمان‌بندی بعدی را با فاصله نامنظم تنظیم کن
                if success:
                    # زمان‌بندی نامنظم: بین 3 تا 15 دقیقه
                    next_interval = random.randint(3, 15)
                    # برنامه‌ریزی برای نردبان بعدی با فاصله نامنظم
                    # استفاده از scheduler global
                    global scheduler
                    scheduler.add_job(
                        sendNardeban,
                        "date",
                        args=[chatid],
                        run_date=now_tehran() + timedelta(minutes=next_interval)
                    )
                    await bot_send_message(chat_id=chatid, 
                                     text=f"⏰ نردبان بعدی در {next_interval} دقیقه انجام می‌شود.")
            except Exception as e:
                print(f"Error in natural flow nardeban: {e}")
                await bot_send_message(chat_id=chatid, text=f"خطا در نردبان جریان طبیعی: {str(e)}")

    except Exception as e:
        try:
            await bot_send_message(chat_id=chatid,
                             text=f"در فرایند اولیه شروع نردبان مشکلی وجود دارد ، متن ارور : {str(e)}")
            print(e)
        except Exception as e:
            print(f"Error sending message: {e}")

async def handleNardebanResult(result, login_info, chatid, nardebanAPI):
    """تابع helper برای مدیریت نتیجه نردبان - برمی‌گرداند True اگر موفق بود"""
    if result[0] == 1:
        # به‌روزرسانی وضعیت توکن به success بعد از نردبان موفق
        token = result[1] if len(result) > 1 else None
        phone = result[2] if len(result) > 2 else login_info[0]
        
        if token:
            updated = update_token_status(chatid=chatid, phone=int(phone), token=token, new_status="success")
            if updated:
                print(f"✅ توکن {token} به وضعیت success تغییر یافت (نردبان موفق)")
                
                # بررسی اینکه آیا این آخرین اگهی pending بود
                remaining_pending = has_pending_tokens_in_json(chatid=chatid)
                if not remaining_pending:
                    print(f"🎯 [handleNardebanResult] همه اگهی‌ها پردازش شدند - آماده ریست خودکار")
            else:
                print(f"⚠️ توکن {token} در JSON یافت نشد یا به‌روزرسانی نشد")
        
        # به‌روزرسانی تعداد نردبان‌های استفاده‌شده برای لاگین فعلی
        curd.updateLimitLogin(phone=login_info[0])
        
        # دریافت اطلاعات به‌روز شده لاگین
        updated_logins = curd.getCookies(chatid=chatid)
        updated_login = next((l for l in updated_logins if str(l[0]) == str(login_info[0])), login_info)
        
        # اگر موفقیت‌آمیز بود
        try:
            bot = get_bot()
            if bot:
                await bot.send_message(chat_id=chatid,
                                 text=f"آگهی {str(result[1])} از شماره {str(result[2])} نردبان شد.")
                await bot.send_message(chat_id=chatid,
                                 text=f"از شماره {str(result[2])} تا به حال تعداد {str(updated_login[2])} آگهی نردبان شده است.")
        except Exception as e:
            print(f"Error sending message: {e}")
        
        # اگر هیچ اگهی pending باقی نمانده باشد، بلافاصله ریست و استخراج جدید انجام بده
        await auto_reset_and_extract_if_all_done(chatid)
        return True
    elif result[0] == 0:
        # اگر نردبان موفق نبود - به‌روزرسانی وضعیت به failed
        error_token = result[1] if len(result) > 1 else None
        error_msg = result[2] if len(result) > 2 else "خطای نامشخص"
        phone = login_info[0]
        
        if error_token:
            updated = update_token_status(chatid=chatid, phone=int(phone), token=error_token, new_status="failed")
            if updated:
                print(f"⚠️ توکن {error_token} به وضعیت failed تغییر یافت")
        
        print(f"Failed to nardeban ad with token {error_token}: {error_msg}")
        await bot_send_message(chat_id=chatid,
                         text=f"نردبان آگهی با توکن {str(error_token)} با مشکل مواجه شد.\nخطا: {str(error_msg)}")
        return False
    elif result[0] == 2:
        # اگر هیچ پستی موجود نبود
        error_msg = result[1] if len(result) > 1 else "هیچ اگهی برای نردبان پیدا نشد."
        await bot_send_message(chat_id=chatid, text=str(error_msg))
        return False
    else:
        # سایر خطاها
        error_msg = result[1] if len(result) > 1 else "خطای نامشخص"
        await bot_send_message(chat_id=chatid, text=str(error_msg))
        return False

async def remJob(sch, id, chatid):
    """تابع برای توقف خودکار job نردبان در ساعت مشخص شده"""
    try:
        # حذف job نردبان
        try:
            sch.remove_job(id)
        except Exception as e:
            print(f"⚠️ خطا در حذف job نردبان {id}: {e}")
        
        # حذف job توقف خودکار مربوطه (اگر وجود داشته باشد)
        try:
            stop_job_id = f"auto_stop_{chatid}_{id}"
            sch.remove_job(stop_job_id)
        except:
            pass  # اگر job توقف وجود نداشت، مشکلی نیست
        
        curd.removeJob(chatid=chatid)
        refreshUsed(chatid=chatid)
        
        await bot_send_message(chat_id=chatid, text="✅ عملیات نردبان شما با موفقیت به پایان رسید!")
    except Exception as e:
        try:
            await bot_send_message(chat_id=chatid,
                             text=f"❌ در فرایند حذف فرایند زمان‌بندی نردبان مشکلی وجود دارد:\n{str(e)}")
            print(f"❌ خطا در remJob: {e}")
            import traceback
            traceback.print_exc()
        except Exception as e2:
            print(f"❌ Error sending message in remJob: {e2}")

async def reExtractTokens(chatid):
    """استخراج مجدد اگهی‌ها برای تمام لاگین‌های فعال"""
    try:
        logins = curd.getCookies(chatid=chatid)  # 0 : Phone , 1:Cookie , 2 : used
        if not logins:
            await bot_send_message(chat_id=chatid, text="⚠️ هیچ لاگین فعالی برای استخراج وجود ندارد.")
            return
        
        total_extracted = 0
        success_count = 0
        failed_count = 0
        
        for l in logins:
            try:
                nardebanAPI = nardeban(apiKey=l[1])
                brandToken = nardebanAPI.getBranToken()
                
                if not brandToken:
                    await bot_send_message(chat_id=chatid, 
                                                     text=f"❌ خطا در دریافت brand token برای شماره {l[0]}")
                    failed_count += 1
                    continue
                
                # استخراج توکن‌های جدید
                tokens = nardebanAPI.get_all_tokens(brand_token=brandToken)
                
                if tokens:
                    # ذخیره توکن‌ها در JSON
                    new_count = add_tokens_to_json(chatid=chatid, phone=int(l[0]), tokens=tokens)
                    
                    if new_count > 0:
                        # همچنین در دیتابیس هم ذخیره کن (برای سازگاری)
                        existing_tokens = curd.get_tokens_by_phone(phone=int(l[0]))
                        new_tokens = [t for t in tokens if t not in existing_tokens]
                        if new_tokens:
                            curd.insert_tokens_by_phone(phone=int(l[0]), tokens=new_tokens)
                        
                        total_extracted += new_count
                        success_count += 1
                        await bot_send_message(chat_id=chatid,
                                                     text=f"✅ از شماره {l[0]}: {new_count} اگهی جدید استخراج و در JSON ذخیره شد.")
                    else:
                        await bot_send_message(chat_id=chatid,
                                                     text=f"ℹ️ از شماره {l[0]}: همه اگهی‌ها قبلاً استخراج شده بودند.")
                        success_count += 1
                else:
                    await bot_send_message(chat_id=chatid,
                                                     text=f"⚠️ از شماره {l[0]}: هیچ اگهی‌ای یافت نشد.")
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error extracting tokens for phone {l[0]}: {e}")
                await bot_send_message(chat_id=chatid,
                                                 text=f"❌ خطا در استخراج برای شماره {l[0]}: {str(e)}")
                failed_count += 1
        
        # پیام خلاصه
        summary = f"""📊 <b>خلاصه استخراج مجدد:</b>

✅ موفق: {success_count} لاگین
❌ ناموفق: {failed_count} لاگین
📦 کل اگهی‌های استخراج شده: {total_extracted}"""
        await bot_send_message(chat_id=chatid, text=summary, parse_mode='HTML')
        
    except Exception as e:
        print(f"Error in reExtractTokens: {e}")
        await bot_send_message(chat_id=chatid, text=f"❌ خطا در فرآیند استخراج مجدد: {str(e)}")

async def resetAllExtractions(chatid):
    """حذف تمام اگهی‌های استخراج شده و صفر کردن شمارنده‌ها برای یک chatid"""
    try:
        phones = curd.get_phone_numbers_by_chatid(chatid=chatid) or []
        json_reset = reset_tokens_for_chat(chatid)

        deleted_from_db = 0
        for phone in phones:
            curd.delete_tokens_by_phone(phone=int(phone))
            deleted_from_db += 1

        curd.remSents(chatid)
        curd.refreshUsed(chatid)

        summary_lines = ["♻️ <b>ریست استخراج‌ها انجام شد.</b>"]
        summary_lines.append("• JSON پاک‌سازی شد." if json_reset else "• در JSON داده‌ای برای پاک کردن نبود.")
        summary_lines.append(f"• رکوردهای دیتابیس برای {deleted_from_db} لاگین حذف شد.")
        summary_lines.append("• شمارنده استفاده لاگین‌ها صفر شد و لاگ‌های نردبان پاک شدند.")

        await bot_send_message(chat_id=chatid, text="\n".join(summary_lines), parse_mode='HTML')
    except Exception as e:
        print(f"Error in resetAllExtractions: {e}")
        await bot_send_message(chat_id=chatid, text=f"❌ خطا در ریست استخراج‌ها: {str(e)}")

def refreshUsed(chatid):
    """بازنشانی وضعیت استفاده شده - بدون حذف اگهی‌های استخراج شده"""
    curd.refreshUsed(chatid)
    curd.remSents(chatid)
    curd.removeJob(chatid=chatid)
    curd.setStatusManage(q="climit", v=0, chatid=chatid)
    # حذف اگهی‌های استخراج شده حذف شد - اگهی‌ها باید باقی بمانند
    # numbers = curd.get_phone_numbers_by_chatid(chatid=chatid)
    # for n in numbers:
    #     curd.delete_tokens_by_phone(phone=n)

def build_application():
    global application_instance
    
    # Fix timezone issue by setting environment variable
    import os
    
    # Set timezone to UTC to avoid timezone detection issues
    os.environ['TZ'] = 'UTC'
    
    # Try to import pytz, if not available use fallback
    try:
        import pytz
        timezone_available = True
    except ImportError:
        print("⚠️ pytz not available, using fallback timezone handling")
        timezone_available = False
    
    try:
        # Try to create application without JobQueue to avoid timezone issues
        application = (
            ApplicationBuilder()
            .token(Datas.token)
            .rate_limiter(AIORateLimiter())
            .build()
        )
    except Exception as e:
        print(f"❌ خطا در ساخت Application با rate limiter: {e}")
        try:
            # Try without rate limiter
            application = (
                ApplicationBuilder()
                .token(Datas.token)
                .build()
            )
        except Exception as e2:
            print(f"❌ خطا در ساخت Application ساده: {e2}")
            raise e2
    application_instance = application

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('end', shoro))
    application.add_handler(CommandHandler('add', addadmin, filters=filters.User(user_id=Datas.admin)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mainMenu))
    application.add_handler(CallbackQueryHandler(qrycall))

    application.post_init = on_startup
    application.post_shutdown = on_shutdown
    return application


async def on_startup(application: Application):
    print("🚀 Application post_init - starting scheduler")
    loop = asyncio.get_running_loop()
    scheduler.configure(event_loop=loop)
    if not scheduler.running:
        scheduler.start()
    
    # تنظیم jobهای شروع خودکار برای همه ادمین‌ها
    try:
        start_time = get_start_time_from_config()
        if start_time is not None:
            start_hour, start_minute = start_time
            admins = curd.getAdmins()
            for admin_id in admins:
                try:
                    await setup_auto_start_job(int(admin_id), start_hour, start_minute)
                except Exception as e:
                    print(f"⚠️ خطا در تنظیم شروع خودکار برای ادمین {admin_id}: {e}")
            # همچنین برای ادمین پیش‌فرض
            if Datas.admin:
                await setup_auto_start_job(int(Datas.admin), start_hour, start_minute)
    except Exception as e:
        print(f"⚠️ خطا در تنظیم jobهای شروع خودکار: {e}")


async def on_shutdown(application: Application):
    print("🛑 Application shutting down - stopping scheduler")
    if scheduler.running:
        scheduler.shutdown(wait=False)


def main():
    print("=" * 50)
    print("🤖 در حال راه‌اندازی ربات تلگرام...")
    print("=" * 50)
    application = build_application()
    application.run_polling(
        poll_interval=1.0,
        timeout=10,
        bootstrap_retries=3,
        close_loop=False,
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ ربات توسط کاربر متوقف شد.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطا در اتصال به تلگرام: {e}")
        print("لطفاً موارد زیر را بررسی کنید:")
        print("  1. اتصال اینترنت")
        print("  2. صحت token ربات در فایل configs.json")
        import traceback
        traceback.print_exc()
        sys.exit(1)