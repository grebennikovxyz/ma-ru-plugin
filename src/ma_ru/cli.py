import argparse
import json

from . import wizard
from .accounts import Problem, forget, profiles


def main():
    cli = argparse.ArgumentParser(prog="ma-ru", description="Почта Mail.ru для агентов")
    actions = cli.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("connect", help="Мастер подключения")
    interface = setup.add_mutually_exclusive_group()
    interface.add_argument("--terminal", action="store_true", help="Текстовый мастер")
    interface.add_argument(
        "--web",
        action="store_true",
        help="Форма в браузере для компьютера или SSH-туннеля",
    )
    setup.add_argument(
        "--port", type=int, default=8766, help="Локальный порт веб-мастера"
    )
    actions.add_parser("status", help="Подключённые ящики и разрешения")
    check = actions.add_parser(
        "check", help="Проверить список папок и поиск по INBOX без вывода писем"
    )
    check.add_argument("account")
    actions.add_parser("serve", help="MCP через stdio")
    http = actions.add_parser("serve-http", help="Личный MCP за HTTPS-прокси")
    http.add_argument(
        "--public-origin", required=True, help="Внешний HTTPS-адрес без пути"
    )
    http.add_argument("--port", type=int, default=8765, help="Порт на 127.0.0.1")
    logout = actions.add_parser(
        "disconnect", help="Удалить локальный доступ и позиции расписаний"
    )
    logout.add_argument("account")
    args = cli.parse_args()
    try:
        if args.action == "serve":
            from .server import mcp

            mcp.run()
        elif args.action == "serve-http":
            from .remote import serve

            if not 1 <= args.port <= 65535:
                raise Problem("Укажите порт от 1 до 65535.")
            serve(args.public_origin, args.port)
        elif args.action == "status":
            print(json.dumps(profiles(), ensure_ascii=False, indent=2))
        elif args.action == "check":
            from .accounts import current
            from .folders import allow
            from .transport import mailbox

            account = current(args.account)
            with mailbox(account) as client:
                allow(account.email, "INBOX", client)
                folders = client.list_folders()
                client.select_folder("INBOX", readonly=True)
                matches = client.search(["UNDELETED", "UNSEEN"])
                print(
                    json.dumps(
                        {
                            "imap": "OK",
                            "folder_count": len(folders),
                            "unread_count": len(matches),
                        }
                    )
                )
        elif args.action == "disconnect":
            forget(args.account)
            print(
                "Локальный доступ отключён. Для отзыва пароля удалите его на",
                wizard.PASSWORDS,
            )
        elif args.web:
            from .web_wizard import serve

            if not 1 <= args.port <= 65535:
                raise Problem("Укажите порт от 1 до 65535.")
            serve(args.port)
        elif args.terminal:
            wizard.terminal()
        else:
            try:
                import tkinter
            except ImportError:
                wizard.terminal()
            else:
                try:
                    wizard.window()
                except tkinter.TclError:
                    wizard.terminal()
    except Problem as exc:
        cli.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
