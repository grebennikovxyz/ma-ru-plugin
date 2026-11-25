import getpass
import sys
import threading
import webbrowser
from queue import Empty, Queue

from .accounts import MODES, Problem
from .transport import connect

SETTINGS = "https://id.mail.ru/contacts"
PASSWORDS = "https://account.mail.ru/user/2-step-auth/passwords/"
STEPS = (
    (
        "Проверьте телефон в Mail ID",
        "Войдите в нужный ящик Mail. Откройте «Контакты и адреса» и убедитесь, что к аккаунту привязан телефон. Если его нет, добавьте и подтвердите номер на странице Mail.",
        SETTINGS,
    ),
    (
        "Создайте пароль приложения",
        "Нажмите «Создать» в разделе «Пароли для внешних приложений». Укажите название, например «Ma-Ru для агента», и нажмите «Продолжить». Выберите «Полный доступ к Почте» → «Продолжить». Подтвердите вход, если попросит Mail. Скопируйте пароль для следующего шага. Mail показывает его один раз, он действует до отзыва.",
        PASSWORDS,
    ),
)
MODENAMES = (
    "Только чтение",
    "Чтение, метки, папки и черновики",
    "Также разрешить отправку писем",
)


def terminal():
    if not sys.stdin.isatty():
        raise Problem("Откройте ma-ru connect --terminal в интерактивном терминале.")
    for n, (title, hint, url) in enumerate(STEPS, 1):
        print(f"\n{n}. {title}\n{hint}\n{url}")
        if (
            input("Enter — открыть ссылку, минус — пропустить открытие: ").strip()
            != "-"
        ):
            webbrowser.open(url)
        input("После выполнения шага нажмите Enter.")
    email = input("Полный адрес подключаемого ящика: ")
    for n, name in enumerate(MODENAMES, 1):
        print(n, name)
    choice = input("Режим доступа [1]: ").strip() or "1"
    if choice not in ("1", "2", "3"):
        raise Problem("Выберите 1, 2 или 3.")
    connect(
        email,
        getpass.getpass("Пароль приложения (скрытый ввод): "),
        MODES[int(choice) - 1],
    )
    print("Почта подключена.")


def window():
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Ma-Ru — подключение почты Mail.ru")
    box = ttk.Frame(root, padding=24)
    box.pack(fill="both", expand=True)
    email, secret = tk.StringVar(), tk.StringVar()
    mode = tk.IntVar(value=0)
    result = Queue()

    def draw(step):
        for widget in box.winfo_children():
            widget.destroy()
        title = STEPS[step][0] if step < 2 else "Проверьте и подключите ящик"
        ttk.Label(box, text=f"Шаг {step + 1} из 3").pack(anchor="w")
        ttk.Label(box, text=title, font=("TkDefaultFont", 15, "bold")).pack(
            anchor="w", pady=10
        )
        if step < 2:
            _, hint, url = STEPS[step]
            ttk.Label(box, text=hint, wraplength=460).pack(anchor="w")
            ttk.Button(
                box,
                text=("Контакты и адреса", "Создать пароль в Mail")[step],
                command=lambda: webbrowser.open(url),
            ).pack(anchor="w", pady=12)
        else:
            for label, var, mask in (
                ("Полный адрес ящика", email, ""),
                ("Пароль приложения из шага 2", secret, "*"),
            ):
                ttk.Label(box, text=label).pack(anchor="w")
                ttk.Entry(box, textvariable=var, show=mask, width=48).pack(
                    fill="x", pady=(2, 8)
                )
            for i, label in enumerate(MODENAMES):
                ttk.Radiobutton(box, text=label, variable=mode, value=i).pack(
                    anchor="w"
                )
            ttk.Label(
                box,
                text="После проверки пароль сохранится в хранилище вашей ОС.",
                wraplength=460,
            ).pack(anchor="w", pady=8)
        bar = ttk.Frame(box)
        bar.pack(fill="x", pady=12)
        if step:
            ttk.Button(bar, text="Назад", command=lambda: draw(step - 1)).pack(
                side="left"
            )
        ttk.Button(
            bar,
            text="Далее" if step < 2 else "Проверить и подключить",
            command=lambda: draw(step + 1) if step < 2 else start(),
        ).pack(side="right")

    def start():
        args = email.get(), secret.get(), MODES[mode.get()]
        secret.set("")
        for w in box.winfo_children():
            w.destroy()
        ttk.Label(box, text="Проверяем соединение с почтой Mail.ru…").pack()

        def run():
            try:
                connect(*args)
                result.put(None)
            except Problem as exc:
                result.put(str(exc))
            except Exception:  # noqa: BLE001 — the UI must clear the secret and report a safe error
                result.put(
                    "Не удалось сохранить вход. Проверьте доступность системного хранилища паролей."
                )

        threading.Thread(target=run, daemon=True).start()
        root.after(100, finish)

    def finish():
        try:
            error = result.get_nowait()
        except Empty:
            root.after(100, finish)
            return
        for w in box.winfo_children():
            w.destroy()
        if error:
            ttk.Label(box, text=error, wraplength=460).pack()
            ttk.Button(box, text="Вернуться к вводу", command=lambda: draw(2)).pack(
                pady=8
            )
        else:
            ttk.Label(box, text="Подключён ящик " + email.get()).pack()
            ttk.Label(
                box, text="Попросите агента показать последние письма из Входящих."
            ).pack(pady=8)
            ttk.Button(box, text="Готово", command=root.destroy).pack()

    draw(0)
    root.mainloop()
