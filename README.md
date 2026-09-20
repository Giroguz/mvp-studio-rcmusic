# MVP Studio RCmusic

Aplicación para separar voces e instrumentos, con una interfaz orientada a DJs.

## Prototipo de interfaz

Abre `index.html` en Chrome o Edge para probar la carga de audio, reproducción, forma de onda y controles de mezcla.

## Motor IA local

La carpeta `backend` incluye una API preparada para Demucs. En Windows ejecuta `run_windows.bat`; en macOS/Linux ejecuta `run_mac_linux.sh`. La primera instalación descarga PyTorch y Demucs, por lo que requiere conexión a Internet y espacio libre. Después abre `index.html` y procesa una canción desde la interfaz.

El backend genera los stems WAV en `backend/jobs`. La versión actual conserva el prototipo visual; la integración completa del botón con la API y la exportación avanzada es la siguiente fase.
