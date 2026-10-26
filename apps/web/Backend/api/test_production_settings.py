import json
import logging
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from config.security import security_settings
from api.operational_logging import SafeJSONFormatter

class ProductionPolicyTests(SimpleTestCase):
    def production(self,**values):
        return security_settings({'DJANGO_ENV':'production','DJANGO_SECRET_KEY':'Synthetic-Only-For-Settings-Tests-0123456789-abcdefghijklmnop','DJANGO_ALLOWED_HOSTS':'app.example.invalid',**values})

    def test_secret_hosts_and_debug_required(self):
        for values in [{'DJANGO_ENV':'production'},{'DJANGO_ENV':'unexpected'}]:
            with self.assertRaises(ImproperlyConfigured):security_settings(values)
        for key,value in [('DJANGO_SECRET_KEY',''),('DJANGO_SECRET_KEY','django-insecure-'+'a'*60),('DJANGO_DEBUG','true'),('DJANGO_ALLOWED_HOSTS','*'),('DJANGO_ALLOWED_HOSTS','*.example.invalid'),('DJANGO_ALLOWED_HOSTS','.example.invalid'),('DJANGO_ALLOWED_HOSTS','')]:
            with self.subTest(key=key),self.assertRaises(ImproperlyConfigured):self.production(**{key:value})

    def test_secure_defaults_and_origins(self):
        s=self.production();self.assertFalse(s['DEBUG'])
        for key in ['SESSION_COOKIE_SECURE','CSRF_COOKIE_SECURE','SESSION_COOKIE_HTTPONLY','SECURE_SSL_REDIRECT','SECURE_CONTENT_TYPE_NOSNIFF']:self.assertTrue(s[key])
        self.assertFalse(s['CSRF_COOKIE_HTTPONLY']);self.assertEqual(s['CORS_ALLOWED_ORIGINS'],[]);self.assertEqual(s['SESSION_COOKIE_SAMESITE'],'Lax');self.assertEqual(s['SESSION_COOKIE_AGE'],28800);self.assertIsNone(s['SECURE_PROXY_SSL_HEADER']);self.assertEqual(s['SECURE_HSTS_SECONDS'],60)
        for key,value in [('DJANGO_CORS_ALLOW_ALL_ORIGINS','true'),('DJANGO_CORS_ALLOWED_ORIGINS','http://app.example.invalid'),('DJANGO_CSRF_TRUSTED_ORIGINS','https://*.example.invalid'),('DJANGO_SESSION_COOKIE_SECURE','false'),('DJANGO_CSRF_COOKIE_SECURE','false'),('DJANGO_SECURE_SSL_REDIRECT','false')]:
            with self.subTest(key=key),self.assertRaises(ImproperlyConfigured):self.production(**{key:value})
        self.assertEqual(self.production(DJANGO_CSRF_TRUSTED_ORIGINS='https://app.example.invalid')['CSRF_TRUSTED_ORIGINS'],['https://app.example.invalid'])

    def test_development_legacy_preserved_explicit_prefix_wins(self):
        s=security_settings({});self.assertTrue(s['DEBUG']);self.assertFalse(s['SECURE_SSL_REDIRECT']);self.assertFalse(s['SESSION_COOKIE_SECURE']);self.assertEqual(s['PRIVATE_MEDIA_DELIVERY'],'django')
        s=security_settings({'DEBUG':'release','DJANGO_DEBUG':'true','SECRET_KEY':'dev-local'});self.assertTrue(s['DEBUG']);self.assertEqual(s['SECRET_KEY'],'dev-local')
        self.assertFalse(security_settings({'DEBUG':'release'})['DEBUG']);self.assertEqual(self.production(DJANGO_TRUST_PROXY='true')['SECURE_PROXY_SSL_HEADER'],('HTTP_X_FORWARDED_PROTO','https'))

    def test_logging_ignores_credentials_payload_and_exception(self):
        record=logging.LogRecord('django.request',logging.ERROR,'',0,'password=%s',('synthetic-secret',),None)
        record.password='secret';record.cookie='session';record.request={'body':'clinical-content'};record.exc_info=(ValueError,ValueError('clinical-private-exception'),None);record.status=403;record.user_id=17;record.event='request_outcome'
        data=json.loads(SafeJSONFormatter().format(record));self.assertEqual(data['status'],403);self.assertEqual(data['user_id'],17)
        for forbidden in ['synthetic-secret','session','clinical','password']:self.assertNotIn(forbidden,json.dumps(data))

    def test_production_api_error_redacts_internal_message_but_keeps_status(self):
        from django.test import RequestFactory, override_settings
        from django.http import JsonResponse
        from api.operational_logging import OperationalLogMiddleware
        request=RequestFactory().get('/api/muestras/1/segmentar/')
        middleware=OperationalLogMiddleware(lambda r:None)
        with override_settings(DJANGO_ENV='production'):
            response=middleware.process_response(request,JsonResponse({'error':'upstream http://private-host/ secret'},status=503))
            self.assertEqual(response.status_code,503)
            self.assertNotIn(b'private-host',response.content);self.assertNotIn(b'secret',response.content)
            self.assertEqual(json.loads(response.content)['code'],'SERVICE_UNAVAILABLE')
