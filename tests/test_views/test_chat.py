"""
Tests para el módulo de Chat con IA (Señor SAM / Gemini).
Cubre: autenticación, validaciones, respuesta exitosa, fallback sin API key.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

URL = reverse('core:chat_ayuda')


@pytest.mark.django_db
class TestChatAyuda:

    def test_requiere_autenticacion(self, client):
        response = client.post(URL, data=json.dumps({'pregunta': 'hola'}),
                               content_type='application/json')
        assert response.status_code == 302
        assert '/login/' in response['Location']

    def test_solo_acepta_post(self, authenticated_client):
        response = authenticated_client.get(URL)
        assert response.status_code == 405

    def test_pregunta_vacia_retorna_400(self, authenticated_client):
        response = authenticated_client.post(URL, data=json.dumps({'pregunta': '   '}),
                                             content_type='application/json')
        assert response.status_code == 400
        assert 'error' in response.json()

    def test_pregunta_muy_larga_retorna_400(self, authenticated_client):
        response = authenticated_client.post(URL, data=json.dumps({'pregunta': 'x' * 601}),
                                             content_type='application/json')
        assert response.status_code == 400

    def test_sin_api_key_retorna_fallback(self, authenticated_client):
        with patch('core.views.chat.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = ''
            response = authenticated_client.post(URL, data=json.dumps({'pregunta': 'hola'}),
                                                 content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert 'respuesta' in data
        assert 'soporte@sammetrologia.com' in data['respuesta']

    def test_respuesta_exitosa_de_gemini(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.text = '¡Hola! Soy SAM, tu asistente.'
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch('core.views.chat.settings') as mock_settings, \
             patch('google.genai.Client', return_value=mock_client_instance):
            mock_settings.GEMINI_API_KEY = 'fake-key'
            response = authenticated_client.post(URL,
                data=json.dumps({'pregunta': '¿Cómo agrego un equipo?'}),
                content_type='application/json')

        assert response.status_code == 200
        assert 'respuesta' in response.json()

    def test_error_gemini_retorna_fallback(self, authenticated_client):
        with patch('core.views.chat.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = 'fake-key'
            with patch('google.genai.Client') as mock_client:
                mock_client.side_effect = Exception('API error')
                response = authenticated_client.post(URL,
                    data=json.dumps({'pregunta': 'hola'}),
                    content_type='application/json')

        assert response.status_code == 200
        assert 'respuesta' in response.json()

    def test_historial_se_recibe_correctamente(self, authenticated_client):
        """El endpoint acepta historial sin explotar aunque Gemini falle."""
        historial = [
            {'tipo': 'usuario', 'texto': 'hola'},
            {'tipo': 'bot', 'texto': 'hola, soy SAM'},
        ]
        with patch('core.views.chat.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = ''
            response = authenticated_client.post(URL,
                data=json.dumps({'pregunta': 'y ahora?', 'historial': historial}),
                content_type='application/json')
        assert response.status_code == 200
