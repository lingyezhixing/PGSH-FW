import flet as ft
from .api import QiekjAPI
from . import storage
from .views.home_view import HomePage
from .views.login_view import LoginSheet


def main(page: ft.Page):
    page.title = "胖乖饮水"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 16

    api = QiekjAPI()
    home = HomePage(page, api)
    login_sheet = LoginSheet(page, api, on_success=home.load)

    page.floating_action_button = home.fab
    page.add(home)

    token = storage.load_token()
    if token:
        api.token = token
        if api.check_token():
            home.load()
        else:
            home.load()
            login_sheet.show("登录已过期，请重新登录")
    else:
        login_sheet.show("首次使用，请登录")


if __name__ == '__main__':
    ft.run(main)
