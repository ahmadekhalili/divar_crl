from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("test/", views.test.as_view(), name="test"),
    path("crawl/", views.CrawlView.as_view(), name="crawl_view"),
]
