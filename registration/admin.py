from django.contrib import admin
from django.db.models import Count, Q

from .models import CampusAmbassadorApplication, IntegrationRecord


admin.site.register(CampusAmbassadorApplication)


@admin.register(IntegrationRecord)
class IntegrationRecordAdmin(admin.ModelAdmin):
    change_list_template = 'admin/registration/integrationrecord/change_list.html'
    list_display = ['created_at', 'kind', 'status', 'application', 'actor', 'recipient',
                    'test_email', 'http_status', 'error_type']
    list_filter = ['kind', 'status', 'test_email', 'created_at', 'backend']
    search_fields = ['recipient', 'subject', 'application__full_name', 'actor__username']
    date_hierarchy = 'created_at'
    readonly_fields = [field.name for field in IntegrationRecord._meta.fields]
    list_select_related = ['application', 'actor']
    actions = None

    def changelist_view(self, request, extra_context=None):
        if self.has_view_permission(request):
            totals = self.get_queryset(request).aggregate(
                api_calls=Count('pk', filter=Q(kind=IntegrationRecord.Kind.REMOVE_BG)),
                mail_attempts=Count('pk', filter=~Q(kind=IntegrationRecord.Kind.REMOVE_BG)),
                mail_accepted=Count('pk', filter=~Q(kind=IntegrationRecord.Kind.REMOVE_BG)
                                    & Q(status=IntegrationRecord.Status.SUCCESS)),
                failures=Count('pk', filter=Q(status=IntegrationRecord.Status.FAILED)),
            )
            extra_context = {**(extra_context or {}), 'integration_totals': totals}
        return super().changelist_view(request, extra_context=extra_context)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
