from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from Login.views import (
    RegistroUsuario, UsuarioABMView, UsuarioUpdateView, UsuarioDeleteView,
    CelularListView, CelularCreateView, CelularUpdateView, CelularDeleteView,
    CelularDetailView, agregar_al_carrito, ver_carrito
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    

    path('registrar/', RegistroUsuario.as_view(), name='registrar'),
    path('home/', UsuarioABMView.as_view(), name='home'),
    path('editar/<int:pk>/', UsuarioUpdateView.as_view(), name='editar_usuario'),
    path('eliminar/<int:pk>/', UsuarioDeleteView.as_view(), name='eliminar_usuario'),
    path('', CelularListView.as_view(), name='inicio'), 

    path('celulares/', CelularListView.as_view(), name='lista_celulares'),
    path('celulares/nuevo/', CelularCreateView.as_view(), name='crear_celular'),
    path('celulares/editar/<int:pk>/', CelularUpdateView.as_view(), name='editar_celular'),
    path('celulares/eliminar/<int:pk>/', CelularDeleteView.as_view(), name='eliminar_celular'),
    
   
    path('celulares/detalle/<int:pk>/', CelularDetailView.as_view(), name='detalle_celular'),
    
    path('carrito/', ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:pk>/', agregar_al_carrito, name='agregar_carrito'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)