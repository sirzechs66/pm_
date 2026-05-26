from django.http import JsonResponse


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_id = None

        if request.path.startswith("/api/"):
            tenant_value = (
                request.headers.get("X-Tenant-Id")
                or request.GET.get("tenant_id")
                or request.POST.get("tenant_id")
            )
            if tenant_value is None:
                tenant_value = "1"
            try:
                request.tenant_id = int(tenant_value)
            except (TypeError, ValueError):
                return JsonResponse({"detail": "Invalid tenant id."}, status=400)

        return self.get_response(request)

