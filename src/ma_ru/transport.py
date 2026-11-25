import imaplib
import smtplib
import ssl
from contextlib import contextmanager

from imapclient import IMAPClient
from imapclient.exceptions import LoginError

from .accounts import MODES, Account, Problem, address, save


@contextmanager
def mailbox(account):
    try:
        with IMAPClient(
            "imap.mail.ru",
            port=993,
            ssl=True,
            ssl_context=ssl.create_default_context(),
            timeout=25,
        ) as client:
            client.login(account.email, account.password)
            yield client
    except LoginError:
        raise Problem(
            "Mail.ru отклонил вход. Проверьте полный адрес и пароль внешнего приложения с типом «Полный доступ к Почте»."
        ) from None
    except imaplib.IMAP4.error:
        raise Problem(
            "Mail.ru отклонил команду IMAP. Проверьте доступ к ящику, папку и поддержку операции."
        ) from None
    except OSError:
        raise Problem(
            "Соединение IMAP прервано. Проверьте сеть и состояние письма перед повтором."
        ) from None


@contextmanager
def outgoing(account):
    try:
        with smtplib.SMTP_SSL(
            "smtp.mail.ru", 465, timeout=25, context=ssl.create_default_context()
        ) as smtp:
            smtp.login(account.email, account.password)
            yield smtp
    except (OSError, smtplib.SMTPException):
        raise Problem(
            "Ошибка SMTP. Проверьте доступ и состояние отправки в Почте."
        ) from None


def connect(email, password, mode):
    if mode not in MODES:
        raise Problem("Выберите режим доступа.")
    email = address(email).lower()
    password = password.strip()
    if (
        not password
        or not password.isascii()
        or any(ord(c) < 33 or ord(c) > 126 for c in password)
        or len(password) > 128
    ):
        raise Problem(
            "Скопируйте пароль из раздела Mail «Пароли для внешних приложений»."
        )
    account = Account(email, mode, password)
    with mailbox(account) as client:
        client.select_folder("INBOX", readonly=True)
    if mode == "send":
        with outgoing(account):
            pass
    from keyring.errors import KeyringError

    try:
        save(account)
    except KeyringError:
        raise Problem(
            "Вход проверен. Разблокируйте системное хранилище паролей пользователя и повторите подключение."
        ) from None
