import json
import os

class configBot:
    def __init__(self):
        with open('configs.json', encoding="utf8") as data:
            self.config = json.load(data)
            # برای SQLite فقط نام فایل دیتابیس نیاز است
            # اگر مسیر کامل نباشد، در همان پوشه فعلی ایجاد می‌شود
            db_name = self.config.get('database', 'bot.db')
            if not os.path.isabs(db_name):
                # اگر مسیر نسبی است، در پوشه فعلی قرار می‌گیرد
                self.database = db_name
            else:
                self.database = db_name
            
            self.token = self.config['token']
            # تبدیل admin به int برای اطمینان از مقایسه صحیح
            admin_value = self.config.get('admin')
            if admin_value is not None:
                try:
                    # تبدیل به int (ممکن است string یا int باشد)
                    if isinstance(admin_value, str):
                        self.admin = int(admin_value.strip())
                    else:
                        self.admin = int(admin_value)
                    print(f"✅ [loadConfig] Admin پیش‌فرض: {self.admin} (type: {type(self.admin)})")
                except (ValueError, TypeError) as e:
                    print(f"❌ [loadConfig] خطا در تبدیل admin به int: {e} (admin: {admin_value}, type: {type(admin_value)})")
                    self.admin = None
            else:
                self.admin = None
                print("⚠️ [loadConfig] admin در فایل configs.json تعریف نشده است!")
            self.times = self.config['times']
            
            # برای سازگاری با کد قدیمی (اگر جایی استفاده شده باشد)
            self.host = None
            self.user = None
            self.passwd = None
