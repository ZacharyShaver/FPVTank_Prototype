// wewbot
/*
For use with the Adafruit Motor Shield v2
---->	http://www.adafruit.com/products/1438
*/

#include <WiFi.h>
                                   #include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "utility/Adafruit_MS_PWMServoDriver.h"

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield();

// motors 
Adafruit_DCMotor * MR = AFMS.getMotor(1);
Adafruit_DCMotor * ML = AFMS.getMotor(2);

// states
int state = 0;

// Driving Globals
int accel = 30;
bool breaking = false;
uint8_t speedL = 0;
uint8_t speedR = 0;
uint8_t desiredL = 0;
uint8_t desiredR = 0;

// resting position 
int restX = 523;
int restY = 506;

// Joystick pin numbers
const int SW_pin = 2; // digital pin connected to switch output
const int X_pin = 0; // analog pin connected to X output
const int Y_pin = 1; // analog pin connected to Y output

// Testing
bool outputTesting = true;

// You can also make another motor on port M2
// Adafruit_DCMotor *myOtherMotor = AFMS.getMotor(2);
#include "wifi_secrets.h"  // untracked: copy wifi_secrets.example.h to wifi_secrets.h and fill it in
const char *ssid = WIFI_SSID;
const char *password = WIFI_PASSWORD;

void setup() {
  Serial.begin(115200); // set up Serial library at 9600 bps
  while (!Serial) {
    delay(100);
  }
  Serial.println("Adafruit Motorshield v2 - DC Motor test!");
  pinMode(SW_pin, INPUT);
  digitalWrite(SW_pin, HIGH);
  if (!AFMS.begin()) { // create with the default frequency 1.6KHz
    // if (!AFMS.begin(1000)) {  // OR with a different frequency, say 1KHz
    Serial.println("Could not find Motor Shield. Check wiring.");
    while (1);
  }
  Serial.println("Motor Shield found.");
}

void HandleControlInput(int Xin, int Yin) {
  int ForwardReverse = 1;
  int forwardSpeed = 0;

  // handle input from from forward joystick
  if (abs(restX - Xin) > 4) {
    breaking = false;
    if (Xin < restX) { //backwards
      if (outputTesting) Serial.println("Back");

      ForwardReverse = BACKWARD;
      forwardSpeed = 255 - ((float) Xin / (float) 512) * 255;
    } else { // forward                                                      
      if (outputTesting) Serial.println("Forward");

      ForwardReverse = FORWARD;
      forwardSpeed = 255 - ((1023 - (float) Xin) / (float) 512) * 255;
    }
  } else {
    breaking = true;
    desiredR = 0;
    desiredL = 0;
  }
  ML -> run(ForwardReverse);
  MR -> run(ForwardReverse);

  // handle input from side joystick
  if(abs(restY-Yin) > 4){
    
    if (Yin < restY) //left 
    {
      // far left 0 - 502 close to 0
      //Serial.print("Left");
      float scr = (restY - Yin) / restY;
      desiredR = (int)((float)forwardSpeed * scr);
      desiredL = forwardSpeed;
      /*
      if(breaking){ 
        desiredR = (int)((float)255*scr);
      }*/ 
    }else { // right
      //Serial.print("Right");
      float scr = (Yin- restY) / restY;
      desiredL = (int)((float)forwardSpeed * scr);
      desiredR = forwardSpeed;
    }

  }else {
    desiredL = desiredR = forwardSpeed;
  }

}

uint8_t Accelerate(uint8_t desired, uint8_t speed){
  if (!(desired == speed)) {
    if (desired - speed < 0) {
      speed = speed <= accel ? 0 : speed - accel;
    } else {
      speed = speed + accel > 255 ? 255 : speed + accel;
    }
  }
  return speed;
}

void HandleSpeedControl(int Xin, int Yin) {

  if (breaking) {
    desiredL = speedL = desiredR = speedR = 0;
  } else {
    //speedL = Accelerate(desiredL, speedL);
    //speedR = Accelerate(desiredR, speedR);
  }

  ML -> setSpeed(speedL);
  MR -> setSpeed(speedR);

  if (!breaking && outputTesting){
    Serial.println(desiredL);
    Serial.println(desiredR);

    Serial.println(Xin);
    Serial.println(Yin);
    Serial.println("\n");
  }
}


void loop() {
  breaking = false;
  //char receivedChar = Serial.read();
  int SWpin = digitalRead(SW_pin);
  int Xin = analogRead(X_pin);
  int Yin = analogRead(Y_pin);
  
  if (state == 0) {
    // handles input of joystick controller
    HandleControlInput(Xin, Yin);
    HandleSpeedControl(Xin, Yin);
  }

  delay(100);

}