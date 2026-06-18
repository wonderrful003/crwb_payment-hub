from django.urls import path
from . import views

app_name = "uploads"

urlpatterns = [
    path("", views.index, name="index"),
    path("history/", views.history, name="history"),
    path("job/<int:job_id>/", views.job_detail, name="job_detail"),
    path("download/<int:job_id>/", views.download_file, name="download_file"),
    path("api/stats/", views.stats_api, name="stats_api"),
    # Template download URL
    path("template/<str:payment_type>/", views.download_template, name="download_template"),
]