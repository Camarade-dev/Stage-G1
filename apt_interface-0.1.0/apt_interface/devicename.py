from device import Device
from pydantic import BaseModel, field_validator, Field, ValidationInfo
from pydantic_yaml import parse_yaml_file_as
from apt_interface import VALID_BAUDRATES
from struct import pack
from typing import Literal, Annotated

 
class DeviceNameConfig(BaseModel):
    """Description du fichier yaml"""
 
    name: str = "KPZ101_default_controller"
 
	# remplacez xx par les deux premiers chiffre du numéro de série du device
    serial_nm: Annotated[str, Field(pattern=r"^29.*")]
    baudrate: VALID_BAUDRATES = 115200
 
 
class DeviceName():
    pass
 
class DeviceName():
 
    def __init__(self, config_file="config_devicename.yaml") -> None:
        self.conf = parse_yaml_file_as(DeviceNameConfig, config_file)
 
        self.dev = Device(self.conf.serial_nm, self.conf.baudrate)
 
    def __enter__(self) -> DeviceName:
        self.dev.begin_connection()
        # ajouter des fonction à appeller au début de la connection
        return self
    
    def identify(self) -> bool:
        """MGMSG_MOD_IDENTIFY"""
 
		# Les paramètres devraients marcher sur la plupart des appareils
        return self.dev.write(0x0223, 2, 0x00)
 
 
    def __exit__(self, *exc_info) -> None:
	    # Ajouter des fonctions à appeller avant que la connexion s'arrête
        self.dev.end_connection()
 
if __name__ == "__main__":
    with DeviceName() as dev:
        dev.identify()