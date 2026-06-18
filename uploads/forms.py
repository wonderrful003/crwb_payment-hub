from django import forms


PAYMENT_TYPES = [
    ("supplier", "Supplier"),
    ("salary", "Salary"),
    ("remittancePRN", "Remittance PRN"),
    ("remittanceTR", "Remittance TR"),
    ("foreign", "Foreign"),
]


class UploadForm(forms.Form):
    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPES,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )

    excel_file = forms.FileField(
        widget=forms.FileInput(
            attrs={
                "class": "form-control"
            }
        )
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data["excel_file"]

        if not excel_file.name.lower().endswith((".xlsx", ".xls")):
            raise forms.ValidationError("Please upload an Excel file (.xlsx or .xls)")

        if excel_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large. Maximum size is 10MB")

        return excel_file