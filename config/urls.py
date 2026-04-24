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
    InventarioListView, buscar_cliente, actualizar_cantidad_ajax,
    PagosPendientesListView, confirmar_pago, rechazar_pago,
    api_get_venta_status, api_notificaciones_admin, esperando_pago,
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDetailView,
    CompraListView, registrar_compra, ReclamoListView, ReclamoCreateView
)

urlpatterns = [
    # --- RUTA DE ADMINISTRACIÓN ---
    # Permite acceder al panel de administración nativo de Django.
    path('admin/', admin.site.urls),

    # --- RUTAS DE AUTENTICACIÓN (Predeterminadas de Django) ---
    # Incluye: login, logout, password_change, etc. 
    # Mapea a las plantillas dentro de 'templates/registration/'
    path('accounts/', include('django.contrib.auth.urls')),
    
    # --- FLUJO DE CLIENTES ---
    # Se llama mediante AJAX desde el carrito para verificar si un cliente existe por su documento.
    path('buscar-cliente/', buscar_cliente, name='buscar_cliente'),

    # Registro de nuevos usuarios (Clientes). 
    # Lleva a: templates/registration/registro.html. Al éxito redirige al 'login'.
    path('registrar/', RegistroUsuario.as_view(), name='registrar'),

    # Panel principal de gestión de usuarios (Solo para Administradores).
    path('home/', UsuarioABMView.as_view(), name='home'),

    # Edición y borrado de usuarios.
    path('editar/<int:pk>/', UsuarioUpdateView.as_view(), name='editar_usuario'),
    path('eliminar/<int:pk>/', UsuarioDeleteView.as_view(), name='eliminar_usuario'),

    # --- FLUJO DE PRODUCTOS (CATÁLOGO) ---
    # Página inicial: Lista todos los celulares. Template: template/celulares/lista_celulares.html
    path('', CelularListView.as_view(), name='inicio'), 

    # Alias para la lista de celulares.
    path('celulares/', CelularListView.as_view(), name='lista_celulares'),

    # Gestión de productos (Crear, Editar, Eliminar) - Solo para Superusuarios.
    path('celulares/nuevo/', CelularCreateView.as_view(), name='crear_celular'),
    path('celulares/editar/<int:pk>/', CelularUpdateView.as_view(), name='editar_celular'),
    path('celulares/eliminar/<int:pk>/', CelularDeleteView.as_view(), name='eliminar_celular'),
    
    # Detalle individual de un producto.
    path('celulares/detalle/<int:pk>/', CelularDetailView.as_view(), name='detalle_celular'),
    
    # --- FLUJO DEL CARRITO Y VENTAS ---
    # Muestra los productos seleccionados. Template: templates/celulares/carrito.html
    path('carrito/', ver_carrito, name='ver_carrito'),

    # Acciones para modificar el carrito (Añadir, Restar, Eliminar item).
    # 'agregar_carrito' añade 1 unidad y redirige de vuelta al 'ver_carrito'.
    path('carrito/agregar/<int:pk>/', agregar_al_carrito, name='agregar_carrito'),
    path('carrito/restar/<int:pk>/', restar_del_carrito, name='restar_carrito'),
    path('carrito/eliminar/<int:pk>/', eliminar_item_carrito, name='eliminar_item_carrito'),

    # Procesamiento final: Convierte el carrito en una Venta y Factura.
    # Al finalizar, redirige a 'detalle_factura'.
    path('carrito/procesar/', procesar_venta, name='procesar_venta'),

    # Muestra el documento PDF/Web de la factura finalizada.
    path('factura/<int:pk>/', detalle_factura, name='detalle_factura'),

    # Crea un registro de Cliente durante el checkout si no existe.
    path('cliente/nuevo/', ClienteCreateView.as_view(), name='crear_cliente'),

    # --- REPORTES E INVENTARIO (ADMIN) ---
    # Listado histórico de todas las ventas realizadas.
    path('ventas/reporte/', ReporteVentasView.as_view(), name='reporte_ventas'),

    # Vista técnica del stock actual y alertas de bajo inventario.
    path('inventario/', InventarioListView.as_view(), name='lista_inventario'),

    # Endpoint AJAX para actualizar cantidades en tiempo real sin recargar la página.
    path('carrito/actualizar-ajax/', actualizar_cantidad_ajax, name='actualizar_cantidad_ajax'),

    # --- NUEVAS RUTAS DE GESTIÓN DE PAGOS ---
    path('ventas/pagos-pendientes/', PagosPendientesListView.as_view(), name='pagos_pendientes'),
    path('pago/confirmar/<int:pk>/', confirmar_pago, name='confirmar_pago'),
    path('pago/rechazar/<int:pk>/', rechazar_pago, name='rechazar_pago'),

    # --- APIS Y ESPERA DE PAGO ---
    path('api/venta-status/<int:pk>/', api_get_venta_status, name='api_get_venta_status'),
    path('api/notificaciones-admin/', api_notificaciones_admin, name='api_notificaciones_admin'),
    path('pago/esperando/<int:pk>/', esperando_pago, name='esperando_pago'),
    # --- MÓDULO DE PROVEEDORES ---
    path('proveedores/', ProveedorListView.as_view(), name='lista_proveedores'),
    path('proveedores/nuevo/', ProveedorCreateView.as_view(), name='crear_proveedor'),
    path('proveedores/editar/<int:pk>/', ProveedorUpdateView.as_view(), name='editar_proveedor'),
    path('proveedores/detalle/<int:pk>/', ProveedorDetailView.as_view(), name='detalle_proveedor'),

    # Aprovisionamiento (Compras)
    path('proveedores/compras/', CompraListView.as_view(), name='lista_compras'),
    path('proveedores/compras/registrar/', registrar_compra, name='registrar_compra'),

    # Reclamos
    path('proveedores/reclamos/', ReclamoListView.as_view(), name='lista_reclamos'),
    path('proveedores/reclamos/nuevo/', ReclamoCreateView.as_view(), name='crear_reclamo'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)