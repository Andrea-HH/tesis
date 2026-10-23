"""Exportación09 protegida por la auditoría10; los originales quedan privados.

El exportador09 original completo está en la instantánea privada. Este punto de
entrada público ya no puede sobrescribir la tesis con una salida no revisada.
"""
from tesis_enasem.quality_outputs import export_public
if __name__=='__main__':
    print(export_public())
