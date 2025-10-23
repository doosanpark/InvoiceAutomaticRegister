from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Service, CustomUser, Declaration


class LoginForm(forms.Form):
    """로그인 폼"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '아이디 (관리자: admin, 관세사: 부호 5자리)',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '비밀번호'
        })
    )


class PasswordChangeForm(forms.Form):
    """비밀번호 변경 폼"""
    new_password = forms.CharField(
        label='새 비밀번호',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '새 비밀번호'
        })
    )
    confirm_password = forms.CharField(
        label='비밀번호 확인',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '비밀번호 확인'
        })
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if self.user:
            try:
                validate_password(password, self.user)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('비밀번호가 일치하지 않습니다.')

        return cleaned_data


class ServiceForm(forms.ModelForm):
    """서비스 추가/수정 폼"""
    class Meta:
        model = Service
        fields = ['name', 'slug', 'description', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '서비스명 (예: RK통관)'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '영문명 (예: rk-customs, help-manager)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': '서비스 설명',
                'rows': 3
            }),
            'db_host': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'localhost 또는 IP 주소'
            }),
            'db_port': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '1433'
            }),
            'db_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'database_name'
            }),
            'db_user': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'sa'
            }),
            'db_password': forms.PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': 'DB 비밀번호'
            }),
        }
        labels = {
            'name': '서비스명',
            'slug': '영문명',
            'description': '설명',
            'db_host': 'DB 호스트',
            'db_port': 'DB 포트',
            'db_name': 'DB 이름',
            'db_user': 'DB 사용자',
            'db_password': 'DB 비밀번호',
        }
        help_texts = {
            'slug': 'URL에 사용될 영문 식별자 (소문자, 하이픈만 사용 가능)',
        }


class CustomUserForm(forms.ModelForm):
    """관세사 사용자 추가 폼"""
    password = forms.CharField(
        label='비밀번호',
        initial='init123',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'value': 'init123',
            'readonly': 'readonly'
        }),
        help_text='기본 비밀번호: init123'
    )

    class Meta:
        model = CustomUser
        fields = ['customs_code', 'customs_name', 'password']
        widgets = {
            'customs_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '5자리 관세사부호 (예: 6N001)',
                'maxlength': '5'
            }),
            'customs_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '관세사명 (예: A관세사)'
            }),
        }
        labels = {
            'customs_code': '관세사부호',
            'customs_name': '관세사명',
        }

    def clean_customs_code(self):
        customs_code = self.cleaned_data.get('customs_code')
        if len(customs_code) != 5:
            raise forms.ValidationError('관세사부호는 5자리여야 합니다.')
        return customs_code


class DeclarationForm(forms.ModelForm):
    """신고서 추가/수정 폼"""
    class Meta:
        model = Declaration
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '신고서명 (예: 수입신고서)'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '신고서 코드 (예: IMPORT, EXPORT)',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': '신고서 설명',
                'rows': 3
            }),
        }
        labels = {
            'name': '신고서명',
            'code': '신고서 코드',
            'description': '설명',
        }
        help_texts = {
            'code': 'API나 외부 시스템에서 사용할 고유 코드 (필수, 중복 불가)',
        }
