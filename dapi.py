# This Python file uses the following encoding: utf-8

import requests,json
import time
from loadConfig import configBot
from curds import curdCommands,CreateDB

class api:
    def __init__(self):
        self.author = "ATRISK"
        self.headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-S918B Build/TP1A.220624.014)",
            "X-Device-Model": "SM-S918B",
            "X-OS-Version": "13",
            "X-Platform": "android",
            "Content-Type": "application/json",
            "Accept": "*/*"
        }
    
    def login(self, phone: str):
        url = "https://api.divar.ir/v5/auth/authenticate"
        data = {"phone": phone}
        sendCode = requests.post(url=url, headers=self.headers, json=data)
        return sendCode.json()

    def verifyOtp(self, phone: str, code: str):
        url = "https://api.divar.ir/v5/auth/confirm"
        data = {"phone": str(phone), "code": code}
        confirm = requests.post(url=url, headers=self.headers, json=data)
        return confirm.json()  # token is : {'token':''}

class nardeban:
    def __init__(self,apiKey):
        self.apikey = apiKey
        self.Datas = configBot()
        self.curd = curdCommands(self.Datas)
        # Header اصلی برای درخواست‌های نردبان
        self.headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-S918B Build/TP1A.220624.014)",
            "X-Device-Model": "SM-S918B",
            "X-OS-Version": "13",
            "X-Platform": "android",
            "Content-Type": "application/json",
            "Accept": "*/*",
            'Authorization': f'Basic {str(self.apikey)}',
        }
        self.cookies = {
            '_ga': 'GA1.2.600389233.1620222355',
            '_ga_SXEW31VJGJ': 'GS1.1.1727021501.44.1.1727022691.56.0.0',
            'did': '4fd58ceb-b62e-4eba-aa9b-29ab65717dc7',
            'FEATURE_FLAG': '%7B%22flags%22%3A%7B%22location_selector_enabled%22%3A%7B%22name%22%3A%22location_selector_enabled%22%2C%22bool_value%22%3Afalse%7D%2C%22location_selector_ux_adaption%22%3A%7B%22name%22%3A%22location_selector_ux_adaption%22%2C%22bool_value%22%3Afalse%7D%2C%22location_selector_enabled_with_defaults%22%3A%7B%22name%22%3A%22location_selector_enabled_with_defaults%22%2C%22bool_value%22%3Afalse%7D%2C%22custom_404_experiment%22%3A%7B%22name%22%3A%22custom_404_experiment%22%2C%22bool_value%22%3Atrue%7D%2C%22web_shopping_assistant_enabled%22%3A%7B%22name%22%3A%22web_shopping_assistant_enabled%22%2C%22bool_value%22%3Afalse%7D%2C%22web_shopping_assistant_enabled_on_all_cats%22%3A%7B%22name%22%3A%22web_shopping_assistant_enabled_on_all_cats%22%2C%22bool_value%22%3Afalse%7D%2C%22explore%22%3A%7B%22name%22%3A%22explore%22%2C%22bool_value%22%3Afalse%7D%2C%22enable_new_post_card_web%22%3A%7B%22name%22%3A%22enable_new_post_card_web%22%2C%22bool_value%22%3Afalse%7D%2C%22web_show_ios_appstore_promotion_banner%22%3A%7B%22name%22%3A%22web_show_ios_appstore_promotion_banner%22%2C%22bool_value%22%3Afalse%7D%2C%22chat_translate_enabled%22%3A%7B%22name%22%3A%22chat_translate_enabled%22%2C%22bool_value%22%3Atrue%7D%2C%22post-card-title-top%22%3A%7B%22name%22%3A%22post-card-title-top%22%2C%22bool_value%22%3Atrue%7D%2C%22post-card-small-img%22%3A%7B%22name%22%3A%22post-card-small-img%22%2C%22bool_value%22%3Afalse%7D%2C%22map_discovery_halfMapTest_active%22%3A%7B%22name%22%3A%22map_discovery_halfMapTest_active%22%2C%22bool_value%22%3Afalse%7D%2C%22map_discovery_halfMapTest_map_state%22%3A%7B%22name%22%3A%22map_discovery_halfMapTest_map_state%22%2C%22string_value%22%3A%22HALF_MAP%22%7D%7D%2C%22evaluatedAt%22%3A%222024-09-22T16%3A11%3A40.117895503Z%22%2C%22maximumCacheUsageSecondsOnError%22%3A86400%2C%22minimumRefetchIntervalSeconds%22%3A3600%2C%22expireDate%22%3A1727025100125%7D',
            '_gcl_au': '1.1.1878132329.1726746171',
            'LANGUAGE': 'fa',
            'theme': 'light',
           'token': apiKey,
            '_gid': 'GA1.2.766956976.1727008200',
            'access-token': '',
            'chat_opened': '',
            'sessionid': '',
            'csid': '',
            '_gat': '1',
            '_gat_UA-32884252-2': '1',
        }

    def selectPlan(self,token):
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-S918B Build/TP1A.220624.014)",
            "X-Device-Model": "SM-S918B",
            "X-OS-Version": "13",
            "X-Platform": "android",
            "Content-Type": "application/json",
            "Accept": "*/*",
            'Authorization': f'Basic {str(self.apikey)}',
        }
        
        # تلاش برای دریافت اطلاعات با retry در صورت timeout
        max_retries = 3
        retry_delay = 2  # ثانیه
        res = None
        
        for attempt in range(max_retries):
            try:
                res = requests.get(f'https://api.divar.ir/v8/payment/costs/{token}',
                                   headers=headers, timeout=30)
                break  # اگر موفق بود، از حلقه خارج شو
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    # اگر آخرین تلاش نبود، صبر کن و دوباره تلاش کن
                    time.sleep(retry_delay)
                    continue
                else:
                    raise ValueError(f"Request timeout after {max_retries} attempts: {str(e)}")
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Request failed: {str(e)}")
        
        # بررسی اینکه res تعریف شده باشد
        if res is None:
            raise ValueError("Request failed: no response received after all retries")
        
        if res.status_code != 200:
            error_msg = f"HTTP {res.status_code}"
            try:
                error_data = res.json()
                if isinstance(error_data, dict):
                    error_msg_detail = error_data.get('error', {})
                    if isinstance(error_msg_detail, dict):
                        error_msg += f": {error_msg_detail.get('message', error_msg_detail.get('type', 'Unknown error'))}"
                    elif isinstance(error_msg_detail, str):
                        error_msg += f": {error_msg_detail}"
                    else:
                        error_msg += f": {str(error_data.get('message', res.text[:150]))}"
                else:
                    error_msg += f": {str(error_data)[:150]}"
            except Exception:
                error_text = res.text[:200] if res.text else "No response body"
                error_msg += f": {error_text}"
            raise ValueError(error_msg)
        
        try:
            response_data = res.json()
        except Exception as e:
            raise ValueError(f"invalid costs response: {str(e)}")
        
        # بررسی وجود کلید 'costs' در پاسخ
        if not isinstance(response_data, dict) or 'costs' not in response_data:
            raise ValueError(f"costs not found in response: {response_data}")
        
        data = response_data['costs']
        
        # بررسی اینکه data یک لیست است و حداقل یک عنصر دارد
        if not isinstance(data, list):
            raise ValueError(f"costs is not a list: {type(data)}")
        
        if len(data) == 0:
            raise ValueError("no costs/plans available for this post")
        
        # بررسی وجود حداقل یک عنصر برای data[0]
        if len(data) < 1:
            raise ValueError("costs list is empty")
        
        # اگر داده‌ها کافی است، بررسی index 2
        if len(data) >= 3:
            # بررسی اینکه data[2] یک دیکشنری است و دارای 'available' و 'id' است
            if isinstance(data[2], dict) and data[2].get('available') == True:
                plan_id = data[2].get('id')
                if plan_id:
                    return plan_id
        
        # اگر data[2] در دسترس نبود یا وجود نداشت، از data[0] استفاده کن
        if isinstance(data[0], dict):
            plan_id = data[0].get('id')
            if plan_id:
                return plan_id
            else:
                raise ValueError("plan id not found in data[0]")
        else:
            raise ValueError(f"data[0] is not a dict: {type(data[0])}")

    def createOrderID(self,token,planPrice):
        json_data = {
            'cost_ids': [
                planPrice,
            ],
            'cost_to_option': {
            },
        }
        
        # تلاش برای ایجاد سفارش با retry در صورت timeout
        max_retries = 3
        retry_delay = 2  # ثانیه
        response = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f'https://api.divar.ir/v8/payment/start/post/{token}',
                    headers=self.headers,
                    json=json_data,
                    timeout=30
                )
                break  # اگر موفق بود، از حلقه خارج شو
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    raise ValueError(f"Request timeout after {max_retries} attempts: {str(e)}")
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Request failed: {str(e)}")
        
        # بررسی اینکه response تعریف شده باشد
        if response is None:
            raise ValueError("Request failed: no response received after all retries")
        
        # بررسی status code
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    if 'error' in error_data:
                        error_msg_detail = error_data.get('error', {})
                        if isinstance(error_msg_detail, dict):
                            error_msg += f": {error_msg_detail.get('message', error_msg_detail.get('type', error_msg_detail.get('code', 'Unknown error')))}"
                        elif isinstance(error_msg_detail, str):
                            error_msg += f": {error_msg_detail}"
                        else:
                            error_msg += f": {str(error_data.get('message', response.text[:150]))}"
                    elif 'message' in error_data:
                        error_msg += f": {error_data.get('message')}"
                    else:
                        error_msg += f": {str(error_data)[:150]}"
                elif isinstance(error_data, str):
                    error_msg += f": {error_data[:150]}"
                else:
                    error_msg += f": {str(error_data)[:150]}"
            except Exception:
                error_text = response.text[:200] if response.text else "No response body"
                error_msg += f": {error_text}"
            raise ValueError(error_msg)
        
        # بررسی و استخراج order_id
        try:
            response_data = response.json()
        except Exception as e:
            raise ValueError(f"invalid response: {str(e)}")
        
        if not isinstance(response_data, dict):
            raise ValueError(f"response is not a dict: {type(response_data)}")
        
        if 'order_id' not in response_data:
            raise ValueError(f"order_id not found in response: {response_data}")
        
        order_id = response_data.get('order_id')
        if not order_id:
            raise ValueError("order_id is empty or None")
        
        return order_id

    def createFlow(self,order):
        requests.get(f'https://api.divar.ir/v8/paymentcore/flow/{order}', headers=self.headers)
    def createCheckOut(self,order):
        response = requests.get(f'https://api.divar.ir/v8/paymentcore/bazaarpay/initiate/{order}',
                                headers=self.headers)
        try:
            if response.status_code != 200:
                print(f"Error in createCheckOut: status code {response.status_code}")
                raise Exception(f"HTTP {response.status_code}")
            data = response.json()
            if 'checkout_token' not in data:
                raise Exception("checkout_token not found in response")
            return data['checkout_token']
        except Exception as e:
            print(f"Error in createCheckOut: {e}")
            raise

    def pay(self,orderid,checkout,number):
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-S918B Build/TP1A.220624.014)",
            "X-Device-Model": "SM-S918B",
            "X-OS-Version": "13",
            "X-Platform": "android",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        params = {
            'checkout_token': checkout,
        }
        json_data = {
            'checkout_token': checkout,
            'method': 'enough_balance',
            'redirect_url': f'https://cafebazaar.ir/bazaar-pay/payment/status?token={checkout}&phone=98{number}&callback=%7B%22url%22%3A%22https%3A%2F%2Fapi.divar.ir%2Fv8%2Fpaymentcore%2Fbazaarpay%2Fcallback%2F{orderid}%22%2C%22method%22%3A%22post%22%2C%22data%22%3A%7B%7D%7D&auth_mode=authenticated_token',
        }
        requests.post('https://api.bazaar-pay.ir/badje/v1/pay/', params=params, headers=headers,
                                 json=json_data)
    def promote(self,orderid,token):
        a = requests.get(url=f'https://divar.ir/real-estate/admin/posts/{token}/promote?payment_order_id={orderid}',
                         headers=self.headers)
    def isValidPost(self,uid):
        response = requests.get(
            f'https://api.divar.ir/v8/post-management-page/web-page/{uid}',
            headers=self.headers,
        )
        try:
            isValid = response.json()['show_delete_post']
        except Exception as e:
            print(e)
            return 0
        else:
            if isValid == True:
                return 1
            else:
                return 0
    def getPosts(self):
        tokens = []
        brantToken = self.getBranToken()
        json_data = {
            'brand_token': brantToken,
            'specification': {
                'query': '',
                'last_item_identifier': '',
            },
        }
        response = requests.post(f'https://api.divar.ir/v8/premium-user/web/business/{brantToken}/post-list',
                                 headers=self.headers, json=json_data)
        res = response.json()
        for i in res['page']['widget_list']:
            try:
                token = i['uid']
            except Exception as e:
                print(e)
                pass
            else:
                if token not in tokens:
                    if self.isValidPost(uid=token) == 1:
                        tokens.append(token)
        return tokens

    def get_all_tokens(self, brand_token):
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-S918B Build/TP1A.220624.014)",
            "X-Device-Model": "SM-S918B",
            "X-OS-Version": "13",
            "X-Platform": "android",
            "Content-Type": "application/json",
            "Accept": "*/*",
            'Authorization': f'Basic {self.apikey}',
        }

        last_item_identifier = ''
        all_tokens = []
        while True:
            json_data = {
                'brand_token': brand_token,
                'specification': {
                    'query': '',
                    'last_item_identifier': last_item_identifier,
                },
            }

            response = requests.post(f'https://api.divar.ir/v8/premium-user/web/business/{brand_token}/post-list',
                                     headers=headers, json=json_data)

            if response.status_code == 200:
                data = response.json()
                widgets = data.get('page', {}).get('widget_list', [])
                # استخراج توکن‌ها از widget_list
                for widget in widgets:
                    if widget.get('widget_type') == 'POST_ROW' and widget.get('data', {}).get('label') == "منتشر شده":
                        token = widget['uid']
                        if token:
                            all_tokens.append(token)

                infinite_scroll_response = data.get('page', {}).get('infinite_scroll_response', {})
                has_next = infinite_scroll_response.get('last_item_identifier')
                if not has_next:
                    break  # اگر has_next False باشد، از حلقه خارج می‌شود

                last_item_identifier = has_next  # به‌روزرسانی برای درخواست بعدی
            else:
                print(f"Error: {response.status_code}")
                break

        return all_tokens

    def getBranToken(self):
        try:
            response = requests.get('https://api.divar.ir/v8/premium-user/web/get-business-list-web', headers=self.headers)
            bToken = response.json()['business_data_list'][0]['brand_token']
        except Exception as e:
            print(e)
            return None
        else:
            return bToken

    def sendNardeban(self, number, chatid):
        iPost = -1
        # دریافت توکن‌های pending از JSON
        from tokens_manager import get_tokens_from_json
        
        tokens = get_tokens_from_json(chatid=chatid, phone=int(number), status="pending")
        
        if not tokens:
            # هیچ توکن pending وجود ندارد
            return [2, "هیچ اگهی برای نردبان پیدا نشد."]
        
        # انتخاب اولین توکن از لیست (قدیمی‌ترین)
        token = tokens[0] if tokens else None
        
        if not token:
            # هیچ توکن pending پیدا نشد
            return [2, "هیچ اگهی برای نردبان پیدا نشد."]
        
        # حالا توکن pending را پیدا کردیم، نردبان را انجام می‌دهیم
        try:
            planCost = int(self.selectPlan(token=token))
        except Exception as e:
            # خطا در انتخاب پلن
            error_msg = str(e).strip()
            if not error_msg:
                error_msg = "Unknown error"
            print(f"selectPlan error for token {token}: {error_msg}")
            self.curd.addSent(token=token, chatid=chatid, status="failed")
            # برگرداندن پیام خطای دقیق‌تر (با محدودیت طول برای جلوگیری از پیام‌های خیلی طولانی)
            error_display = error_msg[:150] if len(error_msg) > 150 else error_msg
            return [0, token, f"selectPlan: {error_display}"]
        else:
            try:
                orderId = self.createOrderID(token=token, planPrice=planCost)
            except Exception as e:
                # خطا در ایجاد سفارش
                error_msg = str(e).strip()
                if not error_msg:
                    error_msg = "Unknown error"
                print(f"createOrderID error for token {token}: {error_msg}")
                self.curd.addSent(token=token, chatid=chatid, status="failed")
                error_display = error_msg[:150] if len(error_msg) > 150 else error_msg
                return [0, token, f"createOrderID: {error_display}"]
            else:
                try:
                    self.createFlow(order=orderId)
                except Exception as e:
                    print(e)
                    self.curd.addSent(token=token, chatid=chatid, status="failed")
                    return [0, token, "createFlow"]
                else:
                    try:
                        checkout = self.createCheckOut(order=orderId)
                    except Exception as e:
                        print(e)
                        self.curd.addSent(token=token, chatid=chatid, status="failed")
                        return [0, token, "createCheckOut"]
                    else:
                        try:
                            self.pay(orderid=orderId, checkout=checkout, number=str(number))
                        except Exception as e:
                            print(e)
                            self.curd.addSent(token=token, chatid=chatid, status="failed")
                            return [0, token, "pay"]
                        else:
                            try:
                                self.promote(orderid=orderId, token=token)
                            except Exception as e:
                                print(e)
                                self.curd.addSent(token=token, chatid=chatid, status="failed")
                                return [0, token, "promote"]
                            else:
                                # فقط در صورت موفقیت کامل، توکن را به عنوان success ذخیره می‌کنیم
                                self.curd.addSent(token=token, chatid=chatid, status="success")
                                # بازگشت لیست با مقدار [1, token, number] در صورت موفقیت
                                return [1, token, number]

    def sendNardebanWithToken(self, number, chatid, token):
        """نردبان یک توکن خاص"""
        # چک کردن اینکه توکن قبلاً نردبان نشده باشد
        # بررسی اینکه آیا این توکن در لیست pending است یا نه
        pending_tokens = self.curd.get_pending_tokens_by_phone(phone=number, chatid=chatid)
        if token not in pending_tokens:
            # توکن قبلاً نردبان شده است
            return [0, token, "این توکن قبلاً نردبان شده است"]
        
        try:
            planCost = int(self.selectPlan(token=token))
        except Exception as e:
            error_msg = str(e).strip()
            if not error_msg:
                error_msg = "Unknown error"
            print(f"selectPlan error for token {token}: {error_msg}")
            self.curd.addSent(token=token, chatid=chatid, status="failed")
            error_display = error_msg[:150] if len(error_msg) > 150 else error_msg
            return [0, token, f"selectPlan: {error_display}"]
        else:
            try:
                orderId = self.createOrderID(token=token, planPrice=planCost)
            except Exception as e:
                error_msg = str(e).strip()
                if not error_msg:
                    error_msg = "Unknown error"
                print(f"createOrderID error for token {token}: {error_msg}")
                self.curd.addSent(token=token, chatid=chatid, status="failed")
                error_display = error_msg[:150] if len(error_msg) > 150 else error_msg
                return [0, token, f"createOrderID: {error_display}"]
            else:
                try:
                    self.createFlow(order=orderId)
                except Exception as e:
                    print(e)
                    self.curd.addSent(token=token, chatid=chatid, status="failed")
                    return [0, token, "createFlow"]
                else:
                    try:
                        checkout = self.createCheckOut(order=orderId)
                    except Exception as e:
                        print(e)
                        self.curd.addSent(token=token, chatid=chatid, status="failed")
                        return [0, token, "createCheckOut"]
                    else:
                        try:
                            self.pay(orderid=orderId, checkout=checkout, number=str(number))
                        except Exception as e:
                            print(e)
                            self.curd.addSent(token=token, chatid=chatid, status="failed")
                            return [0, token, "pay"]
                        else:
                            try:
                                self.promote(orderid=orderId, token=token)
                            except Exception as e:
                                print(e)
                                self.curd.addSent(token=token, chatid=chatid, status="failed")
                                return [0, token, "promote"]
                            else:
                                # فقط در صورت موفقیت کامل، توکن را به عنوان success ذخیره می‌کنیم
                                self.curd.addSent(token=token, chatid=chatid, status="success")
                                return [1, token, number]
