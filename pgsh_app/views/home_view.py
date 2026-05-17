import asyncio

import flet as ft

from .. import storage
from ..api import QiekjAPI

_ACCENT = '#2196F3'
_BALANCE_THRESHOLD = 0.2


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
            content=ft.Text("免密", size=10, color=ft.Colors.WHITE,
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
        name = device.get('name', '未知设备')
        buttons = ft.Row(spacing=12, alignment=ft.MainAxisAlignment.END)

        if 'goodsId_cold' in device:
            buttons.controls.append(self._build_water_button(
                icon=ft.Icons.AC_UNIT, tooltip="冷水",
                color=ft.Colors.BLUE_400, goods_id=device['goodsId_cold'],
            ))
        if 'goodsId_hot' in device:
            buttons.controls.append(self._build_water_button(
                icon=ft.Icons.LOCAL_FIRE_DEPARTMENT, tooltip="热水",
                color=ft.Colors.ORANGE_400, goods_id=device['goodsId_hot'],
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
                    ft.Column([
                        ft.Text(name, size=16, weight=ft.FontWeight.W_600),
                        ft.Text("饮水机", size=11, color=ft.Colors.GREY_400),
                    ], spacing=2, expand=True),
                    buttons,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(left=16, top=14, right=16, bottom=14),
            ),
        )

    def _build_water_button(self, icon, tooltip: str, color, goods_id: str) -> ft.IconButton:
        return ft.IconButton(
            icon=icon, tooltip=tooltip,
            on_click=lambda _, gid=goods_id: self._dispense(gid),
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

    def load(self):
        self._update_sign_status()
        self._update_balance()
        self._load_devices()
        self._check_balance_warning()

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

    def _check_balance_warning(self):
        if not self._balance:
            return
        if not self._alipay_signed and self._balance['token_coin'] < _BALANCE_THRESHOLD:
            dialog = ft.AlertDialog(
                title=ft.Text("余额不足"),
                content=ft.Text(f"当前余额 ¥{self._balance['token_coin']:.2f}，"
                                f"低于 ¥{_BALANCE_THRESHOLD:.2f}，请尽快充值或开通免密支付"),
                actions=[
                    ft.TextButton("知道了", on_click=lambda _: self._close_dialog(dialog)),
                ],
            )
            self._page.overlay.append(dialog)
            dialog.open = True
            self._page.update()

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
            devices = self._api.get_grouped_devices()
            storage.save_devices(devices)
            self._render_devices(devices)
        except Exception:
            cached = storage.load_devices()
            if cached:
                self._render_devices(cached)

    def _render_devices(self, devices: list[dict]):
        self._device_list.controls.clear()
        if not devices:
            self._device_list.controls.append(self._build_empty_state())
        else:
            for d in devices:
                self._device_list.controls.append(self._build_device_card(d))
        self._page.update()

    # ---- 出水 ----

    def _dispense(self, goods_id: str):
        self._show_toast("正在出水，请稍候...")
        try:
            result = self._api.dispense(goods_id)
            self._show_toast(result)
        except Exception as ex:
            self._show_toast(f"出水失败: {ex}")
        self._update_balance()

    def _refresh(self, _e):
        self._load_devices()
        self._update_balance()

    # ---- Toast 通知 ----

    def _show_toast(self, msg: str):
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
        self._page.run_task(self._hide_toast, toast)

    async def _hide_toast(self, toast):
        await asyncio.sleep(3)
        if toast in self._page.overlay:
            self._page.overlay.remove(toast)
            self._page.update()
