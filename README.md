# Goal: maintain compatibility with old machines (ROS1 ubuntu 16) for now. 

Functionality: when the IR beam is broken, a servo swivels slightly to make it harder for rat to grasp. A "reset" button on the box moves the servo back to center and re-arms the sensing.

# Wiring
FINAL:
9: CAMTRIG OUTPUT
13: LED OUTPUT - TO BUTTON LED
4: IR SENSOR INPUT
5: PWM SERVO OUTPUT

The camera trigger pin is 9

Not sure what pins we used for the push buttons - let's use Lauren and Harshita's box. Have the buttons now to add. Can use a hole for a 3 pin connector?

## IR Breakbeam:

https://www.adafruit.com/product/2168

Emitter: 2 wires:
5V for more range, GND, draws 20 mA.

Sensor: 3 wires:
GND, 5V (whichever logic lev using), yellow/white goes to digital pin.

The receiver is open collector which means that you do need a pull up resistor. Most microcontrollers have the ability to turn on a built in pull up resistor. If you do not, connect a 10K resistor between the white wire of the receiver and the red wire.

EG On an Arduino, we'll connect the signal (yellow/white) pin to Digital #4

```C
/* 
  IR Breakbeam sensor demo!
*/

#define LEDPIN 13
  // Pin 13: Arduino has an LED connected on pin 13
  // Pin 11: Teensy 2.0 has the LED on pin 11
  // Pin  6: Teensy++ 2.0 has the LED on pin 6
  // Pin 13: Teensy 3.0 has the LED on pin 13

#define SENSORPIN 4

// variables will change:
int sensorState = 0, lastState=0;         // variable for reading the pushbutton status

void setup() {
  // initialize the LED pin as an output:
  pinMode(LEDPIN, OUTPUT);      
  // initialize the sensor pin as an input:
  pinMode(SENSORPIN, INPUT);     
  digitalWrite(SENSORPIN, HIGH); // turn on the pullup
  
  Serial.begin(9600);
}

void loop(){
  // read the state of the pushbutton value:
  sensorState = digitalRead(SENSORPIN);

  // check if the sensor beam is broken
  // if it is, the sensorState is LOW:
  if (sensorState == LOW) {     
    // turn LED on:
    digitalWrite(LEDPIN, HIGH);  
  } 
  else {
    // turn LED off:
    digitalWrite(LEDPIN, LOW); 
  }
  
  if (sensorState && !lastState) {
    Serial.println("Unbroken");
  } 
  if (!sensorState && lastState) {
    Serial.println("Broken");
  }
  lastState = sensorState;
}
```

## Servo

PWM Pins:
UNO (R3 and earlier), Nano, Mini
3, 5, 6, 9, 10, 11

3 wires...
PWR, GND, PWM...

Total pins if shared:

PWR, GND, IRSENSOR, SERVO

But probably want servo on a separate lead really...
3 pin to IR sensor, 3 pin to servo?
Split the PWR and GND on IR SENSOR?
Can use a BNC wired to power for the IR emitter...
