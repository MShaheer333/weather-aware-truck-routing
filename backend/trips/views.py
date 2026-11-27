from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.views import View
from rest_framework.response import Response
from rest_framework.views import APIView

from .presenters import present
from .serializers import AnalyzeRequestSerializer
from .services import analysis, geocoding


class HealthView(APIView):
    throttle_classes: list = []

    def get(self, request):
        return Response({"status": "ok"})


class GeocodeView(APIView):
    """GET /api/geocode/?q=chicago -> place suggestions."""

    def get(self, request):
        places = geocoding.search(request.query_params.get("q", ""))
        return Response({"results": [{"label": p.label, "lat": p.lat, "lon": p.lon} for p in places]})


class AnalyzeView(APIView):
    """POST /api/analyze/ -> 3 weather-scored routes, a recommendation and heatmap data."""

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        origin, destination = data["origin"], data["destination"]
        result = analysis.analyze(
            origin=(origin["lat"], origin["lon"]),
            destination=(destination["lat"], destination["lon"]),
            departure=data["departure_time"],
            load_lb=data["load_weight_lb"],
            interval_miles=data["checkpoint_interval_miles"],
        )
        echo = {
            "origin": dict(origin),
            "destination": dict(destination),
            "departure_time": result.departure.isoformat(),
            "load_weight_lb": result.load_lb,
            "checkpoint_interval_miles": result.interval_miles,
        }
        return Response(present(result, echo))


class SpaView(View):
    """Serve the React build's index.html (production). In development the Vite server is used."""

    def get(self, request, *args, **kwargs):
        index = settings.FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(open(index, "rb"), content_type="text/html")
        return JsonResponse({"message": "Weather-aware truck routing API. Frontend build not found."})
