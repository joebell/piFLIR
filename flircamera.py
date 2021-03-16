import os
import PySpin
import sys

class FlirSystem:

    def __init__(self):
        # Initialize library and get the version
        self.system = PySpin.System.GetInstance()
        self.version = self.system.GetLibraryVersion()
        print('Spinnaker Library version: %d.%d.%d.%d' % (self.version.major, self.version.minor, self.version.type, self.version.build))

        # Get the cameras
        self.cam_list = self.system.GetCameras()
        print('Detected %d cameras.' % (len(self.cam_list)))
        self.cameras = []
        for cam in self.cam_list:
            self.cameras.append(FlirCamera(cam))

    def __del__(self):
        for camera in self.cameras:
            del camera
        self.cameras = []
        self.cam_list.Clear()
        self.system.ReleaseInstance()

class FlirCamera:
    def __init__(self, cam):
        self.cam = cam
        cam.Init()
        self.nodemap = cam.GetNodeMap()
        self.triggerCmd = None
        self.defaultSettings()

    def defaultSettings(self):
        self.configureTrigger(TriggerType.SOFTWARE)
        self.setExposure(5000) # us
        self.setPixelFormat(PySpin.PixelFormat_Mono8)
        self.setLineMode('Line2','Output')
        self.setAcquisitionMode('Continuous')
        self.checkOtherValues()

    def configureTrigger(self, triggerType):
        configure_trigger(self.cam, triggerType)    
        node_softwaretrigger_cmd = PySpin.CCommandPtr(self.nodemap.GetNode('TriggerSoftware'))
        if not PySpin.IsAvailable(node_softwaretrigger_cmd) or not PySpin.IsWritable(node_softwaretrigger_cmd):
            print('Unable to execute trigger. Aborting...')
            self.triggerCmd = None
        else:
            self.triggerCmd = node_softwaretrigger_cmd

    def getSerialNumber(self):
        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)
        return device_serial_number

    def setExposure(self, exposureTime):
        if self.cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to disable automatic exposure. Aborting...')
            return False
        self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        print('Automatic exposure disabled...')
        if self.cam.ExposureTime.GetAccessMode() != PySpin.RW:
            print('Unable to set exposure time. Aborting...')
            return False
        # Ensure desired exposure time does not exceed the maximum
        exposureTime = min(self.cam.ExposureTime.GetMax(), exposureTime)
        self.cam.ExposureTime.SetValue(exposureTime)
        print('Shutter time set to %s us...\n' % exposureTime)

    def setPixelFormat(self, pixFormat):
        # Set pixel format to Mono8
        if self.cam.PixelFormat.GetAccessMode() == PySpin.RW:
            self.cam.PixelFormat.SetValue(pixFormat)
            print('Pixel format set to %s...' % self.cam.PixelFormat.GetCurrentEntry().GetSymbolic())
        else:
            print('Pixel format not available...')

    def setLineMode(self, line, mode):
        print('LineSelector')
        node_line_selector = PySpin.CEnumerationPtr(self.nodemap.GetNode('LineSelector'))
        entry_line_selector_line_1 = node_line_selector.GetEntryByName(line)
        line_selector_line_1 = entry_line_selector_line_1.GetValue()
        node_line_selector.SetIntValue(line_selector_line_1)
        print(self.cam.LineSelector.GetCurrentEntry().GetSymbolic())

        print('LineMode')
        node_line_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('LineMode'))
        entry_output = node_line_mode.GetEntryByName(mode)
        value_output = entry_output.GetValue()
        node_line_mode.SetIntValue(value_output)
        print(self.cam.LineMode.GetCurrentEntry().GetSymbolic())

    def setAcquisitionMode(self, mode):
        # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False
        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(mode)
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                node_acquisition_mode_continuous):
            print('Unable to set acquisition mode. Aborting...')
            return False
        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
        print('Acquisition mode set.')

    def checkOtherValues(self):
        cam = self.cam
        print('IspEnable')
        print(cam.IspEnable.GetValue())
        print('BinningHorizontal')
        print(cam.BinningHorizontal.GetValue())
        print('BinningVertical')
        print(cam.BinningVertical.GetValue())
        print('DecimationHorizontal')
        print(cam.DecimationHorizontal.GetValue())
        print('DecimationVertical')
        print(cam.DecimationVertical.GetValue())
        print('AdcBitDepth')
        print(cam.AdcBitDepth.GetCurrentEntry().GetSymbolic())
        print('TriggerDelay (min = 11 us)')
        print(cam.TriggerDelay.GetValue())

    def stop(self):
        self.cam.EndAcquisition()

    def __del__(self):
        self.cam.DeInit()
        del self.cam

class TriggerType:
    SOFTWARE = 1
    HARDWARE = 2

def configure_trigger(cam, triggerType):
    """
    This function configures the camera to use a trigger. First, trigger mode is
    set to off in order to select the trigger source. Once the trigger source
    has been selected, trigger mode is then enabled, which has the camera
    capture only a single image upon the execution of the chosen trigger.

     :param cam: Camera to configure trigger for.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """
    result = True

    print('*** CONFIGURING TRIGGER ***\n')

    print('Note that if the application / user software triggers faster than frame time, the trigger may be dropped / skipped by the camera.\n')
    print('If several frames are needed per trigger, a more reliable alternative for such case, is to use the multi-frame mode.\n\n')

    if triggerType == TriggerType.SOFTWARE:
        print('Software trigger chosen ...')
    elif triggerType == TriggerType.HARDWARE:
        print('Hardware trigger chose ...')

    try:
        # Ensure trigger mode off
        # The trigger must be disabled in order to configure whether the source
        # is software or hardware.
        nodemap = cam.GetNodeMap()
        node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
        if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
            print('Unable to disable trigger mode (node retrieval). Aborting...')
            return False

        node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
            print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())
        print('Trigger mode disabled...')

        # Set TriggerSelector to FrameStart
        # For this example, the trigger selector should be set to frame start.
        # This is the default for most cameras.
        node_trigger_selector= PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSelector'))
        if not PySpin.IsAvailable(node_trigger_selector) or not PySpin.IsWritable(node_trigger_selector):
            print('Unable to get trigger selector (node retrieval). Aborting...')
            return False

        node_trigger_selector_framestart = node_trigger_selector.GetEntryByName('FrameStart')
        if not PySpin.IsAvailable(node_trigger_selector_framestart) or not PySpin.IsReadable(
                node_trigger_selector_framestart):
            print('Unable to set trigger selector (enum entry retrieval). Aborting...')
            return False
        node_trigger_selector.SetIntValue(node_trigger_selector_framestart.GetValue())
        print('Trigger selector set to frame start...')

        # Select trigger source
        # The trigger source must be set to hardware or software while trigger
        # mode is off.
        node_trigger_source = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSource'))
        if not PySpin.IsAvailable(node_trigger_source) or not PySpin.IsWritable(node_trigger_source):
            print('Unable to get trigger source (node retrieval). Aborting...')
            return False

        if triggerType == TriggerType.SOFTWARE:
            node_trigger_source_software = node_trigger_source.GetEntryByName('Software')
            if not PySpin.IsAvailable(node_trigger_source_software) or not PySpin.IsReadable(
                    node_trigger_source_software):
                print('Unable to set trigger source (enum entry retrieval). Aborting...')
                return False
            node_trigger_source.SetIntValue(node_trigger_source_software.GetValue())
            print('Trigger source set to software...')

        elif triggerType == TriggerType.HARDWARE:
            node_trigger_source_hardware = node_trigger_source.GetEntryByName('Line0')
            if not PySpin.IsAvailable(node_trigger_source_hardware) or not PySpin.IsReadable(
                    node_trigger_source_hardware):
                print('Unable to set trigger source (enum entry retrieval). Aborting...')
                return False
            node_trigger_source.SetIntValue(node_trigger_source_hardware.GetValue())
        print('Trigger source set to hardware...')

        # Turn trigger mode on
        # Once the appropriate trigger source has been set, turn trigger mode
        # on in order to retrieve images using the trigger.
        node_trigger_mode_on = node_trigger_mode.GetEntryByName('On')
        if not PySpin.IsAvailable(node_trigger_mode_on) or not PySpin.IsReadable(node_trigger_mode_on):
            print('Unable to enable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())
        print('Trigger mode turned back on...')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result

def reset_trigger(nodemap):
    """
    This function returns the camera to a normal state by turning off trigger mode.
  
    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True
        node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
        if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
            print('Unable to disable trigger mode (node retrieval). Aborting...')
            return False

        node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
            print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

        print('Trigger mode disabled...')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result

