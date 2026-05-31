from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import IntegrityError
from .models import CrowdSnapshot
from accounts.models import Office

@method_decorator(csrf_exempt, name='dispatch')
class CrowdDetectionUploadView(APIView):

    def post(self, request):
        # 1. Capture the data
        data = request.data
        office_id = data.get("office")
        people_count = data.get("people_count")
        crowd_status = data.get("crowd_status")

        # DEBUG: This will show up in your Django terminal
        print(f"\n--- Incoming Request ---")
        print(f"Data: {data}")
        print(f"------------------------\n")

        # 2. Detailed Validation for Required Fields
        missing_fields = []
        if office_id is None: missing_fields.append("office")
        if people_count is None: missing_fields.append("people_count")
        if crowd_status is None: missing_fields.append("crowd_status")

        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}", "received": data},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validate Office Existence
        try:
            # We use office_id=office_id to match the model field name
            office = Office.objects.get(office_id=office_id)
        except Office.DoesNotExist:
            return Response(
                {"error": f"Office ID {office_id} not found in database."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. Validate and Convert people_count
        try:
            people_count = int(people_count)
            if people_count < 0:
                return Response({"error": "people_count cannot be negative"}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({"error": "people_count must be a valid integer"}, status=status.HTTP_400_BAD_REQUEST)

        # 5. Validate crowd_status against Model Choices
        valid_statuses = dict(CrowdSnapshot.CROWD_STATUS_CHOICES)
        if crowd_status not in valid_statuses:
            return Response(
                {"error": f"Invalid crowd_status. Must be one of: {list(valid_statuses.keys())}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 6. Save Snapshot
        try:
            snapshot = CrowdSnapshot.objects.create(
                office=office,
                people_count=people_count,
                crowd_status=crowd_status
            )

            return Response({
                "message": "✅ Crowd data saved successfully",
                "snapshot_id": snapshot.snapshot_id,
                "office": office.branch_name,
                "people_count": snapshot.people_count,
                "crowd_status": snapshot.crowd_status
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)