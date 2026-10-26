# Registration Turnstile

Set `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` in the root `.env` or deployment environment. `.others/.env.prod` is a reference file and is not loaded automatically. Create a Cloudflare Turnstile widget and allow your application hostname in its settings. Never expose the secret key to the browser.

Set `TURNSTILE_REQUIRE=true` to require verification, including for authenticated users. When the flag is absent or false, the widget and backend verification are skipped for local development. The older `TURNSTILE_REQUIRE_AUTH` flag is also accepted when `TURNSTILE_REQUIRE` is absent. Missing keys block submissions only when verification is required. The backend POSTs the token to Cloudflare Siteverify with a ten-second timeout and requires `success: true`, action `registration`, and a hostname matching the request. Missing, expired, reused, or invalid tokens and service failures block saving and emailing. Errors return the form with a verification message.

The widget automatically refreshes expired tokens. Tokens are single use and expire after five minutes. After a rejected submission, complete verification again and reselect the photo if the browser clears it.

Tests mock Siteverify and do not contact Cloudflare. For manual testing, configure a widget for your development hostname or use Cloudflare's documented testing keys; production credentials must be used for deployment.

References:
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- https://developers.cloudflare.com/turnstile/troubleshooting/testing/
