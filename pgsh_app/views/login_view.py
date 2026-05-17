import asyncio

import flet as ft

from .. import storage
from ..api import QiekjAPI

_ACCENT = '#2196F3'


class LoginPage(ft.Column):
    def __init__(self, page: ft.Page, api: QiekjAPI, on_success):
        super().__init__()
        self._page = page
        self._api = api
        self._on_success = on_success
        self._phone = ''
        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # ---- 步骤一：手机号 ----
        self._phone_field = ft.TextField(
            label="手机号",
            keyboard_type=ft.KeyboardType.PHONE,
            max_length=11, autofocus=True,
            border_color=ft.Colors.GREY_300,
            focused_border_color=_ACCENT,
            border_radius=12, text_size=16, width=300, counter='',
        )
        self._phone_error = ft.Text(size=12, color=ft.Colors.RED_400)
        self._phone_view = ft.Column([
            ft.Icon(ft.Icons.WATER_DROP_ROUNDED, color=_ACCENT, size=48),
            ft.Container(height=8),
            ft.Text("胖乖饮水", size=26, weight=ft.FontWeight.BOLD, color=_ACCENT),
            ft.Text("请输入手机号登录", size=13, color=ft.Colors.GREY_500),
            ft.Container(height=20),
            self._phone_field,
            self._phone_error,
            ft.Container(height=12),
            ft.ElevatedButton(
                "下一步", on_click=self._go_verify, width=300,
                style=ft.ButtonStyle(
                    bgcolor=_ACCENT, color=ft.Colors.WHITE,
                    padding=ft.Padding(left=40, top=14, right=40, bottom=14),
                    text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_600),
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

        # ---- 步骤二：验证码 ----
        self._code_inputs = [
            self._make_code_field(i) for i in range(4)
        ]
        self._code_row = ft.Row(
            self._code_inputs,
            alignment=ft.MainAxisAlignment.CENTER, spacing=10,
        )
        self._spinner = ft.Container(
            content=ft.ProgressRing(color=_ACCENT, width=48, height=48),
            visible=False, height=60, alignment=ft.Alignment(0, 0),
        )
        self._tail_text = ft.Text("验证码已发送至尾号 ****",
                                  size=13, color=ft.Colors.GREY_500)
        self._verify_error = ft.Text(size=12, color=ft.Colors.RED_400)
        self._verify_view = ft.Column([
            ft.Icon(ft.Icons.SMS_ROUNDED, color=_ACCENT, size=40),
            ft.Container(height=8),
            ft.Text("输入验证码", size=22, weight=ft.FontWeight.BOLD),
            self._tail_text,
            ft.Container(height=20),
            self._code_row,
            self._spinner,
            ft.Container(height=8),
            self._verify_error,
            ft.Container(height=16),
            ft.TextButton("重新发送", on_click=self._resend,
                          style=ft.ButtonStyle(color=_ACCENT)),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

        self._page.on_keyboard_event = self._on_key
        self.controls = [self._phone_view]

    def _make_code_field(self, idx: int) -> ft.TextField:
        return ft.TextField(
            width=56, height=60,
            text_align=ft.TextAlign.CENTER, text_size=24,
            max_length=1, keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            border_color=ft.Colors.GREY_300,
            focused_border_color=_ACCENT,
            border_radius=10, counter='',
            on_change=lambda _, i=idx: self._on_code_input(i),
        )

    # ---- 公共方法 ----

    def show(self, reason: str = ''):
        if reason:
            self._phone_error.value = reason
        self._phone_field.value = ''
        self.controls = [self._phone_view]
        self._page.update()

    # ---- 手机号步骤 ----

    def _go_verify(self, _e):
        phone = self._phone_field.value
        if len(phone) != 11:
            self._phone_error.value = '请输入11位手机号'
            self._page.update()
            return

        try:
            self._api.send_code(phone)
        except Exception as ex:
            self._phone_error.value = str(ex)
            self._page.update()
            return

        self._phone = phone
        self._tail_text.value = f"验证码已发送至尾号 {phone[-4:]}"
        self._clear_code()
        self._verify_error.value = ''
        self.controls = [self._verify_view]
        self._page.update()
        self._page.run_task(self._delayed_focus)

    async def _delayed_focus(self):
        await asyncio.sleep(0.1)
        await self._code_inputs[0].focus()

    # ---- 验证码步骤 ----

    def _on_code_input(self, idx: int):
        val = self._code_inputs[idx].value
        if not val and idx > 0:
            self._focus(idx - 1)
        elif val and idx < 3:
            self._focus(idx + 1)

        if len(self._get_code()) == 4:
            self._auto_login()
        self._page.update()

    def _on_key(self, e):
        if e.key == 'Backspace':
            for i, f in enumerate(self._code_inputs):
                if not f.value and i > 0:
                    self._focus(i - 1)
                    break

    def _get_code(self) -> str:
        return ''.join(f.value for f in self._code_inputs)

    def _clear_code(self):
        for f in self._code_inputs:
            f.value = ''
            f.border_color = ft.Colors.GREY_300

    def _auto_login(self):
        code = self._get_code()
        self._code_row.visible = False
        self._spinner.visible = True
        self._page.update()
        self._page.run_task(self._do_login, code)

    async def _do_login(self, code: str):
        try:
            token = await asyncio.to_thread(self._api.login, self._phone, code)
            storage.save_token(token)
            self._on_success()
        except Exception:
            self._code_row.visible = True
            self._spinner.visible = False
            self._page.update()
            await self._shake_and_error()

    def _resend(self, _e):
        try:
            self._api.send_code(self._phone)
            self._clear_code()
            self._verify_error.value = ''
            self._page.update()
            self._focus(0)
        except Exception as ex:
            self._verify_error.value = str(ex)
            self._page.update()

    # ---- 焦点管理 ----

    def _focus(self, idx: int):
        self._page.run_task(self._code_inputs[idx].focus)

    # ---- 错误动画 ----

    async def _shake_and_error(self):
        if hasattr(self._page, 'vibrate'):
            self._page.vibrate()

        for f in self._code_inputs:
            f.border_color = ft.Colors.RED_400
        self._verify_error.value = '验证码错误，请重试'
        self._page.update()

        offsets = [-0.05, 0.05, -0.03, 0.03, 0]
        for dx in offsets:
            self._code_row.offset = ft.Offset(dx, 0)
            self._code_row.animate_offset = ft.Animation(50, ft.AnimationCurve.EASE_IN_OUT)
            self._page.update()
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.2)
        self._clear_code()
        self._page.update()
        self._focus(0)
