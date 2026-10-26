# Registration email setup

The application loads `.env` from the project root. `.others/.env.prod` is a deployment reference; its values must be provided through the deployment environment or copied into the root `.env`.

Set these values:

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
AWS_SES_REGION=ap-south-1
AWS_SES_SMTP_USERNAME=<SES SMTP username>
AWS_SES_SMTP_PASSWORD=<SES SMTP password>
DJANGO_DEFAULT_FROM_EMAIL=BIIN <noreply@biin.org.bd>
SITE_URL=https://biin.org.bd
REGISTRATION_RESPONSE_EMAIL=
REGISTRATION_PDF_LINK_MAX_AGE=604800
```

Use the region where your SES sender identity is verified. SMTP uses STARTTLS on port 587. SES SMTP credentials differ from AWS API credentials; do not copy API access keys into these settings. Verify the sender identity in SES. In the SES sandbox, recipients must also be verified (or request production access).

An empty `REGISTRATION_RESPONSE_EMAIL` sends to the email entered in the form. Set it to one fixed email address to redirect confirmations there. Each email contains plain text, HTML, the completed application PDF attachment, and a unique signed download link that expires after seven days. Anyone holding that link can download that one application until expiry. Files are generated on demand rather than stored under public media URLs.

A mail failure is logged against the application ID; the saved submission remains available to staff. No automatic retry is configured.

For local development use `DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`. Tests use an in-memory mailbox and do not send real emails.

AWS reference: https://docs.aws.amazon.com/ses/latest/dg/send-email-smtp.html
