# VigiEPP

Plataforma de **detección de EPP con IA** + **identificación de trabajadores** para faenas en Chile.

## Módulos

| Módulo | Uso |
|--------|-----|
| **Vivo** | Webcam, un canal RTSP o foto · portería / kiosk |
| **Masivo** | Hasta 16 canales NVR/DVR en paralelo · barrido EPP |
| **Equipos** | Conectar Dahua, Hikvision, Uniview · importar canales |
| **Personas** | Enrolamiento facial, RUT, QR cédula |
| **EPP** | Entrenar ropa de empresa (YOLO) |
| **Config** | Zonas, audio, privacidad Ley 21.719 |
| **Informes** | Safety Score, CSV, notificaciones |

## NVR / DVR (Dahua, Hikvision)

1. Ir a **Equipos**
2. Ingresar IP, usuario, contraseña y cantidad de canales
3. **Probar conexión** → genera URLs RTSP
4. **Importar a masivo** → aparecen en **Masivo**
5. **Iniciar barrido** → IA analiza cada canal

URLs generadas automáticamente:

- **Hikvision:** `rtsp://…/Streaming/Channels/101` (canal 1 principal)
- **Dahua:** `rtsp://…/cam/realmonitor?channel=1&subtype=0`

Requisito: VigiEPP **edge** en la misma red que el NVR (Render cloud no alcanza cámaras LAN).

## Desarrollo local

```bash
bash .cursor/install.sh   # primera vez
bash scripts/probar.sh      # VigiEPP :8000 + Forense :8001
```

Guía completa: **[docs/PROBAR.md](docs/PROBAR.md)**

PIN admin por defecto (solo dev): `vigiepp` · portería: `porteria`

## Despliegue

- **Edge faena:** `docker-compose up` o `start-edge.bat`
- **Cloud:** Render / Railway (demo; RTSP requiere edge)
