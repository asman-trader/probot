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
            self.admin = int(self.config['admin']) if self.config.get('admin') is not None else None
            self.times = self.config['times']
            
            # برای سازگاری با کد قدیمی (اگر جایی استفاده شده باشد)
            self.host = None
            self.user = None
            self.passwd = None
