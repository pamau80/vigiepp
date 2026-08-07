/**
 * VigiEPP ALARM v1.0 — ESP32 DevKit V1
 *
 * Endpoints (GET o POST):
 *   /alarma  → sirena + baliza roja
 *   /ok      → apaga alarma (baliza verde si cableás NC2→verde)
 *   /status  → JSON de estado
 *   /        → ayuda
 *
 * Pines (como en el diagrama):
 *   GPIO25 → Relé IN1 (sirena)
 *   GPIO26 → Relé IN2 (baliza roja)
 *
 * Cableado baliza 2 colores con 1 relé:
 *   COM2 ← 12V+
 *   NO2  → Rojo+
 *   NC2  → Verde+   (verde encendido en reposo /ok)
 *   Negro baliza → GND 12V
 */

#include <WiFi.h>
#include <WebServer.h>

// ====== CONFIGURÁ ESTO ======
const char* WIFI_SSID = "TU_WIFI";
const char* WIFI_PASS = "TU_CLAVE";
// ============================

#define RELAY_SIRENA 25
#define RELAY_BALIZA 26

// Relés activos en HIGH (módulos optoacoplados típicos). Si el tuyo es activo-LOW, invertí.
#define RELAY_ON  HIGH
#define RELAY_OFF LOW

WebServer server(80);
bool alarmaActiva = false;
unsigned long alarmaHasta = 0;
const unsigned long ALARMA_MS = 8000;  // auto-apagado de sirena (baliza sigue hasta /ok)

void setAlarma(bool on) {
  alarmaActiva = on;
  digitalWrite(RELAY_SIRENA, on ? RELAY_ON : RELAY_OFF);
  digitalWrite(RELAY_BALIZA, on ? RELAY_ON : RELAY_OFF);
  if (on) {
    alarmaHasta = millis() + ALARMA_MS;
  } else {
    alarmaHasta = 0;
    digitalWrite(RELAY_SIRENA, RELAY_OFF);
  }
}

void handleRoot() {
  String ip = WiFi.localIP().toString();
  String html = F("<!DOCTYPE html><html><body style='font-family:sans-serif'>");
  html += F("<h1>VigiEPP Alarm</h1>");
  html += "<p>IP: <b>" + ip + "</b></p>";
  html += F("<p><a href='/alarma'>/alarma</a> · <a href='/ok'>/ok</a> · <a href='/status'>/status</a></p>");
  html += F("<p>En VigiEPP → Informes → Notificaciones → URL: http://");
  html += ip;
  html += F("</p></body></html>");
  server.send(200, "text/html", html);
}

void handleAlarma() {
  setAlarma(true);
  server.send(200, "application/json", "{\"ok\":true,\"action\":\"alarma\",\"source\":\"VigiEPP\"}");
}

void handleOk() {
  setAlarma(false);
  server.send(200, "application/json", "{\"ok\":true,\"action\":\"ok\",\"source\":\"VigiEPP\"}");
}

void handleStatus() {
  String j = "{\"ok\":true,\"alarma\":";
  j += alarmaActiva ? "true" : "false";
  j += ",\"ip\":\"";
  j += WiFi.localIP().toString();
  j += "\",\"rssi\":";
  j += String(WiFi.RSSI());
  j += "}";
  server.send(200, "application/json", j);
}

void handleVigiEpp() {
  // Compatible con POST JSON { "kind": "access_deny" | "access_allow" | ... }
  String body = server.arg("plain");
  body.toLowerCase();
  if (body.indexOf("access_allow") >= 0 || body.indexOf("\"allow\":true") >= 0) {
    setAlarma(false);
    server.send(200, "application/json", "{\"ok\":true,\"action\":\"ok\"}");
    return;
  }
  if (body.indexOf("access_deny") >= 0 || body.indexOf("non_compliant") >= 0 ||
      body.indexOf("unknown_face") >= 0 || body.indexOf("alarma") >= 0) {
    setAlarma(true);
    server.send(200, "application/json", "{\"ok\":true,\"action\":\"alarma\"}");
    return;
  }
  server.send(400, "application/json", "{\"ok\":false,\"detail\":\"kind desconocido\"}");
}

void setup() {
  pinMode(RELAY_SIRENA, OUTPUT);
  pinMode(RELAY_BALIZA, OUTPUT);
  setAlarma(false);

  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/alarma", HTTP_GET, handleAlarma);
  server.on("/alarma", HTTP_POST, handleAlarma);
  server.on("/ok", HTTP_GET, handleOk);
  server.on("/ok", HTTP_POST, handleOk);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/vigiepp", HTTP_POST, handleVigiEpp);
  server.begin();
}

void loop() {
  server.handleClient();
  // Apaga solo la sirena tras ALARMA_MS; la baliza roja sigue hasta /ok
  if (alarmaActiva && alarmaHasta && (long)(millis() - alarmaHasta) >= 0) {
    digitalWrite(RELAY_SIRENA, RELAY_OFF);
    alarmaHasta = 0;
  }
}
