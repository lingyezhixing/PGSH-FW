import time
import json
import requests
from jsonpath_ng import parse

BASE_URL = 'https://userapi.qiekj.com'


class QiekjAPI:
    def __init__(self, token: str = ''):
        self.token = token

    def _timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def _headers(self, auth: bool = True) -> dict:
        h = {
            'Version': '1.59.3',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'User-Agent': 'okhttp/3.14.9',
            'timestamp': self._timestamp(),
            'Host': 'userapi.qiekj.com',
            'phoneBrand': 'Redmi',
        }
        if auth:
            h['Authorization'] = self.token
            h['channel'] = 'channel'
        else:
            h['channel'] = 'android_app'
            h['Connection'] = 'Keep-Alive'
            h['Accept-Encoding'] = 'gzip'
        return h

    def _request(self, path: str, data: dict, auth: bool = True) -> dict:
        url = f'{BASE_URL}{path}'
        resp = requests.post(url, headers=self._headers(auth), data=data)
        return resp.json()

    def _extract(self, json_data, expr: str):
        return [m.value for m in parse(expr).find(json_data)]

    # ---- 登录 ----

    def send_code(self, phone: str) -> bool:
        resp = self._request('/common/sms/sendCode',
                             {'phone': phone, 'template': 'reg'}, auth=False)
        return resp.get('code') == 0

    def login(self, phone: str, code: str) -> str:
        resp = self._request('/user/reg', {
            'channel': 'android_app',
            'phone': phone,
            'verify': code,
        }, auth=False)
        token = resp['data']['token']
        self.token = token
        return token

    # ---- Token 校验 ----

    def check_token(self) -> bool:
        resp = self._request('/user/balance', {'token': self.token})
        return resp.get('code') != 2

    # ---- 余额 ----

    def get_balance(self) -> dict:
        resp = self._request('/user/balance', {'token': self.token})
        data = resp.get('data', {})
        return {
            'token_coin': data.get('tokenCoin', 0) / 100,
            'integral': data.get('integral', 0),
            'integral_amount': data.get('integralAmount'),
        }

    # ---- 设备列表 ----

    def get_latest_used(self) -> list[dict]:
        resp = self._request('/goods/latestUsed', {
            'categoryCode': '5', 'token': self.token,
        })
        names = self._extract(resp, '$..goodsName')
        ids = self._extract(resp, '$..goodsId')
        return [{'name': n, 'goodsId': g} for n, g in zip(names, ids)]

    def get_grouped_devices(self) -> list[dict]:
        raw = self.get_latest_used()
        groups = {}
        for item in raw:
            name = item['name']
            gid = item['goodsId']
            if name.endswith('热'):
                key = name[:-1]
                groups.setdefault(key, {})['goodsId_hot'] = gid
                groups[key]['name'] = key
            elif name.endswith('冷'):
                key = name[:-1]
                groups.setdefault(key, {})['goodsId_cold'] = gid
                groups[key]['name'] = key
            else:
                key = name
                groups.setdefault(key, {'name': key})['goodsId_hot'] = gid
        return list(groups.values())

    # ---- 商品详情 ----

    def get_sku(self, goods_id: str) -> str:
        resp = self._request('/goods/normal/skus', {
            'goodsId': goods_id, 'token': self.token,
        })
        return self._extract(resp, '$.data[0].skuId')[0]

    def get_imei(self, goods_id: str) -> str:
        resp = self._request('/goods/normal/details', {
            'goodsId': goods_id, 'token': self.token,
        })
        return self._extract(resp, '$.data.imei')[0]

    # ---- 积分风控 ----

    def use_integral(self):
        self._request('/userIntegral/checkUserIsRisk', {'token': self.token})

    # ---- 出水 ----

    def unlock_water(self, sku: str) -> tuple[str, str]:
        self._request('/payChannelRoute/addUserAfterPayChannel', {
            'method': '15', 'token': self.token,
        })
        resp = self._request('/orderRisk/isCheckLocation', {
            'categoryCode': '04',
            'imei': self.get_imei(self._current_goods_id),
            'token': self.token,
        })
        resp = self._request('/goods/water/unlock', {
            'skuId': sku,
            'promotions': json.dumps([
                {"assetId": "0", "oldPromotionId": "", "orgId": "0", "promotionId": "0", "promotionType": "-6"},
                {"assetId": "0", "oldPromotionId": "", "orgId": "0", "promotionId": "0", "promotionType": "-7"},
                {"assetId": "0", "oldPromotionId": "0", "orgId": "0", "promotionId": "0", "promotionType": "8"},
            ]),
            'token': self.token,
        })
        return resp['data']['msgId'], resp['data']['orderNo']

    def dispense(self, goods_id: str) -> str:
        self._current_goods_id = goods_id
        sku = self.get_sku(goods_id)
        self.use_integral()
        self.unlock_water(sku)
        return self._poll_and_pay(sku)

    def _poll_and_pay(self, sku: str) -> str:
        max_wait = 60
        waited = 0
        while waited < max_wait:
            resp = self._request('/goods/water/sync', {
                'skuId': sku, 'token': self.token,
            })
            status = resp.get('data', {}).get('workStatus')
            if status != 2:
                break
            time.sleep(1)
            waited += 1

        identify = resp.get('data', {}).get('identify')
        amount = resp.get('data', {}).get('amount')

        if amount is not None and amount != 0 and identify:
            resp2 = self._request('/order/afterPay/creating', {
                'orderNo': identify, 'token': self.token,
            })
            order_id = resp2.get('data', {}).get('orderId')
            if order_id:
                detail = self._request('/order/detail', {
                    'orderId': order_id, 'token': self.token,
                })
                return self._format_cost(detail)
        return '出水完成，本次免费'

    def _format_cost(self, detail: dict) -> str:
        data = detail.get('data', {})
        items = data.get('tradeOrderItem', [])
        origin = items[0].get('originPrice', '?') if items else '?'
        parts = [f'原价: {origin}元']
        for p in data.get('promotionList', []):
            pt = p.get('promotionType')
            da = p.get('discountAmount', 0)
            if pt == 4:
                parts.append(f'小票抵扣: {da}')
            elif pt == 8:
                parts.append(f'积分抵扣: {da}')
        return ' | '.join(parts)
