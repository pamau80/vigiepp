# VigiEPP Alarm (ESP32)

Firmware y cableado para baliza + sirena controlados por VigiEPP.

## Flujo

```
Cámara → VigiEPP → GET http://IP_ESP32/alarma  (incumple)
                 → GET http://IP_ESP32/ok      (cumple)
```

## Configurar en VigiEPP

1. Informes → Notificaciones → Canales  
2. Activar **Hardware VigiEPP Alarm**  
3. URL: `http://IP_DEL_ESP32` (sin `/alarma`)  
4. Guardar → **Probar /alarma** y **Probar /ok**

**Importante:** el proceso que corre VigiEPP (PC local o edge) debe estar en la **misma red** que el ESP32. Si VigiEPP está solo en Railway (nube), no alcanzará la IP LAN del ESP32.

## Flash

1. Arduino IDE → placa **ESP32 Dev Module**  
2. Editar `WIFI_SSID` / `WIFI_PASS` en `vigiepp_alarm.ino`  
3. Subir sketch → abrir Monitor Serie 115200 → copiar IP

## Cableado resumido

| ESP32 | Relé |
|-------|------|
| 5V | VCC |
| GND | GND |
| GPIO25 | IN1 (sirena) |
| GPIO26 | IN2 (baliza) |

| Relé / 12V | Carga |
|------------|--------|
| COM1 ← 12V+ | NO1 → Sirena+ |
| COM2 ← 12V+ | NO2 → Rojo+ ; NC2 → Verde+ (opcional) |
| GND 12V | Sirena−, baliza negro, GND común con ESP32 |
