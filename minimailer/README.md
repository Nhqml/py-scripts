minimailer
==========

A simple mailer that use jinja2 template to send mass[^1] mailing.

# Installation

## Requirements

Make sure you have python3 and pip3 installed.
Then install the requirements with pip3:
```bash
pip3 install jinja2
```

# Usage

A help is available with the `--help` option.

```bash
./minimailer.py --help
```

## CSV Format

The CSV file should have at least one column named email.

Any value in the CSV file can be used in the template as a variable.

## Example

Some example files are provided in the `example` directory, try them out!

```bash
./minimailer.py --dry-run --subject 'Hello World!' example/data.csv 'Kenji <kenji@example.com>' example/template.j2
```

As you can see, the `--dry-run` option is useful to test your template before sending the emails, have fun with it!

# Security

As you're concerned about security, you probably have 2FA enabled on your email account. To use this script, I strongly advise you to create a dedicated app password.

More information can be found here:
- https://support.google.com/accounts/answer/185833
- https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944

[^1]: do not abuse this tool or you could be blacklisted (or at least rate limited) by your email provider. For real mass mailing use a dedicated service.
