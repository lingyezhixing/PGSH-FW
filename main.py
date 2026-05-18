import flet as ft
from pgsh_app.api import QiekjAPI
from pgsh_app import storage
from pgsh_app.views.home_view import HomePage
from pgsh_app.views.login_view import LoginPage


def main(page: ft.Page):
    page.title = "胖乖饮水"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    api = QiekjAPI()
    login = LoginPage(page, api, on_success=lambda: _switch_to_home())
    home = HomePage(page, api)

    def _switch_to_home(balance=None):
        page.on_keyboard_event = None  # 修复退格键报错：清理登录页残留的键盘事件
        page.floating_action_button = home.fab
        page.controls.clear()
        page.add(ft.SafeArea(content=home, expand=True))
        home.load(balance)

    def _switch_to_login(reason=''):
        page.on_keyboard_event = None
        page.floating_action_button = None
        page.controls.clear()
        page.add(ft.SafeArea(content=login, expand=True))
        login.show(reason)

    token = storage.load_token()
    if token:
        api.token = token
        balance = api.check_token()
        if balance:
            _switch_to_home(balance)
        else:
            _switch_to_login("登录已过期，请重新登录")
    else:
        _switch_to_login("首次使用，请登录")


if __name__ == '__main__':
    ft.run(main)