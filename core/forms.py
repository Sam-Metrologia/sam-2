# core/forms.py - VERSION MEJORADA

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm as DjangoAuthenticationForm, PasswordChangeForm
from .models import (
    CustomUser, Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    BajaEquipo, Ubicacion, Procedimiento, Proveedor, Documento,
    PrestamoEquipo, AgrupacionPrestamo
)
from .services import ValidationService

from django.forms.widgets import DateInput, FileInput, ClearableFileInput, TextInput
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
import re
import logging

# Importar constantes centralizadas
from .constants import (
    ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_EN_CALIBRACION,
    ESTADO_EN_COMPROBACION, ESTADO_EN_MANTENIMIENTO, ESTADO_DE_BAJA,
    ESTADO_EN_PRESTAMO,
    PRESTAMO_ACTIVO, PRESTAMO_DEVUELTO, PRESTAMO_VENCIDO, PRESTAMO_CANCELADO,
)

logger = logging.getLogger('core')

# Formulario de Autenticación personalizado para usar CustomUser
class AuthenticationForm(DjangoAuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Nombre de usuario'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Contraseña'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        
        if username:
            # Log intento de login para seguridad
            logger.info(f"Intento de login para usuario: {username}")
        
        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='Mínimo 8 caracteres, no solo numérica'
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='Ingresa la misma contraseña para verificación'
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + (
            'email', 'first_name', 'last_name', 'empresa', 'rol_usuario',
            'is_staff', 'is_superuser', 'groups', 'user_permissions',
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'rol_usuario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Hacer email obligatorio
        self.fields['email'].required = True

        if request and not request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa.pk)
            self.fields['empresa'].empty_label = None
            self.fields['empresa'].initial = request.user.empresa
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
        elif request and request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Validar formato de username
            if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', username):
                raise ValidationError(
                    "El nombre de usuario debe tener entre 3-30 caracteres y solo contener letras, números, guiones y guiones bajos."
                )
        return username


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'empresa', 'rol_usuario')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'rol_usuario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Hacer email obligatorio
        self.fields['email'].required = True

        if request and not request.user.is_superuser:
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
            if self.instance and self.instance != request.user:
                self.fields['is_active'].widget.attrs['disabled'] = 'disabled'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar que el email no esté en uso por otro usuario
            qs = CustomUser.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un usuario con este correo electrónico.")
        return email


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'empresa', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'disabled': 'disabled', 'class': 'form-select'}),
            'username': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        if self.instance and not self.instance.is_superuser:
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['empresa'].help_text = "Tu empresa no puede ser cambiada desde aquí."
            self.fields['empresa'].required = False

        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['username'].help_text = "El nombre de usuario no puede ser cambiado."

    def clean_empresa(self):
        if self.instance and self.instance.empresa and self.fields['empresa'].widget.attrs.get('readonly'):
            return self.instance.empresa
        return self.cleaned_data.get('empresa')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = CustomUser.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un usuario con este correo electrónico.")
        return email


class EmpresaForm(forms.ModelForm):
    fecha_inicio_plan = forms.DateField(
        label="Fecha Inicio Plan",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
        required=False
    )

    class Meta:
        model = Empresa
        fields = [
            'nombre', 'nit', 'direccion', 'telefono', 'email', 'logo_empresa',
            'formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa',
            'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan',
            'limite_equipos_empresa', 'limite_almacenamiento_mb', 'duracion_suscripcion_meses',
            'acceso_manual_activo', 'estado_suscripcion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'nit': forms.TextInput(attrs={'class': 'form-input'}),
            'direccion': forms.TextInput(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'logo_empresa': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'formato_fecha_version_empresa': DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'es_periodo_prueba': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'duracion_prueba_dias': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '365'}),
            'limite_equipos_empresa': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '10000'}),
            'limite_almacenamiento_mb': forms.NumberInput(attrs={'class': 'form-input', 'min': '100', 'max': '100000', 'step': '100'}),
            'duracion_suscripcion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '120'}),
            'acceso_manual_activo': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'estado_suscripcion': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Hacer email obligatorio
        self.fields['email'].required = True

        if self.instance and self.instance.fecha_inicio_plan:
            if isinstance(self.instance.fecha_inicio_plan, datetime):
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan.date().strftime('%Y-%m-%d')
            else:
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan.strftime('%Y-%m-%d')

        if request and not request.user.is_superuser:
            # Ocultar campos de gestión para usuarios no superusuarios
            subscription_fields = [
                'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan',
                'limite_equipos_empresa', 'limite_almacenamiento_mb', 'duracion_suscripcion_meses',
                'acceso_manual_activo', 'estado_suscripcion'
            ]
            
            for field in subscription_fields:
                self.fields[field].widget = forms.HiddenInput()
                self.fields[field].required = False
                if self.instance and self.instance.pk:
                    self.fields[field].initial = getattr(self.instance, field)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = Empresa.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe una empresa con este correo electrónico.")
        return email

    def clean_nit(self):
        nit = self.cleaned_data.get('nit')
        if nit:
            # Validar formato de NIT (básico)
            nit_clean = re.sub(r'[^0-9]', '', nit)
            if len(nit_clean) < 9:
                raise ValidationError("El NIT debe tener al menos 9 dígitos.")
            
            qs = Empresa.objects.filter(nit=nit)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe una empresa con este NIT.")
        return nit

    def clean_limite_equipos_empresa(self):
        limite = self.cleaned_data.get('limite_equipos_empresa')
        if limite is not None and limite < 1:
            raise ValidationError("El límite de equipos debe ser mayor a 0.")
        return limite

    def clean_limite_almacenamiento_mb(self):
        limite = self.cleaned_data.get('limite_almacenamiento_mb')
        if limite is not None and limite < 100:
            raise ValidationError("El límite de almacenamiento debe ser mayor a 100 MB.")
        return limite


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
    fecha_ultima_calibracion = forms.DateField(
        label="Fecha Última Calibración",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_ultimo_mantenimiento = forms.DateField(
        label="Fecha Último Mantenimiento",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_ultima_comprobacion = forms.DateField(
        label="Fecha Última Comprobación",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Equipo
        exclude = ('fecha_registro', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion')
        widgets = {
            'codigo_interno': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '20'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '200'}),
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
            'tipo_equipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'modelo': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'rango_medida': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'resolucion': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'error_maximo_permisible': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'puntos_calibracion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Ej: 0, 25, 50, 75, 100'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'archivo_compra_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'manual_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'otros_documentos_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'imagen_equipo': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.jpg,.jpeg,.png'}),
            'version_formato': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'codificacion_formato': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'frecuencia_calibracion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'max': '120', 'step': '0.01'}),
            'frecuencia_mantenimiento_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'max': '120', 'step': '0.01'}),
            'frecuencia_comprobacion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'max': '120', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa asignada no puede crear equipos
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

        # Inicializar fechas en formato DD/MM/YYYY
        if self.instance:
            date_fields = ['fecha_ultima_calibracion', 'fecha_ultimo_mantenimiento', 'fecha_ultima_comprobacion']
            for field_name in date_fields:
                date_value = getattr(self.instance, field_name, None)
                if date_value:
                    self.fields[field_name].initial = date_value.strftime('%Y-%m-%d')

    def clean_empresa(self):
        # SEGURIDAD: Manejo diferenciado por tipo de usuario
        if self.request:
            if self.request.user.is_superuser:
                # Superusuario: retornar lo que seleccionó en el formulario
                return self.cleaned_data.get('empresa')
            else:
                # Usuario normal: siempre asignar su empresa
                if self.instance and self.instance.pk:
                    # Al editar, mantener la empresa actual
                    return self.instance.empresa
                elif self.request.user.empresa:
                    # Al crear, asignar empresa del usuario
                    return self.request.user.empresa
        return self.cleaned_data.get('empresa')

    def clean_codigo_interno(self):
        codigo = self.cleaned_data.get('codigo_interno')
        # Sin restricciones de formato - el cliente puede usar cualquier código
        return codigo

    def clean_numero_serie(self):
        numero_serie = self.cleaned_data.get('numero_serie')
        if numero_serie:
            # Verificar unicidad del número de serie
            qs = Equipo.objects.filter(numero_serie=numero_serie)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un equipo con este número de serie.")
        return numero_serie

    def clean(self):
        cleaned_data = super().clean()

        # Asegurar que empresa esté en cleaned_data antes de validaciones
        if not cleaned_data.get('empresa'):
            # Si empresa no está en cleaned_data, obtenerla del clean_empresa()
            empresa = self.clean_empresa()
            if empresa:
                cleaned_data['empresa'] = empresa

        # Validar fechas lógicas
        fecha_adquisicion = cleaned_data.get('fecha_adquisicion')
        if fecha_adquisicion and fecha_adquisicion > timezone.now().date():
            raise ValidationError("La fecha de adquisición no puede ser futura.")

        # Validar frecuencias
        for field_name in ['frecuencia_calibracion_meses', 'frecuencia_mantenimiento_meses', 'frecuencia_comprobacion_meses']:
            freq = cleaned_data.get(field_name)
            if freq is not None and freq <= 0:
                raise ValidationError(f"La {field_name.replace('_', ' ')} debe ser positiva.")

        # Validar unicidad de codigo_interno con empresa
        codigo = cleaned_data.get('codigo_interno')
        empresa = cleaned_data.get('empresa')
        if codigo and empresa:
            qs = Equipo.objects.filter(codigo_interno=codigo, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({
                    'codigo_interno': f"Ya existe un equipo con el código '{codigo}' en {empresa.nombre}"
                })

        return cleaned_data

    def save(self, commit=True):
        # Validar límite de equipos al crear
        if not self.instance.pk:
            empresa = self.cleaned_data.get('empresa')
            if empresa:
                limite_equipos = empresa.get_limite_equipos()
                if limite_equipos is not None and limite_equipos != float('inf') and limite_equipos > 0:
                    equipos_actuales = Equipo.objects.filter(empresa=empresa).count()
                    if equipos_actuales >= limite_equipos:
                        raise ValidationError(f"La empresa ya alcanzó su límite de {limite_equipos} equipos.")

        instance = super().save(commit=commit)
        
        # Log de auditoría
        if self.request:
            from .services import AuditService
            action = "created" if not self.instance.pk else "updated"
            AuditService.log_equipment_action(action, instance, self.request.user)
        
        return instance


# Formularios de actividades mejorados
class CalibracionForm(forms.ModelForm):
    fecha_calibracion = forms.DateField(
        label="Fecha de Calibración",
        widget=forms.TextInput(attrs={'placeholder': 'YYYY-MM-DD', 'class': 'form-input'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    )

    class Meta:
        model = Calibracion
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'numero_certificado': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'documento_calibracion': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'confirmacion_metrologica_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'intervalos_calibracion_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_calibracion:
            self.fields['fecha_calibracion'].initial = self.instance.fecha_calibracion.strftime('%Y-%m-%d')

        # Filtrar proveedores por tipo de servicio y empresa
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(
                empresa=empresa,
                tipo_servicio__in=['Calibración', 'Otro']
            )
        else:
            # Fallback: sin proveedores si no hay empresa
            self.fields['proveedor'].queryset = Proveedor.objects.none()

    def clean_fecha_calibracion(self):
        fecha = self.cleaned_data.get('fecha_calibracion')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de calibración no puede ser futura.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que al menos se proporcione proveedor o nombre_proveedor
        proveedor = cleaned_data.get('proveedor')
        nombre_proveedor = cleaned_data.get('nombre_proveedor')
        
        if not proveedor and not nombre_proveedor:
            raise ValidationError("Debe seleccionar un proveedor o ingresar el nombre del proveedor.")
        
        return cleaned_data


class MantenimientoForm(forms.ModelForm):
    fecha_mantenimiento = forms.DateField(
        label="Fecha de Mantenimiento",
        widget=forms.TextInput(attrs={'placeholder': 'YYYY-MM-DD', 'class': 'form-input'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    )

    class Meta:
        model = Mantenimiento
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'costo': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'documento_externo': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf,.xlsx,.xls'}),
            'analisis_interno': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf,.xlsx,.xls'}),
            'documento_mantenimiento': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_mantenimiento:
            self.fields['fecha_mantenimiento'].initial = self.instance.fecha_mantenimiento.strftime('%Y-%m-%d')

        # Filtrar proveedores por tipo de servicio y empresa
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(
                empresa=empresa,
                tipo_servicio__in=['Mantenimiento', 'Otro']
            )
        else:
            # Fallback: sin proveedores si no hay empresa
            self.fields['proveedor'].queryset = Proveedor.objects.none()

    def clean_fecha_mantenimiento(self):
        fecha = self.cleaned_data.get('fecha_mantenimiento')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de mantenimiento no puede ser futura.")
        return fecha

    def clean_costo(self):
        costo = self.cleaned_data.get('costo')
        if costo is not None and costo < 0:
            raise ValidationError("El costo no puede ser negativo.")
        return costo


class ComprobacionForm(forms.ModelForm):
    fecha_comprobacion = forms.DateField(
        label="Fecha de Comprobación",
        widget=forms.TextInput(attrs={'placeholder': 'YYYY-MM-DD', 'class': 'form-input'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    )

    class Meta:
        model = Comprobacion
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'documento_externo': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf,.xlsx,.xls'}),
            'analisis_interno': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf,.xlsx,.xls'}),
            'documento_comprobacion': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_comprobacion:
            self.fields['fecha_comprobacion'].initial = self.instance.fecha_comprobacion.strftime('%Y-%m-%d')

        # Filtrar proveedores por tipo de servicio y empresa
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(
                empresa=empresa,
                tipo_servicio__in=['Comprobación', 'Otro']
            )
        else:
            # Fallback: sin proveedores si no hay empresa
            self.fields['proveedor'].queryset = Proveedor.objects.none()

    def clean_fecha_comprobacion(self):
        fecha = self.cleaned_data.get('fecha_comprobacion')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de comprobación no puede ser futura.")
        return fecha


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
            'razon_baja': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'maxlength': '1000'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '500'}),
            'documento_baja': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_baja:
            if isinstance(self.instance.fecha_baja, datetime):
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.date().strftime('%Y-%m-%d')
            else:
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.strftime('%Y-%m-%d')

    def clean_fecha_baja(self):
        fecha = self.cleaned_data.get('fecha_baja')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de baja no puede ser futura.")
        return fecha

    def clean_razon_baja(self):
        razon = self.cleaned_data.get('razon_baja')
        if razon and len(razon.strip()) < 10:
            raise ValidationError("La razón de baja debe tener al menos 10 caracteres.")
        return razon


# Formularios de configuración mejorados
class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = '__all__'
        widgets = {
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '500'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear ubicaciones
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        empresa = self.cleaned_data.get('empresa')

        if nombre and empresa:
            # Verificar unicidad por empresa
            qs = Ubicacion.objects.filter(nombre=nombre, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Ya existe una ubicación con el nombre '{nombre}' en {empresa.nombre}.")
        return nombre

    def clean_empresa(self):
        # SEGURIDAD: Manejo diferenciado por tipo de usuario
        if self.request:
            if self.request.user.is_superuser:
                # Superusuario: retornar lo que seleccionó
                return self.cleaned_data.get('empresa')
            else:
                # Usuario normal: siempre su empresa
                if self.instance and self.instance.pk:
                    return self.instance.empresa
                elif self.request.user.empresa:
                    return self.request.user.empresa
        return self.cleaned_data.get('empresa')


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
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'codigo': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'version': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'documento_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear procedimientos
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

        if self.instance and self.instance.fecha_emision:
            self.fields['fecha_emision'].initial = self.instance.fecha_emision.strftime('%Y-%m-%d')

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        empresa = self.cleaned_data.get('empresa') or (self.request.user.empresa if self.request else None)
        
        if codigo and empresa:
            # Verificar unicidad por empresa
            qs = Procedimiento.objects.filter(codigo=codigo, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Ya existe un procedimiento con el código '{codigo}' en {empresa.nombre}.")
        return codigo

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data.get('empresa')


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = '__all__'
        widgets = {
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
            'tipo_servicio': forms.Select(attrs={'class': 'form-select'}),
            'nombre_contacto': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '200'}),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '20'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '200'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-input'}),
            'pagina_web': forms.URLInput(attrs={'class': 'form-input'}),
            'alcance': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'servicio_prestado': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear proveedores
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

    def clean_nombre_empresa(self):
        nombre_empresa = self.cleaned_data.get('nombre_empresa')
        empresa = self.cleaned_data.get('empresa') or (self.request.user.empresa if self.request else None)
        
        if nombre_empresa and empresa:
            # Verificar unicidad por empresa
            qs = Proveedor.objects.filter(nombre_empresa=nombre_empresa, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Ya existe un proveedor con el nombre '{nombre_empresa}' en {empresa.nombre}.")
        return nombre_empresa

    def clean_correo_electronico(self):
        email = self.cleaned_data.get('correo_electronico')
        if email:
            # Validación básica adicional de email
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                raise ValidationError("Ingrese una dirección de correo electrónico válida.")
        return email

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data.get('empresa')


# Formularios adicionales
class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Seleccionar archivo Excel",
        help_text="Sube un archivo .xlsx con el listado de equipos.",
        widget=forms.FileInput(attrs={'class': 'form-input-file', 'accept': '.xlsx'})
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        if excel_file:
            if not excel_file.name.endswith('.xlsx'):
                raise ValidationError('El archivo debe ser un Excel (.xlsx)')
            
            # Validar tamaño (máximo 5MB para archivos Excel)
            if excel_file.size > 5 * 1024 * 1024:
                raise ValidationError('El archivo Excel no puede ser mayor a 5MB')
        
        return excel_file


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['nombre_archivo', 'descripcion', 'empresa']
        widgets = {
            'nombre_archivo': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '500'}),
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear documentos
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

    def clean_empresa(self):
        # SEGURIDAD: Manejo diferenciado por tipo de usuario
        if self.request:
            if self.request.user.is_superuser:
                # Superusuario: retornar lo que seleccionó
                return self.cleaned_data.get('empresa')
            else:
                # Usuario normal: siempre su empresa
                if self.instance and self.instance.pk:
                    return self.instance.empresa
                elif self.request.user.empresa:
                    return self.request.user.empresa
        return self.cleaned_data.get('empresa')


# Formulario específico para formato de empresa
class EmpresaFormatoForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa']
        widgets = {
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'formato_fecha_version_empresa': DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
        }
        labels = {
            'formato_version_empresa': "Versión del Formato",
            'formato_codificacion_empresa': "Codificación del Formato",
        }

    def clean_formato_fecha_version_empresa(self):
        fecha = self.cleaned_data.get('formato_fecha_version_empresa')
        if fecha and fecha > timezone.localdate():
            raise ValidationError("La fecha de versión no puede ser en el futuro.")
        return fecha


# ==============================================================================
# FORMS PARA SISTEMA DE PRÉSTAMOS DE EQUIPOS
# ==============================================================================

class PrestamoEquipoForm(forms.ModelForm):
    """
    Formulario para crear y editar préstamos de equipos.
    Incluye validación para evitar prestar equipos que ya están en préstamo activo.
    Incluye verificación de salida del equipo.
    """
    # Campo personalizado para múltiples equipos
    equipos = forms.ModelMultipleChoiceField(
        queryset=Equipo.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '10',
            'style': 'height: auto; min-height: 200px;'
        }),
        label='Equipos a Prestar (puede seleccionar varios con Ctrl+Click)',
        help_text='Mantenga presionado Ctrl (Windows) o Cmd (Mac) para seleccionar múltiples equipos'
    )

    # Verificación de salida
    estado_fisico_salida = forms.ChoiceField(
        choices=[
            ('Bueno', 'Bueno'),
            ('Regular', 'Regular'),
            ('Malo', 'Malo'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Estado Físico al Salir',
        initial='Bueno'
    )

    funcionalidad_salida = forms.ChoiceField(
        choices=[
            ('Conforme', 'Conforme - Funciona correctamente'),
            ('No Conforme', 'No Conforme - Requiere atención'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Funcionalidad al Salir',
        initial='Conforme'
    )

    # Punto de medición de salida
    punto_medicion_salida = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Temperatura'}),
        label='Parámetro Medido'
    )

    valor_referencia_salida = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 25.0°C'}),
        label='Valor Referencia'
    )

    valor_medido_salida = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 25.1°C'}),
        label='Valor Medido'
    )

    class Meta:
        model = PrestamoEquipo
        fields = [
            'equipo', 'agrupacion', 'nombre_prestatario', 'cedula_prestatario',
            'cargo_prestatario', 'email_prestatario', 'telefono_prestatario',
            'fecha_devolucion_programada', 'observaciones_prestamo'
        ]
        # Excluir explícitamente campos que se asignan automáticamente en la vista
        exclude = ['empresa', 'prestado_por', 'recibido_por', 'verificacion_salida',
                   'verificacion_entrada', 'fecha_devolucion_real', 'estado_prestamo']
        widgets = {
            'equipo': forms.Select(attrs={'class': 'form-select'}),
            'agrupacion': forms.Select(attrs={'class': 'form-select'}),
            'nombre_prestatario': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombre completo'}),
            'cedula_prestatario': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Cédula (opcional)'}),
            'cargo_prestatario': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Cargo (opcional)'}),
            'email_prestatario': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@ejemplo.com'}),
            'telefono_prestatario': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+57 300 123 4567'}),
            'fecha_devolucion_programada': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'observaciones_prestamo': forms.Textarea(attrs={'rows': 2, 'class': 'form-textarea', 'placeholder': 'Observaciones del préstamo...'}),
        }
        labels = {
            'equipo': 'Equipo a Prestar (uno solo)',
            'agrupacion': 'Agrupación (opcional)',
            'nombre_prestatario': 'Nombre del Inspector/Prestatario',
            'cedula_prestatario': 'Cédula',
            'cargo_prestatario': 'Cargo',
            'email_prestatario': 'Email',
            'telefono_prestatario': 'Teléfono',
            'fecha_devolucion_programada': 'Fecha de Devolución Programada',
            'observaciones_prestamo': 'Observaciones',
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        # Hacer equipo opcional para permitir selección múltiple
        self.fields['equipo'].required = False

        if empresa:
            # Solo equipos disponibles de la empresa (no en préstamo activo ni dados de baja)
            equipos_disponibles = Equipo.objects.filter(
                empresa=empresa,
                estado__in=[ESTADO_ACTIVO, ESTADO_EN_MANTENIMIENTO, ESTADO_EN_CALIBRACION, ESTADO_EN_COMPROBACION]
            ).exclude(
                prestamos__estado_prestamo=PRESTAMO_ACTIVO,
                prestamos__fecha_devolucion_real__isnull=True
            ).order_by('codigo_interno')

            self.fields['equipo'].queryset = equipos_disponibles
            self.fields['equipos'].queryset = equipos_disponibles  # Para selección múltiple

            # Solo agrupaciones de la empresa
            self.fields['agrupacion'].queryset = AgrupacionPrestamo.objects.filter(
                empresa=empresa
            ).order_by('-fecha_creacion')

    def clean(self):
        cleaned_data = super().clean()
        equipo_individual = cleaned_data.get('equipo')
        equipos_multiples = cleaned_data.get('equipos')

        # Debe seleccionar al menos uno (individual O múltiples)
        if not equipo_individual and not equipos_multiples:
            raise ValidationError(
                'Debes seleccionar al menos un equipo (individual o múltiples).'
            )

        return cleaned_data

    def clean_equipo(self):
        equipo = self.cleaned_data.get('equipo')

        if not equipo:
            return equipo

        # Validar que equipo no esté ya prestado
        prestamo_activo = PrestamoEquipo.objects.filter(
            equipo=equipo,
            estado_prestamo=PRESTAMO_ACTIVO,
            fecha_devolucion_real__isnull=True
        ).exists()

        if prestamo_activo:
            raise ValidationError(
                f'El equipo {equipo.codigo_interno} ya está en préstamo activo. '
                'No se puede prestar un equipo que ya está prestado.'
            )

        # Validar que equipo no esté de baja
        if equipo.estado == ESTADO_DE_BAJA:
            raise ValidationError(
                f'El equipo {equipo.codigo_interno} está dado de baja. '
                'No se puede prestar un equipo dado de baja.'
            )

        return equipo

    def clean_fecha_devolucion_programada(self):
        fecha = self.cleaned_data.get('fecha_devolucion_programada')

        if fecha and fecha < timezone.now().date():
            raise ValidationError(
                'La fecha de devolución programada no puede ser en el pasado.'
            )

        return fecha

    def get_verificacion_salida_data(self, user):
        """
        Construye el JSON de verificación de salida del equipo.
        Para préstamo individual (un solo equipo).
        """
        data = self.cleaned_data

        # Construir punto de medición si se proporcionó
        punto_medicion_data = None
        if data.get('punto_medicion_salida'):
            punto_medicion_data = {
                'punto': data.get('punto_medicion_salida'),
                'valor_referencia': data.get('valor_referencia_salida', ''),
                'valor_medido': data.get('valor_medido_salida', '')
            }

        return {
            'fecha_verificacion': timezone.now().isoformat(),
            'verificado_por': user.get_full_name() or user.username,
            'estado_fisico': data.get('estado_fisico_salida'),
            'funcionalidad': data.get('funcionalidad_salida'),
            'resultado_general': data.get('funcionalidad_salida'),
            'punto_medicion': punto_medicion_data
        }

    def get_verificacion_salida_por_equipo(self, user, equipo_id, request_post):
        """
        Construye el JSON de verificación de salida para un equipo específico
        en préstamos múltiples.
        Extrae los datos de medición desde request.POST usando el patrón:
        medicion_equipo_{id}_punto, medicion_equipo_{id}_referencia, medicion_equipo_{id}_medido
        """
        data = self.cleaned_data

        # Extraer datos de medición específicos para este equipo
        punto_key = f'medicion_equipo_{equipo_id}_punto'
        referencia_key = f'medicion_equipo_{equipo_id}_referencia'
        medido_key = f'medicion_equipo_{equipo_id}_medido'

        punto_medicion_data = None
        if request_post.get(punto_key):
            punto_medicion_data = {
                'punto': request_post.get(punto_key, ''),
                'valor_referencia': request_post.get(referencia_key, ''),
                'valor_medido': request_post.get(medido_key, '')
            }

        return {
            'fecha_verificacion': timezone.now().isoformat(),
            'verificado_por': user.get_full_name() or user.username,
            'estado_fisico': data.get('estado_fisico_salida'),
            'funcionalidad': data.get('funcionalidad_salida'),
            'resultado_general': data.get('funcionalidad_salida'),
            'punto_medicion': punto_medicion_data
        }


class VerificacionFuncionalForm(forms.Form):
    """
    Formulario para registrar verificación funcional de un equipo
    al momento del préstamo (salida) o devolución (entrada).
    Incluye campos para mediciones (valor medido vs valor referencia).
    """

    verificado_por = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombre del técnico verificador'}),
        label='Verificado por'
    )

    estado_fisico = forms.ChoiceField(
        choices=[
            ('Bueno', 'Bueno - Sin daños ni desgaste anormal'),
            ('Regular', 'Regular - Desgaste normal de uso'),
            ('Malo', 'Malo - Daños o desgaste excesivo'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Estado Físico del Equipo'
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea', 'placeholder': 'Observaciones de la verificación...'}),
        label='Observaciones Generales'
    )

    resultado_general = forms.ChoiceField(
        choices=[
            ('Aprobado', 'Aprobado'),
            ('No Aprobado', 'No Aprobado'),
            ('Aprobado con Observaciones', 'Aprobado con Observaciones'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Resultado General'
    )

    # Campos para puntos de medición (3 puntos)
    # Punto 1
    punto_medicion_1 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Temperatura'}),
        label='Punto de Medición 1'
    )
    valor_referencia_1 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 25.0°C'}),
        label='Valor de Referencia 1'
    )
    valor_medido_1 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 25.1°C'}),
        label='Valor Medido 1'
    )
    conformidad_1 = forms.ChoiceField(
        choices=[
            ('', '-- Seleccionar --'),
            ('Conforme', 'Conforme'),
            ('No Conforme', 'No Conforme'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Conformidad 1'
    )

    # Punto 2
    punto_medicion_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Humedad'}),
        label='Punto de Medición 2'
    )
    valor_referencia_2 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 50%'}),
        label='Valor de Referencia 2'
    )
    valor_medido_2 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 48%'}),
        label='Valor Medido 2'
    )
    conformidad_2 = forms.ChoiceField(
        choices=[
            ('', '-- Seleccionar --'),
            ('Conforme', 'Conforme'),
            ('No Conforme', 'No Conforme'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Conformidad 2'
    )

    # Punto 3
    punto_medicion_3 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Presión'}),
        label='Punto de Medición 3'
    )
    valor_referencia_3 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 101.3 kPa'}),
        label='Valor de Referencia 3'
    )
    valor_medido_3 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 101.2 kPa'}),
        label='Valor Medido 3'
    )
    conformidad_3 = forms.ChoiceField(
        choices=[
            ('', '-- Seleccionar --'),
            ('Conforme', 'Conforme'),
            ('No Conforme', 'No Conforme'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Conformidad 3'
    )

    def get_puntos_medicion(self):
        """
        Extrae los puntos de medición del formulario limpio.
        Retorna una lista de diccionarios con los datos de cada punto.
        """
        puntos = []
        data = self.cleaned_data

        for i in range(1, 4):  # 3 puntos de medición
            punto = data.get(f'punto_medicion_{i}')
            if punto:  # Solo agregar si se completó el punto
                puntos.append({
                    'punto': punto,
                    'valor_referencia': data.get(f'valor_referencia_{i}', ''),
                    'valor_medido': data.get(f'valor_medido_{i}', ''),
                    'conformidad': data.get(f'conformidad_{i}', '')
                })

        return puntos

    def to_json(self):
        """
        Convierte los datos del formulario a la estructura JSON esperada
        para almacenar en verificacion_salida o verificacion_entrada.
        """
        data = self.cleaned_data
        return {
            'fecha_verificacion': timezone.now().isoformat(),
            'verificado_por': data.get('verificado_por'),
            'estado_fisico': data.get('estado_fisico'),
            'observaciones': data.get('observaciones', ''),
            'resultado_general': data.get('resultado_general'),
            'puntos_verificacion': self.get_puntos_medicion()
        }


class DevolucionEquipoForm(forms.Form):
    """
    Formulario para registrar la devolución de un equipo prestado.
    Incluye verificación funcional con mediciones de entrada.
    """

    observaciones_devolucion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-textarea',
            'placeholder': 'Observaciones sobre la devolución del equipo...'
        }),
        label='Observaciones de Devolución'
    )

    documento_devolucion = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-input-file',
            'accept': '.pdf'
        }),
        label='Acta de Devolución (PDF)',
        help_text='Opcional: Documento firmado de devolución'
    )

    # Campos de verificación funcional de entrada
    verificado_por = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Nombre del técnico que recibe'
        }),
        label='Recibido por'
    )

    condicion_equipo = forms.ChoiceField(
        choices=[
            ('Bueno', 'Bueno - Sin daños ni desgaste anormal'),
            ('Regular', 'Regular - Desgaste normal de uso'),
            ('Malo', 'Malo - Daños o desgaste excesivo'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Condición del Equipo al Devolverlo'
    )

    verificacion_funcional_ok = forms.ChoiceField(
        choices=[
            ('Conforme', 'Conforme - Funciona correctamente'),
            ('No Conforme', 'No Conforme - Requiere revisión o mantenimiento'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Verificación Funcional'
    )

    # Campo para punto de medición (solo 1 para rapidez)
    punto_medicion = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Temperatura'}),
        label='Parámetro Medido',
        help_text='Parámetro principal que se verificó'
    )
    valor_referencia = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 25.0°C'}),
        label='Valor de Referencia'
    )
    valor_medido = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 25.1°C'}),
        label='Valor Medido'
    )
    conformidad = forms.ChoiceField(
        choices=[
            ('', '-- Seleccionar --'),
            ('Conforme', 'Conforme'),
            ('No Conforme', 'No Conforme'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Conformidad'
    )

    def clean_documento_devolucion(self):
        archivo = self.cleaned_data.get('documento_devolucion')

        if archivo:
            # Validar que sea PDF
            if not archivo.name.endswith('.pdf'):
                raise ValidationError('El documento debe ser un archivo PDF')

            # Validar tamaño máximo (10MB)
            if archivo.size > 10 * 1024 * 1024:
                raise ValidationError('El archivo no puede ser mayor a 10MB')

        return archivo

    def to_verificacion_json(self):
        """
        Convierte los datos del formulario a la estructura JSON
        para almacenar en verificacion_entrada.
        """
        data = self.cleaned_data

        # Construir punto de medición si se proporcionó
        punto_medicion_data = None
        if data.get('punto_medicion'):
            punto_medicion_data = {
                'punto': data.get('punto_medicion'),
                'valor_referencia': data.get('valor_referencia', ''),
                'valor_medido': data.get('valor_medido', ''),
                'conformidad': data.get('conformidad', '')
            }

        return {
            'fecha_verificacion': timezone.now().isoformat(),
            'verificado_por': data.get('verificado_por'),
            'condicion_equipo': data.get('condicion_equipo'),
            'verificacion_funcional': data.get('verificacion_funcional_ok'),
            'observaciones': data.get('observaciones_devolucion', ''),
            'resultado_general': 'Aprobado' if data.get('verificacion_funcional_ok') == 'Conforme' else 'No Aprobado',
            'punto_medicion': punto_medicion_data
        }