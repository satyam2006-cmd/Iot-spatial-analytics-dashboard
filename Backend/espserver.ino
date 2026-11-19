#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include "wifi_secrets.h"

ESP8266WebServer server(80);

const int MQ135_PIN = A0;

unsigned long lastReadTime = 0;
const unsigned long readInterval = 2000;

int mq135Value = 0;
int sequenceNumber = 0;

void readSensor()
{
    if (millis() - lastReadTime >= readInterval)
    {
        lastReadTime = millis();

        mq135Value = analogRead(MQ135_PIN);
        sequenceNumber++;

        Serial.print("MQ-135 ADC: ");
        Serial.println(mq135Value);
    }
}

void handleRoot()
{
    String page = "<html><head>";
    page += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    page += "<title>MQ-135 Monitor</title></head><body>";
    page += "<h2>ESP8266 MQ-135 Sensor</h2>";
    page += "<p>Live ADC: <span id='adc'>Loading...</span></p>";
    page += "<script>";
    page += "setInterval(()=>{fetch('/data').then(r=>r.json()).then(d=>";
    page += "document.getElementById('adc').innerText=d.mq135_adc);},2000);";
    page += "</script></body></html>";

    server.send(200, "text/html", page);
}

void handleData()
{
    String json = "{";

    json += "\"valid\":true,";
    json += "\"device\":\"ESP8266\",";
    json += "\"sensor\":\"MQ-135\",";
    json += "\"sequence\":" + String(sequenceNumber) + ",";
    json += "\"uptime_ms\":" + String(millis()) + ",";
    json += "\"mq135_adc\":" + String(mq135Value);

    json += "}";

    server.send(200, "application/json", json);
}

void handleStatus()
{
    server.send(200, "application/json",
                "{\"status\":\"online\"}");
}

void setup()
{
    Serial.begin(115200);

    pinMode(MQ135_PIN, INPUT);

    WiFi.begin(ssid, password);

    Serial.print("Connecting to WiFi");

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("WiFi Connected!");

    Serial.print("ESP8266 IP Address: ");
    Serial.println(WiFi.localIP());

    // Initial sensor reading
    mq135Value = analogRead(MQ135_PIN);

    server.on("/", handleRoot);
    server.on("/data", handleData);
    server.on("/status", handleStatus);

    server.begin();

    Serial.println("HTTP Server Started");
}

void loop()
{
    readSensor();
    server.handleClient();
}
