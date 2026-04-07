from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Cliente, Producto, Venta, DetalleVenta, Pago, Factura, MovimientoInventario

class UsuarioCustomAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('nombre_completo', 'rol', 'estado')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('nombre_completo', 'rol', 'estado')}),
    )

admin.site.register(Usuario, UsuarioCustomAdmin)
admin.site.register(Cliente)
admin.site.register(Producto)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Pago)
admin.site.register(Factura)
admin.site.register(MovimientoInventario)
