# LaRA private engine analytics

The LaRA server exposes POST /_lara/admin/engine-analytics using the existing host-only admin authentication and LARA_ADMIN_TOKEN. Send a JSON analysis object such as {"capability":"descriptive","values":[1,3]}. The server calls the private engine over its internal network.

Deploy the private engine branch engine/build-10-15-foundation on a private network and enable the LaRA tenant via analytics_tenants. On the LaRA host set GIE_INTERNAL_URL, GIE_SERVICE_TOKEN and GIE_ANALYTICS_TENANT in the environment. Use a service token authorized for that tenant. The admin endpoint returns HTTP 503 until configuration is present.

The route is for authenticated server-host callers. The public browser widget and chat generation do not invoke it.
