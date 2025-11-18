import sqlite3
import os

class curdCommands:
    def __init__(self, Datas):
        self.Datas = Datas
        self.db_path = Datas.database  # مسیر فایل دیتابیس SQLite
        
        # اطمینان از وجود دایرکتوری دیتابیس
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
    def _get_connection(self):
        """ایجاد و بازگرداندن اتصال به دیتابیس SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            # فعال کردن foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            print(f"خطا در اتصال به دیتابیس: {e}")
            raise
    
    def cTable_admins(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT, chatid INTEGER UNIQUE)"
            cur.execute(command)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating admins table: {e}")

    def cTable_tokens(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone INTEGER NOT NULL,
                    token TEXT NOT NULL
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating tokens table: {e}")

    def cTable_jobs(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, chatid INTEGER UNIQUE, jobid TEXT)"
            cur.execute(command)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating jobs table: {e}")

    def insert_tokens_by_phone(self, phone, tokens):
        print(phone)
        print(tokens)
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            tokens_combined = ",".join(tokens)
            sql_insert = "INSERT INTO tokens (phone, token) VALUES (?, ?)"
            cur.execute(sql_insert, (phone, tokens_combined))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error inserting tokens: {e}")

    def check_tokens_by_phone(self, phone):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tokens WHERE phone = ?", (phone,))
            exists = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            if exists > 0:
                return 0  # توکن‌هایی برای شماره تلفن وجود دارد
            else:
                return 1  # توکن‌هایی برای شماره تلفن وجود ندارد
        except Exception as e:
            print(f"Error checking tokens: {e}")
            return -1

    def delete_tokens_by_phone(self, phone):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            sql_delete = "DELETE FROM tokens WHERE phone = ?"
            cur.execute(sql_delete, (phone,))
            conn.commit()
            print(f"{cur.rowcount} توکن برای شماره {phone} حذف شد.")
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error deleting tokens: {e}")

    def get_tokens_by_phone(self, phone):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            sql_select = "SELECT token FROM tokens WHERE phone = ?"
            cur.execute(sql_select, (phone,))
            tokens = cur.fetchall()
            
            if not tokens:
                cur.close()
                conn.close()
                return []
            
            token_list = tokens[0][0].split(',')
            cur.close()
            conn.close()
            return token_list
        except Exception as e:
            print(f"Error retrieving tokens: {e}")
            return []

    def addJob(self, chatid, job):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "INSERT OR REPLACE INTO jobs (chatid, jobid) VALUES (?, ?)"
            cur.execute(insrt, (chatid, job))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error adding job: {e}")
            return 0

    def removeJob(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "DELETE FROM jobs WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error removing job: {e}")
            return 0

    def getJob(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT jobid FROM jobs WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            data = cur.fetchone()
            cur.close()
            conn.close()
            if data:
                return data[0]
            else:
                return None
        except Exception as e:
            print(f"Error getting job: {e}")
            return None

    def setAdmin(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "INSERT OR IGNORE INTO admins (chatid) VALUES (?)"
            cur.execute(insrt, (chatid,))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error setting admin: {e}")
            return 0

    def getAdmins(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT chatid FROM admins"
            cur.execute(insrt)
            admin_chatids = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            return admin_chatids
        except Exception as e:
            print(f"Error getting admins: {e}")
            return []

    def remAdmin(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "DELETE FROM admins WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error removing admin: {e}")
            return 0

    def cTable_sents(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "CREATE TABLE IF NOT EXISTS sents(id INTEGER PRIMARY KEY AUTOINCREMENT, chatid INTEGER, token TEXT UNIQUE, status TEXT)"
            cur.execute(command)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating sents table: {e}")

    def cTable_adminp(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "CREATE TABLE IF NOT EXISTS adminp(id INTEGER PRIMARY KEY AUTOINCREMENT, chatid INTEGER UNIQUE, slogin INTEGER, slimit INTEGER, scode INTEGER)"
            cur.execute(command)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating adminp table: {e}")

    def addAdmin(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "INSERT OR IGNORE INTO adminp (chatid, slogin, slimit, scode) VALUES (?, ?, ?, ?)"
            cur.execute(insrt, (chatid, 0, 0, 0))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error adding admin: {e}")
            return 0

    def cTable_logins(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "CREATE TABLE IF NOT EXISTS logins(id INTEGER PRIMARY KEY AUTOINCREMENT, chatid INTEGER, phone INTEGER UNIQUE, cookie TEXT, active INTEGER, used INTEGER)"
            cur.execute(command)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating logins table: {e}")

    def cTable_manage(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "CREATE TABLE IF NOT EXISTS manage(id INTEGER PRIMARY KEY AUTOINCREMENT, chatid INTEGER UNIQUE, active INTEGER, limite INTEGER, climit INTEGER, nardeban_type INTEGER, last_round_robin_phone INTEGER)"
            cur.execute(command)
            # اضافه کردن ستون nardeban_type به جدول موجود (اگر وجود نداشته باشد)
            try:
                cur.execute("ALTER TABLE manage ADD COLUMN nardeban_type INTEGER DEFAULT 1")
                conn.commit()
            except:
                pass  # ستون قبلاً وجود دارد
            # اضافه کردن ستون last_round_robin_phone برای ردیابی آخرین لاگین استفاده شده در نوع نوبتی
            try:
                cur.execute("ALTER TABLE manage ADD COLUMN last_round_robin_phone INTEGER")
                conn.commit()
            except:
                pass  # ستون قبلاً وجود دارد
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error creating manage table: {e}")

    def addManage(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "INSERT OR IGNORE INTO manage (chatid, active, limite, climit, nardeban_type, last_round_robin_phone) VALUES (?, ?, ?, ?, ?, ?)"
            cur.execute(insrt, (chatid, 0, 100, 0, 1, None))  # 1 = ترتیبی کامل هر لاگین (پیش‌فرض)
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error adding manage: {e}")
            return 0

    def addLogin(self, chatid, phone, cookie):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "INSERT OR IGNORE INTO logins (chatid, phone, cookie, active, used) VALUES (?, ?, ?, ?, ?)"
            cur.execute(insrt, (chatid, phone, cookie, 0, 0))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"error to add login , code : {str(e)}")
            return 0

    def delLogin(self, phone):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "DELETE FROM logins WHERE phone = ?"
            cur.execute(insrt, (phone,))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(e)
            return 0

    def setStatus(self, q, v, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            # استفاده از f-string برای نام ستون (امن است چون از داخل کنترل می‌شود)
            insrt = f"UPDATE adminp SET {q} = ? WHERE chatid = ?"
            cur.execute(insrt, (v, chatid))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(e)
            return 0

    def setStatusManage(self, q, v, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = f"UPDATE manage SET {q} = ? WHERE chatid = ?"
            cur.execute(insrt, (v, chatid))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(e)
            return 0

    def getStatusByQ(self, q, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = f"SELECT {q} FROM adminp WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            if result:
                return result[0]
            return 0
        except Exception as e:
            print(e)
            return 0

    def get_phone_numbers_by_chatid(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            command = "SELECT phone FROM logins WHERE chatid = ?"
            cur.execute(command, (chatid,))
            phone_numbers = cur.fetchall()
            cur.close()
            conn.close()
            return [phone[0] for phone in phone_numbers]
        except Exception as e:
            print(f"Error getting phone numbers: {e}")
            return []

    def getStatus(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT slogin, slimit, scode FROM adminp WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            if result:
                return result
            return (0, 0, 0)
        except Exception as e:
            print(e)
            return (0, 0, 0)

    def updateLogin(self, phone, cookie):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "UPDATE logins SET cookie = ? WHERE phone = ?"
            cur.execute(insrt, (cookie, phone))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error updating login: {e}")
            return 0

    def refreshUsed(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "UPDATE logins SET used = ? WHERE chatid = ?"
            cur.execute(insrt, (0, chatid))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error in refresh used, error : {str(e)}")
            return 0

    def updateLimitLogin(self, phone):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "UPDATE logins SET used = used + ? WHERE phone = ?"
            cur.execute(insrt, (1, phone))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error updating limit login: {e}")
            return 0

    def getLimitLogin(self, phone):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT used FROM logins WHERE phone = ?"
            cur.execute(insrt, (phone,))
            data = cur.fetchone()
            cur.close()
            conn.close()
            if data:
                return data[0]
            else:
                return 0
        except Exception as e:
            print(f"Error getting limit login: {e}")
            return 0

    def activeLogin(self, phone, status):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "UPDATE logins SET active = ? WHERE phone = ?"
            cur.execute(insrt, (status, phone))
            conn.commit()
            cur.close()
            conn.close()
            return "Done"
        except Exception as e:
            print(f"Error activating login: {e}")
            return "Error"

    def addSent(self, chatid, token, status):
        """افزودن توکن نردبان شده به دیتابیس - برمی‌گرداند 1 اگر جدید بود، 0 اگر قبلاً وجود داشت"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # چک کردن اینکه آیا توکن قبلاً وجود دارد یا نه
            check_sql = "SELECT id FROM sents WHERE chatid = ? AND token = ?"
            cur.execute(check_sql, (chatid, token))
            existing = cur.fetchone()
            
            if existing:
                # توکن قبلاً وجود دارد
                cur.close()
                conn.close()
                return 0
            
            # توکن جدید است، اضافه می‌کنیم
            insrt = "INSERT INTO sents (chatid, token, status) VALUES (?, ?, ?)"
            cur.execute(insrt, (chatid, token, status))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error adding sent: {e}")
            return 0

    def getCookies(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT phone, cookie, used FROM logins WHERE active = ? AND chatid = ?"
            cur.execute(insrt, (1, chatid))
            data = cur.fetchall()
            cur.close()
            conn.close()
            if data:
                return data
            else:
                return None
        except Exception as e:
            print(f"Error getting cookies: {e}")
            return None

    def getLogins(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT phone, cookie, active FROM logins WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            data = cur.fetchall()
            cur.close()
            conn.close()
            if data:
                return data
            else:
                return 0
        except Exception as e:
            print(f"Error getting logins: {e}")
            return 0

    def getStatusBot(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT active FROM manage WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            data = cur.fetchone()
            cur.close()
            conn.close()
            if data:
                return data[0]
            else:
                return 0
        except Exception as e:
            print(f"Error getting status bot: {e}")
            return 0

    def getManage(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "SELECT active, limite, climit, nardeban_type, last_round_robin_phone FROM manage WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            data = cur.fetchone()
            cur.close()
            conn.close()
            if data:
                # اگر last_round_robin_phone وجود نداشته باشد (None)، به عنوان None برمی‌گردانیم
                return data
            else:
                return (0, 100, 0, 1, None)  # پیش‌فرض: ترتیبی کامل، بدون آخرین لاگین
        except Exception as e:
            print(f"Error getting manage: {e}")
            return (0, 100, 0, 1, None)

    def editLimit(self, newLimit, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "UPDATE manage SET limite = ? WHERE chatid = ?"
            cur.execute(insrt, (int(newLimit), chatid))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error editing limit: {e}")
            return 0

    def get_pending_tokens_by_phone(self, phone, chatid):
        """دریافت لیست توکن‌های pending برای یک شماره خاص"""
        try:
            all_tokens = self.get_tokens_by_phone(phone=phone)
            if not all_tokens:
                return []
            
            conn = self._get_connection()
            cur = conn.cursor()
            # دریافت توکن‌های نردبان شده (success)
            placeholders = ','.join(['?' for _ in all_tokens])
            cur.execute(f"SELECT token FROM sents WHERE chatid = ? AND status = ? AND token IN ({placeholders})", 
                       (chatid, "success") + tuple(all_tokens))
            sent_tokens = {row[0] for row in cur.fetchall()}
            cur.close()
            conn.close()
            
            # برگرداندن توکن‌هایی که نردبان نشده‌اند
            pending = [t for t in all_tokens if t and t.strip() and t not in sent_tokens]
            return pending
        except Exception as e:
            print(f"Error getting pending tokens by phone: {e}")
            return []

    def get_all_pending_tokens(self, chatid):
        """دریافت تمام توکن‌های pending از همه لاگین‌ها به صورت لیست (phone, token)"""
        try:
            phone_numbers = self.get_phone_numbers_by_chatid(chatid=chatid)
            all_pending = []
            
            for phone in phone_numbers:
                pending = self.get_pending_tokens_by_phone(phone=phone, chatid=chatid)
                for token in pending:
                    all_pending.append((phone, token))
            
            return all_pending
        except Exception as e:
            print(f"Error getting all pending tokens: {e}")
            return []

    def get_next_pending_token_by_phone(self, phone, chatid):
        """دریافت اولین توکن pending برای یک شماره (برای حالت نوبتی)"""
        pending = self.get_pending_tokens_by_phone(phone=phone, chatid=chatid)
        return pending[0] if pending else None

    def remSents(self, chatid):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            insrt = "DELETE FROM sents WHERE chatid = ?"
            cur.execute(insrt, (chatid,))
            conn.commit()
            cur.close()
            conn.close()
            return 1
        except Exception as e:
            print(f"Error removing sents: {e}")
            return 0

    def getStats(self, chatid):
        """دریافت آمار اگهی‌ها برای یک chatid (با جزئیات هر لاگین) - استفاده از JSON با ساختار جدید"""
        try:
            from tokens_manager import get_token_stats, load_tokens_json
            
            # دریافت شماره‌های مربوط به این chatid
            phone_numbers = self.get_phone_numbers_by_chatid(chatid=chatid)
            
            # آمار هر لاگین
            login_stats = []
            total_nardeban = 0
            total_tokens_all = 0
            total_pending = 0
            total_failed = 0
            
            # دریافت توکن‌ها از JSON
            tokens_data = load_tokens_json()
            json_tokens_by_phone = tokens_data.get(chatid, {})
            
            for phone in phone_numbers:
                # دریافت آمار برای این phone از JSON
                phone_stats = get_token_stats(chatid=chatid, phone=phone)
                
                pending_count = phone_stats.get("pending", 0)
                success_count = phone_stats.get("success", 0)
                failed_count = phone_stats.get("failed", 0)
                total_count = phone_stats.get("total", 0)
                
                login_stats.append({
                    'phone': phone,
                    'nardeban_count': success_count,
                    'total_tokens': total_count,
                    'pending_count': pending_count,
                    'failed_count': failed_count
                })
                
                total_nardeban += success_count
                total_tokens_all += total_count
                total_pending += pending_count
                total_failed += failed_count
            
            return {
                'login_stats': login_stats,
                'total_nardeban': total_nardeban,
                'total_tokens': total_tokens_all,
                'total_pending': total_pending,
                'total_failed': total_failed
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            import traceback
            traceback.print_exc()
            return {
                'login_stats': [],
                'total_nardeban': 0,
                'total_tokens': 0,
                'total_pending': 0,
                'total_failed': 0
            }


class CreateDB:
    def __init__(self, Datas):
        self.Datas = Datas
        self.db_path = Datas.database
    
    def create(self):
        """ایجاد فایل دیتابیس SQLite (اگر وجود نداشته باشد)"""
        try:
            # SQLite خودکار فایل را ایجاد می‌کند
            conn = sqlite3.connect(self.db_path)
            conn.close()
            print(f"Database file created/verified: {self.db_path}")
        except Exception as e:
            print(f"Error creating database: {e}")
