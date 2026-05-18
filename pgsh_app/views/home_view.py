import asyncio
from concurrent.futures import ThreadPoolExecutor

import flet as ft

from .. import storage
from ..api import QiekjAPI

_ACCENT = '#2196F3'


class HomePage(ft.Column):
    def __init__(self, page: ft.Page, api: QiekjAPI):
        super().__init__()
        self._page = page
        self._api = api
        self._alipay_signed = False
        self._balance = None
        self.spacing = 0
        self.scroll = ft.ScrollMode.AUTO
        self.padding = 0
        self.expand = True

        self._balance_text = ft.Text("加载中...", size=15, color=ft.Colors.WHITE,
                                     weight=ft.FontWeight.W_600)
        self._sign_badge = ft.Container(
            content=ft.Text("免密", size=11, color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.WHITE),
            border_radius=6,
            padding=ft.Padding(left=6, top=2, right=6, bottom=2),
            visible=False,
        )
        self._device_list = ft.Column(spacing=12)

        self.controls = [
            self._build_header(),
            ft.Container(
                content=self._device_list,
                padding=ft.Padding(left=16, right=16, top=16, bottom=90),
                expand=True,
            ),
        ]

        self.fab = ft.FloatingActionButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            on_click=self._refresh,
            tooltip="刷新设备",
            bgcolor=_ACCENT,
        )

    # ---- 布局 ----

    def _build_header(self) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WATER_DROP_ROUNDED, color=ft.Colors.WHITE, size=26),
                ft.Text("胖乖饮水", size=22, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
                                color=ft.Colors.WHITE, size=16),
                        self._balance_text,
                        self._sign_badge,
                    ], spacing=6, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                    border_radius=20,
                    padding=ft.Padding(left=14, top=6, right=14, bottom=6),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=_ACCENT,
            padding=ft.Padding(left=20, right=20, top=16, bottom=18),
            border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=20, bottom_right=20),
        )

    def _build_device_card(self, device: dict) -> ft.Card:
        original_name = device.get('name', '未知设备')
        display_name = self._aliases.get(original_name, original_name)
        buttons = ft.Row(spacing=12, alignment=ft.MainAxisAlignment.END)

        if 'goodsId_cold' in device:
            buttons.controls.append(self._build_water_button(
                icon=ft.Icons.AC_UNIT, tooltip="冷水",
                color=ft.Colors.BLUE_400, goods_id=device['goodsId_cold'],
                sku=device.get('sku_cold', ''), imei=device.get('imei_cold', ''),
            ))
        if 'goodsId_hot' in device:
            buttons.controls.append(self._build_water_button(
                icon=ft.Icons.LOCAL_FIRE_DEPARTMENT, tooltip="热水",
                color=ft.Colors.ORANGE_400, goods_id=device['goodsId_hot'],
                sku=device.get('sku_hot', ''), imei=device.get('imei_hot', ''),
            ))

        return ft.Card(
            elevation=2,
            content=ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.WATER_DROP_ROUNDED,
                                        color=_ACCENT, size=24),
                        bgcolor=ft.Colors.with_opacity(0.12, _ACCENT),
                        border_radius=10, padding=8,
                        width=42, height=42,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(display_name, size=16, weight=ft.FontWeight.W_600),
                            ft.Text("饮水机", size=11, color=ft.Colors.GREY_400),
                        ], spacing=2),
                        expand=True, on_click=lambda _: self._edit_name(original_name),
                    ),
                    buttons,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(left=16, top=14, right=16, bottom=14),
            ),
        )

    def _build_water_button(self, icon, tooltip: str, color, goods_id: str,
                            sku: str = '', imei: str = '') -> ft.IconButton:
        return ft.IconButton(
            icon=icon, tooltip=tooltip,
            on_click=lambda _, gid=goods_id, s=sku, im=imei: self._dispense(gid, s, im),
            icon_color=ft.Colors.WHITE, icon_size=22,
            style=ft.ButtonStyle(
                bgcolor=color,
                padding=12,
                shape=ft.CircleBorder(),
            ),
        )

    def _build_empty_state(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.WATER_DROP_OUTLINED,
                        color=ft.Colors.GREY_300, size=48),
                ft.Text("暂无设备", size=16, color=ft.Colors.GREY_400,
                        weight=ft.FontWeight.W_500),
                ft.Text("请先在胖乖生活 App 中使用过饮水机",
                        size=12, color=ft.Colors.GREY_400),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            alignment=ft.Alignment(0, 0), padding=40,
        )

    # ---- 公共方法 ----

    def load(self, initial_balance=None):
        self._aliases = storage.load_aliases()
        self._update_sign_status()
        if initial_balance is not None:
            self._balance = initial_balance
            self._balance_text.value = f"¥{self._balance['token_coin']:.2f}"
            self._page.update()
        else:
            self._update_balance()
        self._load_devices()
        self._check_warnings()

    # ---- 别名 ----

    def _edit_name(self, original_name: str):
        field = ft.TextField(
            value=self._aliases.get(original_name, original_name),
            autofocus=True, border_radius=8, text_size=14,
        )
        dialog = ft.AlertDialog(
            title=ft.Text("修改名称"),
            content=ft.Column([field], tight=True),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._close_dialog(dialog)),
                ft.TextButton("保存", on_click=lambda _: self._save_alias(original_name, field.value, dialog)),
            ],
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _save_alias(self, original_name: str, new_name: str, dialog):
        if new_name and new_name != original_name:
            self._aliases[original_name] = new_name
            storage.save_aliases(self._aliases)
        elif original_name in self._aliases:
            del self._aliases[original_name]
            storage.save_aliases(self._aliases)
        dialog.open = False
        self._render_devices(storage.load_devices())
        self._page.update()

    # ---- 余额 ----

    def _update_sign_status(self):
        try:
            self._alipay_signed = self._api.check_alipay_sign()
        except Exception:
            self._alipay_signed = False
        self._sign_badge.visible = self._alipay_signed
        self._page.update()

    def _update_balance(self):
        try:
            self._balance = self._api.get_balance()
            self._balance_text.value = f"¥{self._balance['token_coin']:.2f}"
        except Exception:
            self._balance = None
            self._balance_text.value = "获取失败"
        self._page.update()

    def _check_warnings(self):
        if self._alipay_signed:
            return
        dialog = ft.AlertDialog(
            title=ft.Text("未开通支付宝免密"),
            content=ft.Text("饮水机使用后需要自动扣款，请先在胖乖生活 App 中开通支付宝免密支付"),
            actions=[
                ft.TextButton("退出", on_click=lambda _: self._exit_app(dialog),
                              style=ft.ButtonStyle(color=ft.Colors.RED_400)),
            ],
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _exit_app(self, dialog):
        dialog.open = False
        self._page.update()
        self._page.run_task(self._page.window.destroy)

    def _close_dialog(self, dialog):
        dialog.open = False
        self._page.update()

    # ---- 设备列表 ----

    def _load_devices(self):
        self._device_list.controls.clear()
        self._page.update()

        try:
            cached = storage.load_devices()
            if cached:
                self._render_devices(cached)
            with ThreadPoolExecutor(max_workers=2) as pool:
                devices_fut = pool.submit(self._api.get_grouped_devices)
                pool.submit(self._api._post, '/payChannelRoute/addUserAfterPayChannel',
                            {'method': '15', 'token': self._api.token})
                devices = devices_fut.result()
            cache_map = {(d.get('goodsId_hot'), d.get('goodsId_cold')): d
                         for d in cached}
            for dev in devices:
                key = (dev.get('goodsId_hot'), dev.get('goodsId_cold'))
                cached_dev = cache_map.get(key)
                if cached_dev:
                    for field in ('sku_hot', 'imei_hot', 'sku_cold', 'imei_cold'):
                        if field in cached_dev and field not in dev:
                            dev[field] = cached_dev[field]
            self._enrich_devices(devices)
            storage.save_devices(devices)
            self._render_devices(devices)
        except Exception:
            cached = storage.load_devices()
            if cached:
                self._render_devices(cached)

    def _enrich_devices(self, devices):
        for dev in devices:
            for suffix, gid_key in [('hot', 'goodsId_hot'), ('cold', 'goodsId_cold')]:
                if gid_key not in dev:
                    continue
                sku_key, imei_key = f'sku_{suffix}', f'imei_{suffix}'
                if sku_key in dev and imei_key in dev:
                    continue
                gid = dev[gid_key]
                try:
                    dev[sku_key] = self._api.get_sku(gid)
                    dev[imei_key] = self._api.get_imei(gid)
                except Exception:
                    pass

    def _render_devices(self, devices: list[dict]):
        self._device_list.controls.clear()
        if not devices:
            self._device_list.controls.append(self._build_empty_state())
        else:
            for d in devices:
                self._device_list.controls.append(self._build_device_card(d))
        self._page.update()

    # ---- 出水 ----

    def _dispense(self, goods_id: str, sku: str = '', imei: str = ''):
        self._show_toast("正在解锁...", duration=0)
        self._page.run_task(self._do_dispense, goods_id, sku, imei)

    async def _do_dispense(self, goods_id: str, sku: str = '', imei: str = ''):
        def on_status(msg):
            self._show_toast(msg, duration=0)
        try:
            result = await asyncio.to_thread(
                self._api.dispense, goods_id, sku, imei, on_status)
            self._show_toast(result, duration=5)
        except Exception as ex:
            self._show_toast(f"启动失败: {ex}")
        self._update_balance()

    def _refresh(self, _e):
        self._load_devices()
        self._update_balance()

    # ---- Toast 通知 ----

    def _show_toast(self, msg: str, duration: float = 3):
        overlay = self._page.overlay
        for c in list(overlay):
            if getattr(c, '_is_toast', False):
                overlay.remove(c)

        toast = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.WHITE, size=18),
                ft.Text(msg, size=13, color=ft.Colors.WHITE, expand=True),
            ], tight=True, spacing=8),
            bgcolor=ft.Colors.with_opacity(0.88, ft.Colors.GREY_800),
            border_radius=10,
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            margin=ft.Margin(top=50, left=16, right=16),
        )
        toast._is_toast = True
        overlay.append(toast)
        self._page.update()
        if duration > 0:
            self._page.run_task(self._hide_toast, toast, duration)

    async def _hide_toast(self, toast, delay: float = 3):
        await asyncio.sleep(delay)
        if toast in self._page.overlay:
            self._page.overlay.remove(toast)
            self._page.update()
