from django.contrib import admin
from .models import Doctor, DietPlan,Question,Exercise, Profile, CustomUser,Option,DoctorExerciseResponse,PatientResponse





admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Doctor)
admin.site.register(DietPlan)
admin.site.register(Exercise)
admin.site.register(DoctorExerciseResponse)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(PatientResponse)