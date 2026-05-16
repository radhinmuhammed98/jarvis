#include <WiFi.h>
#include <WebServer.h>

// Replace with your actual network credentials
const char* ssid = "Ismail-Kv";
const char* password = "RaniagencieS";

// Pins
const int PIN_RED1 = 2;
const int PIN_RED2 = 4;
const int PIN_BLUE = 5;

// States
bool isRed1On = false;
bool isRed2On = false;
bool isBlueOn = false;

// Create WebServer object on port 80
WebServer server(80);

void setLight(int pin, bool state) {
  digitalWrite(pin, state ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);
  delay(100);

  // Initialize the light pins
  pinMode(PIN_RED1, OUTPUT);
  pinMode(PIN_RED2, OUTPUT);
  pinMode(PIN_BLUE, OUTPUT);
  
  setLight(PIN_RED1, false);
  setLight(PIN_RED2, false);
  setLight(PIN_BLUE, false);

  // Connect to Wi-Fi
  Serial.println("\nConnecting to Wi-Fi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // Base route
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/plain", "ESP32 Jarvis Multi-Light device online");
  });

  // RED 1 Routes
  server.on("/red1/on", HTTP_POST, []() {
    setLight(PIN_RED1, true);
    isRed1On = true;
    server.send(200, "text/plain", "Red Light 1 turned on");
  });
  server.on("/red1/off", HTTP_POST, []() {
    setLight(PIN_RED1, false);
    isRed1On = false;
    server.send(200, "text/plain", "Red Light 1 turned off");
  });
  server.on("/red1/status", HTTP_GET, []() {
    server.send(200, "text/plain", isRed1On ? "Red 1 is on" : "Red 1 is off");
  });

  // RED 2 Routes
  server.on("/red2/on", HTTP_POST, []() {
    setLight(PIN_RED2, true);
    isRed2On = true;
    server.send(200, "text/plain", "Red Light 2 turned on");
  });
  server.on("/red2/off", HTTP_POST, []() {
    setLight(PIN_RED2, false);
    isRed2On = false;
    server.send(200, "text/plain", "Red Light 2 turned off");
  });
  server.on("/red2/status", HTTP_GET, []() {
    server.send(200, "text/plain", isRed2On ? "Red 2 is on" : "Red 2 is off");
  });

  // BLUE Routes
  server.on("/blue/on", HTTP_POST, []() {
    setLight(PIN_BLUE, true);
    isBlueOn = true;
    server.send(200, "text/plain", "Blue Light turned on");
  });
  server.on("/blue/off", HTTP_POST, []() {
    setLight(PIN_BLUE, false);
    isBlueOn = false;
    server.send(200, "text/plain", "Blue Light turned off");
  });
  server.on("/blue/status", HTTP_GET, []() {
    server.send(200, "text/plain", isBlueOn ? "Blue is on" : "Blue is off");
  });

  // ALL RED LIGHTS Routes
  server.on("/red/on", HTTP_POST, []() {
    setLight(PIN_RED1, true);
    setLight(PIN_RED2, true);
    isRed1On = isRed2On = true;
    server.send(200, "text/plain", "Both red lights turned on");
  });
  server.on("/red/off", HTTP_POST, []() {
    setLight(PIN_RED1, false);
    setLight(PIN_RED2, false);
    isRed1On = isRed2On = false;
    server.send(200, "text/plain", "Both red lights turned off");
  });
  server.on("/red/status", HTTP_GET, []() {
    String res = (isRed1On && isRed2On) ? "Both reds are on" : (isRed1On || isRed2On ? "One red is on" : "Reds are off");
    server.send(200, "text/plain", res);
  });

  // ALL LIGHTS Routes
  server.on("/all/on", HTTP_POST, []() {
    setLight(PIN_RED1, true);
    setLight(PIN_RED2, true);
    setLight(PIN_BLUE, true);
    isRed1On = isRed2On = isBlueOn = true;
    server.send(200, "text/plain", "All lights turned on");
  });
  server.on("/all/off", HTTP_POST, []() {
    setLight(PIN_RED1, false);
    setLight(PIN_RED2, false);
    setLight(PIN_BLUE, false);
    isRed1On = isRed2On = isBlueOn = false;
    server.send(200, "text/plain", "All lights turned off");
  });
  server.on("/all/status", HTTP_GET, []() {
    String res = String("Red1: ") + (isRed1On?"ON":"OFF") + ", Red2: " + (isRed2On?"ON":"OFF") + ", Blue: " + (isBlueOn?"ON":"OFF");
    server.send(200, "text/plain", res);
  });

  // Legacy light route mapping to all
  server.on("/light/status", HTTP_GET, []() {
    String res = String("All system lights: ") + (isRed1On && isRed2On && isBlueOn ? "ALL ON" : "Mixed State");
    server.send(200, "text/plain", res);
  });

  // Diagnostic Blink Test
  server.on("/test", HTTP_GET, []() {
    server.send(200, "text/plain", "Starting Blink Test on Pins 2, 4, 5...");
    int pins[] = {PIN_RED1, PIN_RED2, PIN_BLUE};
    for(int i=0; i<3; i++) {
      setLight(pins[i], true);
      delay(500);
      setLight(pins[i], false);
      delay(500);
    }
  });

  // Pin Scanner / Dynamic Control
  server.on("/on", HTTP_GET, []() {
    if (server.hasArg("p")) {
      int p = server.arg("p").toInt();
      pinMode(p, OUTPUT);
      digitalWrite(p, HIGH);
      server.send(200, "text/plain", "Pin " + String(p) + " turned ON");
    } else {
      server.send(400, "text/plain", "Missing 'p' argument");
    }
  });

  server.on("/off", HTTP_GET, []() {
    if (server.hasArg("p")) {
      int p = server.arg("p").toInt();
      pinMode(p, OUTPUT);
      digitalWrite(p, LOW);
      server.send(200, "text/plain", "Pin " + String(p) + " turned OFF");
    } else {
      server.send(400, "text/plain", "Missing 'p' argument");
    }
  });

  server.onNotFound([]() {
    server.send(404, "text/plain", "Not Found");
  });

  server.begin();
  Serial.println("HTTP Server started");
}

void loop() {
  server.handleClient();
}
