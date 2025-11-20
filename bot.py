# Standard library imports
from datetime import datetime, timedelta
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

    welcome_text = f"""🤖 <b>منوی مدیریت ربات نردبان</b>

{status_emoji} <b>وضعیت ربات:</b> {status_text}
📊 <b>آمار کلی:</b>
   ✅ نردبان شده: <b>{stats['total_nardeban']}</b>
   📦 کل استخراج: <b>{stats['total_tokens']}</b>
   ⏳ در انتظار: <b>{stats['total_pending']}</b>
   ❌ ناموفق: <b>{stats.get('total_failed', 0)}</b>

⚙️ <b>تنظیمات جاری:</b>
   🔽 سقف نردبان: <b>{mngDetail[1]}</b>
   🎯 نوع نردبان: <b>{type_name}</b>
   {job_status}
   ⏱️ فاصله نردبان: <b>{interval_text}</b>

👇 <i>یکی از گزینه‌های زیر را انتخاب کنید:</i>"""

    btns = [
        [
            InlineKeyboardButton(
                f"{'🟢' if is_active else '🔴'} {'خاموش کردن' if is_active else 'روشن کردن'} ربات",
                callback_data="setactive:0" if is_active else "setactive:1"
            )
        ],
        [InlineKeyboardButton('📊 مشاهده آمار کامل', callback_data='stats_info')],
        [InlineKeyboardButton('📱 مدیریت لاگین‌ها', callback_data='managelogin')],
        [
            InlineKeyboardButton(f'🔽 سقف نردبان: {mngDetail[1]}', callback_data='setlimit'),
            InlineKeyboardButton(f'⚙️ نوع: {type_name[:10]}', callback_data='setNardebanType')
        ],
        [
            InlineKeyboardButton('🔄 استخراج مجدد', callback_data='reExtract'),
            InlineKeyboardButton('⏹️ توقف نردبان', callback_data='remJob')
        ],
        [InlineKeyboardButton('♻️ ریست استخراج‌ها', callback_data='resetTokens')],
    ]

    if int(chat_id) == int(Datas.admin):
        btns.append([InlineKeyboardButton('👥 مدیریت ادمین‌ها', callback_data='manageAdmins')])

    btns.append([InlineKeyboardButton('❓ راهنما', callback_data='help_menu')])
    btns.append([InlineKeyboardButton('🔁 بروزرسانی منو', callback_data='refreshMenu')])

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

    buttons.append([InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')])
    return text, InlineKeyboardMarkup(buttons)


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
            
            if status[1] == 1:
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
                [InlineKeyboardButton('🔙 بازگشت به منو', callback_data='backToMenu')]
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
        elif data == "setlimit":
            try:
                await qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            curd.setStatus(q="slimit", v=1, chatid=chatid)
            await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً یک عدد برای تعیین سقف مجاز تعداد اگهی نردبان روازنه ارسال کنید : ")
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
                    scheduler.remove_job(job_id=job_id)
                except Exception as e:
                    txtResult = f"در غیر فعال سازی عملیات نردبان یک مشکل وجود دارد ! متن ارور : {str(e)}"
                    curd.removeJob(chatid=chatid)
                else:
                    txtResult = f"عملیات نردبان با آیدی {str(job_id)} با موفقیت غیرفعال سازی شد ."
                    curd.removeJob(chatid=chatid)
                try:
                    await qry.answer()  # پاسخ به callback
                except Exception as e:
                    print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
                await context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                                 text=txtResult)
            else:
                await qry.answer(text="شما هیج نردبان فعالی ندارید !", show_alert=True)
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
    
    total_nardeban = int(manageDetails[1])
    currentLimit = round(total_nardeban / len(logins))

    await bot_send_message(chat_id=chatid, text=f"برای هر لاگین سقف نردبان به عدد {str(currentLimit)} است.")
    curd.setStatusManage(q="climit", v=currentLimit, chatid=chatid)

    current_hour = int(datetime.now().hour)
    remainTime_hours = end - current_hour

    if remainTime_hours <= 0:
        await bot_send_message(chat_id=chatid, text="زمان پایان نردبان‌ها از زمان فعلی گذشته است.")
        return

    stopTime_minutes = round((remainTime_hours * 60) / total_nardeban)
    nardeban_type = manageDetails[3] if len(manageDetails) > 3 else 1
    
    if nardeban_type == 4:
        await bot_send_message(chat_id=chatid, text="🎢 نوع نردبان: جریان طبیعی - زمان‌بندی نامنظم فعال است.")
        await sendNardeban(chatid)
    else:
        await bot_send_message(chat_id=chatid, text=f"زمان بین نردبان‌ها حدود {str(stopTime_minutes)} دقیقه است.")
        job = scheduler.add_job(sendNardeban, "interval", args=[chatid], minutes=stopTime_minutes)
        scheduler.add_job(remJob, trigger="cron", args=[scheduler, job.id, chatid], hour=end)
        curd.addJob(chatid=chatid, job=job.id)

def shouldExtractTokens(chatid, available_logins):
    """بررسی می‌کند که آیا باید استخراج انجام شود یا نه
    فقط زمانی استخراج انجام می‌شود که:
    1. هیچ توکن pending وجود نداشته باشد
    2. حداقل یک توکن نردبان شده (success) وجود داشته باشد
    """
    try:
        # چک کردن اینکه آیا توکن pending در JSON وجود دارد
        has_pending = has_pending_tokens_in_json(chatid=chatid)
        
        # اگر توکن pending وجود دارد، نیازی به استخراج نیست
        if has_pending:
            return False
        
        # بررسی اینکه آیا حداقل یک توکن نردبان شده (success) وجود دارد
        # استفاده از getStats برای بررسی تعداد نردبان شده
        stats = curd.getStats(chatid=chatid)
        
        # اگر حداقل یک نردبان انجام شده باشد و هیچ pending در JSON وجود نداشته باشد
        # یعنی همه توکن‌ها نردبان شده‌اند و باید استخراج مجدد انجام شود
        if stats['total_nardeban'] > 0:
            # همه اگهی‌ها نردبان شده‌اند - استخراج مجدد انجام می‌شود
            return True
        
        # اگر هیچ نردبانی انجام نشده یا هنوز pending وجود دارد، استخراج نکن
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

async def sendNardeban(chatid):
    try:
        logins = curd.getCookies(chatid=chatid)  # 0 : Phone , 1:Cookie , 2 : used
        manageDetails = curd.getManage(chatid=chatid)
        if not manageDetails or manageDetails[0] != 1:
            return
        
        climit = manageDetails[2] if manageDetails[2] is not None else 0
        nardeban_type = manageDetails[3] if len(manageDetails) > 3 else 1  # نوع نردبان
        
        # فیلتر کردن لاگین‌هایی که به سقف نرسیده‌اند
        available_logins = [l for l in logins if l[2] <= int(climit)]
        
        if not available_logins:
            await bot_send_message(chat_id=chatid, text="تمام لاگین‌ها به سقف نردبان رسیده‌اند.")
            return
        
        # بررسی و استخراج توکن‌ها فقط در صورتی که همه اگهی‌ها نردبان شده باشند
        await extractTokensIfNeeded(chatid, available_logins)
        
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
                    scheduler.add_job(sendNardeban, "date", args=[chatid], 
                                   run_date=datetime.now() + timedelta(minutes=next_interval))
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
        
        # اگر هیچ اگهی pending باقی نمانده باشد، بلافاصله استخراج جدید انجام بده
        await trigger_extract_if_done(chatid)
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
    try:
        await bot_send_message(chat_id=chatid, text="عملیات نردبان شما با موفقیت به پایان رسید !")
        sch.remove_job(id)
        curd.removeJob(chatid=chatid)
        refreshUsed(chatid=chatid)
    except Exception as e:
        try:
            await bot_send_message(chat_id=chatid,
                             text=f"در فرایند حذف فرایند زمان بندی نردبان مشکلی وجود دارد ، متن ارور : {str(e)}")
            print(e)
        except Exception as e:
            print(f"Error sending message: {e}")

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
    application = (
        ApplicationBuilder()
        .token(Datas.token)
        .rate_limiter(AIORateLimiter())
        .build()
    )
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