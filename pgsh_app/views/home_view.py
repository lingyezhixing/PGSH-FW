import flet as ft
from .. import storage
from ..api import QiekjAPI


class HomePage(ft.Column):
    def __init__(self, page: ft.Page, api: QiekjAPI):
        super().__init__()
        self._page = page
        self.api = api
        self.spacing = 10
        self.scroll = ft.ScrollMode.AUTO

        self.balance_text = ft.Text("余额: 加载中...", size=14, weight=ft.FontWeight.BOLD)
        self.device_list = ft.Column(spacing=10)

        self.expand = True
        self.controls = [
            ft.Row([
                ft.Text("胖乖饮水", size=22, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                self.balance_text,
            ]),
            ft.Divider(),
            self.device_list,
        ]

        self.fab = ft.FloatingActionButton(
            icon=ft.Icons.REFRESH,
            on_click=self._refresh,
            tooltip="刷新设备",
        )

    def load(self):
        self._update_balance()
        self._load_devices()

    def _update_balance(self):
        try:
            b = self.api.get_balance()
            self.balance_text.value = f"余额: ¥{b['token_coin']:.2f}"
        except Exception:
            self.balance_text.value = "余额: 获取失败"
        self._page.update()

    def _load_devices(self):
        self.device_list.controls.clear()
        self._page.update()

        try:
            cached = storage.load_devices()
            if cached:
                self._render_devices(cached)
            devices = self.api.get_grouped_devices()
            storage.save_devices(devices)
            self._render_devices(devices)
        except Exception as ex:
            cached = storage.load_devices()
            if cached:
                self._render_devices(cached)

    def _render_devices(self, devices: list[dict]):
        self.device_list.controls.clear()
        if not devices:
            self.device_list.controls.append(
                ft.Text("暂无设备，请先在 App 中使用过饮水机",
                        color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
            )
            self._page.update()
            return
        for d in devices:
            self.device_list.controls.append(self._build_card(d))
        self._page.update()

    def _build_card(self, device: dict) -> ft.Card:
        name = device.get('name', '未知设备')
        has_cold = 'goodsId_cold' in device
        has_hot = 'goodsId_hot' in device

        buttons = ft.Row(spacing=12, alignment=ft.MainAxisAlignment.END)
        if has_cold:
            buttons.controls.append(ft.IconButton(
                icon=ft.Icons.AC_UNIT,
                tooltip="冷水",
                on_click=lambda e, gid=device['goodsId_cold']: self._dispense(gid),
                icon_color=ft.Colors.WHITE,
                icon_size=24,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_400,
                    padding=ft.padding.all(12),
                    shape=ft.CircleBorder(),
                ),
            ))
        if has_hot:
            buttons.controls.append(ft.IconButton(
                icon=ft.Icons.LOCAL_FIRE_DEPARTMENT,
                tooltip="热水",
                on_click=lambda e, gid=device['goodsId_hot']: self._dispense(gid),
                icon_color=ft.Colors.WHITE,
                icon_size=24,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.ORANGE_400,
                    padding=ft.padding.all(12),
                    shape=ft.CircleBorder(),
                ),
            ))

        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLUE_300, size=32),
                    ft.Text(name, size=18, weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    buttons,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=20, vertical=18),
            ),
        )

    def _show_snack(self, msg: str):
        snack = ft.SnackBar(content=ft.Text(msg))
        self._page.overlay.append(snack)
        snack.open = True
        self._page.update()

    def _dispense(self, goods_id: str):
        try:
            b = self.api.get_balance()
            if b['token_coin'] < 0.5:
                self._show_snack(f"余额不足 ¥0.50（当前 ¥{b['token_coin']:.2f}），请先充值")
                return
        except Exception:
            pass

        self._show_snack("正在出水，请稍候...")
        try:
            result = self.api.dispense(goods_id)
            self._show_snack(result)
        except Exception as ex:
            self._show_snack(f"出水失败: {ex}")
        self._update_balance()

    def _refresh(self, e):
        self._load_devices()
        self._update_balance()
