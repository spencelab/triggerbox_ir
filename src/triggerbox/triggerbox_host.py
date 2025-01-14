#!/usr/bin/env python
import argparse
import numpy as np
import time

import roslib; roslib.load_manifest('triggerbox')

import rospy

from triggerbox.api import TriggerboxAPI
from triggerbox.msg import TriggerClockModel, AOutVolts, AOutRaw, AOutConfirm, \
     TriggerClockMeasurement
from triggerbox.srv import SetFramerate, SetFramerateResponse
from triggerbox.triggerbox_device import TriggerboxDevice

import std_msgs

def _make_ros_topic(base, other):
    if base == '~':
        return base+other

    #ensure no start slash and one trailing slash
    if base[0] == '/':
        base = base[1:]
    if base[-1] == '/':
        base = base[:-1]

    return base + '/' + other

class TriggerboxHost(TriggerboxDevice, TriggerboxAPI):
    '''an in-process version of the triggerbox client with identical API'''
    def __init__(self, device,ros_topic_base='~'):

        self._gain = np.nan
        self._offset = np.nan
        self._expected_framerate = None

        self.pub_time = rospy.Publisher(
                                _make_ros_topic(ros_topic_base,'time_model'),
                                TriggerClockModel)
        self.pub_rate = rospy.Publisher(
                                _make_ros_topic(ros_topic_base,'expected_framerate'),
                                std_msgs.msg.Float32,
                                latch=True)
        self.pub_raw = rospy.Publisher(
                                _make_ros_topic(ros_topic_base,'raw_measurements'),
                                TriggerClockMeasurement)
        self.pub_aout_confirm = rospy.Publisher(
                                _make_ros_topic(ros_topic_base,'aout_confirm'),
                                AOutConfirm)

        super(TriggerboxHost,self).__init__(device)

        rospy.Subscriber(
                _make_ros_topic(ros_topic_base,'set_triggerrate'),
                std_msgs.msg.Float32,
                self._on_set_triggerrate)
        rospy.Subscriber(
                _make_ros_topic(ros_topic_base,'pause_and_reset'),
                std_msgs.msg.Float32,
                self._on_pause_and_reset)
        rospy.Subscriber(
                _make_ros_topic(ros_topic_base,'aout_volts'),
                AOutVolts,
                self._on_aout_volts)
        rospy.Subscriber(
                _make_ros_topic(ros_topic_base,'aout_raw'),
                AOutRaw,
                self._on_aout_raw)

        rospy.Service(
                _make_ros_topic(ros_topic_base,'set_framerate'),
                SetFramerate,
                self._on_set_framerate_service)

        # emit expected frame rate every 5 seconds
        rospy.Timer(rospy.Duration(5.0), self._on_emit_framerate)

    def _on_set_triggerrate(self,_msg):
        rospy.loginfo('triggerbox_host: _on_set_triggerrate %s'%_msg.data)
        self.set_triggerrate(_msg.data)

    def _on_pause_and_reset(self,_msg):
        rospy.loginfo('triggerbox_host: _on_pause_and_reset %s'%_msg.data)
        self.pause_and_reset(_msg.data)

    def _on_aout_volts(self,_msg):
        rospy.loginfo('triggerbox_host: _on_aout_volts %s'%_msg)
        self.set_aout_ab_volts(_msg.aout0,_msg.aout1)

    def _on_aout_raw(self,_msg):
        rospy.loginfo('triggerbox_host: _on_aout_raw %s'%_msg)
        self.set_aout_ab_raw(_msg.aout0,_msg.aout1)

    def _on_set_framerate_service(self, req):
        self.set_frames_per_second_blocking(req.data)
        return SetFramerateResponse()

    def _on_emit_framerate(self, _=None):
        if self._expected_framerate is not None:
            self.pub_rate.publish(self._expected_framerate)

    #Callbacks from the underlying hardware
    def _notify_framerate(self, expected_trigger_rate):
        self._expected_framerate = expected_trigger_rate
        self.pub_rate.publish(self._expected_framerate)
        self._api_callback(self.framerate_callback, expected_trigger_rate)

    def _notify_clockmodel(self, gain, offset):
        self._gain = gain
        self._offset = offset
        self.pub_time.publish(self._gain, self._offset)
        self._api_callback(self.clockmodel_callback, gain, offset)

    def _notify_clock_measurement(self, start_timestamp, pulsenumber, fraction_n_of_255, stop_timestamp):
        if fraction_n_of_255 > 255:
            #occasionally, when changing framerates, and due to the async
            #and out-of-order nature of comms with the hardware, we gen a
            #fraction value that exceeds 255 here. Ignore it.
            #If a similar bogus value made it into the model, it will
            #eventually be filtered out anyway
            rospy.logerr("triggerbox_host: invalid raw clock measurment. fraction %s exceeds 255" % fraction_n_of_255)
            return

        self.pub_raw.publish(start_timestamp, pulsenumber, fraction_n_of_255, stop_timestamp)
        self._api_callback(self.clock_measurement_callback, start_timestamp, pulsenumber, fraction_n_of_255, stop_timestamp)

    def _notify_aout_confirm(self, pulsenumber, fraction_n_of_255, aout0, aout1):
        if fraction_n_of_255 > 255:
            #occasionally, when changing framerates, and due to the async
            #and out-of-order nature of comms with the hardware, we gen a
            #fraction value that exceeds 255 here. Ignore it.
            rospy.logerr("triggerbox_host: invalid raw clock measurment. fraction %s exceeds 255" % fraction_n_of_255)
            return

        self.pub_aout_confirm.publish(pulsenumber, fraction_n_of_255, aout0, aout1)

    def _notify_fatal_error(self, msg):
        rospy.logfatal(msg)
        rospy.signal_shutdown(msg)
        self._api_callback(self.fatal_error_callback, msg)

    def _notify_connected(self, name, device):
        rospy.loginfo("triggerbox_host: connected to %r on device %r" % (name, device))
        self._api_callback(self.connected_callback, name, device)

    #ClientAPI
    def have_estimate(self):
        return (not np.isnan(self._gain)) and (not np.isnan(self._offset))

    def wait_for_estimate(self):
        while not self.have_estimate():
            rospy.loginfo('triggerbox_host: waiting for clockmodel estimate')
            time.sleep(0.5)
        rospy.loginfo('triggerbox_host: got clockmodel estimate')

    def timestamp2framestamp(self, timestamp ):
        return (timestamp-self._offset)/self._gain

    def framestamp2timestamp(self, framestamp ):
        return framestamp*self._gain + self._offset

    def get_frames_per_second(self,wait_for_valid=True):
        while True:
            result = self._expected_framerate
            if result is not None:
                break
            if not wait_for_valid:
                break
            time.sleep(0.01)
        return result

    def set_frames_per_second(self,value):
        rospy.loginfo('triggerbox_host: setting FPS to %s' % value)
        self.set_triggerrate(value)

    def set_frames_per_second_blocking(self, *args, **kwargs):
        while not self.connected:
            rospy.loginfo('triggerbox_host: waiting for connection')
            time.sleep(0.5)
        self.set_frames_per_second(*args, **kwargs)

    def synchronize(self, pause_duration_seconds=2 ):
        rospy.loginfo('triggerbox_host: synchronizing')
        self.pause_and_reset(pause_duration_seconds)

if __name__=='__main__':
    rospy.init_node('triggerbox_host')
    parser = argparse.ArgumentParser('triggerbox_host')
    parser.add_argument('--device', '-d', dest='device')
    args = parser.parse_args()
    if args.device:
        tb = TriggerboxHost(args.device)
    else:
        tb = TriggerboxHost('/dev/ttyUSB0')
    tb.set_frames_per_second_blocking(25.0)
    tb.wait_for_estimate()
    rospy.spin()
