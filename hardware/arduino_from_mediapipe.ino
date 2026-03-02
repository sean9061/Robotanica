#include <ESP32Servo.h>

Servo servo[3];
const int servo_pin[3] = {25, 26, 27};
uint8_t value[3];

void motor_speed(Servo &servo, uint8_t value){
  int speed = 180 * value / 255;
  servo.write(speed);
}

void setup() {
  for(int i=0;i<3;i++) servo[i].attach(servo_pin[i], 700, 2300);
  Serial.begin(115200);
}

void loop() {
  if (Serial.available() >= 4) {
    if(Serial.read() == 0xFF){
      Serial.readBytes(value, 3);
    }else{
      Serial.read();
    }

    
  }
  for(int i=0;i<3;i++){
      motor_speed(servo[i], value[i]);
    }
}
