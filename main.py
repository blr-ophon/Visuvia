"""
Execute visuvia on GUI or CMD mode, which is a mode for just data transfer.
"""


# Standard library imports
import argparse
# Local imports
from visuvia.gui import root
from visuvia.mctp_comm import CommTask
from visuvia.utils.serial_ctrl import SerialCtrl
from visuvia.utils.data_registry import DataRegistry

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Define the --gui flag
    parser.add_argument('--gui', action='store_true', help='Use GUI mode')
    parser.add_argument('--cmd', action='store_true', help='Use CMD mode')

    args = parser.parse_args()

    data_registry = DataRegistry()
    serial_ctrl = SerialCtrl()

    if args.cmd:
        print("CMD mode")
        serial_ctrl.set_serial("/dev/ttyACM0", 115200, 2)
        task = CommTask(serial_ctrl, data_registry)
        task.start()

        running = True
        while running:
            command = input()
            match command:
                case "sync":
                    task.start_sync()
                case "request":
                    task.send_request()
                case "stop":
                    task.send_stop()
                    data_registry.save_data()
                    data_registry.clear_data()
                case "drop":
                    task.send_drop()
                case "exit":
                    running = False
                case _:
                    print(f"Unknown command: {command}")
    else:
        print("GUI mode")
        root.init()
