#include <WiFi.h>
#include <WebServer.h>
#include "ArrayList.h"
#include <ESP32Servo.h>

#include <Wire.h>
#include "MS5837.h"

struct DepthPacket {
  double depth;
  double pressure;
  unsigned long Time;
};
DepthPacket mySensorData;
ArrayList<DepthPacket> mySensorDataList;

struct PIDControl {
  unsigned long time;
  unsigned long prevTime;
  int timeStep;
  double depth;
  double error;
  double integral;
  double derivative;
  double control;
};

bool needCollectPIDData = true;
ArrayList<PIDControl> myPIDControlList;

//PIN assignment
const int MOTOR_IN1 = 15;
const int MOTOR_IN2 = 33;
const int SERVO_PIN = 32;

Servo myServo; // Servo Initialization/setup
MS5837 sensor;

unsigned long maxProfilingTime = 15*1000; //15seconds; 60*1000 milliseconds
int profilingCount = 0;
String ctrlCommand = "";
String msg;
String companyName = "EX01";

// Pids initialization
double p = 0.5;
double i = 0.01;
double d = 0.1;
double targetDepth=2.5;
double targetDepthTolerance=0.2;
double prevError=0.0;
unsigned long prevTime=0;
double integral=0.0;
double derivative=0.0;
double error=0.0;
double control=0.0;
double depth=0;
int secondsUpOrDown = 5;
double startDepth = 0.2;

//ESP32 as Access Point (AP), ie., its own local WiFi network
const char* ssid = "JHS_POD";  // Local network SSID
const char* password = "Porsche911!";        // Local network password
const int Wi_Fi_CHANNEL = 6; //1, 6, 11
String Wi_Fi_IP;

//Web Server to handle requests from clients to control the float
WebServer webServer(80);

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Wire.begin();
  
  // Initialize pressure sensor
  // Returns true if initialization was successful
  // We can't continue with the rest of the program unless we can initialize the sensor
  while (!sensor.init()) {
    Serial.println("Init failed!");
    Serial.println("Are SDA/SCL connected correctly?");
    Serial.println("Blue Robotics Bar30: White=SDA, Green=SCL");
    Serial.println("\n\n\n");
    delay(5000);
  }

  // .init sets the sensor model for us but we can override it if required.
  // Uncomment the next line to force the sensor model to the MS5837_30BA.
  sensor.setModel(MS5837::MS5837_02BA);
  sensor.setFluidDensity(1000); // kg/m^3 (freshwater, 1029 for seawater)

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);

  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);

  ESP32PWM::allocateTimer(0);
  // ESP32PWM::allocateTimer(1);
  // ESP32PWM::allocateTimer(2);
  // ESP32PWM::allocateTimer(3);
  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 1000, 2000);

  // Create WiFi network Access Point
  WiFi.softAP(ssid, password, Wi_Fi_CHANNEL);
  Serial.println("Wi-Fi Network Created");
  Wi_Fi_IP = WiFi.softAPIP().toString();
  Serial.println("IP Address: " + Wi_Fi_IP);

  // Configure Web Server Routes
  webServer.on("/data", handleDataRequest);
  webServer.on("/ctrl", handleControlRequest);
  webServer.on("/piddata", handlePIDDataRequest);
  webServer.begin();
  Serial.println("Web Server Started");
}

void loop() {
  //check if any control command
  webServer.handleClient();
  delay(100);
  sensor.read();
  Serial.println(sensor.depth());
}

// Send Sensor Data as plain text
void handleDataRequest() {
  Serial.println("Preparing data payload to be sent ...");
  
  //multiple lines format
  String dataPayload = "";
  for (int i = 0; i<mySensorDataList.size(); i++) {
    if (i != 0)
      dataPayload += "\n";
    DepthPacket data = mySensorDataList.get(i);
    dataPayload += getDataPacketString(data);
  }
  webServer.send(200, "text/plain", dataPayload);
  Serial.println("Data payload is sent.");
};

// Send Sensor Data as JSON
void handleControlRequest() {
  String msg;
  Serial.println("Processing control request...");

  if (webServer.hasArg("command"))
  {
    ctrlCommand = webServer.arg("command");
    Serial.println(ctrlCommand);

    if (ctrlCommand == "START") {  
      profilingCount++;
      mySensorDataList.clear();
      myPIDControlList.clear();
      p = webServer.arg("p").toDouble();
      i = webServer.arg("i").toDouble();
      d = webServer.arg("d").toDouble();
      prevTime = millis();
      msg = "Received START command with pid(" + webServer.arg("p") + ", " + webServer.arg("i") + ", " + webServer.arg("d") + "). Profiling " + String(profilingCount) + " starts...";
      Serial.println(msg);
      webServer.send(200, "text/plain", msg);
      profiling();
      msg = "Profiling is finished."; //may have error for send response the 2nd time at the end of this function. TODO - test
    }
    else if (ctrlCommand == "STATUS") {
      mySensorData = readData();
      msg = getDataPacketString(mySensorData) + " p " + String(p) + " i " + String(i) + " d " + String(d);
    }
    else if (ctrlCommand == "UP") {
      secondsUpOrDown = webServer.arg("seconds").toDouble();
      digitalWrite(MOTOR_IN2, HIGH);
      digitalWrite(MOTOR_IN1, LOW);
      delay(secondsUpOrDown * 1000);
      digitalWrite(MOTOR_IN2, LOW);
      msg = "Going UP for " + String(secondsUpOrDown) + " seconds.";
    }
    else if (ctrlCommand == "DOWN") {
      secondsUpOrDown = webServer.arg("seconds").toDouble();
      digitalWrite(MOTOR_IN1, HIGH);
      digitalWrite(MOTOR_IN2, LOW);
      delay(secondsUpOrDown * 1000);
      digitalWrite(MOTOR_IN1, LOW);
      msg = "Going DOWN for " + String(secondsUpOrDown) + " seconds.";
    }
    else if (ctrlCommand.startsWith("DEPLOYFLAPS")){
      myServo.write(59);
      msg = "Deploying Flaps";
    }
    else if (ctrlCommand.startsWith("RETRACTFLAPS")){
      myServo.write(90);
      msg = "Retracting Flaps";
    }
    else if (ctrlCommand == "STOP"){
      digitalWrite(MOTOR_IN1, LOW);
      digitalWrite(MOTOR_IN2, LOW);
      msg = "Stopped pump.";
    }
    else if (ctrlCommand == "RESET"){
      Serial.println("Reset starting now...");
      ESP.restart();
    }
    else if (ctrlCommand == "GETCONFIG"){
      mySensorData = readData();
      msg = "{" + getQuotedFieldName("Company Name") + getQuotedString(companyName)
        +", " + getQuotedFieldName("Max Profiling Time") + String(maxProfilingTime / 1000)
        +", " + getQuotedFieldName("Target Depth Tolerance") + String(targetDepthTolerance)
        +", " + getQuotedFieldName("Current Depth") + String(mySensorData.depth)
        +", " + getQuotedFieldName("Float ESP32 IP") + getQuotedString(Wi_Fi_IP)
        + "}";
    }
    else if (ctrlCommand == "SETCONFIG"){
      if (webServer.arg("Company Name") != "" &&
        webServer.arg("Max Profiling Time").toInt() != 0 &&
        webServer.arg("Target Depth Tolerance").toDouble() != 0
        ) {
        companyName = webServer.arg("Company Name");
        maxProfilingTime = webServer.arg("Max Profiling Time").toInt() * 1000;
        targetDepthTolerance = webServer.arg("Target Depth Tolerance").toDouble();
        Serial.print(companyName + " " + String(maxProfilingTime) + " " + String(targetDepthTolerance));
        msg = "Config settings are updated.";
      }
      else 
        msg = "Invalid values in sent config settings.";
    }
    else {
      msg = "Command " + ctrlCommand + " received. But it is not coded yet.";
    }
    webServer.send(200, "text/plain", msg);
    Serial.println(msg);
  }
};

void profiling() {
  double timeStep;  
  mySensorData = readData();
  startDepth = mySensorData.depth; //read before profiling
  unsigned long profilingStartTime = millis();
  int totalTimeAtTarget = 0;
  int now;

  integral = 0;
  prevError = 0;
  prevTime = millis();
  
  double max_integral = 0.5 / i; //based on i parameter
  while (true) {
    //safety measure
    if (millis() - profilingStartTime > maxProfilingTime) {
      abortProfiling();    //TODO, uncomment once finish testing packets
      return;
    }

    collectData(); //depth is set in collectData() function
    now = millis();
    error = targetDepth - depth;
    //no PID needed to maintain the depth if else continue lines are uncommented
    if (abs(error) <= targetDepthTolerance) {
      totalTimeAtTarget += (now - prevTime)/1000;
      if (totalTimeAtTarget > 45)
        break; //go out of while loop if the float at target depth for more than 45 seconds
      // else
      //   continue;
    }    

    //PID control
    timeStep = (now - prevTime)/1000.0; //in seconds
    integral += error * timeStep;
    integral = constrain(integral, -1*max_integral, max_integral);
    if (timeStep > 0)
      derivative = (error - prevError)/timeStep;
    else
      derivative = 0;
    control = p * error + i * integral + d * derivative;
    control = constrain(control, -1, 1);
    prevError = error;
    prevTime = now;
    
    if (needCollectPIDData)
      collectPIDControlData(now, prevTime, timeStep, depth, error, integral, derivative, control);

    if (control > 0){ // adjustment going down
      digitalWrite(MOTOR_IN1, HIGH);
      digitalWrite(MOTOR_IN2, LOW);
    }
    else if (control < 0){ // adjustment going up
      digitalWrite(MOTOR_IN2, HIGH);
      digitalWrite(MOTOR_IN1, LOW);
    }

    delay(500); //collect data every second
  }
 
  //after 45 second maintaining at target depth, go up
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, HIGH);
  do {    
    collectData();
    delay(500); //collect data every second
  }
  while (depth >= startDepth + 1.0); 
  digitalWrite(MOTOR_IN2, LOW);

  do {    
    collectData();
    delay(500); //collect data every second
  }
  while (depth >= startDepth + 0.2); 
}

//go up without collecting data
void abortProfiling() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, HIGH);
  do {
    mySensorData = readData();
    depth = mySensorData.depth;
    delay(1000);
  }
  while (depth >= startDepth); //tolerance default 0.2    
  digitalWrite(MOTOR_IN2, LOW);
}

void collectData() {
  Serial.println("reading sensor...");
  unsigned long collectStartTime = millis();

  do {
    mySensorData = readData(); 
    //safety measure
    if (millis() - collectStartTime > 3000) {
      abortProfiling();    //TODO, uncomment once finish testing packets
      return;
    }
    delay(500);
  }  while(mySensorData.depth < -1 || mySensorData.depth > 4);

  mySensorDataList.add(mySensorData);
  getDataPacketString(mySensorData);
  depth = mySensorData.depth;
}

DepthPacket readData() {
  DepthPacket data;
  sensor.read();
  data.depth = sensor.depth();
  data.pressure = sensor.pressure();
  data.Time = millis()/1000;
  Serial.print(data.depth);
  return data;
};

String getDataPacketString(DepthPacket data){
  String s = companyName + " " + String(data.Time) + " s " + String(data.pressure) + " kpa " + String(data.depth) + " m";
  Serial.println(s);
  return s;
};

String getQuotedString(String s){
  return "\"" + s + "\"";
}

String getQuotedFieldName(String s) {
  return "\"" + s + "\":";
}

void collectPIDControlData(unsigned long now, unsigned long prevTime, int timeStep, double depth, double error, double integral, double derivative, double control){
  //time, timestep, depth, error, integral, derivative, control
  PIDControl myPIDControl;
  myPIDControl.time = now;
  myPIDControl.prevTime = prevTime;
  myPIDControl.timeStep = timeStep;
  myPIDControl.depth = depth;
  myPIDControl.error = error;
  myPIDControl.integral = integral;
  myPIDControl.derivative = derivative;
  myPIDControl.control = control;
  myPIDControlList.add(myPIDControl);
}

// Send Sensor Data as plain text
void handlePIDDataRequest() {
  Serial.println("Preparing data payload to be sent ...");
  
  //multiple lines format
  String dataPayload = "";
  String record;
  for (int i = 0; i<myPIDControlList.size(); i++) {
    if (i != 0)
      dataPayload += "\n";
    PIDControl data = myPIDControlList.get(i);
    record = "{" + getQuotedFieldName("Time") + String(data.time)
      +", " + getQuotedFieldName("Prev Time") + String(data.prevTime)
      +", " + getQuotedFieldName("Time Step") + String(data.timeStep)
      +", " + getQuotedFieldName("Depth") + String(data.depth)
      +", " + getQuotedFieldName("Error") + String(data.error)
      +", " + getQuotedFieldName("Integral") + String(data.integral)
      +", " + getQuotedFieldName("Derivative") + String(data.derivative)
      +", " + getQuotedFieldName("Control") + String(data.control)
      + "}";
    dataPayload += record;
  }
  webServer.send(200, "text/plain", dataPayload);
  Serial.println("PID payload is sent.");
};