import json
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from jsonpath_ng import parse

BASE_URL = 'https://userapi.qiekj.com'

_PROMOTIONS = json.dumps([
    {"assetId": "0", "oldPromotionId": "", "orgId": "0", "promotionId": "0", "promotionType": "-6"},
    {"assetId": "0", "oldPromotionId": "", "orgId": "0", "promotionId": "0", "promotionType": "-7"},
    {"assetId": "0", "oldPromotionId": "0", "orgId": "0", "promotionId": "0", "promotionType": "8"},
])


class QiekjAPI:
    def __init__(self, token: str = ''):
        self.token = token

    def _headers(self, auth: bool = True) -> dict:
        h = {
            'Version': '1.119.1',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'User-Agent': 'okhttp/4.12.0',
            'timestamp': str(int(time.time() * 1000)),
            'Host': 'userapi.qiekj.com',
            'channel': 'android_app',
        }
        if auth:
            h['Authorization'] = self.token
        return h

    def _post(self, path: str, data: dict, auth: bool = True) -> dict:
        resp = requests.post(f'{BASE_URL}{path}', headers=self._headers(auth), data=data)
        return resp.json()

    def _extract(self, data: dict, expr: str) -> list:
        return [m.value for m in parse(expr).find(data)]

    # ---- 登录 ----

    def send_code(self, phone: str) -> bool:
        resp = self._post('/common/sms/sendCode',
                          {'phone': phone, 'template': 'reg'}, auth=False)
        if resp.get('code') != 0:
            raise RuntimeError(resp.get('msg', '发送验证码失败'))
        return True

    def login(self, phone: str, code: str) -> str:
        resp = self._post('/user/reg', {
            'channel': 'android_app', 'phone': phone, 'verify': code,
        }, auth=False)
        token = resp.get('data', {}).get('token')
        if not token:
            raise RuntimeError(resp.get('msg', '登录失败'))
        self.token = token
        return token

    def check_token(self) -> bool:
        resp = self._post('/user/balance', {'token': self.token})
        return resp.get('code') != 2

    def check_alipay_sign(self) -> bool:
        resp = self._post('/alipay/isSign', {'token': self.token})
        return resp.get('data', False) is True

    # ---- 余额 ----

    def get_balance(self) -> dict:
        data = self._post('/user/balance', {'token': self.token}).get('data', {})
        return {
            'token_coin': data.get('tokenCoin', 0) / 100,
            'integral': data.get('integral', 0),
            'integral_amount': data.get('integralAmount'),
        }

    # ---- 设备 ----

    def get_latest_used(self) -> list[dict]:
        resp = self._post('/goods/latestUsed', {
            'categoryCode': '5', 'token': self.token,
        })
        names = self._extract(resp, '$..goodsName')
        ids = self._extract(resp, '$..goodsId')
        return [{'name': n, 'goodsId': g} for n, g in zip(names, ids)]

    def get_grouped_devices(self) -> list[dict]:
        groups: dict[str, dict] = {}
        for item in self.get_latest_used():
            name, gid = item['name'], item['goodsId']
            if name.endswith('热') or name.endswith('冷'):
                key, suffix = name[:-1], 'hot' if name[-1] == '热' else 'cold'
            else:
                key, suffix = name, 'hot'
            groups.setdefault(key, {'name': key})[f'goodsId_{suffix}'] = gid
        return list(groups.values())

    # ---- 商品详情 ----

    def get_sku(self, goods_id: str) -> str:
        resp = self._post('/goods/normal/skus', {
            'goodsId': goods_id, 'token': self.token,
        })
        return self._extract(resp, '$.data[0].skuId')[0]

    def get_imei(self, goods_id: str) -> str:
        resp = self._post('/goods/normal/details', {
            'goodsId': goods_id, 'token': self.token,
        })
        return self._extract(resp, '$.data.imei')[0]

    # ---- 出水 ----

    def dispense(self, goods_id: str, sku: str = '', imei: str = '') -> str:
        if not sku or not imei:
            with ThreadPoolExecutor(max_workers=2) as pool:
                sku_fut = pool.submit(self.get_sku, goods_id) if not sku else None
                imei_fut = pool.submit(self.get_imei, goods_id) if not imei else None
                if sku_fut:
                    sku = sku_fut.result()
                if imei_fut:
                    imei = imei_fut.result()

        with ThreadPoolExecutor(max_workers=3) as pool:
            pool.submit(self._post, '/userIntegral/checkUserIsRisk', {'token': self.token})
            pool.submit(self._post, '/payChannelRoute/addUserAfterPayChannel', {
                'method': '15', 'token': self.token,
            })
            pool.submit(self._post, '/orderRisk/isCheckLocation', {
                'categoryCode': '04', 'imei': imei, 'token': self.token,
            }).result()

        self._post('/goods/water/unlock', {
            'skuId': sku, 'promotions': _PROMOTIONS, 'token': self.token,
        })

        for _ in range(60):
            resp = self._post('/goods/water/sync', {
                'skuId': sku, 'token': self.token,
            })
            if resp.get('data', {}).get('workStatus') != 2:
                break
            time.sleep(1)

        identify = resp.get('data', {}).get('identify')
        amount = resp.get('data', {}).get('amount')

        if amount is None:
            return '启动完成，本次未出水'
        if amount == 0:
            return '出水完成，本次免费'

        if identify:
            resp2 = self._post('/order/afterPay/creating', {
                'orderNo': identify, 'token': self.token,
            })
            order_id = resp2.get('data', {}).get('orderId')
            if order_id:
                detail = self._post('/order/detail', {
                    'orderId': order_id, 'token': self.token,
                })
                return self._format_cost(detail)

        return '出水完成，费用未知'

    def _format_cost(self, detail: dict) -> str:
        data = detail.get('data', {})
        items = data.get('tradeOrderItem', [])
        origin = items[0].get('originPrice', '?') if items else '?'
        parts = [f'原价: {origin}元']
        for p in data.get('promotionList', []):
            pt, da = p.get('promotionType'), p.get('discountAmount', 0)
            if pt == 4:
                parts.append(f'小票抵扣: {da}')
            elif pt == 8:
                parts.append(f'积分抵扣: {da}')
        return ' | '.join(parts)
