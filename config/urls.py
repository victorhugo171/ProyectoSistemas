from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from Login.views import (
    RegistroUsuario, UsuarioABMView, UsuarioUpdateView, UsuarioDeleteView,
    CelularListView, CelularCreateView, CelularUpdateView, CelularDeleteView,
    CelularDetailView, agregar_al_carrito, ver_carrito,
    procesar_venta, detalle_factura, ClienteCreateView,
    restar_del_carrito, eliminar_item_carrito, ReporteVentasView,
    InventarioListView, buscar_cliente, actualizar_cantidad_ajax
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('buscar-cliente/', buscar_cliente, name='buscar_cliente'),

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
    path('carrito/restar/<int:pk>/', restar_del_carrito, name='restar_carrito'),
    path('carrito/eliminar/<int:pk>/', eliminar_item_carrito, name='eliminar_item_carrito'),
    path('carrito/procesar/', procesar_venta, name='procesar_venta'),
    path('factura/<int:pk>/', detalle_factura, name='detalle_factura'),
    path('cliente/nuevo/', ClienteCreateView.as_view(), name='crear_cliente'),
    path('ventas/reporte/', ReporteVentasView.as_view(), name='reporte_ventas'),
    path('inventario/', InventarioListView.as_view(), name='lista_inventario'),
    path('carrito/actualizar-ajax/', actualizar_cantidad_ajax, name='actualizar_cantidad_ajax'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)