# Standard library imports
from datetime import datetime, timedelta
import random
import sys
import time
import io

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
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext
)
from apscheduler.schedulers.background import BackgroundScheduler

# Local imports
from loadConfig import configBot
from curds import curdCommands, CreateDB
from dapi import api, nardeban

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

# ایجاد Updater برای نسخه PTB 12.8
try:
    # در نسخه PTB 12.8 از Updater استفاده می‌شود
    updater = Updater(token=Datas.token, use_context=True)
    dispatcher = updater.dispatcher
    print("✅ Updater با موفقیت ایجاد شد")
except Exception as e:
    print(f"❌ خطا در ایجاد Updater: {e}")
    print("\n💡 راهنمای رفع مشکل:")
    print("   1. بررسی اتصال اینترنت")
    print("   2. بررسی صحت token ربات در فایل configs.json")
    import traceback
    traceback.print_exc()
    sys.exit(1)

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

def addadmin(update: Update, context: CallbackContext):
    """افزودن ادمین جدید - فقط ادمین پیش‌فرض می‌تواند استفاده کند"""
    try:
        user = update.message
        chatid = user.chat.id
        
        # بررسی اینکه آیا کاربر ادمین پیش‌فرض است
        admin_int = int(Datas.admin) if Datas.admin is not None else None
        if chatid != admin_int:
            context.bot.send_message(chat_id=chatid, text="❌ شما مجاز به استفاده از این دستور نیستید.")
            return
        
        # بررسی صحت ورودی
        parts = user.text.split(" ")
        if len(parts) < 2:
            context.bot.send_message(chat_id=chatid, text="❌ لطفاً چت آیدی ادمین را وارد کنید.\nمثال: /add 123456789")
            return
        
        try:
            adminChatid = int(parts[1])
        except ValueError:
            context.bot.send_message(chat_id=chatid, text="❌ چت آیدی باید یک عدد باشد.\nمثال: /add 123456789")
            return
        
        # بررسی اینکه آیا این ادمین قبلاً اضافه شده یا نه
        if adminChatid == admin_int:
            context.bot.send_message(chat_id=chatid, text="❌ این ادمین پیش‌فرض است و قبلاً در سیستم موجود است.")
            return
        
        # اضافه کردن ادمین
        if curd.setAdmin(chatid=adminChatid) == 1:
            context.bot.send_message(chat_id=chatid, text="✅ ادمین جدید با موفقیت به لیست ادمین ها افزوده شد.")
            try:
                context.bot.send_message(chat_id=adminChatid, text="تبریک ، شما به ادمین های ربات اضافه شدید ، برای تایید فعال سازی لطفا /start را ارسال کنید")
            except:
                pass
        else:
            context.bot.send_message(chat_id=chatid, text="❌ مشکلی در اضافه کردن ادمین وجود دارد.")
    except Exception as e:
        print(f"❌ خطا در تابع addadmin: {e}")
        import traceback
        traceback.print_exc()
        try:
            context.bot.send_message(chat_id=chatid, text="❌ خطایی در پردازش درخواست شما رخ داد.")
        except:
            pass

def start(update: Update, context: CallbackContext):
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
            curd.addAdmin(chatid=chat_id)
            curd.addManage(chatid=chat_id)
            mngDetail = curd.getManage(chatid=chat_id)
            if mngDetail[0] == 0:
                botStatus = ["✅ روشن کردن ربات ✅", "setactive:1"]
            else:
                botStatus = ["❌ خاموش کردن ربات ❌", "setactive:0"]

            # دریافت آمار اگهی‌ها
            stats = curd.getStats(chatid=chat_id)
            stats_text = f"📊 نردبان: {stats['total_nardeban']} | کل: {stats['total_tokens']} | انتظار: {stats['total_pending']}"

            # تعیین نوع نردبان فعلی
            nardeban_type = mngDetail[3] if len(mngDetail) > 3 else 1
            type_names = {1: "ترتیبی کامل", 2: "تصادفی", 3: "ترتیبی نوبتی", 4: "جریان طبیعی"}
            type_name = type_names.get(nardeban_type, "ترتیبی کامل")

            btns = [
                [InlineKeyboardButton(botStatus[0], callback_data=botStatus[1])],
                [InlineKeyboardButton(stats_text, callback_data='stats_info')],
                [InlineKeyboardButton('🗣 مدیریت لاگین های دیوار 🗣', callback_data='managelogin')],
                [InlineKeyboardButton(f'🔽 سقف تعداد نردبان : {str(mngDetail[1])} 🔽', callback_data='setlimit')],
                [InlineKeyboardButton(f'⚙️ نوع نردبان: {type_name}', callback_data='setNardebanType')],
                [InlineKeyboardButton('🔄 استخراج مجدد اگهی‌ها', callback_data='reExtract')],
                [InlineKeyboardButton('غیر فعال کردن نردبان', callback_data='remJob')],
            ]
            if int(chat_id) == int(Datas.admin):
                btns.append([InlineKeyboardButton('مدیریت ادمین ها',callback_data='manageAdmins')])
            context.bot.send_message(chat_id=chat_id, text="🔥 M E N U : 👇", reply_markup=InlineKeyboardMarkup(btns))
            print(f"✅ منو برای کاربر {chat_id} ارسال شد")
        else:
            # اگر کاربر ادمین نبود → یک پیام و کیبورد بفرستد
            # بررسی مجدد برای اطمینان از اینکه کاربر واقعاً ادمین نیست
            final_check = isAdmin(chat_id)
            if final_check:
                print(f"⚠️ [start] کاربر {chat_id} در بررسی مجدد ادمین تشخیص داده شد - پیام خطا ارسال نمی‌شود")
                return
            
            keyRequest = [[InlineKeyboardButton('درخواست ادمین شدن', callback_data='reqAdmin')]]
            context.bot.send_message(
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
                context.bot.send_message(
                    chat_id=update.message.chat.id,
                    text="❌ خطایی در پردازش درخواست شما رخ داد. لطفاً دوباره تلاش کنید."
                )
        except:
            pass

def shoro(update: Update, context: CallbackContext):
    user = update.message
    print(f"📨 [shoro] دستور /end دریافت شد از کاربر: {user.chat.id}")
    is_admin_result = isAdmin(user.chat.id)
    print(f"🔍 [shoro] نتیجه isAdmin: {is_admin_result}")
    if is_admin_result:
        if curd.getJob(chatid=user.chat.id):
            context.bot.send_message(chat_id=user.chat.id, text="شما یک عملیات نردبان فعال دارید ، از غیرفعال سازی آن اطمینان یابید سپس اقدام کنید !", reply_to_message_id=user.message_id)
        else:
            refreshUsed(chatid=user.chat.id)
            user = update.message
            endTime = int(user.text.split("=")[1])
            if endTime in range(0, 24):
                startNardebanDasti(sch=scheduler, end=endTime, chatid=user.chat.id)
                context.bot.send_message(chat_id=user.chat.id, text="عملیات نردبان دستی شکل گرفت.", reply_to_message_id=user.message_id)
            else:
                context.bot.send_message(chat_id=user.chat.id,
                                 text="مقدار ساعت پایانی عددی باید بین 0 تا 23 باشد !",
                                 reply_to_message_id=user.message_id)
    else:
        # بررسی مجدد برای اطمینان از اینکه کاربر واقعاً ادمین نیست
        final_check = isAdmin(user.chat.id)
        if final_check:
            print(f"⚠️ [shoro] کاربر {user.chat.id} در بررسی مجدد ادمین تشخیص داده شد - پیام خطا ارسال نمی‌شود")
            return
        
        print(f"❌ [shoro] کاربر {user.chat.id} ادمین نیست - ارسال پیام خطا")
        context.bot.send_message(chat_id=user.chat.id, text="شما مجاز به استفاده از ربات نمیباشید .")

def mainMenu(update: Update, context: CallbackContext):
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
                context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
                                 parse_mode='HTML')
            elif status[0] == 1:
                print(f"✅ [mainMenu] پردازش slogin برای کاربر {chatid}")
                curd.setStatus(q="slogin", v=user.text, chatid=chatid)
                divarApi.login(phone=user.text)
                curd.setStatus(q="scode", v=1, chatid=chatid)
                txt = f"🔎 کد با موفقیت به شماره <code>{str(user.text)}</code>ارسال شد ، لطفا کد را ارسال کنید :  ✅"
                context.bot.send_message(chat_id=chatid, text=txt, reply_to_message_id=user.message_id,
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
                context.bot.send_message(chat_id=chatid, text=txtr, reply_to_message_id=user.message_id,
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
            context.bot.send_message(chat_id=chatid, text="شما مجاز به استفاده از ربات نمیباشید .")
    except Exception as e:
        print(f"❌ خطا در تابع mainMenu: {e}")
        import traceback
        traceback.print_exc()
        try:
            context.bot.send_message(chat_id=chatid, 
                                   text="❌ خطایی در پردازش پیام شما رخ داد.")
        except:
            pass

def qrycall(update: Update, context: CallbackContext):
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
                context.bot.send_message(chat_id=Datas.admin, text=txtReq, reply_markup=InlineKeyboardMarkup(btnadmin))
            except:
                txtResult = "مشکلی در ارسال درخواست وجود دارد ."
            else:
                txtResult = "درخواست شما برای ادمین ارسال شد ، منتظر تایید آن باشید !"
            qry.answer(text=txtResult, show_alert=True)
            return  # خروج از تابع بعد از پردازش reqAdmin
        
        # بررسی ادمین بودن برای سایر callback ها
        print(f"🔍 [qrycall] بررسی ادمین بودن برای chatid={chatid}, data={data}")
        is_admin = isAdmin(chatid)
        print(f"🔍 [qrycall] نتیجه isAdmin: {is_admin}")
        if not is_admin:
            print(f"❌ [qrycall] کاربر {chatid} ادمین نیست - فقط پاسخ callback (بدون پیام خطا)")
            # فقط پاسخ callback بده، بدون نمایش alert
            try:
                qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            return
        print(f"✅ [qrycall] کاربر {chatid} ادمین است - ادامه پردازش")
        
        # اگر ادمین است، پردازش callback ها
        if data == "stats_info":
            # نمایش اطلاعات آمار در یک پیام جداگانه
            stats = curd.getStats(chatid=chatid)
            
            # ساخت پیام با آمار هر لاگین
            stats_msg = "📊 <b>آمار اگهی‌های شما:</b>\n\n"
            
            # آمار هر لاگین
            if stats['login_stats']:
                for login_stat in stats['login_stats']:
                    stats_msg += f"📱 <b>شماره {login_stat['phone']}:</b>\n"
                    stats_msg += f"   ✅ نردبان شده: {login_stat['nardeban_count']}\n"
                    stats_msg += f"   📦 کل استخراج شده: {login_stat['total_tokens']}\n"
                    stats_msg += f"   ⏳ در انتظار: {login_stat['pending_count']}\n\n"
            else:
                stats_msg += "⚠️ هیچ لاگینی ثبت نشده است.\n\n"
            
            # جمع کل
            stats_msg += "━━━━━━━━━━━━━━━━\n"
            stats_msg += f"📊 <b>جمع کل:</b>\n"
            stats_msg += f"   ✅ نردبان شده: {stats['total_nardeban']}\n"
            stats_msg += f"   📦 کل استخراج شده: {stats['total_tokens']}\n"
            stats_msg += f"   ⏳ در انتظار: {stats['total_pending']}"
            
            try:
                qry.answer()  # پاسخ سریع به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            context.bot.send_message(chat_id=chatid, text=stats_msg, parse_mode='HTML')
        elif data == "reExtract":
            # استخراج مجدد اگهی‌ها برای تمام لاگین‌های فعال
            qry.answer(text="در حال استخراج مجدد اگهی‌ها...", show_alert=False)
            reExtractTokens(chatid=chatid)
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
                qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            context.bot.send_message(
                chat_id=chatid,
                text="⚙️ <b>انتخاب نوع نردبان:</b>\n\n"
                     "1️⃣ <b>ترتیبی کامل هر لاگین:</b>\n"
                     "   هر لاگین → همه آگهی‌هاش کامل نردبان می‌شود → بعد لاگین بعدی\n\n"
                     "2️⃣ <b>تصادفی:</b>\n"
                     "   در هر بار اجرای ربات، یک آگهی کاملاً تصادفی از بین همه لاگین‌ها انتخاب و نردبان می‌شود\n\n"
                     "3️⃣ <b>ترتیبی نوبتی:</b>\n"
                     "   از هر لاگین فقط یک آگهی → می‌ره سراغ لاگین بعدی → دوباره برمی‌گرده تا همه آگهی‌ها تمام شوند\n\n"
                     "🎢 4️⃣ <b>جریان طبیعی:</b>\n"
                     "   آگهی‌های قدیمی‌تر اولویت می‌گیرند\n"
                     "   آگهی‌هایی که بازدید کمتر دارند زودتر نردبان می‌شوند\n"
                     "   فاصله زمانی بین نردبان‌ها کاملاً نامنظم است",
                reply_markup=InlineKeyboardMarkup(type_buttons),
                parse_mode='HTML'
            )
        elif data.startswith("nardebanType:"):
            # تنظیم نوع نردبان
            nardeban_type = int(data.split(":")[1])
            curd.setStatusManage(q="nardeban_type", v=nardeban_type, chatid=chatid)
            
            type_names = {1: "ترتیبی کامل", 2: "تصادفی", 3: "ترتیبی نوبتی", 4: "جریان طبیعی"}
            qry.answer(text=f"نوع نردبان به {type_names[nardeban_type]} تغییر یافت", show_alert=True)
            # بازگشت به منو
            start(update, context)
        elif data == "backToMenu":
            try:
                qry.answer()
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            start(update, context)
        elif data == "manageAdmins":
            # فقط ادمین پیش‌فرض می‌تواند ادمین‌ها را مدیریت کند
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            if chatid != admin_int:
                qry.answer(text="❌ فقط ادمین پیش‌فرض می‌تواند ادمین‌ها را مدیریت کند!", show_alert=True)
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
                qry.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(newKeyAdmins))
            else:
                qry.answer(text="هیچ ادمینی وجود ندارد .", show_alert=True)
        elif data.startswith("setactive"):
            value = data.split(":")[1]
            if value == "1":
                curd.setStatusManage(q="active", v=1, chatid=chatid)
            else:
                curd.setStatusManage(q="active", v=0, chatid=chatid)
            
            # ساخت keyboard جدید به جای تغییر دادن keyboard موجود
            old_keyboard = qry.message.reply_markup.inline_keyboard
            new_keyboard = []
            for row in old_keyboard:
                new_row = []
                for button in row:
                    button_text = button.text
                    button_callback = button.callback_data
                    
                    # تغییر دکمه setactive
                    if "setactive" in str(button_callback):
                        if "خاموش" in button_text:
                            button_text = "✅ روشن کردن ربات ✅"
                            button_callback = "setactive:1"
                        elif "روشن" in button_text:
                            button_text = "❌ خاموش کردن ربات ❌"
                            button_callback = "setactive:0"
                    
                    new_row.append(InlineKeyboardButton(button_text, callback_data=button_callback))
                new_keyboard.append(new_row)
            
            try:
                qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            qry.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
        elif data.startswith("delAdmin"):
            # فقط ادمین پیش‌فرض می‌تواند ادمین حذف کند
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            if chatid != admin_int:
                qry.answer(text="❌ فقط ادمین پیش‌فرض می‌تواند ادمین حذف کند!", show_alert=True)
                return
            
            adminID = int(data.split(":")[1])
            # بررسی اینکه آیا این ادمین پیش‌فرض است یا نه
            if adminID == admin_int:
                txtResult = "❌ نمی‌توانید ادمین پیش‌فرض را حذف کنید!"
                qry.answer(text=txtResult, show_alert=True)
            else:
                if curd.remAdmin(chatid=adminID) == 1:
                    txtResult = "کاربر مورد نظر با موفقیت از لیست ادمین ها حذف شد ."
                    try:
                        context.bot.send_message(chat_id=adminID,
                                         text="متاسفانه شما از لیست ادمین های ربات خارج شدید !")
                    except:
                        pass
                else:
                    txtResult = "مشکلی در حذف کردن کاربر وجود دارد ."
                qry.answer(text=txtResult, show_alert=True)
        elif data.startswith("admin"):
            # فقط ادمین پیش‌فرض می‌تواند ادمین اضافه کند
            admin_int = int(Datas.admin) if Datas.admin is not None else None
            if chatid != admin_int:
                qry.answer(text="❌ فقط ادمین پیش‌فرض می‌تواند ادمین اضافه کند!", show_alert=True)
                return
            
            newAdminChatID = int(data.split(":")[1])
            if curd.setAdmin(chatid=newAdminChatID) == 1:
                txtResult = "کاربر مورد نظر با موفقیت به لیست ادمین ها اضافه شد ."
                try:
                    context.bot.send_message(chat_id=newAdminChatID, text="شما با موفقیت به لیست ادمین های ربات اضافه شدید برای فعال سازی لطفا /start را بزنید.")
                except:
                    pass
            else:
                txtResult = "مشکلی در اضافه کردن کاربر وجود دارد ."
            qry.answer(text=txtResult, show_alert=True)
        elif data.startswith("del"):
            if curd.delLogin(phone=data.split(":")[1]) == 1:
                qry.answer(text="با موفقیت حذف شد")
            else:
                qry.answer(text="مشکلی در حذف شدن وحود دارد")
        elif data.startswith("update"):
            try:
                qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            phoneL = data.split(":")[1]
            curd.setStatus(q="slogin", v=phoneL, chatid=chatid)
            divarApi.login(phone=phoneL)
            curd.setStatus(q="scode", v=1, chatid=chatid)
            txt = f"🔎 کد با موفقیت به شماره <code>{str(phoneL)}</code>ارسال شد ، لطفا کد را ارسال کنید :  ✅"
            context.bot.send_message(chat_id=qry.message.chat.id, text=txt, parse_mode='HTML')
        elif data == "setlimit":
            try:
                qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            curd.setStatus(q="slimit", v=1, chatid=chatid)
            context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                             text="🤠 لطفاً یک عدد برای تعیین سقف مجاز تعداد اگهی نردبان روازنه ارسال کنید : ")
        elif data == "managelogin":
            try:
                qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            txt = "🗣 لیست لاگین های شما : "
            logins = curd.getLogins(chatid=chatid)
            keyAdd = [InlineKeyboardButton('➕ اضافه کردن لاگین جدید ', callback_data='addlogin')]
            if logins == 0:
                txt += "شما هیچ شماره ای تا به حال اضافه نکرده اید !"
                context.bot.send_message(chat_id=chatid, text=txt, reply_markup=InlineKeyboardMarkup([keyAdd]))
            else:
                key = []
                for l in logins:
                    phoneL = l[0]
                    print(phoneL)
                    if l[2] == 0:
                        status = ["❌", 1]
                    else:
                        status = ["✅", 0]
                    keyL = [
                        InlineKeyboardButton(status[0], callback_data=f"status:{str(status[1])}:{str(phoneL)}"),
                        InlineKeyboardButton(str(phoneL), callback_data=f"del:{str(phoneL)}"),
                        InlineKeyboardButton("🔄", callback_data=f"update:{str(phoneL)}"),
                    ]
                    key.append(keyL)
                key.append(keyAdd)
                context.bot.send_message(chat_id=chatid, text=txt, reply_markup=InlineKeyboardMarkup(key))
        elif data == "addlogin":
            try:
                qry.answer()  # پاسخ به callback
            except Exception as e:
                print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
            curd.setStatus(q="slogin", v=1, chatid=chatid)
            context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
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
                    qry.answer()  # پاسخ به callback
                except Exception as e:
                    print(f"⚠️ [qrycall] خطا در پاسخ به callback query (احتمالاً قدیمی است): {e}")
                context.bot.send_message(reply_to_message_id=qry.message.message_id, chat_id=chatid,
                                 text=txtResult)
            else:
                qry.answer(text="شما هیج نردبان فعالی ندارید !", show_alert=True)
        elif data.startswith("status"):
            details = data.split(":")
            result = curd.activeLogin(phone=details[2], status=int(details[1]))
            
            # ساخت keyboard جدید به جای تغییر دادن keyboard موجود
            old_keyboard = qry.message.reply_markup.inline_keyboard
            new_keyboard = []
            for row in old_keyboard:
                new_row = []
                for button in row:
                    button_text = button.text
                    button_callback = str(button.callback_data)
                    
                    # تغییر دکمه status مربوط به این شماره
                    if button_callback.split(":")[0] == "status" and button_callback.split(":")[2] == details[2]:
                        if "❌" in button_text:
                            button_text = button_text.replace("❌", "✅")
                            button_callback = f"status:0:{details[2]}"
                        elif "✅" in button_text:
                            button_text = button_text.replace("✅", "❌")
                            button_callback = f"status:1:{details[2]}"
                    
                    new_row.append(InlineKeyboardButton(button_text, callback_data=button_callback))
                new_keyboard.append(new_row)
            
            qry.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
            qry.answer(text=result)
        else:
            # اگر هیچ callback match نکرد، فقط پاسخ بده (بدون پیام خطا)
            print(f"⚠️ [qrycall] هیچ handler برای data={data} پیدا نشد")
            try:
                qry.answer()
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

def startNardebanDasti(sch, chatid, end: int):
    updater.bot.send_message(chat_id=chatid, text="عملیات شروع شد")

    manageDetails = curd.getManage(chatid=chatid)  # 0 = Active , 1 = Limite Global
    logins = curd.getCookies(chatid=chatid)

    if logins:
        # محاسبه سقف نردبان برای هر لاگین
        total_nardeban = int(manageDetails[1])
        currentLimit = round(total_nardeban / len(logins))  # سقف نردبان هر لاگین

        updater.bot.send_message(chat_id=chatid, text=f"برای هر لاگین سقف نردبان به عدد {str(currentLimit)} است.")

        # ذخیره سقف نردبان برای هر لاگین
        curd.setStatusManage(q="climit", v=currentLimit, chatid=chatid)

        # محاسبه زمان باقی‌مانده بر اساس ساعت شروع و ساعت پایان
        current_hour = int(datetime.now().hour)
        remainTime_hours = end - current_hour

        if remainTime_hours <= 0:
            updater.bot.send_message(chat_id=chatid, text="زمان پایان نردبان‌ها از زمان فعلی گذشته است.")
            return

        # محاسبه زمان بین نردبان‌ها به دقیقه و گرد کردن آن به عدد صحیح
        stopTime_minutes = (remainTime_hours * 60) / total_nardeban
        stopTime_minutes = round(stopTime_minutes)  # گرد کردن دقیقه به عدد صحیح

        # بررسی نوع نردبان
        nardeban_type = manageDetails[3] if len(manageDetails) > 3 else 1
        
        # اگر نوع نردبان "جریان طبیعی" است، از زمان‌بندی نامنظم استفاده نکن
        if nardeban_type == 4:
            updater.bot.send_message(chat_id=chatid, text="🎢 نوع نردبان: جریان طبیعی - زمان‌بندی نامنظم فعال است.")
            # شروع اولین نردبان (زمان‌بندی بعدی در خود sendNardeban تنظیم می‌شود)
            sendNardeban(chatid)
            # برای نوع 4، job خاصی ذخیره نمی‌کنیم چون هر بار job جدید ایجاد می‌شود
        else:
            updater.bot.send_message(chat_id=chatid, text=f"زمان بین نردبان‌ها حدود {str(stopTime_minutes)} دقیقه است.")

        # تنظیم job برای زمان‌بندی نردبان
        s = sch.add_job(sendNardeban, "interval", args=[chatid], minutes=stopTime_minutes)

        # تنظیم job برای حذف job در زمان پایان
        sch.add_job(remJob, trigger="cron", args=[sch, s.id, chatid], hour=end)

        # ذخیره اطلاعات job در دیتابیس
        curd.addJob(chatid=chatid, job=s.id)

    else:
        updater.bot.send_message(chat_id=chatid, text="تمامی لاگین‌های شما غیرفعال است و نمی‌توانم نردبانی انجام دهم!")

def ensureTokensExtracted(chatid, available_logins):
    """بررسی و استخراج توکن‌ها در صورت نبودن"""
    try:
        # چک کردن اینکه آیا توکن pending وجود دارد
        all_pending = curd.get_all_pending_tokens(chatid=chatid)
        
        if not all_pending:
            # اگر توکن pending وجود نداشت، استخراج کن
            updater.bot.send_message(chat_id=chatid, text="⚠️ هیچ اگهی pending یافت نشد. در حال استخراج...")
            
            for l in available_logins:
                try:
                    nardebanAPI = nardeban(apiKey=l[1])
                    brandToken = nardebanAPI.getBranToken()
                    
                    if not brandToken:
                        updater.bot.send_message(chat_id=chatid, 
                                         text=f"❌ خطا در دریافت brand token برای شماره {l[0]}")
                        continue
                    
                    # استخراج توکن‌های جدید
                    tokens = nardebanAPI.get_all_tokens(brand_token=brandToken)
                    
                    if tokens:
                        # حذف توکن‌های قدیمی
                        curd.delete_tokens_by_phone(phone=l[0])
                        # اضافه کردن توکن‌های جدید
                        curd.insert_tokens_by_phone(phone=int(l[0]), tokens=tokens)
                        updater.bot.send_message(chat_id=chatid,
                                         text=f"✅ از شماره {l[0]}: {len(tokens)} اگهی استخراج شد.")
                    else:
                        updater.bot.send_message(chat_id=chatid,
                                         text=f"⚠️ از شماره {l[0]}: هیچ اگهی‌ای یافت نشد.")
                        
                except Exception as e:
                    print(f"Error extracting tokens for phone {l[0]}: {e}")
                    updater.bot.send_message(chat_id=chatid,
                                     text=f"❌ خطا در استخراج برای شماره {l[0]}: {str(e)}")
            
            updater.bot.send_message(chat_id=chatid, text="✅ استخراج اگهی‌ها به پایان رسید.")
    except Exception as e:
        print(f"Error in ensureTokensExtracted: {e}")

def sendNardeban(chatid):
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
            updater.bot.send_message(chat_id=chatid, text="تمام لاگین‌ها به سقف نردبان رسیده‌اند.")
            return
        
        # بررسی و استخراج توکن‌ها در صورت نبودن
        ensureTokensExtracted(chatid, available_logins)
        
        # نوع 1: ترتیبی کامل هر لاگین
        # رفتار: هر لاگین → همه آگهی‌هاش کامل نردبان می‌شود → بعد لاگین بعدی
        # در هر اجرا فقط یک نردبان انجام می‌شود (از آخرین توکن pending)
        if nardeban_type == 1:
            for l in available_logins:
                try:
                    nardebanAPI = nardeban(apiKey=l[1])
                    # چک کردن اینکه آیا توکن برای این شماره وجود دارد یا نه
                    if curd.check_tokens_by_phone(phone=int(l[0])) == 1:
                        # اگر توکن وجود نداشت، استخراج کن
                        brandToken = nardebanAPI.getBranToken()
                        if brandToken:
                            tokens = nardebanAPI.get_all_tokens(brand_token=brandToken)
                            if tokens:
                                curd.insert_tokens_by_phone(phone=int(l[0]), tokens=tokens)
                                updater.bot.send_message(chat_id=chatid,
                                             text=f"تعداد {str(len(tokens))} آکهی از شماره {str(l[0])} برای نردبان یافت و در دیتابیس ذخیره شد .")
                    
                    # sendNardeban از آخر لیست توکن‌ها شروع می‌کند و اولین توکن pending را پیدا می‌کند
                    result = nardebanAPI.sendNardeban(number=int(l[0]), chatid=chatid)
                    success = handleNardebanResult(result, l, chatid, nardebanAPI)
                    
                    # در هر اجرا فقط یک نردبان انجام می‌شود
                    if success:
                        break
                    
                except Exception as e:
                    print(f"Error in nardeban process for phone {l[0]}: {e}")
                    updater.bot.send_message(chat_id=chatid, text=f"خطا در فرآیند نردبان برای شماره {l[0]}: {str(e)}")
        
        # نوع 2: تصادفی
        # رفتار: در هر بار اجرای ربات، یک آگهی کاملاً تصادفی از بین همه لاگین‌ها انتخاب و نردبان می‌شود
        elif nardeban_type == 2:
            # دریافت تمام توکن‌های pending از همه لاگین‌ها
            all_pending = curd.get_all_pending_tokens(chatid=chatid)
            
            if not all_pending:
                # اگر بعد از استخراج هم توکن pending وجود نداشت
                updater.bot.send_message(chat_id=chatid, text="⚠️ بعد از استخراج هم هیچ اگهی pending برای نردبان وجود ندارد.")
                return
            
            # انتخاب تصادفی یک توکن از بین همه توکن‌های pending
            selected_phone, selected_token = random.choice(all_pending)
            
            # پیدا کردن لاگین مربوطه
            selected_login = next((l for l in available_logins if str(l[0]) == str(selected_phone)), None)
            if not selected_login:
                updater.bot.send_message(chat_id=chatid, text=f"لاگین برای شماره {selected_phone} یافت نشد.")
                return
            
            try:
                nardebanAPI = nardeban(apiKey=selected_login[1])
                result = nardebanAPI.sendNardebanWithToken(number=int(selected_phone), chatid=chatid, token=selected_token)
                handleNardebanResult(result, selected_login, chatid, nardebanAPI)
            except Exception as e:
                print(f"Error in random nardeban: {e}")
                updater.bot.send_message(chat_id=chatid, text=f"خطا در نردبان تصادفی: {str(e)}")
        
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
                
                # دریافت اولین توکن pending برای این لاگین
                token = curd.get_next_pending_token_by_phone(phone=l[0], chatid=chatid)
                if token:
                    selected_login = l
                    selected_token = token
                    found = True
                    break  # اولین لاگینی که توکن pending دارد را انتخاب می‌کنیم
            
            if not found or not selected_login or not selected_token:
                # اگر بعد از استخراج هم توکن pending وجود نداشت
                updater.bot.send_message(chat_id=chatid, text="⚠️ بعد از استخراج هم هیچ اگهی pending برای نردبان وجود ندارد.")
                return
            
            try:
                nardebanAPI = nardeban(apiKey=selected_login[1])
                result = nardebanAPI.sendNardebanWithToken(number=int(selected_login[0]), chatid=chatid, token=selected_token)
                success = handleNardebanResult(result, selected_login, chatid, nardebanAPI)
                
                # ذخیره آخرین لاگین استفاده شده برای نوبت بعدی
                if success:
                    # ذخیره شماره تلفن آخرین لاگین استفاده شده در دیتابیس
                    curd.setStatusManage(q="last_round_robin_phone", v=int(selected_login[0]), chatid=chatid)
            except Exception as e:
                print(f"Error in round-robin nardeban: {e}")
                updater.bot.send_message(chat_id=chatid, text=f"خطا در نردبان نوبتی: {str(e)}")
        
        # نوع 4: جریان طبیعی (Natural Flow)
        # رفتار: آگهی‌های قدیمی‌تر اولویت می‌گیرند، آگهی‌هایی که بازدید کمتر دارند زودتر نردبان می‌شوند
        # فاصله زمانی بین نردبان‌ها کاملاً نامنظم است (3 تا 15 دقیقه)
        elif nardeban_type == 4:
            # دریافت تمام توکن‌های pending از همه لاگین‌ها
            all_pending = curd.get_all_pending_tokens(chatid=chatid)
            
            if not all_pending:
                # اگر بعد از استخراج هم توکن pending وجود نداشت
                updater.bot.send_message(chat_id=chatid, text="⚠️ بعد از استخراج هم هیچ اگهی pending برای نردبان وجود ندارد.")
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
                updater.bot.send_message(chat_id=chatid, text="⚠️ هیچ آگهی مناسب برای نردبان یافت نشد.")
                return
            
            # انتخاب قدیمی‌ترین آگهی از بین همه لاگین‌ها
            # از اولین کاندیدا استفاده می‌کنیم (قدیمی‌ترین توکن از اولین لاگین)
            # برای طبیعی‌تر شدن، می‌توان از بین چند کاندیدای اول انتخاب تصادفی کرد
            selected_phone, selected_token = selected_candidates[0]
            
            # پیدا کردن لاگین مربوطه
            selected_login = next((l for l in available_logins if str(l[0]) == str(selected_phone)), None)
            if not selected_login:
                updater.bot.send_message(chat_id=chatid, text=f"لاگین برای شماره {selected_phone} یافت نشد.")
                return
            
            try:
                nardebanAPI = nardeban(apiKey=selected_login[1])
                result = nardebanAPI.sendNardebanWithToken(number=int(selected_phone), chatid=chatid, token=selected_token)
                success = handleNardebanResult(result, selected_login, chatid, nardebanAPI)
                
                # اگر موفق بود، زمان‌بندی بعدی را با فاصله نامنظم تنظیم کن
                if success:
                    # زمان‌بندی نامنظم: بین 3 تا 15 دقیقه
                    next_interval = random.randint(3, 15)
                    # برنامه‌ریزی برای نردبان بعدی با فاصله نامنظم
                    # استفاده از scheduler global
                    global scheduler
                    scheduler.add_job(sendNardeban, "date", args=[chatid], 
                                   run_date=datetime.now() + timedelta(minutes=next_interval))
                    updater.bot.send_message(chat_id=chatid, 
                                     text=f"⏰ نردبان بعدی در {next_interval} دقیقه انجام می‌شود.")
            except Exception as e:
                print(f"Error in natural flow nardeban: {e}")
                updater.bot.send_message(chat_id=chatid, text=f"خطا در نردبان جریان طبیعی: {str(e)}")

    except Exception as e:
        try:
            updater.bot.send_message(chat_id=chatid,
                             text=f"در فرایند اولیه شروع نردبان مشکلی وجود دارد ، متن ارور : {str(e)}")
            print(e)
        except Exception as e:
            print(f"Error sending message: {e}")

def handleNardebanResult(result, login_info, chatid, nardebanAPI):
    """تابع helper برای مدیریت نتیجه نردبان - برمی‌گرداند True اگر موفق بود"""
    if result[0] == 1:
        # به‌روزرسانی تعداد نردبان‌های استفاده‌شده برای لاگین فعلی
        curd.updateLimitLogin(phone=login_info[0])
        
        # دریافت اطلاعات به‌روز شده لاگین
        updated_logins = curd.getCookies(chatid=chatid)
        updated_login = next((l for l in updated_logins if str(l[0]) == str(login_info[0])), login_info)
        
        # اگر موفقیت‌آمیز بود
        try:
            updater.bot.send_message(chat_id=chatid,
                             text=f"آگهی {str(result[1])} از شماره {str(result[2])} نردبان شد.")
            updater.bot.send_message(chat_id=chatid,
                             text=f"از شماره {str(result[2])} تا به حال تعداد {str(updated_login[2])} آگهی نردبان شده است.")
        except Exception as e:
            print(f"Error sending message: {e}")
        return True
    elif result[0] == 0:
        # اگر نردبان موفق نبود
        error_token = result[1] if len(result) > 1 else "unknown"
        error_msg = result[2] if len(result) > 2 else "خطای نامشخص"
        print(f"Failed to nardeban ad with token {error_token}: {error_msg}")
        updater.bot.send_message(chat_id=chatid,
                         text=f"نردبان آگهی با توکن {str(error_token)} با مشکل مواجه شد.\nخطا: {str(error_msg)}")
        return False
    elif result[0] == 2:
        # اگر هیچ پستی موجود نبود
        error_msg = result[1] if len(result) > 1 else "هیچ اگهی برای نردبان پیدا نشد."
        updater.bot.send_message(chat_id=chatid, text=str(error_msg))
        return False
    else:
        # سایر خطاها
        error_msg = result[1] if len(result) > 1 else "خطای نامشخص"
        updater.bot.send_message(chat_id=chatid, text=str(error_msg))
        return False

def remJob(sch, id, chatid):
    try:
        updater.bot.send_message(chat_id=chatid, text="عملیات نردبان شما با موفقیت به پایان رسید !")
        sch.remove_job(id)
        curd.removeJob(chatid=chatid)
        refreshUsed(chatid=chatid)
    except Exception as e:
        try:
            updater.bot.send_message(chat_id=chatid,
                             text=f"در فرایند حذف فرایند زمان بندی نردبان مشکلی وجود دارد ، متن ارور : {str(e)}")
            print(e)
        except Exception as e:
            print(f"Error sending message: {e}")

def reExtractTokens(chatid):
    """استخراج مجدد اگهی‌ها برای تمام لاگین‌های فعال"""
    try:
        logins = curd.getCookies(chatid=chatid)  # 0 : Phone , 1:Cookie , 2 : used
        if not logins:
            updater.bot.send_message(chat_id=chatid, text="⚠️ هیچ لاگین فعالی برای استخراج وجود ندارد.")
            return
        
        total_extracted = 0
        success_count = 0
        failed_count = 0
        
        for l in logins:
            try:
                nardebanAPI = nardeban(apiKey=l[1])
                brandToken = nardebanAPI.getBranToken()
                
                if not brandToken:
                    updater.bot.send_message(chat_id=chatid, 
                                                     text=f"❌ خطا در دریافت brand token برای شماره {l[0]}")
                    failed_count += 1
                    continue
                
                # استخراج توکن‌های جدید
                tokens = nardebanAPI.get_all_tokens(brand_token=brandToken)
                
                if tokens:
                    # حذف توکن‌های قدیمی
                    curd.delete_tokens_by_phone(phone=l[0])
                    # اضافه کردن توکن‌های جدید
                    curd.insert_tokens_by_phone(phone=int(l[0]), tokens=tokens)
                    total_extracted += len(tokens)
                    success_count += 1
                    updater.bot.send_message(chat_id=chatid,
                                                     text=f"✅ از شماره {l[0]}: {len(tokens)} اگهی استخراج شد.")
                else:
                    updater.bot.send_message(chat_id=chatid,
                                                     text=f"⚠️ از شماره {l[0]}: هیچ اگهی‌ای یافت نشد.")
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error extracting tokens for phone {l[0]}: {e}")
                updater.bot.send_message(chat_id=chatid,
                                                 text=f"❌ خطا در استخراج برای شماره {l[0]}: {str(e)}")
                failed_count += 1
        
        # پیام خلاصه
        summary = f"""📊 <b>خلاصه استخراج مجدد:</b>

✅ موفق: {success_count} لاگین
❌ ناموفق: {failed_count} لاگین
📦 کل اگهی‌های استخراج شده: {total_extracted}"""
        updater.bot.send_message(chat_id=chatid, text=summary, parse_mode='HTML')
        
    except Exception as e:
        print(f"Error in reExtractTokens: {e}")
        updater.bot.send_message(chat_id=chatid, text=f"❌ خطا در فرآیند استخراج مجدد: {str(e)}")

def refreshUsed(chatid):
    curd.refreshUsed(chatid)
    curd.remSents(chatid)
    curd.removeJob(chatid=chatid)
    curd.setStatusManage(q="climit", v=0, chatid=chatid)
    numbers = curd.get_phone_numbers_by_chatid(chatid=chatid)
    for n in numbers:
        curd.delete_tokens_by_phone(phone=n)

scheduler = BackgroundScheduler(timezone="Asia/Tehran")

# اضافه کردن handler ها به dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('end', shoro))
dispatcher.add_handler(CommandHandler('add', addadmin, filters=Filters.user(user_id=Datas.admin)))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, mainMenu))
dispatcher.add_handler(CallbackQueryHandler(qrycall))

# اجرای ربات
if __name__ == '__main__':
    try:
        print("=" * 50)
        print("🤖 در حال راه‌اندازی ربات تلگرام...")
        print("=" * 50)
        
        # شروع scheduler
        if not scheduler.running:
            scheduler.start()
        
        # شروع polling با تنظیمات مناسب
        # start_polling() برای PTB 12.8
        print("🔄 در حال شروع polling...")
        updater.start_polling(
            poll_interval=1.0,  # فاصله بین polling ها (ثانیه)
            timeout=10,         # timeout برای هر درخواست
            bootstrap_retries=3  # تعداد تلاش برای اتصال اولیه
        )
        updater.idle()  # نگه داشتن ربات در حال اجرا
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("🔄 ربات در حال اجرا است. برای توقف از Ctrl+C استفاده کنید.")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\n⚠️ ربات توسط کاربر متوقف شد.")
        try:
            updater.stop()
        except:
            pass
        try:
            scheduler.shutdown()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطا در اتصال به تلگرام: {e}")
        print("لطفاً موارد زیر را بررسی کنید:")
        print("  1. اتصال اینترنت")
        print("  2. صحت token ربات در فایل configs.json")
        import traceback
        traceback.print_exc()
        sys.exit(1)
