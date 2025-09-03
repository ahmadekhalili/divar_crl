from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("test/", views.Test.as_view(), name="test"),
    path("close_map/", views.test_close_map.as_view(), name="test_simple"),
    path("crawl/", views.CrawlView.as_view(), name="crawl_view"),
]
