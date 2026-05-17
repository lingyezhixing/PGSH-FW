import flet as ft
from .. import storage
from ..api import QiekjAPI


class LoginSheet:
    def __init__(self, page: ft.Page, api: QiekjAPI, on_success):
        self.page = page
        self.api = api
        self.on_success = on_success

        self.reason = ft.Text(size=14, color=ft.Colors.RED_400)
        self.phone_field = ft.TextField(
            label="手机号", keyboard_type=ft.KeyboardType.PHONE,
            max_length=11, autofocus=True,
        )
        self.code_field = ft.TextField(
            label="验证码", keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
        )
        self.send_btn = ft.ElevatedButton("获取验证码", on_click=self._send_code)
        self.login_btn = ft.ElevatedButton(
            "登录", on_click=self._login,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_400, color=ft.Colors.WHITE,
            ),
        )
        self.msg = ft.Text(size=12, color=ft.Colors.RED_400)

        self.sheet = ft.BottomSheet(
            content=ft.Container(
                content=ft.Column([
                    self.reason,
                    self.phone_field,
                    ft.Row([self.send_btn], alignment=ft.MainAxisAlignment.END),
                    self.code_field,
                    ft.Row([self.login_btn], alignment=ft.MainAxisAlignment.CENTER),
                    self.msg,
                ], tight=True, spacing=12),
                padding=20,
            ),
            dismissible=False,
        )

    def show(self, reason: str):
        self.reason.value = reason
        self.msg.value = ''
        self.phone_field.value = ''
        self.code_field.value = ''
        self.sheet.open = True
        self.page.overlay.append(self.sheet)
        self.page.update()

    def _send_code(self, e):
        phone = self.phone_field.value
        if len(phone) != 11:
            self.msg.value = '请输入11位手机号'
            self.page.update()
            return
        try:
            self.api.send_code(phone)
            self.msg.value = '验证码已发送'
            self.msg.color = ft.Colors.GREEN_400
        except Exception as ex:
            self.msg.value = f'发送失败: {ex}'
            self.msg.color = ft.Colors.RED_400
        self.page.update()

    def _login(self, e):
        phone = self.phone_field.value
        code = self.code_field.value
        if not phone or not code:
            self.msg.value = '请填写手机号和验证码'
            self.page.update()
            return
        self.login_btn.disabled = True
        self.login_btn.text = "登录中..."
        self.page.update()
        try:
            token = self.api.login(phone, code)
            storage.save_token(token)
            self.sheet.open = False
            self.page.update()
            self.on_success()
        except Exception as ex:
            self.msg.value = f'登录失败: {ex}'
            self.msg.color = ft.Colors.RED_400
            self.login_btn.disabled = False
            self.login_btn.text = "登录"
            self.page.update()
