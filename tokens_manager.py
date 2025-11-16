# -*- coding: utf-8 -*-
"""
ماژول مدیریت توکن‌ها در فایل JSON
"""

import json
import os

TOKENS_JSON_FILE = "tokens.json"

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
        return {}
    except Exception as e:
        print(f"❌ خطا در بارگذاری tokens.json: {e}")
        return {}

def save_tokens_json(tokens_data):
    """ذخیره توکن‌ها در فایل JSON"""
    try:
        # تبدیل کلیدهای int به string برای JSON
        data = {}
        for chatid, phones in tokens_data.items():
            data[str(chatid)] = {}
            for phone, tokens in phones.items():
                data[str(chatid)][str(phone)] = tokens
        
        with open(TOKENS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ خطا در ذخیره tokens.json: {e}")

def add_tokens_to_json(chatid, phone, tokens):
    """اضافه کردن توکن‌ها به JSON"""
    tokens_data = load_tokens_json()
    
    if chatid not in tokens_data:
        tokens_data[chatid] = {}
    
    if phone not in tokens_data[chatid]:
        tokens_data[chatid][phone] = []
    
    # اضافه کردن فقط توکن‌های جدید (غیر تکراری)
    existing = set(tokens_data[chatid][phone])
    new_tokens = [t for t in tokens if t not in existing]
    tokens_data[chatid][phone].extend(new_tokens)
    
    save_tokens_json(tokens_data)
    return len(new_tokens)

def remove_token_from_json(chatid, phone, token):
    """حذف یک توکن از JSON بعد از نردبان موفق"""
    tokens_data = load_tokens_json()
    
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

def get_tokens_from_json(chatid, phone):
    """دریافت توکن‌ها از JSON"""
    tokens_data = load_tokens_json()
    if chatid in tokens_data and phone in tokens_data[chatid]:
        return tokens_data[chatid][phone]
    return []

def get_all_pending_tokens_from_json(chatid):
    """دریافت تمام توکن‌های pending از JSON"""
    tokens_data = load_tokens_json()
    if chatid not in tokens_data:
        return []
    
    all_pending = []
    for phone, tokens in tokens_data[chatid].items():
        for token in tokens:
            all_pending.append((phone, token))
    return all_pending

def has_pending_tokens_in_json(chatid):
    """بررسی اینکه آیا توکن pending در JSON وجود دارد"""
    tokens_data = load_tokens_json()
    if chatid not in tokens_data:
        return False
    
    for phone, tokens in tokens_data[chatid].items():
        if tokens:
            return True
    return False

