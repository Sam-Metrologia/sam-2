# core/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm as DjangoAuthenticationForm, PasswordChangeForm 
from .models import (
    CustomUser, Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    BajaEquipo, Ubicacion, Procedimiento, Proveedor 
)

from django.forms.widgets import DateInput, FileInput, ClearableFileInput, TextInput 
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime 
import os

# Formulario de Autenticación personalizado para usar CustomUser
class AuthenticationForm(DjangoAuthenticationForm):
    pass

# Formulario para CustomUser (Creación)
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Incluir explícitamente 'groups' y 'user_permissions' para asegurar su presencia
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'empresa', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}), # Widget para la selección de grupos
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}), # Widget para permisos
        }
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None) 
        super().__init__(*args, **kwargs)
        
        # Filtrar el queryset de empresa y deshabilitar campos para usuarios no superusuarios
        if request and not request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa.pk)
            self.fields['empresa'].empty_label = None 
            self.fields['empresa'].initial = request.user.empresa
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled' 
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            # Los campos 'groups' y 'user_permissions' deben ser deshabilitados también para no superusuarios
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
        elif request and request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all() 
        
        # Aplicar clases de Tailwind CSS a todos los campos visibles por defecto
        # Se excluyen is_staff, is_superuser, groups, user_permissions de esta aplicación genérica
        # porque ya tienen widgets específicos o son manejados por el template.
        for field_name, field in self.fields.items():
            if field_name not in ['is_staff', 'is_superuser', 'groups', 'user_permissions']: 
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput, forms.PasswordInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})


# Formulario para CustomUser (Cambio/Edición)
class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        # Incluir explícitamente 'groups' y 'user_permissions'
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'empresa',)
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
        }
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None) 
        super().__init__(*args, **kwargs)
        
        # Si el usuario que edita NO es superusuario, restringir ciertos campos
        if request and not request.user.is_superuser:
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
            if self.instance != request.user: 
                self.fields['is_active'].widget.attrs['disabled'] = 'disabled'

        # Aplicar clases de Tailwind CSS a los campos restantes
        for field_name, field in self.fields.items():
            if field_name not in ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']: # Excluir checkboxes y campos selectmultiple
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})


# Formulario para el perfil de usuario (solo para que el usuario edite su propio perfil)
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'empresa', 'username'] 
        widgets = {
            'empresa': forms.Select(attrs={'disabled': 'disabled'}),
            'username': forms.TextInput(attrs={'readonly': 'readonly'}), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.is_superuser:
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['empresa'].help_text = "Tu empresa no puede ser cambiada desde aquí."
            self.fields['empresa'].required = False 
        
        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['username'].help_text = "El nombre de usuario no puede ser cambiado."
        
        # Aplicar clases de Tailwind a los campos restantes
        for field_name, field in self.fields.items():
            if field_name not in ['empresa', 'username']: # Excluir los que ya tienen attrs
                 if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                 elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})

    def clean_empresa(self):
        # Esta lógica asegura que la empresa no se cambie si el campo está en solo lectura
        if self.instance and self.instance.empresa and self.fields['empresa'].widget.attrs.get('readonly'):
            return self.instance.empresa
        return self.cleaned_data.get('empresa')


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
            'pais': forms.TextInput(attrs={'class': 'form-input'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-input'}),
            'logo_empresa': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'formato_fecha_version_empresa': DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

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
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'request' in kwargs:
            request_user = kwargs.pop('request').user
            if not request_user.is_superuser and request_user.empresa:
                self.fields['empresa'].queryset = Empresa.objects.filter(pk=request_user.empresa.pk)
                self.fields['empresa'].initial = request_user.empresa.pk
                self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            elif request_user.is_superuser:
                self.fields['empresa'].queryset = Empresa.objects.all()
            else:
                self.fields['empresa'].queryset = Empresa.objects.none()
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput):
                field.widget.attrs.update({'class': 'form-input-file'})


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
        fields = '__all__' 
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'codigo': forms.TextInput(attrs={'class': 'form-input'}),
            'version': forms.TextInput(attrs={'class': 'form-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}), 
            'documento_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}), 
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
            self.fields['empresa'].queryset = Empresa.objects.all()
            self.fields['empresa'].required = True 

        if self.instance and self.instance.fecha_emision:
            self.fields['fecha_emision'].initial = self.instance.fecha_emision.strftime('%d/%m/%Y')

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput):
                field.widget.attrs.update({'class': 'form-input-file'})

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

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput, forms.URLInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput):
                field.widget.attrs.update({'class': 'form-input-file'})

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
