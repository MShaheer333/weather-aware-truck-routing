from django.urls import include, path

from trips.views import SpaView

urlpatterns = [
    path("api/", include("trips.urls")),
    # Everything else is the React single-page app (served in production only).
    path("", SpaView.as_view()),
]
