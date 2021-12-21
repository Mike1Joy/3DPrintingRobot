# Copyright (c) 2021 Michael Joyce

# For use with Cura 4.x
# Place this script in C:\Program Files\Ultimaker Cura 4.x\plugins\PostProcessingPlugin\scripts

from ..Script import Script

class PrintWithRobot(Script):
    """Adds lines for turning digital pins on and off for printing with a robot.
    Designed for use with Universal Robots in Toolpath mode
    """

    def getSettingDataString(self):
        return """{
            "name": "Print with Robot",
            "key": "PrintWithRobot",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "ACV_pin":
                {
                    "label": "On/Off Pin",
                    "description": "Digital pin for turing extruder on (high) and off (low).",
                    "type": "int",
                    "minimum_value": "0",
                    "default_value": 0
                },
                "DIR_pin":
                {
                    "label": "Direction Pin",
                    "description": "Digital pin for extruding forwards (high) and backwards (low).",
                    "type": "int",
                    "minimum_value": "0",
                    "default_value": 1
                },
                "SPD_pin":
                {
                    "label": "Speed Pin",
                    "description": "Digital pin for extruding proportional to robot speed (high) or at set speed (low).",
                    "type": "int",
                    "minimum_value": "0",
                    "default_value": 2
                },
                "DWELL":
                {
                    "label": "Add Dwells",
                    "description": "Add a dwell when G0/G1 with E but no X, Y or Z movement. Eg 'G1 E-1.0'",
                    "type": "bool",
                    "default_value": false
                },
                "SET_SPEED":
                {
                    "label": "Stationary Feed Rate",
                    "description": "Feed rate (mm/s) for extruder when robot is stopped. This will determine the time the robot will dwell for when extruding and not moving.",
                    "unit": "mm/s",
                    "type": "float",
                    "minimum_value": "0",
                    "minimum_value_warning": "0.1",
                    "default_value": 15.0,
                    "enabled": "DWELL"
                },
                "DEBUG":
                {
                    "label": "Debug Comments",
                    "description": "Add comments after every line for debug purposes",
                    "type": "bool",
                    "default_value": false
                }
            }
        }"""

    def execute(self, data):
        ACV_pin = self.getSettingValueByKey("ACV_pin")
        DIR_pin = self.getSettingValueByKey("DIR_pin")
        SPD_pin = self.getSettingValueByKey("SPD_pin")
        DWELL = self.getSettingValueByKey("DWELL")
        SET_SPEED = self.getSettingValueByKey("SET_SPEED")
        DEBUG = self.getSettingValueByKey("DEBUG")

        HIGH = 62
        LOW = 63

        if ACV_pin is None or DIR_pin is None or SPD_pin is None:
            ACV_pin = 0
            DIR_pin = 1
            SPD_pin = 2

        if SET_SPEED <= 0:
            SET_SPEED = 15.0

        ACV_str = [f"M{LOW} P{ACV_pin} ;Robot Extruder active: Off\n", f"M{HIGH} P{ACV_pin} ;Robot Extruder active: On\n"]
        DIR_str = [f"M{LOW} P{DIR_pin} ;Robot Extruder direction: Backward\n", f"M{HIGH} P{DIR_pin} ;Robot Extruder direction: Forward\n"]
        SPD_str = [f"M{LOW} P{SPD_pin} ;Robot Extruder speed: Use set speed\n", f"M{HIGH} P{SPD_pin} ;Robot Extruder speed: Proportional to robot speed\n"]

        ACV_state = 0
        DIR_state = 0
        SPD_state = 0
        for layer_number, layer in enumerate(data):
            lines = layer.splitlines(keepends=True)
            for line in range(len(lines)):
                this_ACV_state = ACV_state
                this_DIR_state = DIR_state
                this_SPD_state = SPD_state

                E_value = 0
                Dwell_time = 0

                if any(G in lines[line] for G in ["G0","G1","G2","G3","G4","G28"]):
                    if "E" in lines[line]:
                        E_value = float(lines[line].split("E")[-1].split()[0])

                    if E_value == 0:
                        this_ACV_state = 0
                    else:
                        this_ACV_state = 1
                        if E_value < 0:
                            this_DIR_state = 0
                        else:
                            this_DIR_state = 1
                        
                        if any(move in lines[line] for move in ["X","Y","Z","A","B","C"]):
                            this_SPD_state = 1
                        else:
                            this_SPD_state = 0
                            Dwell_time = abs(E_value)/SET_SPEED
                    
                    # add lines to gcode in reverse order
                    if DWELL and Dwell_time > 0:
                        lines[line] = f"G4 P{Dwell_time:.5f} ;Robot Dwell\n" + lines[line]
                    if this_ACV_state != ACV_state:
                        ACV_state = this_ACV_state
                        lines[line] = ACV_str[this_ACV_state] + lines[line]
                    if this_DIR_state != DIR_state:
                        DIR_state = this_DIR_state
                        lines[line] = DIR_str[this_DIR_state] + lines[line]
                    if this_SPD_state != SPD_state:
                        SPD_state = this_SPD_state
                        lines[line] = SPD_str[this_SPD_state] + lines[line]
                    
                    if DEBUG:
                        dbug_str = f";ACV_state: {ACV_state}, DIR_state: {DIR_state}, SPD_state: {SPD_state}, E_value: {E_value}, Dwell_time: {Dwell_time}\n"
                        lines[line] += dbug_str
            
            data[layer_number] = "".join(lines)

        # Header and footer
        data[0] = f";Using Print with Robot post processing script:\n;  On/Off Pin: {ACV_pin}\n;  Direction Pin: {DIR_pin}\n;  Speed Pin: {SPD_pin}\n;  Add Dwell: {DWELL}\n;  Stationary Feed Rate: {SET_SPEED}\n;  Debug Comments: {DEBUG}\nM{LOW} P{ACV_pin} M{LOW} P{DIR_pin} M{LOW} P{SPD_pin} ;Turn all Robot pins off\n" + data[0]
        data[-1] += f"\nM{LOW} P{ACV_pin} M{LOW} P{DIR_pin} M{LOW} P{SPD_pin} ;Turn all Robot pins off\n"

        return data
