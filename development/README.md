# Local email previews

Start Django with `DEBUG=True` and open `/__dev__/emails/` on the current host.

- `/__dev__/emails/application-confirmation/`
- `/__dev__/emails/ambassador-selection/`
- `/__dev__/emails/card/`

Both email previews support `?format=txt` and `?test=1`. Sample PNG and PDF downloads are available from the previews. They use synthetic data, do not access the database, and do not send mail.

The root URL configuration imports this package only when `DEBUG=True`. Every preview view also checks DEBUG before loading sample data or generating assets. With `DEBUG=False`, the routes return 404. The existing `test_email` management command is also disabled in production.

Run the preview checks separately:

```sh
env/bin/python manage.py test development.tests
```
