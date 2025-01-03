# from django.contrib import admin
from django.urls import path, include, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from django.contrib import admin

schema_view = get_schema_view(
    openapi.Info(
        title="Uzinfocom Rent Car System API",
        default_version='v1',
        description="API for Uzinfocom Rent Car System",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="mail@mail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path('users/', include('users.urls')),
    path('stations/', include('stations.urls')),
    path('vehicles/', include('vehicles.urls')),
    path('rentals/', include('rentals.urls')),
    path('payments/', include('payments.urls')),
       path('admin/', admin.site.urls),
]

urlpatterns += [
    # API schema
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]