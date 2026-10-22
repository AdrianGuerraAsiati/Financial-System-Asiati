# Conectar Google Sheets sin consola

## Uso
En Cartera → Fuentes y calidad, una persona con rol super_administrador o ti pulsa Conectar Google Sheets. Autoriza a Google a leer las hojas y regresa a ASIATI. El token de renovación se conserva cifrado en PostgreSQL, por empresa. El botón se convierte en Reconectar Google Sheets, y Probar conexión verifica el acceso. Nadie necesita hacer login con gcloud en Lightsail para reconectar.

## Configuración inicial por TI (una sola vez)
1. Crear aplicación de tipo Web en Google Cloud Console / Google Auth Platform, habilitar Sheets API, configurar pantalla de consentimiento y usuarios autorizados (preferiblemente Internal para Workspace).
2. Registrar el URI de retorno exacto: https://financial.asiaticorp.com/api/v1/integrations/google-sheets/oauth/callback
3. Instalar en un gestor seguro de configuración de backend las variables GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET y GOOGLE_OAUTH_REDIRECT_URI. Poner GOOGLE_OAUTH_TOKEN_KEY estable, aleatorio, 32+ caracteres. Nunca poner esos secretos en Git ni en el navegador.
4. Conservar para Cartera CARTERA_SHEETS_EMPRESA_ID, CARTERA_SHEETS_SPREADSHEET_ID y los tres rangos configurados. Esta primera versión no cambia el documento ni sus rangos desde la interfaz.
5. Ejecutar migración 0036_google_sheets_oauth mediante el flujo habitual del deploy tras CI.

Una aplicación NO puede registrar su propio cliente de Google OAuth sin una configuración administrativa inicial de TI. Esa configuración se hace una vez, y las reconexiones posteriores son desde el navegador.

## Controles
- Scope restringido a spreadsheets.readonly, sin escritura ni acceso general a Drive.
- Acceso a reconexión limitado a roles super_administrador y ti, por permiso específico google_sheets.conectar; token cifrado con Fernet.
- Estado aleatorio vinculado a empresa y usuario, de un solo uso, máximo diez minutos, con PKCE S256.
- El flujo se inicia únicamente con sesión ASIATI vigente y origen HTTPS del mismo sitio; se vincula al usuario autorizado y a su empresa.
- El retorno desde Google usa cookie temporal de 10 minutos, firmada con HMAC, HttpOnly, Secure y SameSite=Lax solo para la ruta exacta del callback. La sesión principal de ASIATI conserva SameSite=Strict y no viaja desde Google. Se vuelve a verificar que el usuario iniciador siga activo y autorizado.
- Auditoría de conexión y desconexión, y restauración de error de credenciales como HTTP 503 con instrucción de reconexión.
- Inventario Drive usa una integración independiente que no se modifica.
- No se modifica Cartera, pagos, movimientos ni saldos.

## Fuera del alcance de esta entrega
El módulo Compras y la selección/cambio de ID y rangos de hojas mediante UI. Es una ampliación posterior al primer flujo que resuelve la expiración de autenticación de Cartera.
