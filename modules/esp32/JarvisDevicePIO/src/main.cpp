#include <Arduino.h>
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

// WiFi Credentials
const char* ssid = "Ismail-Kv";
const char* password = "RaniagencieS";

// Pin Definitions
const int PIN_RED1 = 2;
const int PIN_RED2 = 4;
const int PIN_BLUE = 5;

WebServer server(80);

// Helper to send JSON responses
void sendJsonResponse(int code, String message, bool success = true) {
  String json = "{\"success\":" + String(success ? "true" : "false") + ",\"message\":\"" + message + "\"}";
  server.send(code, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  
  pinMode(PIN_RED1, OUTPUT);
  pinMode(PIN_RED2, OUTPUT);
  pinMode(PIN_BLUE, OUTPUT);
  
  digitalWrite(PIN_RED1, LOW);
  digitalWrite(PIN_RED2, LOW);
  digitalWrite(PIN_BLUE, LOW);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected. IP: " + WiFi.localIP().toString());

  // Root / Ping
  server.on("/", HTTP_GET, []() {
    sendJsonResponse(200, "Jarvis Hardware v2.0 Online");
  });

  // Dynamic Control Route (POST /control?dev=red1&state=on)
  server.on("/control", HTTP_POST, []() {
    if (!server.hasArg("dev") || !server.hasArg("state")) {
      sendJsonResponse(400, "Missing dev or state args", false);
      return;
    }
    
    String dev = server.arg("dev");
    bool state = (server.arg("state") == "on");
    int targetPin = -1;

    if (dev == "red1") targetPin = PIN_RED1;
    else if (dev == "red2") targetPin = PIN_RED2;
    else if (dev == "blue") targetPin = PIN_BLUE;

    if (targetPin != -1) {
      digitalWrite(targetPin, state ? HIGH : LOW);
      sendJsonResponse(200, dev + " turned " + (state ? "on" : "off"));
    } else {
      sendJsonResponse(404, "Unknown device ID", false);
    }
  });

  // Individual Legacy Routes
  auto handleLight = [](int pin, String name, bool state) {
    digitalWrite(pin, state ? HIGH : LOW);
    sendJsonResponse(200, name + " turned " + (state ? "on" : "off"));
  };

  server.on("/red1/on", HTTP_POST, [=]() { handleLight(PIN_RED1, "Red 1", true); });
  server.on("/red1/off", HTTP_POST, [=]() { handleLight(PIN_RED1, "Red 1", false); });
  server.on("/red2/on", HTTP_POST, [=]() { handleLight(PIN_RED2, "Red 2", true); });
  server.on("/red2/off", HTTP_POST, [=]() { handleLight(PIN_RED2, "Red 2", false); });
  server.on("/blue/on", HTTP_POST, [=]() { handleLight(PIN_BLUE, "Blue", true); });
  server.on("/blue/off", HTTP_POST, [=]() { handleLight(PIN_BLUE, "Blue", false); });

  // Group Routes
  server.on("/all/on", HTTP_POST, [=]() {
    digitalWrite(PIN_RED1, HIGH); digitalWrite(PIN_RED2, HIGH); digitalWrite(PIN_BLUE, HIGH);
    sendJsonResponse(200, "All lights on");
  });
  server.on("/all/off", HTTP_POST, [=]() {
    digitalWrite(PIN_RED1, LOW); digitalWrite(PIN_RED2, LOW); digitalWrite(PIN_BLUE, LOW);
    sendJsonResponse(200, "All lights off");
  });

  // Legacy Manual Routes (for user curl scripts)
  server.on("/light/on", HTTP_POST, [=]() {
    digitalWrite(PIN_RED1, HIGH); digitalWrite(PIN_RED2, HIGH); digitalWrite(PIN_BLUE, HIGH);
    sendJsonResponse(200, "All lights turned on (Legacy)");
  });
  server.on("/light/off", HTTP_POST, [=]() {
    digitalWrite(PIN_RED1, LOW); digitalWrite(PIN_RED2, LOW); digitalWrite(PIN_BLUE, LOW);
    sendJsonResponse(200, "All lights turned off (Legacy)");
  });
  server.on("/blue_light/on", HTTP_POST, [=]() {
    digitalWrite(PIN_BLUE, HIGH);
    sendJsonResponse(200, "Blue light turned on (Legacy)");
  });
  server.on("/blue_light/off", HTTP_POST, [=]() {
    digitalWrite(PIN_BLUE, LOW);
    sendJsonResponse(200, "Blue light turned off (Legacy)");
  });

  // Unified Status
  server.on("/status", HTTP_GET, []() {
    String json = "{";
    json += "\"red1\":\"" + String(digitalRead(PIN_RED1) ? "on" : "off") + "\",";
    json += "\"red2\":\"" + String(digitalRead(PIN_RED2) ? "on" : "off") + "\",";
    json += "\"blue\":\"" + String(digitalRead(PIN_BLUE) ? "on" : "off") + "\"";
    json += "}";
    server.send(200, "application/json", json);
  });

  server.begin();
}

void loop() {
  server.handleClient();
}
