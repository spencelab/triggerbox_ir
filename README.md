# Goal: maintain compatibility with old machines (ROS1 ubuntu 16) for now. 

Functionality: when the IR beam is broken, a servo swivels slightly to make it harder for rat to grasp. A "reset" button on the box moves the servo back to center and re-arms the sensing.

# Wiring

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

