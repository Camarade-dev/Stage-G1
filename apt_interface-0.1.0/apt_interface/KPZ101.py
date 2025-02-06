print("=== DEBUG: LOADED MY CUSTOM KPZ101.PY VERSION ===")

from typing import Optional, Literal
from pydantic import BaseModel, Field, root_validator
from pydantic_yaml import parse_yaml_file_as
from struct import pack
from device import Device

class KPZ101Config(BaseModel):
    """Configuration du KPZ101 (Pydantic v2 compatible)"""

    name: str = "KPZ101_default_controller"
    # Pydantic v2 => on remplace `regex` par `pattern`
    serial_nm: str = Field(..., pattern=r"^29.*")  
    baudrate: int = 115200

    mode: Literal["open_loop", "closed_loop"] = "open_loop"

    # feedback_in doit être facultatif
    feedback_in: Optional[Literal["chann1", "chann2", "extin"]] = None

    voltage_limit: Literal[75, 100, 150] = 75

    @root_validator(pre=True)
    def handle_feedback(cls, values):
        """Si mode=closed_loop => feedback_in doit être spécifié.
           Sinon (open_loop) => on ignore feedback_in."""
        mode = values.get("mode", "open_loop")
        fb   = values.get("feedback_in")
        if mode == "closed_loop":
            if fb not in ("chann1", "chann2", "extin"):
                raise ValueError("In closed_loop mode, feedback_in must be 'chann1','chann2', or 'extin'.")
        else:
            # On force feedback_in à None en open_loop
            values["feedback_in"] = None
        return values

class KPZ101:
    """Classe de contrôle du KPZ101, adaptée pour open_loop ou closed_loop."""

    def __init__(self, config_file="config_KPZ.yaml") -> None:
        print("=== DEBUG: Ctor KPZ101 called ===")
        self.conf = parse_yaml_file_as(KPZ101Config, config_file)
        self.dev = Device(self.conf.serial_nm, self.conf.baudrate)

    def __enter__(self):
        self.dev.begin_connection()
        self.disable_output()
        self.set_io()
        self.set_mode()
        return self

    def __exit__(self, *exc_info):
        self.disable_output()
        self.dev.end_connection()

    def set_mode(self) -> None:
        mode_dict = {"open_loop": 0x03, "closed_loop": 0x04}
        self.dev.write(0x0640, 2, mode_dict[self.conf.mode])

    def set_io(self) -> None:
        v_lim_dict = {75: 0x01, 100: 0x02, 150: 0x03}
        v_lim = v_lim_dict[self.conf.voltage_limit]

        # Si feedback_in est None, c'est du open_loop => on met "extin" (0x03) ou un canal inactif
        if self.conf.feedback_in is None:
            a_in = 0x03
        else:
            a_in_dict = {"chann1": 0x01, "chann2": 0x02, "extin": 0x03}
            a_in = a_in_dict[self.conf.feedback_in]

        data = pack("HHHHH", 0x0001, v_lim, a_in, 0x0000, 0x0000)
        self.dev.write_with_data(0x07d4, 10, data)

    def enable_output(self) -> None:
        print("Warning High Voltage !!")
        self.dev.write(0x0210, 2, 0x01)

    def disable_output(self) -> None:
        self.dev.write(0x0210, 2, 0x02)

    def set_output_voltage(self, tension: float) -> None:
        if self.conf.mode != "open_loop":
            raise RuntimeError("set_output_voltage() requires open_loop mode.")
        if not (0 <= tension <= self.conf.voltage_limit):
            raise ValueError(f"Tension {tension}V out of range [0..{self.conf.voltage_limit}]")

        device_unit = 32767 / self.conf.voltage_limit
        device_value = int(tension * device_unit)
        data = pack("HH", 0x0001, device_value)
        self.dev.write_with_data(0x0643, 4, data)

    def set_position(self, pos: int) -> None:
        if self.conf.mode != "closed_loop":
            raise RuntimeError("set_position() requires closed_loop mode.")
        if not (0 <= pos <= 32767):
            raise ValueError("Position out of range [0..32767]")

        data = pack("Hh", 0x0001, pos)
        self.dev.write_with_data(0x0646, 4, data)
