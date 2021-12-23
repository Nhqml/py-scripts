import argparse
import csv
import smtplib
import sys
import textwrap
from collections import defaultdict
from collections.abc import Generator, Iterable
from email.generator import Generator as EmailGenerator
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.utils import formataddr, parseaddr
from getpass import getpass
from pathlib import Path
from tempfile import mkdtemp
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


def read_data(path: str) -> list[dict[str, str]]:
    with open(path, 'r', encoding='utf-8', newline='') as data_file:
        reader = csv.DictReader(data_file, restkey='_unnamed_values', restval='')

        if not reader.fieldnames:
            sys.exit('Your data file is empty!')

        data = [dict(row.items()) for row in reader]

    return data


def save_email(path: Path, mail: EmailMessage):
    with open(path.with_suffix('.eml'), 'w', encoding='utf-8') as email_file:
        EmailGenerator(email_file).flatten(mail)


def send_email(conn: smtplib.SMTP, mail: EmailMessage):
    try:
        conn.send_message(mail)
        print(f"Mail sent to {mail['To']}")
    except smtplib.SMTPException as e:
        print(f"Failed to send mail to {mail['To']}! Reason: {e}", file=sys.stderr)


def wrap(content: str,
         width: int = 74,
         break_long_words: bool = False,
         replace_whitespace: bool = False,
         **kwargs) -> str:
    wrapped_lines = []

    for line in content.splitlines():
        if line == '-- ':  # Signature line: you don't want it to be changed!
            wrapped_lines.append(line)
        elif line.strip() == '':
            wrapped_lines.append('')
        else:
            wrapped_lines.extend(
                textwrap.wrap(line,
                              width=width,
                              break_long_words=break_long_words,
                              replace_whitespace=replace_whitespace,
                              **kwargs))

    return '\n'.join(wrapped_lines)


def compose_email(mail_headers: dict[str, str],
                  content: str,
                  attachments: Optional[Iterable[Path]] = None) -> EmailMessage:
    message = EmailMessage()
    message.set_content(wrap(content))

    for key, value in mail_headers.items():
        message[key] = value

    if attachments:
        message.make_mixed()
        for attachment in attachments:
            with open(attachment, 'rb') as attachment_file:
                part = MIMEApplication(attachment_file.read())
                part.add_header('Content-Disposition', 'attachment', filename=attachment.name)
                message.attach(part)

    return message


def compose_mass_email(data: list[dict[str, str]],
                       mail_headers: dict[str, str],
                       recipients_format: list[str],
                       template: Template,
                       attachments_formats: Optional[list[str]] = None) -> Generator[EmailMessage, None, None]:
    for line in data:
        context = defaultdict(str, line)
        mail_headers['To'] = ', '.join(map(lambda s: s.format_map(context), recipients_format))  # pylint: disable=cell-var-from-loop

        if attachments_formats:
            yield compose_email(mail_headers, template.render(**line),
                                map(lambda s: Path(s.format_map(context)), attachments_formats))  # pylint: disable=cell-var-from-loop
        else:
            yield compose_email(mail_headers, template.render(**line))


def send_mass_email(args: argparse.Namespace) -> None:
    jinja_env = Environment(loader=FileSystemLoader(args.template_dir))

    try:
        jinja_template = jinja_env.get_template(args.template_name)
    except TemplateNotFound:
        sys.exit(f"Template '{args.template_name}' not found!")

    data = read_data(args.data_csv)

    sender = formataddr(parseaddr(args.sender))

    mail_headers = {
        'From': sender,
    }

    if args.subject:
        mail_headers['Subject'] = args.subject

    reply_to = formataddr(parseaddr(args.reply_to)) if args.reply_to else None
    if reply_to:
        mail_headers['Reply-to'] = reply_to

    mails = compose_mass_email(data, mail_headers, args.recipients, jinja_template, args.attachments)

    if args.dry_run:
        tmp_dir = Path(mkdtemp(prefix='minimailer'))

        for i, mail in enumerate(mails):
            save_email(tmp_dir / str(i), mail)

        print(f"Email have been saved to '{tmp_dir}'")
    else:
        with smtplib.SMTP_SSL(host=args.smtp_host, port=args.smtp_port) as conn:
            smtp_user = args.smtp_user or input('Please enter SMTP user: ')

            if args.password_file:
                with open(args.password_file, 'r', encoding='utf-8') as password_file:
                    password = password_file.read().strip()
            else:
                password = getpass('Please enter SMTP password: ')

            conn.login(
                user=smtp_user,
                password=password,
            )

            for mail in mails:
                send_email(conn, mail)


def get_argparser():
    parser = argparse.ArgumentParser(description="Mass email sender")

    parser.add_argument('data_csv', help='CSV file containing addresses and template data')
    parser.add_argument('sender', help="'From' field of the email")
    parser.add_argument('template_name', help='name of the Jinja2 template to use')
    parser.add_argument('--subject', help='subject of the email')

    parser.add_argument('--reply-to', help="'Reply-to' field of the email")

    parser.add_argument('--recipients',
                        help="email's recipients format-string - Python syntax (default: `%(default)s`)",
                        default=['{firstname} {lastname} <{email}>'],
                        nargs='*')
    parser.add_argument('--attachments', help="email's attachments format-strings - Python syntax", nargs='*')

    parser.add_argument('-u', '--smtp-user', help='SMTP username')
    parser.add_argument('-p', '--password-file', help='path to the file containing the SMTP password')
    parser.add_argument('--smtp-host', '--host', help='hostname of the SMTP server', default='smtp.gmail.com')
    parser.add_argument('--smtp-port', '--port', help='port of the SMTP server', default=465)

    parser.add_argument('--template-dir', help='directory where Jinja2 templates are stored', default='.')

    parser.add_argument('--dry-run',
                        '--fake-run',
                        help='do not send mail, save them to a temp dir for review instead',
                        action='store_true',
                        default=False)
    return parser


if __name__ == '__main__':
    send_mass_email(get_argparser().parse_args())
