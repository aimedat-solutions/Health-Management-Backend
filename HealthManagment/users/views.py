from rest_framework import generics, permissions
from .models import Patient, Doctor, Question,DietPlan, CustomUser,SectionOneQuestions, SectionTwoQuestions, SectionThreeQuestions, SectionFourQuestions, SectionFiveQuestions
from .serializers import PatientSerializer, DietPlanSerializer,DoctorSerializer, QuestionSerializer,UserRegistrationSerializer,UserLoginSerializer,CustomUserDetailsSerializer,CombinedSectionSerializer
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from dj_rest_auth.views import LoginView
from datetime import date
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import authenticate
from .decryption import decrypt_password
from rest_framework.views import APIView
from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema
from users.permissions import PermissionsManager
from rest_framework import viewsets
from rest_framework import serializers
class UserRegistrationAPIView(APIView):
    serializer_class = UserRegistrationSerializer
    def post(self, request):
        decrypted_data = {}
        for field, value in request.data.items():
            decrypted_data[field] = decrypt_password(value)
        serializer = UserRegistrationSerializer(data=decrypted_data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            response_data = serializer.data
            response_data['access_token'] = access_token
            response_data['refresh_token'] = refresh_token
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomLoginView(LoginView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = UserLoginSerializer
    
    def post(self, request, *args, **kwargs):
        decrypted_data = {}
        for field, value in request.data.items():
            decrypted_data[field] = decrypt_password(value)
        serializer = self.get_serializer(data=decrypted_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
        }
        response_data.update(CustomUserDetailsSerializer(user).data)
        return Response(response_data, status=status.HTTP_200_OK)
    
@extend_schema(methods=['GET'], exclude=True)
class LogoutAPIView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = 'dj_rest_auth'

    def get(self, request, *args, **kwargs):
        if getattr(settings, 'ACCOUNT_LOGOUT_ON_GET', False):
            response = self.logout(request)
        else:
            response = self.http_method_not_allowed(request, *args, **kwargs)

        return self.finalize_response(request, response, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.logout(request)

    def logout(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            pass

        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_logout(request)

        response = Response(
            {'detail': ('Successfully logged out.')},
            status=status.HTTP_200_OK,
        )

        if getattr(settings, 'REST_USE_JWT', False):
            from rest_framework_simplejwt.exceptions import TokenError
            from rest_framework_simplejwt.tokens import RefreshToken

            from .jwt_auth import unset_jwt_cookies
            cookie_name = getattr(settings, 'JWT_AUTH_COOKIE', None)

            unset_jwt_cookies(response)

            if 'rest_framework_simplejwt.token_blacklist' in settings.INSTALLED_APPS:
                try:
                    token = RefreshToken(request.data['refresh'])
                    token.blacklist()
                except KeyError:
                    response.data = {'detail': _(
                        'Refresh token was not included in request data.')}
                    response.status_code = status.HTTP_401_UNAUTHORIZED
                except (TokenError, AttributeError, TypeError) as error:
                    if hasattr(error, 'args'):
                        if 'Token is blacklisted' in error.args or 'Token is invalid or expired' in error.args:
                            response.data = {'detail': _(error.args[0])}
                            response.status_code = status.HTTP_401_UNAUTHORIZED
                        else:
                            response.data = {'detail': _(
                                'An error has occurred.')}
                            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    else:
                        response.data = {'detail': _('An error has occurred.')}
                        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            elif not cookie_name:
                message = _(
                    'Neither cookies or blacklist are enabled, so the token '
                    'has not been deleted server side. Please make sure the token is deleted client side.',
                )
                response.data = {'detail': message}
                response.status_code = status.HTTP_200_OK
        return response

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    
class UserEditView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    
class PatientListCreateView(generics.ListCreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [PermissionsManager]
    codename = 'patient'

class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [PermissionsManager]
    codename = 'patient'
    
class DoctorListCreateView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [PermissionsManager]
    codename = 'doctor'

class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [PermissionsManager]
    codename = 'doctor'
        
class DietPlanViewSet(viewsets.ModelViewSet):
    queryset = DietPlan.objects.all()
    serializer_class = DietPlanSerializer
    permission_classes = [PermissionsManager]
    codename = 'doctor'

    def perform_create(self, serializer):
        patient_id = self.request.data.get('patient_id')
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient does not exist.")
        serializer.save(patient=patient)
    
    def retrieve(self, request, patient_id, selected_date):
        try:
            # Convert selected_date to a date object
            selected_date = date.fromisoformat(selected_date)
            # Retrieve the diet plan for the specific date
            diet_plan = DietPlan.objects.filter(patient_id=patient_id, date=selected_date)

            if not diet_plan.exists():
                return Response({"error": "Diet plan not found for the selected date."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DietPlanSerializer(diet_plan, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    # def get_queryset(self):
    #     user = self.request.user
    #     if hasattr(user, 'doctor' and 'admin'):
    #         return DietPlan.objects.filter(patient__doctor=user.doctor)
    #     return DietPlan.objects.none()

class QuestionListCreateView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    # permission_classes = [permissions.IsAdminUser]

class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAdminUser]
    

class CombinedSectionView(APIView):
    serializer_class = CombinedSectionSerializer
    def post(self, request, *args, **kwargs):
        serializer = CombinedSectionSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SectionDataView(APIView):
    serializer_class = CombinedSectionSerializer
    def get(self, request, section_type, user_id, *args, **kwargs):
        if section_type == 'I':
            instance = SectionOneQuestions.objects.filter(user_id=user_id).first()
        elif section_type == 'II':
            instance = SectionTwoQuestions.objects.filter(user_id=user_id).first()
        elif section_type == 'III':
            instance = SectionThreeQuestions.objects.filter(user_id=user_id).first()
        elif section_type == 'IV':
            instance = SectionFourQuestions.objects.filter(user_id=user_id).first()
        elif section_type == 'V':
            instance = SectionFiveQuestions.objects.filter(user_id=user_id).first()
        else:
            return Response({"detail": "Invalid section type"}, status=status.HTTP_400_BAD_REQUEST)

        if not instance:
            return Response({"detail": "Data not found"}, status=status.HTTP_404_NOT_FOUND)

        context = {'section_type': section_type}
        serializer = CombinedSectionSerializer(instance, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)