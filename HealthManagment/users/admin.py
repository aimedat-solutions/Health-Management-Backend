from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Doctor, DietPlan,Question, Patient, CustomUser, SectionOneQuestions, SectionTwoQuestions, SectionThreeQuestions, SectionFourQuestions, SectionFiveQuestions

admin.site.register(CustomUser)
admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(DietPlan)
admin.site.register(Question)
admin.site.register(SectionOneQuestions)
admin.site.register(SectionTwoQuestions)
admin.site.register(SectionThreeQuestions)
admin.site.register(SectionFourQuestions)
admin.site.register(SectionFiveQuestions)