# Fix Patient Response API for Doctor View

## Problem
The `/doctor/patientresponse/` API currently returns flat responses without:
- Grouping by patient
- Including `selected_option` details
- Proper image URLs for questions
- Clear structure showing which patient answered which questions

## Current State
- Endpoint: `GET /doctor/patientresponse/`
- View: `QuestionAnswerListCreateView` in `users/views.py`
- Serializer: `QuestionAnswerSerializer` in `users/serializers.py`
- Model: `PatientResponse` links user → question → selected_option/response_text

## Changes Required

### 1. `users/serializers.py`

#### Add `selected_option` to `QuestionAnswerSerializer`
```python
class QuestionAnswerSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    user_info = ProfileSerializer(source="user.profile", read_only=True)
    selected_option = OptionSerializer(read_only=True)  # NEW
    class Meta:
        model = PatientResponse
        fields = ["id", "user", "questions", "selected_option", "response_text", "user_info", "created_at", "created_by", "updated_at", "updated_by"]
```

#### Create `DoctorPatientResponseSerializer`
```python
class DoctorPatientResponseSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    patient_name = serializers.CharField()
    phone_number = serializers.CharField()
    responses = QuestionAnswerSerializer(many=True)
```

### 2. `users/views.py`

#### Update `QuestionAnswerListCreateView.get()` for doctor role
```python
def get(self, request):
    user = request.user
    if user.role == "patient":
        answers = PatientResponse.objects.filter(user=user)
        serializer = QuestionAnswerSerializer(answers, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif user.role == "doctor":
        patient_ids = CustomUser.objects.filter(
            role="patient",
            assigned_diets__doctor=user
        ).values_list("id", flat=True).distinct()
        
        answers = PatientResponse.objects.filter(user_id__in=patient_ids).select_related('question', 'user', 'selected_option')
        
        patient_id_filter = request.query_params.get("patient_id")
        if patient_id_filter:
            answers = answers.filter(user_id=patient_id_filter)
        
        # Group responses by patient
        from collections import defaultdict
        grouped = defaultdict(list)
        for answer in answers:
            grouped[answer.user.id].append(answer)
        
        result = []
        for patient_id, responses in grouped.items():
            patient = responses[0].user
            profile = getattr(patient, "profile", None)
            first_name = getattr(profile, "first_name", "") or ""
            last_name = getattr(profile, "last_name", "") or ""
            
            result.append({
                "patient_id": patient_id,
                "patient_name": f"{first_name} {last_name}".strip() or patient.username,
                "phone_number": str(patient.phone_number) if patient.phone_number else "",
                "responses": QuestionAnswerSerializer(responses, many=True, context={'request': request}).data
            })
        
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response({"detail": "Unauthorized user."}, status=status.HTTP_403_FORBIDDEN)
```

### 3. Add imports to `users/views.py`
```python
from collections import defaultdict
```

## Expected API Response

### Doctor View
```json
[
  {
    "patient_id": 5,
    "patient_name": "Jane Doe",
    "phone_number": "+1234567890",
    "responses": [
      {
        "id": 12,
        "user": 5,
        "questions": {
          "id": 1,
          "question_text": "Do you have diabetes?",
          "question_image": "https://hospitalhealth.duckdns.org/media/questions_images/diabetes.png",
          "category": "initial",
          "type": "radio",
          "options": [
            {"id": 1, "value": "Yes", "type": "default"},
            {"id": 2, "value": "No", "type": "default"}
          ]
        },
        "selected_option": {"id": 1, "value": "Yes", "type": "default"},
        "response_text": null,
        "user_info": {
          "id": 10,
          "first_name": "Jane",
          "last_name": "Doe",
          ...
        },
        "created_at": "2026-05-20T10:30:00Z"
      }
    ]
  }
]
```

### Patient View (unchanged)
```json
[
  {
    "id": 12,
    "user": 5,
    "questions": {...},
    "selected_option": {...},
    "response_text": "...",
    "user_info": {...},
    "created_at": "..."
  }
]
```

## Query Parameters (Doctor only)
- `?patient_id=X` - Filter responses for a specific patient

## Files to Modify
1. `users/serializers.py` - Add `selected_option` field + `DoctorPatientResponseSerializer`
2. `users/views.py` - Update GET logic to group by patient for doctors, add imports

## Risks
- Breaking patient view if serializer changes affect both roles (mitigated by keeping `QuestionAnswerSerializer` unchanged for patients)
- Performance with many responses (mitigated by `select_related`)
