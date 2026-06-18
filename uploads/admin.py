from django.contrib import admin
from .models import UploadJob, ReferenceCounter, PaymentTemplate


@admin.register(UploadJob)
class UploadJobAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_type", "status", "total_records", "uploaded_by", "created_at")
    list_filter = ("payment_type", "status")
    search_fields = ("uploaded_by__username", "error_message")
    readonly_fields = ("created_at", "completed_at")


@admin.register(ReferenceCounter)
class ReferenceCounterAdmin(admin.ModelAdmin):
    list_display = ("prefix", "last_number", "updated_at")


@admin.register(PaymentTemplate)
class PaymentTemplateAdmin(admin.ModelAdmin):
    list_display = ("payment_type", "get_payment_type_display", "version", "is_active", "uploaded_at")
    list_filter = ("payment_type", "is_active")
    search_fields = ("description",)
    readonly_fields = ("uploaded_at", "updated_at")
    
    fieldsets = (
        (None, {
            "fields": ("payment_type", "template_file", "version", "description")
        }),
        ("Status", {
            "fields": ("is_active", "uploaded_by")
        }),
        ("Timestamps", {
            "fields": ("uploaded_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)