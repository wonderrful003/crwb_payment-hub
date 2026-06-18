from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UploadJob(models.Model):

    PAYMENT_TYPES = [
        ("supplier", "Supplier"),
        ("salary", "Salary"),
        ("remittancePRN", "Remittance PRN"),
        ("remittanceTR", "Remittance TR"),
        ("foreign", "Foreign"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPES)
    uploaded_file = models.FileField(upload_to="uploads/%Y/%m/")

    generated_file = models.FileField(upload_to="generated/", null=True, blank=True)

    total_records = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    error_message = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="upload_jobs",
    )

    preview_data = models.JSONField(null=True, blank=True)

    # Stores the first and last generated reference numbers, e.g. "SLR00000001 – SLR00000025"
    reference_range = models.CharField(max_length=60, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.payment_type} - {self.status}"


class ReferenceCounter(models.Model):
    """
    Stores a single global sequential reference number
    for all payment types (cheque-style numbering).
    """

    prefix = models.CharField(max_length=10, unique=True, default="54SC")
    last_number = models.BigIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.prefix}{str(self.last_number).zfill(8)}"


# NEW: Template model for storing uploaded templates
class PaymentTemplate(models.Model):
    """
    Stores Excel templates that users can download and fill.
    Admins upload these through Django admin.
    """
    
    PAYMENT_TYPES = [
        ("supplier", "Supplier"),
        ("salary", "Salary"),
        ("remittancePRN", "Remittance PRN"),
        ("remittanceTR", "Remittance TR"),
        ("foreign", "Foreign"),
    ]
    
    payment_type = models.CharField(
        max_length=30, 
        choices=PAYMENT_TYPES,
        unique=True,
        help_text="The payment type this template is for"
    )
    
    template_file = models.FileField(
        upload_to="templates/%Y/%m/",
        help_text="Excel template file (.xlsx or .xls)"
    )
    
    version = models.CharField(
        max_length=10, 
        default="1.0",
        help_text="Template version number"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional description of this template"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is available for download"
    )
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_templates",
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['payment_type']
        verbose_name = "Payment Template"
        verbose_name_plural = "Payment Templates"
    
    def __str__(self):
        return f"{self.get_payment_type_display()} Template v{self.version}"
    
    def filename(self):
        """Return the filename of the template."""
        return self.template_file.name.split('/')[-1] if self.template_file else None