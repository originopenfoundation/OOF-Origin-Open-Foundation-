import os

from gie.service import InternalGIEService, Principal, TokenAuthenticator, serve_private


def main():
    token = os.environ["GIE_SERVICE_TOKEN"]
    tenant = os.environ["GIE_ANALYTICS_TENANT"]
    if len(token) < 32 or not 1 <= len(tenant) <= 80:
        raise SystemExit("Set a service token of at least 32 characters and a valid tenant.")

    def assessment_disabled(_tenant):
        raise RuntimeError("Assessment runtime is disabled on this service")

    service = InternalGIEService(
        assessment_disabled,
        authenticator=TokenAuthenticator({
            token: Principal("lara", frozenset({tenant})),
        }),
        approved_plugins={},
        analytics_tenants=frozenset({tenant}),
    )
    serve_private(service, host="0.0.0.0", port=8788).serve_forever()


if __name__ == "__main__":
    main()
