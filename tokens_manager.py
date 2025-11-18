# -*- coding: utf-8 -*-
"""
ماژول مدیریت توکن‌ها در فایل JSON
ساختار جدید: هر توکن با وضعیت (pending, success, failed) ذخیره می‌شود
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

def _migrate_old_format_to_new(data):
    """تبدیل ساختار قدیمی به ساختار جدید"""
    try:
        migrated = {}
        for chatid_str, phones in data.items():
            chatid_int = int(chatid_str)
            migrated[chatid_int] = {}
            
            for phone_str, tokens in phones.items():
                phone_int = int(phone_str)
                
                # اگر tokens یک لیست ساده است (ساختار قدیمی)
                if isinstance(tokens, list):
                    # همه توکن‌های قدیمی را به pending تبدیل می‌کنیم
                    migrated[chatid_int][phone_int] = {
                        "pending": tokens,
                        "success": [],
                        "failed": []
                    }
                # اگر tokens یک دیکشنری است (ساختار جدید)
                elif isinstance(tokens, dict):
                    # اطمینان از وجود همه کلیدها
                    migrated[chatid_int][phone_int] = {
                        "pending": tokens.get("pending", []),
                        "success": tokens.get("success", []),
                        "failed": tokens.get("failed", [])
                    }
        
        return migrated
    except Exception as e:
        print(f"⚠️ خطا در تبدیل ساختار قدیمی: {e}")
        return data

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
                
                # تبدیل ساختار قدیمی به جدید (اگر لازم باشد)
                result = _migrate_old_format_to_new(result)
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
            for phone, status_dict in phones.items():
                data[str(chatid)][str(phone)] = status_dict
        
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
    """اضافه کردن توکن‌ها به JSON با وضعیت pending"""
    try:
        print(f"📝 [add_tokens_to_json] شروع: chatid={chatid}, phone={phone}, تعداد توکن‌ها={len(tokens)}")
        
        tokens_data = load_tokens_json()
        print(f"📝 [add_tokens_to_json] داده‌های موجود: {len(tokens_data)} chatid")
        
        if chatid not in tokens_data:
            tokens_data[chatid] = {}
            print(f"📝 [add_tokens_to_json] chatid جدید اضافه شد: {chatid}")
        
        if phone not in tokens_data[chatid]:
            tokens_data[chatid][phone] = {
                "pending": [],
                "success": [],
                "failed": []
            }
            print(f"📝 [add_tokens_to_json] phone جدید اضافه شد: {phone}")
        
        # دریافت تمام توکن‌های موجود (از همه وضعیت‌ها)
        all_existing = set(tokens_data[chatid][phone]["pending"] + 
                          tokens_data[chatid][phone]["success"] + 
                          tokens_data[chatid][phone]["failed"])
        
        # اضافه کردن فقط توکن‌های جدید (غیر تکراری) به pending
        new_tokens = [t for t in tokens if t not in all_existing]
        tokens_data[chatid][phone]["pending"].extend(new_tokens)
        
        print(f"📝 [add_tokens_to_json] {len(new_tokens)} توکن جدید اضافه شد (از {len(tokens)} توکن)")
        
        save_tokens_json(tokens_data)
        print(f"✅ [add_tokens_to_json] توکن‌ها با موفقیت ذخیره شدند")
        
        return len(new_tokens)
    except Exception as e:
        print(f"❌ [add_tokens_to_json] خطا: {e}")
        import traceback
        traceback.print_exc()
        return 0

def update_token_status(chatid, phone, token, new_status):
    """به‌روزرسانی وضعیت یک توکن (pending -> success/failed)"""
    try:
        tokens_data = load_tokens_json()
        
        if chatid not in tokens_data or phone not in tokens_data[chatid]:
            print(f"⚠️ توکن {token} یافت نشد برای به‌روزرسانی")
            return False
        
        status_dict = tokens_data[chatid][phone]
        
        # حذف توکن از وضعیت قبلی
        removed = False
        for status in ["pending", "success", "failed"]:
            if token in status_dict[status]:
                status_dict[status].remove(token)
                removed = True
                break
        
        if not removed:
            print(f"⚠️ توکن {token} در هیچ وضعیتی یافت نشد")
            return False
        
        # اضافه کردن توکن به وضعیت جدید
        if new_status in ["pending", "success", "failed"]:
            status_dict[new_status].append(token)
            save_tokens_json(tokens_data)
            print(f"✅ توکن {token} به وضعیت {new_status} تغییر یافت")
            return True
        else:
            print(f"❌ وضعیت نامعتبر: {new_status}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در به‌روزرسانی وضعیت توکن: {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_token_from_json(chatid, phone, token):
    """حذف یک توکن از JSON - DEPRECATED: استفاده از update_token_status به جای این"""
    # برای سازگاری با کد قدیمی، این تابع وضعیت را به success تغییر می‌دهد
    return update_token_status(chatid, phone, token, "success")

def get_tokens_from_json(chatid, phone, status="pending"):
    """دریافت توکن‌ها از JSON با وضعیت مشخص - اگر فایل وجود نداشت، ایجاد می‌شود"""
    tokens_data = load_tokens_json()
    if chatid in tokens_data and phone in tokens_data[chatid]:
        status_dict = tokens_data[chatid][phone]
        if isinstance(status_dict, dict) and status in status_dict:
            return status_dict[status]
        # سازگاری با ساختار قدیمی
        elif isinstance(status_dict, list):
            return status_dict if status == "pending" else []
    return []

def get_all_pending_tokens_from_json(chatid):
    """دریافت تمام توکن‌های pending از JSON - اگر فایل وجود نداشت، ایجاد می‌شود"""
    tokens_data = load_tokens_json()
    if chatid not in tokens_data:
        return []
    
    all_pending = []
    for phone, status_dict in tokens_data[chatid].items():
        if isinstance(status_dict, dict):
            pending_tokens = status_dict.get("pending", [])
        else:
            # سازگاری با ساختار قدیمی
            pending_tokens = status_dict if isinstance(status_dict, list) else []
        
        for token in pending_tokens:
            all_pending.append((phone, token))
    return all_pending

def get_all_tokens_by_status(chatid, status="pending"):
    """دریافت تمام توکن‌ها با وضعیت مشخص از JSON"""
    tokens_data = load_tokens_json()
    if chatid not in tokens_data:
        return []
    
    all_tokens = []
    for phone, status_dict in tokens_data[chatid].items():
        if isinstance(status_dict, dict):
            tokens = status_dict.get(status, [])
        else:
            # سازگاری با ساختار قدیمی
            tokens = status_dict if isinstance(status_dict, list) and status == "pending" else []
        
        for token in tokens:
            all_tokens.append((phone, token))
    return all_tokens

def has_pending_tokens_in_json(chatid):
    """بررسی اینکه آیا توکن pending در JSON وجود دارد - اگر فایل وجود نداشت، ایجاد می‌شود"""
    tokens_data = load_tokens_json()
    if chatid not in tokens_data:
        return False
    
    for phone, status_dict in tokens_data[chatid].items():
        if isinstance(status_dict, dict):
            if status_dict.get("pending", []):
                return True
        else:
            # سازگاری با ساختار قدیمی
            if isinstance(status_dict, list) and status_dict:
                return True
    return False

def get_token_stats(chatid, phone=None):
    """دریافت آمار توکن‌ها برای یک chatid یا phone خاص"""
    tokens_data = load_tokens_json()
    if chatid not in tokens_data:
        return {
            "pending": 0,
            "success": 0,
            "failed": 0,
            "total": 0
        }
    
    stats = {
        "pending": 0,
        "success": 0,
        "failed": 0,
        "total": 0
    }
    
    if phone:
        # آمار برای یک phone خاص
        if phone in tokens_data[chatid]:
            status_dict = tokens_data[chatid][phone]
            if isinstance(status_dict, dict):
                stats["pending"] = len(status_dict.get("pending", []))
                stats["success"] = len(status_dict.get("success", []))
                stats["failed"] = len(status_dict.get("failed", []))
            else:
                # سازگاری با ساختار قدیمی
                stats["pending"] = len(status_dict) if isinstance(status_dict, list) else 0
            stats["total"] = stats["pending"] + stats["success"] + stats["failed"]
    else:
        # آمار برای تمام phone ها
        for phone_key, status_dict in tokens_data[chatid].items():
            if isinstance(status_dict, dict):
                stats["pending"] += len(status_dict.get("pending", []))
                stats["success"] += len(status_dict.get("success", []))
                stats["failed"] += len(status_dict.get("failed", []))
            else:
                # سازگاری با ساختار قدیمی
                stats["pending"] += len(status_dict) if isinstance(status_dict, list) else 0
        
        stats["total"] = stats["pending"] + stats["success"] + stats["failed"]
    
    return stats
