from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from datetime import timedelta
import pandas as pd
import os
import csv
from io import BytesIO, StringIO
from openpyxl import Workbook

from .forms import UploadForm
from .models import UploadJob, ReferenceCounter, PaymentTemplate
from .utils import (
    convert_supplier,
    convert_salary,
    convert_remittancePRN,
    convert_foreign,
    convert_remittanceTR,
    build_export_filename,
)

PAYMENT_CONFIG = {
    "supplier":      {"prefix": "OBDXPMN", "ref_prefix": "SUP", "name": "Supplier",  "converter": convert_supplier,      "debit_account_col": "Debit Account Num"},
    "salary":        {"prefix": "OBDXSF",  "ref_prefix": "SLR", "name": "Salary",    "converter": convert_salary,        "debit_account_col": "Debit Account Num"},
    "remittancePRN": {"prefix": "OBDXRP",  "ref_prefix": "PRN", "name": "Remittance PRN",    "converter": convert_remittancePRN, "debit_account_col": "Debit Account Num"},
    "remittanceTR":  {"prefix": "OBDXRM",  "ref_prefix": "TRN", "name": "Remittance TR",     "converter": convert_remittanceTR,  "debit_account_col": "Debit Account Num"},
    "foreign":       {"prefix": "OBDXFX",  "ref_prefix": "FRX", "name": "Foreign",   "converter": convert_foreign,       "debit_account_col": "Debit Account"},
}

def _visible_jobs(user):
    """Staff/admin see all jobs; everyone else sees only their own."""
    if user.is_staff:
        return UploadJob.objects.select_related("uploaded_by").all()
    return UploadJob.objects.filter(uploaded_by=user)

@login_required
def download_template(request, payment_type):
    """Download the stored template for the specified payment type."""
    try:
        # Get the active template for this payment type
        template = PaymentTemplate.objects.get(
            payment_type=payment_type,
            is_active=True
        )
        
        # Serve the file
        response = FileResponse(
            template.template_file.open("rb"),
            as_attachment=True,
            filename=template.filename()
        )
        return response
        
    except PaymentTemplate.DoesNotExist:
        messages.error(request, f"No active template found for {payment_type}")
        return redirect("uploads:index")
    except Exception as e:
        messages.error(request, f"Error downloading template: {str(e)}")
        return redirect("uploads:index")

@login_required
def download_file(request, job_id):
    """Download the converted file in the specified format."""
    job = get_object_or_404(_visible_jobs(request.user), id=job_id)

    if not job.generated_file:
        raise Http404("File not found")

    # Get format from query parameter (default to txt)
    file_format = request.GET.get('format', 'txt').lower()
    
    # Read the original file content
    job.generated_file.open('rb')
    content = job.generated_file.read().decode('utf-8')
    job.generated_file.close()
    
    # Get the original filename without extension
    original_filename = job.generated_file.name.split('/')[-1]
    base_filename = os.path.splitext(original_filename)[0]
    
    if file_format == 'csv':
        # Convert to CSV (same as TXT but with .csv extension)
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{base_filename}.csv"'
        return response
        
    elif file_format == 'xlsx':
        # Convert to Excel
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Converted Data"
            
            # Parse the content (assuming it's semicolon-delimited)
            lines = content.strip().split('\n')
            for row_idx, line in enumerate(lines, 1):
                # Split by semicolon (the delimiter used in the original)
                values = line.split(';')
                for col_idx, value in enumerate(values, 1):
                    ws.cell(row=row_idx, column=col_idx, value=value.strip())
            
            # Auto-adjust column widths
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column].width = adjusted_width
            
            # Save to buffer
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            
            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{base_filename}.xlsx"'
            return response
            
        except Exception as e:
            messages.error(request, f"Error converting to Excel: {str(e)}")
            return redirect("uploads:index")
    
    else:  # Default to txt
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{base_filename}.txt"'
        return response

@login_required
def index(request):
    jobs_qs = _visible_jobs(request.user)

    # ── Handle file upload POST ──
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            payment_type = form.cleaned_data["payment_type"]
            excel_file   = form.cleaned_data["excel_file"]

            job = UploadJob.objects.create(
                payment_type=payment_type,
                uploaded_file=excel_file,
                uploaded_by=request.user,
                status="PENDING"
            )

            config = PAYMENT_CONFIG.get(payment_type)
            if not config:
                job.status = "FAILED"
                job.error_message = "Invalid payment type"
                job.completed_at = timezone.now()
                job.save()
                messages.error(request, "Invalid payment type")
                return redirect("uploads:index")

            try:
                excel_file.seek(0)
                df = pd.read_excel(excel_file, dtype=str, engine="openpyxl")
                df.columns = df.columns.str.strip()

                csv_content, references = config["converter"](df)

                # Build reference_range from the actual generated list
                reference_range = ""
                if references:
                    if len(references) == 1:
                        reference_range = references[0]
                    else:
                        reference_range = f"{references[0]} \u2013 {references[-1]}"

                # Build preview with the real reference numbers injected
                preview_df = df.head(10).fillna("").copy()

                # Find or create the reference column
                ref_col = next(
                    (c for c in preview_df.columns if "reference" in c.lower()),
                    None
                )
                if ref_col is None:
                    ref_col = "Reference Num"
                    preview_df.insert(0, ref_col, "")

                # Write the actual generated references row by row
                for i in range(len(preview_df)):
                    if i < len(references):
                        preview_df.at[preview_df.index[i], ref_col] = references[i]

                # Move reference column to front
                cols = list(preview_df.columns)
                if ref_col in cols and cols[0] != ref_col:
                    cols.insert(0, cols.pop(cols.index(ref_col)))
                    preview_df = preview_df[cols]

                preview = preview_df.to_dict(orient="records")
                columns = list(preview_df.columns)

                now = timezone.now()
                debit_col = config["debit_account_col"]
                debit_account_num = df.iloc[0].get(debit_col, "")
                filename = build_export_filename(config["prefix"], debit_account_num)

                job.generated_file.save(filename, ContentFile(csv_content.encode("utf-8")))
                job.total_records   = len(df)
                job.preview_data    = {"rows": preview, "columns": columns, "total_rows": len(df)}
                job.reference_range = reference_range
                job.status          = "SUCCESS"
                job.completed_at    = timezone.now()
                job.save()
                messages.success(request, f"File processed successfully! {len(df)} records converted.")

            except ValueError as e:
                error_msg = str(e).replace("VALIDATION_ERROR: ", "")
                job.status        = "FAILED"
                job.error_message = error_msg
                job.completed_at  = timezone.now()
                job.save()
                messages.error(request, f"Validation error: {error_msg}")

            except Exception as e:
                job.status        = "FAILED"
                job.error_message = str(e)
                job.completed_at  = timezone.now()
                job.save()
                messages.error(request, f"Processing failed: {str(e)}")

            return redirect("uploads:index")
    else:
        form = UploadForm()

    # ── Stats ──
    stats = {
        "total_jobs":      jobs_qs.count(),
        "successful":      jobs_qs.filter(status="SUCCESS").count(),
        "failed":          jobs_qs.filter(status="FAILED").count(),
        "pending":         jobs_qs.filter(status="PENDING").count(),
        "total_processed": jobs_qs.aggregate(total=models.Sum("total_records"))["total"] or 0,
    }

    # ── 7-day activity ──
    last_7 = timezone.now() - timedelta(days=7)
    daily_activity = (
        jobs_qs.filter(created_at__gte=last_7)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # ── Payment distribution ──
    payment_distribution = list(
        jobs_qs.values("payment_type").annotate(count=Count("id"))
    )
    for item in payment_distribution:
        item["display_name"] = PAYMENT_CONFIG.get(item["payment_type"], {}).get("name", item["payment_type"])

    # ── Check if templates exist ──
    template_status = {}
    for key in PAYMENT_CONFIG.keys():
        has_template = PaymentTemplate.objects.filter(
            payment_type=key,
            is_active=True
        ).exists()
        template_status[key] = has_template

    context = {
        "form":                 form,
        "recent_jobs":          jobs_qs.order_by("-created_at")[:5],
        "all_jobs":             jobs_qs.order_by("-created_at"),
        "stats":                stats,
        "daily_activity":       list(daily_activity),
        "payment_distribution": payment_distribution,
        "payment_types":        PAYMENT_CONFIG,
        "template_status":      template_status,
        "status_filter":        "",
        "payment_filter":       "",
        "search_query":         "",
        "status_choices":       UploadJob.STATUS_CHOICES,
    }

    return render(request, "index.html", context)

@login_required
def history(request):
    return redirect("uploads:index")

@login_required
def job_detail(request, job_id):
    return redirect("uploads:index")

@login_required
def stats_api(request):
    """Return live dashboard stats as JSON for client-side polling."""
    from django.http import JsonResponse
    jobs_qs = _visible_jobs(request.user)
    data = {
        "total_jobs":      jobs_qs.count(),
        "successful":      jobs_qs.filter(status="SUCCESS").count(),
        "failed":          jobs_qs.filter(status="FAILED").count(),
        "pending":         jobs_qs.filter(status="PENDING").count(),
        "total_processed": jobs_qs.aggregate(total=models.Sum("total_records"))["total"] or 0,
    }
    return JsonResponse(data)