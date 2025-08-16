# core/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm as DjangoAuthenticationForm, PasswordChangeForm 
from .models import (
    CustomUser, Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    BajaEquipo, Ubicacion, Procedimiento, Proveedor # Importar solo el modelo Proveedor general
)
# Asegúrate de que ProveedorCalibracion, ProveedorMantenimiento, ProveedorComprobacion
# no están siendo importados si ya no existen como modelos separados,
# o si ya no se usan sus formularios. Asumo que Proveedor es el único general.

from django.forms.widgets import DateInput, FileInput, ClearableFileInput, TextInput # Importar TextInput
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime # Importar datetime para el parseo de fechas
import os

# Formulario de Autenticación personalizado para usar CustomUser
class AuthenticationForm(DjangoAuthenticationForm):
    pass

# Formulario para CustomUser (Creación)
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'empresa', 'is_staff', 'is_superuser',) # Asegúrate de incluir is_staff y is_superuser
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            # Añadir widgets para los campos de contraseña que UserCreationForm ya maneja
            # Estos son los nombres de campo por defecto para las contraseñas en UserCreationForm
            'password': forms.PasswordInput(attrs={'class': 'form-input'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-input'}), 
        }
    
    def __init__(self, *args, **kwargs):
        # Extraer 'request' antes de llamar a super().__init__
        request = kwargs.pop('request', None) 
        super().__init__(*args, **kwargs)
        # Si el usuario no es superusuario, no puede elegir empresa ni ser staff/superuser
        if request and not request.user.is_superuser:
            # Filtra el queryset de empresa para mostrar solo la empresa del usuario
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa.pk)
            self.fields['empresa'].empty_label = None # No permitir opción vacía
            self.fields['empresa'].initial = request.user.empresa
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled' # Deshabilitar el campo en la UI
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
        
        # Si el usuario es superusuario, el campo empresa debe ser seleccionable
        elif request and request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all() # Todos los objetos de empresa


# Formulario para CustomUser (Cambio/Edición)
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'empresa',)
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
        }
    
    def __init__(self, *args, **kwargs):
        # EXTRAER 'request' ANTES DE LLAMAR A super().__init__
        request = kwargs.pop('request', None) 
        super().__init__(*args, **kwargs)
        
        # Si el usuario que edita NO es superusuario, restringir ciertos campos
        if request and not request.user.is_superuser:
            # No puede cambiar la empresa del usuario editado
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            # No puede cambiar permisos de staff/superuser
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
            # No puede cambiar el estado activo de otros usuarios (excepto su propia cuenta)
            if self.instance != request.user: 
                self.fields['is_active'].widget.attrs['disabled'] = 'disabled'
        
        # NO eliminar el campo 'password' aquí. UserChangeForm lo maneja internamente.


# Formulario para el perfil de usuario (solo para que el usuario edite su propio perfil)
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'empresa', 'username'] # Añadido 'username' para que se muestre
        widgets = {
            # Deshabilitar el campo 'empresa' para que los usuarios normales no puedan cambiarla
            'empresa': forms.Select(attrs={'disabled': 'disabled'}),
            'username': forms.TextInput(attrs={'readonly': 'readonly'}), # Hacer el username de solo lectura
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.is_superuser:
            # Si el usuario no es superusuario, el campo 'empresa' es de solo lectura.
            # No lo hacemos 'disabled' para que el valor se envíe en el POST.
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['empresa'].help_text = "Tu empresa no puede ser cambiada desde aquí."
            self.fields['empresa'].required = False # No es requerido si es de solo lectura y el valor ya existe
        
        # Asegurarse de que el username sea de solo lectura
        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['username'].help_text = "El nombre de usuario no puede ser cambiado."

    # Sobrescribir el método clean_empresa para manejar el campo empresa si está readonly
    def clean_empresa(self):
        # Si el campo empresa es de solo lectura (para usuarios no superusuario),
        # el valor del formulario puede ser None o incorrecto si no se envía.
        # En ese caso, recuperamos el valor original del instance.
        # La verificación de superusuario se hace sobre self.request.user, no sobre self.instance
        # Nota: self.request no está disponible por defecto en ModelForms.
        # Si necesitas acceso al request, deberías pasarlo al formulario en la vista.
        # Por ahora, asumo que este clean_empresa es para el admin o un contexto donde el request no es crítico aquí.
        # Por seguridad, si el campo está deshabilitado/readonly, se toma el valor de la instancia.
        # Si el usuario es superusuario, se toma el valor del cleaned_data.
        if self.instance and hasattr(self, 'request') and not self.request.user.is_superuser:
            return self.instance.empresa
        return self.cleaned_data['empresa']


# Formularios de Empresa
class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'nit': forms.TextInput(attrs={'class': 'form-input'}),
            'direccion': forms.TextInput(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'logo_empresa': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }

# NUEVO Formulario para la información de formato de la Empresa
class EmpresaFormatoForm(forms.ModelForm):
    fecha_version_formato_empresa = forms.CharField(
        label="Fecha de Versión (DD/MM/YYYY)",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        required=False
    )

    class Meta:
        model = Empresa
        fields = ['formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa']
        widgets = {
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'formato_version_empresa': "Versión del Formato",
            'formato_codificacion_empresa': "Codificación del Formato",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.formato_fecha_version_empresa:
            self.fields['fecha_version_formato_empresa'].initial = self.instance.formato_fecha_version_empresa.strftime('%d/%m/%Y')
        
    def clean_fecha_version_formato_empresa(self):
        fecha_str = self.cleaned_data.get('fecha_version_formato_empresa')
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
            except ValueError:
                raise ValidationError("Formato de fecha inválido. Use DD/MM/YYYY.")
            
            if fecha > timezone.localdate():
                raise ValidationError("La fecha de versión no puede ser en el futuro.")
            return fecha
        return None

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.formato_fecha_version_empresa = self.cleaned_data.get('fecha_version_formato_empresa')
        if commit:
            instance.save()
        return instance


# Formularios de Ubicacion
class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

# Formularios de Procedimiento
class ProcedimientoForm(forms.ModelForm):
    fecha_emision = forms.DateField(
        label="Fecha de Emisión",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    
    class Meta:
        model = Procedimiento
        fields = '__all__' # Incluir todos los campos, incluyendo 'empresa'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'codigo': forms.TextInput(attrs={'class': 'form-input'}),
            'version': forms.TextInput(attrs={'class': 'form-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}), # Añadir widget para observaciones
            'documento_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}), # Widget para el campo empresa
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None) # Captura el request para lógica de permisos
        super().__init__(*args, **kwargs)

        # Lógica para el campo 'empresa' según el tipo de usuario
        if self.request and not self.request.user.is_superuser:
            # Si no es superusuario, el campo empresa debe ser oculto
            # y su valor pre-establecido a la empresa del usuario.
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk: # Solo para nuevas instancias
                self.fields['empresa'].initial = self.request.user.empresa
            else: # Para edición, asegurar que no se pueda cambiar la empresa del procedimiento existente
                self.fields['empresa'].initial = self.instance.empresa
            self.fields['empresa'].required = False # No es requerido si es oculto y pre-establecido
        elif self.request and self.request.user.is_superuser:
            # Si es superusuario, el campo empresa debe ser visible y seleccionable.
            # Por defecto ya es un Select, pero forzamos el queryset a todas las empresas
            self.fields['empresa'].queryset = Empresa.objects.all()
            self.fields['empresa'].required = True # Asegura que sea requerido para superusuarios al añadir/editar

        # Asegurarse de que el campo de fecha se inicialice correctamente al editar
        if self.instance and self.instance.fecha_emision:
            self.fields['fecha_emision'].initial = self.instance.fecha_emision.strftime('%d/%m/%Y')

    # Añadir clean_empresa para manejar la lógica de guardado cuando el campo es HiddenInput
    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']


# Formularios de Proveedores (se mantienen, aunque Calibracion ya no use ProveedorCalibracionForm directamente)
# Considera eliminar estas clases si ya no usas ProveedorCalibracion, ProveedorMantenimiento, ProveedorComprobacion
# y solo usas el modelo general Proveedor.
class ProveedorCalibracionForm(forms.ModelForm):
    class Meta:
        # Asegúrate de que ProveedorCalibracion existe o elimínalo
        # model = ProveedorCalibracion 
        fields = '__all__'
        # Widgets existentes...

class ProveedorMantenimientoForm(forms.ModelForm):
    class Meta:
        # Asegúrate de que ProveedorMantenimiento existe o elimínalo
        # model = ProveedorMantenimiento 
        fields = '__all__'
        # Widgets existentes...

class ProveedorComprobacionForm(forms.ModelForm):
    class Meta:
        # Asegúrate de que ProveedorComprobacion existe o elimínalo
        # model = ProveedorComprobacion 
        fields = '__all__'
        # Widgets existentes...

# NUEVO FORMULARIO: Proveedor General
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = '__all__'
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}), 
            'tipo_servicio': forms.Select(attrs={'class': 'form-select'}),
            'nombre_contacto': forms.TextInput(attrs={'class': 'form-input'}),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-input'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-input'}),
            'pagina_web': forms.URLInput(attrs={'class': 'form-input'}),
            'alcance': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'servicio_prestado': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk:
                self.fields['empresa'].initial = self.request.user.empresa
            else:
                self.fields['empresa'].initial = self.instance.empresa
            self.fields['empresa'].required = False
        elif self.request and self.request.user.is_superuser:
            self.fields['empresa'].required = True

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']


# Formulario para Equipo
class EquipoForm(forms.ModelForm):
    fecha_adquisicion = forms.DateField(
        label="Fecha de Adquisición",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_version_formato = forms.DateField(
        label="Fecha de Versión del Formato",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Equipo
        exclude = ('fecha_registro', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion')
        widgets = {
            'codigo_interno': forms.TextInput(attrs={'class': 'form-input'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}),
            'tipo_equipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-input'}),
            'modelo': forms.TextInput(attrs={'class': 'form-input'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-input'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-input'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input'}), 
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'rango_medida': forms.TextInput(attrs={'class': 'form-input'}),
            'resolucion': forms.TextInput(attrs={'class': 'form-input'}),
            'error_maximo_permisible': forms.TextInput(attrs={'class': 'form-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'archivo_compra_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'ficha_tecnica_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'manual_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'otros_documentos_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'imagen_equipo': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'version_formato': forms.TextInput(attrs={'class': 'form-input'}),
            'codificacion_formato': forms.TextInput(attrs={'class': 'form-input'}),
            'fecha_ultima_calibracion': forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
            'fecha_ultimo_mantenimiento': forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
            'fecha_ultima_comprobacion': forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
            'frecuencia_calibracion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
            'frecuencia_mantenimiento_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
            'frecuencia_comprobacion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
        }
        input_formats = {
            'fecha_ultima_calibracion': ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'fecha_ultimo_mantenimiento': ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'fecha_ultima_comprobacion': ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
        }


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk:
                self.fields['empresa'].initial = self.request.user.empresa
            else:
                self.fields['empresa'].initial = self.instance.empresa
        elif self.request and self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select w-full'})
            self.fields['empresa'].required = True

        if self.instance:
            if self.instance.fecha_ultima_calibracion:
                self.fields['fecha_ultima_calibracion'].initial = self.instance.fecha_ultima_calibracion.strftime('%d/%m/%Y')
            if self.instance.fecha_ultimo_mantenimiento:
                self.fields['fecha_ultimo_mantenimiento'].initial = self.instance.fecha_ultimo_mantenimiento.strftime('%d/%m/%Y')
            if self.instance.fecha_ultima_comprobacion:
                self.fields['fecha_ultima_comprobacion'].initial = self.instance.fecha_ultima_comprobacion.strftime('%d/%m/%Y')

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']


# Formulario para Calibracion
class CalibracionForm(forms.ModelForm):
    fecha_calibracion = forms.DateField(
        label="Fecha de Calibración",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Calibracion
        exclude = ('equipo',)
        widgets = {
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}), 
            'numero_certificado': forms.TextInput(attrs={'class': 'form-input'}),
            'documento_calibracion': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'confirmacion_metrologica_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}), 
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_calibracion:
            self.fields['fecha_calibracion'].initial = self.instance.fecha_calibracion.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


# Formulario para Mantenimiento
class MantenimientoForm(forms.ModelForm):
    fecha_mantenimiento = forms.DateField(
        label="Fecha de Mantenimiento",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Mantenimiento
        exclude = ('equipo',)
        widgets = {
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input'}),
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'costo': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_mantenimiento': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_mantenimiento:
            self.fields['fecha_mantenimiento'].initial = self.instance.fecha_mantenimiento.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

# Formulario para Comprobacion
class ComprobacionForm(forms.ModelForm):
    fecha_comprobacion = forms.DateField(
        label="Fecha de Comprobación",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m/%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Comprobacion
        exclude = ('equipo',)
        widgets = {
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_comprobacion': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_comprobacion:
            self.fields['fecha_comprobacion'].initial = self.instance.fecha_comprobacion.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

# Formulario para BajaEquipo
class BajaEquipoForm(forms.ModelForm):
    fecha_baja = forms.DateField(
        label="Fecha de Baja",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    class Meta:
        model = BajaEquipo
        exclude = ('equipo', 'dado_de_baja_por',)
        widgets = {
            'razon_baja': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_baja': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_baja:
            if isinstance(self.instance.fecha_baja, datetime):
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.date().strftime('%d/%m/%Y')
            else:
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.strftime('%d/%m/%Y')

# NUEVO FORMULARIO: Para la subida de archivos Excel
class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Seleccionar archivo Excel",
        help_text="Sube un archivo .xlsx con el listado de equipos.",
        widget=forms.FileInput(attrs={'class': 'form-input-file'})
    )

