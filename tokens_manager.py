# -*- coding: utf-8 -*-
"""
ماژول مدیریت توکن‌ها در فایل JSON
"""

import json
import os

TOKENS_JSON_FILE = "tokens.json"

def _create_empty_json_file():
    """ایجاد فایل JSON خالی"""
    try:
        data = {}
        with open(TOKENS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ فایل {TOKENS_JSON_FILE} ایجاد شد.")
        return True
    except Exception as e:
        print(f"❌ خطا در ایجاد فایل {TOKENS_JSON_FILE}: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_tokens_json():
    """بارگذاری توکن‌ها از فایل JSON"""
    try:
        if os.path.exists(TOKENS_JSON_FILE):
            with open(TOKENS_JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # تبدیل کلیدهای string به int برای سازگاری
                result = {}
                for chatid_str, phones in data.items():
                    chatid_int = int(chatid_str)
                    result[chatid_int] = {}
                    for phone_str, tokens in phones.items():
                        phone_int = int(phone_str)
                        result[chatid_int][phone_int] = tokens
                return result
        else:
            # اگر فایل وجود ندارد، یک فایل خالی ایجاد کن
            print(f"ℹ️ فایل {TOKENS_JSON_FILE} وجود ندارد. فایل خالی ایجاد می‌شود.")
            _create_empty_json_file()
            return {}
    except Exception as e:
        print(f"❌ خطا در بارگذاری tokens.json: {e}")
        import traceback
        traceback.print_exc()
        # در صورت خطا، یک فایل خالی ایجاد کن
        _create_empty_json_file()
        return {}

def save_tokens_json(tokens_data):
    """ذخیره توکن‌ها در فایل JSON - اگر فایل وجود نداشت، ایجاد می‌شود"""
    try:
        # تبدیل کلیدهای int به string برای JSON
        data = {}
        for chatid, phones in tokens_data.items():
            data[str(chatid)] = {}
            for phone, tokens in phones.items():
                data[str(chatid)][str(phone)] = tokens
        
        # اگر data خالی است، یک ساختار خالی ایجاد کن
        if not data:
            data = {}
        
        # ایجاد فایل JSON (حتی اگر خالی باشد) - اگر وجود نداشت، خودکار ایجاد می‌شود
        with open(TOKENS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # بررسی اینکه فایل واقعاً ایجاد شده است
        if os.path.exists(TOKENS_JSON_FILE):
            print(f"✅ فایل {TOKENS_JSON_FILE} با موفقیت ذخیره شد.")
        else:
            print(f"⚠️ فایل {TOKENS_JSON_FILE} ایجاد نشد!")
    except Exception as e:
        print(f"❌ خطا در ذخیره tokens.json: {e}")
        import traceback
        traceback.print_exc()
        # در صورت خطا، سعی کن فایل خالی ایجاد کنی
        try:
            _create_empty_json_file()
        except:
            pass

def add_tokens_to_json(chatid, phone, tokens):
    """اضافه کردن توکن‌ها به JSON"""
    try:
        print(f"📝 [add_tokens_to_json] شروع: chatid={chatid}, phone={phone}, تعداد توکن‌ها={len(tokens)}")
        
        tokens_data = load_tokens_json()
        print(f"📝 [add_tokens_to_json] داده‌های موجود: {len(tokens_data)} chatid")
        
        if chatid not in tokens_data:
            tokens_data[chatid] = {}
            print(f"📝 [add_tokens_to_json] chatid جدید اضافه شد: {chatid}")
        
        if phone not in tokens_data[chatid]:
            tokens_data[chatid][phone] = []
            print(f"📝 [add_tokens_to_json] phone جدید اضافه شد: {phone}")
        
        # اضافه کردن فقط توکن‌های جدید (غیر تکراری)
        existing = set(tokens_data[chatid][phone])
        new_tokens = [t for t in tokens if t not in existing]
        tokens_data[chatid][phone].extend(new_tokens)
        
        print(f"📝 [add_tokens_to_json] {len(new_tokens)} توکن جدید اضافه شد (از {len(tokens)} توکن)")
        
        save_tokens_json(tokens_data)
        print(f"✅ [add_tokens_to_json] توکن‌ها با موفقیت ذخیره شدند")
        
        return len(new_tokens)
    except Exception as e:
        print(f"❌ [add_tokens_to_json] خطا: {e}")
        import traceback
        traceback.print_exc()
        return 0

def remove_token_from_json(chatid, phone, token):
    """حذف یک توکن از JSON بعد از نردبان موفق - اگر فایل وجود نداشت، ایجاد می‌شود"""
    try:
        tokens_data = load_tokens_json()  # این تابع خودش فایل را ایجاد می‌کند اگر وجود نداشته باشد
        
        if chatid in tokens_data and phone in tokens_data[chatid]:
            if token in tokens_data[chatid][phone]:
                tokens_data[chatid][phone].remove(token)
                # اگر لیست توکن‌ها خالی شد، آن را حذف کن
                if not tokens_data[chatid][phone]:
                    del tokens_data[chatid][phone]
                # اگر لیست شماره‌ها خالی شد، آن را حذف کن
                if not tokens_data[chatid]:
                    del tokens_data[chatid]
                
                save_tokens_json(tokens_data)
                return True
        return False
    except Exception as e:
        print(f"❌ خطا در حذف توکن از JSON: {e}")
        return False

def get_tokens_from_json(chatid, phone):
    """دریافت توکن‌ها از JSON - اگر فایل وجود نداشت، ایجاد می‌شود"""
    tokens_data = load_tokens_json()  # این تابع خودش فایل را ایجاد می‌کند اگر وجود نداشته باشد
    if chatid in tokens_data and phone in tokens_data[chatid]:
        return tokens_data[chatid][phone]
    return []

def get_all_pending_tokens_from_json(chatid):
    """دریافت تمام توکن‌های pending از JSON - اگر فایل وجود نداشت، ایجاد می‌شود"""
    tokens_data = load_tokens_json()  # این تابع خودش فایل را ایجاد می‌کند اگر وجود نداشته باشد
    if chatid not in tokens_data:
        return []
    
    all_pending = []
    for phone, tokens in tokens_data[chatid].items():
        for token in tokens:
            all_pending.append((phone, token))
    return all_pending

def has_pending_tokens_in_json(chatid):
    """بررسی اینکه آیا توکن pending در JSON وجود دارد - اگر فایل وجود نداشت، ایجاد می‌شود"""
    tokens_data = load_tokens_json()  # این تابع خودش فایل را ایجاد می‌کند اگر وجود نداشته باشد
    if chatid not in tokens_data:
        return False
    
    for phone, tokens in tokens_data[chatid].items():
        if tokens:
            return True
    return False

